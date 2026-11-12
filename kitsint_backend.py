
#!/usr/bin/env python3
"""
KITSINT: NIGHTFALL — updated, single-file edition

Local CSV search, dataset management, exports, watchlist, snapshots,
public RDAP lookups, and low-volume diagnostics for systems you own
or are explicitly authorized to test.

Dataset folder: datasets/
Input files:    users_part_*.csv
Combined file:  datasets/users_combined.csv (generated automatically)
Exports:        exports/
Database:       kitsint.db
Settings:       kitsint_settings.json
Watchlist:      kitsint_watchlist.json
Snapshot:       kitsint_snapshot.json

Privacy note:
- Use only synthetic or authorized dataset records.
- IP geolocation is approximate network-level information, not a person's
  location.
- The shared-IP account-linking/alt-account feature has been removed.
"""

import csv
import glob
import hashlib
import json
import os
import socket
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from ipaddress import ip_address

APP_NAME = "KITSINT"
APP_VERSION = "6.1 NIGHTFALL"
USER_AGENT = "KITSINT/6.1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
SETTINGS_FILE = os.path.join(BASE_DIR, "kitsint_settings.json")
DB_FILE = os.path.join(BASE_DIR, "kitsint.db")
WATCHLIST_FILE = os.path.join(BASE_DIR, "kitsint_watchlist.json")
SNAPSHOT_FILE = os.path.join(BASE_DIR, "kitsint_snapshot.json")
GEOLITE_FILE = os.path.join(BASE_DIR, "GeoLite2-City.mmdb")
COMBINED_DATASET_PATH = os.path.join(DATASETS_DIR, "users_combined.csv")
COMBINED_DATASET_TEMP = COMBINED_DATASET_PATH + ".tmp"

COMMON_PORTS = (21, 22, 80, 443, 8080)
DISPLAY_LIMIT = 100
THEMES = {
    "cyan": {"primary": "\033[96m", "secondary": "\033[95m", "success": "\033[92m",
             "warning": "\033[93m", "danger": "\033[91m", "muted": "\033[90m", "text": "\033[97m"},
    "purple": {"primary": "\033[95m", "secondary": "\033[96m", "success": "\033[92m",
               "warning": "\033[93m", "danger": "\033[91m", "muted": "\033[90m", "text": "\033[97m"},
    "red": {"primary": "\033[91m", "secondary": "\033[95m", "success": "\033[92m",
            "warning": "\033[93m", "danger": "\033[91m", "muted": "\033[90m", "text": "\033[97m"},
    "green": {"primary": "\033[92m", "secondary": "\033[96m", "success": "\033[92m",
              "warning": "\033[93m", "danger": "\033[91m", "muted": "\033[90m", "text": "\033[97m"},
}
RESET = "\033[0m"
BOLD = "\033[1m"
DEFAULT_SETTINGS = {
    "colors": True,
    "clear_screen": True,
    "show_timestamps": True,
    "theme": "cyan"
}
SETTINGS = DEFAULT_SETTINGS.copy()

RECORDS = []
LOADED_FILES = []
FILE_STATS = []
ID_INDEX = {}
USERNAME_INDEX = {}
IP_INDEX = {}
INVALID_ROWS = DUPLICATES = RECOVERED_ROWS = READ_FAILURES = 0
LAST_RESULTS = []
LAST_EXPORT_NAME = "KITSINT Results"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def paint(value, style="text", bold=False):
    value = str(value)
    if not SETTINGS.get("colors", True):
        return value
    theme = THEMES.get(SETTINGS.get("theme", "cyan"), THEMES["cyan"])
    text = f"{theme.get(style, theme['text'])}{value}{RESET}"
    return f"{BOLD}{text}" if bold else text


def line(char="─", width=68):
    print(paint(char * width, "muted"))


def clear_screen():
    if SETTINGS.get("clear_screen", True):
        os.system("cls" if os.name == "nt" else "clear")


def safe_input(prompt):
    try:
        return input(paint(prompt, "primary", True)).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        raise SystemExit(0)


def pause(message="Press ENTER to continue..."):
    try:
        input(paint(message, "muted"))
    except (KeyboardInterrupt, EOFError):
        raise SystemExit(0)


def panel(title):
    print()
    line("═")
    print(paint(f"  ◈  {title.upper()}", "primary", True))
    line("═")


def info(label, value, style="text"):
    print(f"  {str(label):<28}{paint(value, style)}")


def show_message(message, style="success"):
    print(f"\n  {paint('◆ ' + str(message), style)}")


def print_header():
    clear_screen()
    print()
    for art in (
        "  ██╗  ██╗██╗████████╗███████╗██╗███╗   ██╗████████╗",
        "  ██║ ██╔╝██║╚══██╔══╝██╔════╝██║████╗  ██║╚══██╔══╝",
        "  █████╔╝ ██║   ██║   ███████╗██║██╔██╗ ██║   ██║",
        "  ██╔═██╗ ██║   ██║   ╚════██║██║██║╚██╗██║   ██║",
        "  ██║  ██╗██║   ██║   ███████║██║██║ ╚████║   ██║",
        "  ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝",
    ):
        print(paint(art, "primary", True))
    print(paint("  N I G H T F A L L   //   C Y B E R   I N T E L", "secondary", True))
    print(paint(f"  VERSION {APP_VERSION}  |  LOCAL INTELLIGENCE TERMINAL", "muted"))


def status_bar():
    state = paint("ONLINE", "success") if RECORDS else paint("EMPTY", "warning")
    print()
    line()
    print(
        f"  DATASETS: {state}  {len(RECORDS):,} records   │   "
        f"FILES: {len(LOADED_FILES)}   │   {timestamp().split()[-1]}"
    )
    line()


def menu_item(number, title, description):
    print(f"  {paint('[' + str(number) + ']', 'primary', True)} {paint(title, 'text', True)}")
    print(f"       {paint(description, 'muted')}")


def format_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} GB"


def safe_filename(value):
    cleaned = "".join(c for c in str(value) if c.isalnum() or c in "-_")
    return cleaned[:60] or "KITSINT_export"


def save_last_results(name, rows):
    global LAST_RESULTS, LAST_EXPORT_NAME
    LAST_EXPORT_NAME = name
    LAST_RESULTS = [dict(row) for row in rows]


# ------------------------------ SETTINGS ------------------------------

def load_settings():
    global SETTINGS
    SETTINGS = DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key in ("colors", "clear_screen", "show_timestamps"):
                if isinstance(data.get(key), bool):
                    SETTINGS[key] = data[key]
            if data.get("theme") in THEMES:
                SETTINGS["theme"] = data["theme"]
    except (OSError, json.JSONDecodeError):
        pass


def save_settings():
    temp = SETTINGS_FILE + ".tmp"
    try:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(SETTINGS, f, indent=2)
        os.replace(temp, SETTINGS_FILE)
        return True
    except OSError as exc:
        show_message(f"Settings save failed: {exc}", "danger")
        return False


def settings_menu():
    global SETTINGS
    while True:
        print_header()
        panel("Appearance & Settings")
        info("ANSI COLORS", "ON" if SETTINGS["colors"] else "OFF")
        info("CLEAR SCREEN", "ON" if SETTINGS["clear_screen"] else "OFF")
        info("SHOW TIMESTAMPS", "ON" if SETTINGS["show_timestamps"] else "OFF")
        info("CURRENT THEME", SETTINGS["theme"].upper())
        print()
        menu_item("1", "Toggle colors", "Enable or disable ANSI colors")
        menu_item("2", "Toggle screen clearing", "Terminal display preference")
        menu_item("3", "Toggle timestamps", "Show or hide timestamps")
        menu_item("4", "Change theme", "Cyan, purple, red or green")
        menu_item("5", "Restore defaults", "Reset preferences")
        menu_item("0", "Return", "Back to dashboard")
        choice = safe_input("\nkitsint/settings > ").lower()

        if choice == "1":
            SETTINGS["colors"] = not SETTINGS["colors"]
        elif choice == "2":
            SETTINGS["clear_screen"] = not SETTINGS["clear_screen"]
        elif choice == "3":
            SETTINGS["show_timestamps"] = not SETTINGS["show_timestamps"]
        elif choice == "4":
            theme = safe_input("Choose theme (cyan/purple/red/green) > ").lower()
            if theme in THEMES:
                SETTINGS["theme"] = theme
            else:
                show_message("Unknown theme.", "warning")
        elif choice == "5":
            SETTINGS = DEFAULT_SETTINGS.copy()
        elif choice == "0":
            save_settings()
            return
        else:
            show_message("Invalid selection.", "warning")

        save_settings()


# ------------------------------ CSV NORMALIZATION ------------------------------

HEADER_ALIASES = {
    "index": "index", "idx": "index", "row": "index", "number": "index",
    "discordid": "discord_id", "userid": "discord_id", "id": "discord_id",
    "username": "username", "user": "username", "name": "username",
    "displayname": "username",
    "ip": "ip_address", "ipaddress": "ip_address", "ipaddr": "ip_address",
    "address": "ip_address",
    "timestamp": "timestamp", "createdat": "timestamp", "created": "timestamp",
    "date": "timestamp", "time": "timestamp", "when": "timestamp",
    "sourcefile": "source_file", "originfile": "source_file", "source": "source_file",
}


def normalize_header(value):
    return "".join(c for c in str(value).strip().lower() if c.isalnum())


def make_header_map(row):
    result = {}
    for pos, value in enumerate(row):
        canonical = HEADER_ALIASES.get(normalize_header(value))
        if canonical:
            result[canonical] = pos
    return result


def row_to_record(row, header_map=None):
    if header_map is None:
        values = [str(v).strip() for v in row[:5]]
        if len(values) < 5:
            return None
        idx, discord_id, username, ip_addr, created = values
        source_file = ""
    else:
        def get(key):
            pos = header_map.get(key)
            return str(row[pos]).strip() if pos is not None and pos < len(row) else ""

        idx = get("index")
        discord_id = get("discord_id")
        username = get("username")
        ip_addr = get("ip_address")
        created = get("timestamp")
        source_file = get("source_file")

    if not discord_id or not username:
        return None

    return {
        "index": idx,
        "discord_id": discord_id,
        "username": username,
        "ip_address": ip_addr,
        "timestamp": created,
        "source_file": source_file,
    }


def parse_csv_line(raw_line):
    try:
        return next(csv.reader([raw_line], strict=True), None), False, False
    except csv.Error:
        try:
            row = next(csv.reader([raw_line], strict=False), None)
            return (row, True, True) if row is not None else (None, True, False)
        except csv.Error:
            return None, True, False


# ------------------------------ INDEXES + DATABASE ------------------------------

def rebuild_indexes():
    global ID_INDEX, USERNAME_INDEX, IP_INDEX
    ID_INDEX, USERNAME_INDEX, IP_INDEX = {}, {}, {}

    for record in RECORDS:
        ID_INDEX.setdefault(record["discord_id"].casefold(), []).append(record)
        USERNAME_INDEX.setdefault(record["username"].casefold(), []).append(record)

        ip_value = record["ip_address"].casefold()
        if ip_value:
            IP_INDEX.setdefault(ip_value, []).append(record)


def db_connect():
    import sqlite3
    connection = sqlite3.connect(DB_FILE, timeout=20)
    connection.execute("PRAGMA busy_timeout=20000")
    return connection


def db_rebuild():
    import sqlite3
    temp_db = DB_FILE + ".tmp"

    try:
        if os.path.exists(temp_db):
            os.remove(temp_db)

        con = sqlite3.connect(temp_db)
        con.execute(
            "CREATE TABLE records ("
            "discord_id TEXT, username TEXT, ip_address TEXT, "
            "timestamp TEXT, source_file TEXT)"
        )
        con.executemany(
            "INSERT INTO records VALUES (?,?,?,?,?)",
            [
                (
                    r["discord_id"],
                    r["username"],
                    r["ip_address"],
                    r["timestamp"],
                    r.get("source_file", ""),
                )
                for r in RECORDS
            ],
        )
        con.execute("CREATE INDEX idx_discord ON records(discord_id)")
        con.execute("CREATE INDEX idx_username ON records(username)")
        con.execute("CREATE INDEX idx_ip ON records(ip_address)")

        try:
            con.execute(
                "CREATE VIRTUAL TABLE records_fts "
                "USING fts5(discord_id, username, ip_address)"
            )
            con.execute(
                "INSERT INTO records_fts "
                "SELECT discord_id, username, ip_address FROM records"
            )
        except sqlite3.OperationalError:
            pass

        con.commit()
        con.close()
        os.replace(temp_db, DB_FILE)
        return True

    except (OSError, sqlite3.Error) as exc:
        try:
            if os.path.exists(temp_db):
                os.remove(temp_db)
        except OSError:
            pass

        show_message(f"Database rebuild failed: {exc}", "warning")
        return False


def db_search(query, limit=DISPLAY_LIMIT):
    import sqlite3

    try:
        con = db_connect()
        like = f"%{query}%"
        rows = con.execute(
            "SELECT discord_id, username, ip_address, timestamp, source_file "
            "FROM records "
            "WHERE discord_id LIKE ? OR username LIKE ? OR ip_address LIKE ? "
            "LIMIT ?",
            (like, like, like, limit),
        ).fetchall()
        con.close()
        return rows
    except sqlite3.Error:
        return []


# ------------------------------ AUTO COMBINER + LOADER ------------------------------

def combine_dataset_files(source_files):
    """Combine source CSVs while preserving which source file each row came from."""
    if not source_files:
        return False, 0

    os.makedirs(DATASETS_DIR, exist_ok=True)
    count = 0

    try:
        with open(
            COMBINED_DATASET_TEMP,
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as out:
            writer = csv.writer(out)
            writer.writerow([
                "index", "discord_id", "username",
                "ip_address", "timestamp", "source_file"
            ])

            for source_path in source_files:
                header_map = None
                first = True

                with open(
                    source_path,
                    "r",
                    encoding="utf-8-sig",
                    errors="replace",
                    newline=""
                ) as src:
                    for raw in src:
                        if not raw.strip():
                            continue

                        row, _, _ = parse_csv_line(raw)
                        if not row:
                            continue

                        if first:
                            first = False
                            candidate = make_header_map(row)
                            if "discord_id" in candidate and "username" in candidate:
                                header_map = candidate
                                continue

                        record = row_to_record(row, header_map)
                        if not record:
                            continue

                        writer.writerow([
                            record["index"],
                            record["discord_id"],
                            record["username"],
                            record["ip_address"],
                            record["timestamp"],
                            os.path.basename(source_path),
                        ])
                        count += 1

        os.replace(COMBINED_DATASET_TEMP, COMBINED_DATASET_PATH)
        return True, count

    except (OSError, csv.Error, UnicodeError) as exc:
        try:
            if os.path.exists(COMBINED_DATASET_TEMP):
                os.remove(COMBINED_DATASET_TEMP)
        except OSError:
            pass

        show_message(f"CSV combine failed: {exc}", "warning")
        return False, 0


def load_datasets(show_summary=True):
    global RECORDS, LOADED_FILES, FILE_STATS
    global INVALID_ROWS, DUPLICATES, RECOVERED_ROWS, READ_FAILURES

    records, loaded, stats, seen = [], [], [], set()
    invalid_total = duplicate_total = recovered_total = failures = 0

    os.makedirs(DATASETS_DIR, exist_ok=True)
    sources = sorted(glob.glob(os.path.join(DATASETS_DIR, "users_part_*.csv")))

    if sources:
        ok, combined_count = combine_dataset_files(sources)
        csv_files = [COMBINED_DATASET_PATH] if ok else sources

        if show_summary and ok:
            info("AUTO-COMBINE", "COMPLETE", "success")
            info("SOURCE FILES", len(sources))
            info("COMBINED ROWS", f"{combined_count:,}")

    elif os.path.isfile(COMBINED_DATASET_PATH):
        csv_files = [COMBINED_DATASET_PATH]
    else:
        csv_files = []

    if show_summary:
        print_header()
        panel("Dataset Initialization")
        info("DATASET FILES FOUND", len(csv_files))

    for number, path in enumerate(csv_files, 1):
        filename = os.path.basename(path)
        valid = invalid = duplicates = recovered = unrecoverable = 0
        error_text = ""
        header_map, first = None, True

        if show_summary:
            print(paint(f"\n  [{number}/{len(csv_files)}] {filename}", "secondary"))

        try:
            with open(
                path,
                "r",
                encoding="utf-8-sig",
                errors="replace",
                newline=""
            ) as f:
                for raw in f:
                    if not raw.strip():
                        continue

                    row, parse_problem, was_recovered = parse_csv_line(raw)

                    if parse_problem:
                        if was_recovered:
                            recovered += 1
                            recovered_total += 1
                        else:
                            unrecoverable += 1

                    if not row:
                        invalid += 1
                        invalid_total += 1
                        continue

                    if first:
                        first = False
                        candidate = make_header_map(row)
                        if "discord_id" in candidate and "username" in candidate:
                            header_map = candidate
                            continue

                    record = row_to_record(row, header_map)
                    if not record:
                        invalid += 1
                        invalid_total += 1
                        continue

                    if not record.get("source_file"):
                        record["source_file"] = filename

                    key = (
                        record["discord_id"],
                        record["username"],
                        record["ip_address"],
                        record["timestamp"],
                    )

                    if key in seen:
                        duplicates += 1
                        duplicate_total += 1
                        continue

                    seen.add(key)
                    records.append(record)
                    valid += 1

            loaded.append(filename)

        except (OSError, UnicodeError) as exc:
            error_text = str(exc)
            failures += 1

        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0

        status = (
            "ERROR" if error_text
            else ("PARTIAL" if invalid or recovered or unrecoverable else "LOADED")
        )

        stats.append({
            "filename": filename,
            "size_bytes": size,
            "valid_records": valid,
            "invalid_rows": invalid,
            "duplicates": duplicates,
            "recovered_rows": recovered,
            "unrecoverable_rows": unrecoverable,
            "error": error_text,
            "status": status,
        })

        if show_summary:
            info("STATUS", status, "success" if status == "LOADED" else "warning")
            info("VALID RECORDS", valid)
            info("RECOVERED", recovered)
            info("SKIPPED", invalid)

            if error_text:
                info("ERROR", error_text, "danger")

    RECORDS, LOADED_FILES, FILE_STATS = records, loaded, stats
    INVALID_ROWS, DUPLICATES = invalid_total, duplicate_total
    RECOVERED_ROWS, READ_FAILURES = recovered_total, failures

    rebuild_indexes()

    if records:
        db_rebuild()

    if show_summary:
        panel("Load Summary")
        info("Files opened", len(loaded))
        info("Valid records", f"{len(records):,}", "success")
        info("Recovered rows", recovered_total)
        info("Skipped rows", invalid_total, "warning")
        info("Duplicates", duplicate_total)
        info("Read failures", failures)

    return records, loaded, invalid_total, duplicate_total


def reload_datasets():
    show_message("Reloading local datasets...", "secondary")
    load_datasets(True)


def dataset_manager():
    while True:
        print_header()
        panel("Dataset Manager")
        info("DATASET DIRECTORY", DATASETS_DIR)
        info("TOTAL RECORDS", f"{len(RECORDS):,}")

        if not FILE_STATS:
            show_message("No dataset files found.", "warning")

        for item in FILE_STATS:
            print()
            print(paint("  ◈ " + item["filename"], "primary", True))
            info("STATUS", item["status"])
            info("SIZE", format_size(item["size_bytes"]))
            info("VALID", item["valid_records"])
            info("SKIPPED", item["invalid_rows"])
            info("DUPLICATES", item["duplicates"])
            info("RECOVERED", item["recovered_rows"])

            if item["error"]:
                info("ERROR", item["error"], "danger")

        print()
        menu_item("R", "Reload datasets", "Read CSV files again")
        menu_item("0", "Return", "Back to dashboard")

        choice = safe_input("\nkitsint/datasets > ").lower()

        if choice == "r":
            reload_datasets()
            pause()
        elif choice == "0":
            return
        else:
            show_message("Invalid option.", "warning")
            time.sleep(0.5)


# ------------------------------ LOCAL SEARCH ------------------------------

def find_records(query):
    q = query.casefold()

    matches = list(ID_INDEX.get(q, []))

    if not matches:
        matches = [
            r
            for name, rows in USERNAME_INDEX.items()
            if q in name
            for r in rows
        ]

    if not matches:
        matches = list(IP_INDEX.get(q, []))

    if not matches:
        matches = [
            r
            for address, rows in IP_INDEX.items()
            if q in address
            for r in rows
        ]

    return matches


def discord_user_lookup():
    print_header()
    panel("Local Dataset Search")
    print(paint(
        "  Search local authorized records by Discord ID, username, or IP.",
        "muted"
    ))

    query = safe_input("\n  SEARCH > ")
    if not query:
        return

    matches = find_records(query)

    if not matches:
        show_message("No matching records found.", "warning")
        save_last_results("User Lookup", [])
        pause()
        return

    print()
    line()
    print(paint(f"  {len(matches):,} MATCHING RECORD(S)", "success", True))
    line()

    rows = []

    for number, r in enumerate(matches[:DISPLAY_LIMIT], 1):
        print()
        print(paint(f"  ┌─ RECORD {number:03d}", "primary", True))
        info("DISCORD ID", r["discord_id"])
        info("USERNAME", r["username"])
        info("IP ADDRESS", r["ip_address"] or "Not provided", "secondary")

        if SETTINGS.get("show_timestamps", True):
            info("TIMESTAMP", r["timestamp"] or "Unknown")

        info("SOURCE FILE", r.get("source_file", "Unknown"))
        print(paint("  └" + "─" * 42, "muted"))

        rows.append({
            k: r.get(k, "")
            for k in (
                "discord_id", "username", "ip_address",
                "timestamp", "source_file"
            )
        })

    if len(matches) > DISPLAY_LIMIT:
        show_message(f"Showing first {DISPLAY_LIMIT} of {len(matches):,}.", "warning")

    save_last_results("User Lookup", rows)
    pause()


# ------------------------------ WATCHLIST + SNAPSHOTS ------------------------------

def load_watchlist():
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [
            str(x).casefold()
            for x in data
            if str(x).strip()
        ] if isinstance(data, list) else []

    except (OSError, json.JSONDecodeError):
        return []


def save_watchlist(entries):
    try:
        temp = WATCHLIST_FILE + ".tmp"

        with open(temp, "w", encoding="utf-8") as f:
            json.dump(sorted(set(entries)), f, indent=2)

        os.replace(temp, WATCHLIST_FILE)
        return True

    except OSError as exc:
        show_message(f"Watchlist save failed: {exc}", "danger")
        return False


def watchlist_menu():
    entries = load_watchlist()

    while True:
        print_header()
        panel("Watchlist")
        info("ENTRIES", len(entries))

        for n, entry in enumerate(entries[:25], 1):
            print(paint(f"    {n:02d}. {entry}", "secondary"))

        if len(entries) > 25:
            print(paint(f"    ... and {len(entries) - 25} more", "muted"))

        print()
        menu_item("1", "Add entry", "Track a username, ID or IP in your local dataset")
        menu_item("2", "Remove entry", "Stop tracking an entry")
        menu_item("3", "Check now", "Scan local records for matches")
        menu_item("0", "Return", "Back to dashboard")

        choice = safe_input("\nkitsint/watchlist > ").lower()

        if choice == "1":
            value = safe_input("  ADD > ").casefold()

            if value:
                entries.append(value)
                save_watchlist(entries)
                show_message("Added.")
                time.sleep(0.4)

        elif choice == "2":
            value = safe_input("  REMOVE > ").casefold()

            if value in entries:
                entries.remove(value)
                save_watchlist(entries)
                show_message("Removed.")
            else:
                show_message("Not on the watchlist.", "warning")

            time.sleep(0.4)

        elif choice == "3":
            hits, export = [], []

            for r in RECORDS:
                haystack = " ".join((
                    r["discord_id"],
                    r["username"],
                    r["ip_address"],
                )).casefold()

                found = [entry for entry in entries if entry in haystack]

                if found:
                    hits.append((r, found))

            panel(f"{len(hits)} WATCHLIST HIT(S)")

            for r, found in hits[:DISPLAY_LIMIT]:
                info("USERNAME", r["username"])
                info("DISCORD ID", r["discord_id"])
                info("MATCHED ON", ", ".join(found), "warning")

                export.append({
                    "username": r["username"],
                    "discord_id": r["discord_id"],
                    "ip_address": r["ip_address"],
                    "matched": ", ".join(found),
                })

            save_last_results("Watchlist Check", export)
            pause()

        elif choice == "0":
            return

        else:
            show_message("Invalid option.", "warning")


def snapshot_key(record):
    return "|".join(
        str(record.get(k, ""))
        for k in ("discord_id", "username", "ip_address", "timestamp")
    )


def take_snapshot():
    keys = sorted(snapshot_key(r) for r in RECORDS)
    digest = hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()

    data = {
        "taken": timestamp(),
        "record_count": len(RECORDS),
        "digest": digest,
        "keys": keys,
    }

    temp = SNAPSHOT_FILE + ".tmp"

    try:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        os.replace(temp, SNAPSHOT_FILE)

    except OSError as exc:
        show_message(f"Could not save snapshot: {exc}", "warning")


def compare_with_previous_snapshot():
    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)

        old_keys = set(old.get("keys", []))
        new = [r for r in RECORDS if snapshot_key(r) not in old_keys]

        return {
            "previous_time": old.get("taken", "unknown"),
            "previous_count": old.get("record_count", 0),
            "new_records": new,
        }

    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def whats_new_module():
    print_header()
    panel("What's New Since Last Run")

    result = compare_with_previous_snapshot()

    if result is None:
        show_message("No previous snapshot found. Saving the first snapshot.", "warning")
        take_snapshot()
        pause()
        return

    new = result["new_records"]

    info("LAST RUN", result["previous_time"], "secondary")
    info("RECORDS THEN", f"{result['previous_count']:,}")
    info("RECORDS NOW", f"{len(RECORDS):,}")
    info("NEW RECORDS", f"{len(new):,}", "success" if new else "muted")

    rows = []

    for n, r in enumerate(new[:DISPLAY_LIMIT], 1):
        info(f"NEW {n:03d}", r["username"], "success")
        info("  DISCORD ID", r["discord_id"])
        info("  TIMESTAMP", r["timestamp"] or "-")

        rows.append({
            k: r.get(k, "")
            for k in ("username", "discord_id", "ip_address", "timestamp")
        })

    if len(new) > DISPLAY_LIMIT:
        show_message(f"Showing first {DISPLAY_LIMIT} of {len(new):,}.", "warning")

    save_last_results("Whats New", rows)
    take_snapshot()
    pause()


# ------------------------------ PUBLIC IP INTELLIGENCE ------------------------------

def geoip_lookup(address):
    """Optional offline MaxMind lookup. City results are approximate, not person location."""
    if not os.path.isfile(GEOLITE_FILE):
        return "GeoLite2 database not installed (optional)"

    try:
        import maxminddb

        with maxminddb.open_database(GEOLITE_FILE) as reader:
            data = reader.get(address) or {}

        country = (
            (data.get("country") or {})
            .get("names", {})
            .get("en", "Unknown")
        )

        subdivision = (
            (data.get("subdivisions") or [{}])[0]
            .get("names", {})
            .get("en", "")
        )

        return f"{subdivision}, {country}" if subdivision else country

    except ImportError:
        return "Install maxminddb to enable"

    except Exception as exc:
        return f"GeoIP error: {exc}"


def detect_ip_type(results):
    network = results.get("network") or {}
    description = str(results.get("asn_description", ""))
    name = str(network.get("name", ""))
    combined = (description + " " + name).lower()

    groups = [
        (
            ("vpn", "proxy", "mullvad", "nordvpn", "expressvpn",
             "surfshark", "tor exit"),
            "Likely VPN / Proxy",
        ),
        (
            ("mobile", "cellular", "wireless", "gsm", "lte", "5g", "4g"),
            "Likely Mobile Network",
        ),
        (
            ("residential", "broadband", "cable", "fiber", "fibre",
             "dsl", "ftth"),
            "Likely Residential / Broadband",
        ),
        (
            ("hosting", "datacenter", "data center", "cloud", "server", "vps"),
            "Hosting / Datacenter",
        ),
    ]

    for words, label in groups:
        if any(word in combined for word in words):
            return label

    return "Unknown"


def ip_lookup():
    print_header()
    panel("Public IP Intelligence")

    raw = safe_input("  ENTER PUBLIC IP > ")

    try:
        parsed = ip_address(raw)
    except ValueError:
        show_message("Invalid IP address.", "danger")
        pause()
        return

    if not parsed.is_global:
        show_message(
            "This is not a globally routable IP. External RDAP lookup skipped.",
            "warning"
        )
        pause()
        return

    try:
        from ipwhois import IPWhois
    except ImportError:
        show_message(
            "Install dependency: python -m pip install ipwhois",
            "warning"
        )
        pause()
        return

    try:
        result = IPWhois(str(parsed)).lookup_rdap(depth=1)
        network = result.get("network") or {}
        org = result.get("asn_description") or "Unknown"

        report = [
            ("IP Address", str(parsed)),
            ("IP Version", f"IPv{parsed.version}"),
            ("Country Code", result.get("asn_country_code") or "Unknown"),
            ("Approx. Geo (offline)", geoip_lookup(str(parsed))),
            ("ASN", result.get("asn") or "Unknown"),
            ("ASN Organization", org),
            ("Network Name", network.get("name") or "Unknown"),
            ("CIDR", network.get("cidr") or result.get("asn_cidr") or "Unknown"),
            ("Network Handle", network.get("handle") or "Unknown"),
            ("Network Type", network.get("type") or "Unknown"),
            ("Connection Estimate", detect_ip_type(result)),
        ]

        try:
            ptr = socket.gethostbyaddr(str(parsed))[0]
        except OSError:
            ptr = "No PTR record"

        report.append(("Reverse DNS", ptr))

        panel("IP Intelligence Report")

        for label, value in report:
            info(label, value, "secondary")

        show_message(
            "Registry and geolocation data describe networks, not individuals.",
            "warning"
        )

        save_last_results(
            "IP Lookup",
            [{"field": k, "value": v} for k, v in report]
        )

    except Exception as exc:
        show_message(f"RDAP lookup failed: {exc}", "danger")

    pause()


def fetch_json(url, timeout=8):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def my_current_ip():
    print_header()
    panel("My Public IP")

    try:
        public_ip = fetch_json(
            "https://api.ipify.org?format=json"
        ).get("ip", "")

        parsed = ip_address(public_ip)
        geo = geoip_lookup(public_ip)

        panel("Connection Information")
        info("PUBLIC IP", public_ip, "success")
        info("IP VERSION", f"IPv{parsed.version}")
        info("APPROX. GEO (OFFLINE)", geo, "secondary")

        save_last_results("My Current IP", [
            {"field": "Public IP", "value": public_ip},
            {"field": "IP Version", "value": f"IPv{parsed.version}"},
            {"field": "Approx. Geo (offline)", "value": geo},
        ])

    except Exception as exc:
        show_message(f"Could not fetch public IP: {exc}", "danger")

    pause()


# ------------------------------ AUTHORIZED WEBSITE DIAGNOSTICS ------------------------------

def normalize_target(target):
    target = target.strip()

    if not target:
        raise ValueError("No target entered.")

    if "://" not in target:
        try:
            literal = ip_address(target)
            host = f"[{literal}]" if literal.version == 6 else str(literal)
            target = "https://" + host + "/"
        except ValueError:
            target = "https://" + target

    parsed = urllib.parse.urlsplit(target)

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS are supported.")

    if not parsed.hostname:
        raise ValueError("Invalid hostname.")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs containing credentials are not supported.")

    port = parsed.port
    expected = 443 if parsed.scheme.lower() == "https" else 80

    if port is not None and port not in (80, 443, 8080):
        raise ValueError(
            "For safety, diagnostics only accept ports 80, 443, and 8080."
        )

    hostname = parsed.hostname

    try:
        literal = ip_address(hostname)
        hostname = str(literal)
        ipv6 = literal.version == 6
    except ValueError:
        hostname = hostname.encode("idna").decode("ascii").lower().rstrip(".")
        ipv6 = False

        if not hostname or len(hostname) > 253:
            raise ValueError("Invalid hostname.")

    hostpart = f"[{hostname}]" if ipv6 else hostname
    netloc = (
        hostpart
        if port is None or port == expected
        else f"{hostpart}:{port}"
    )

    normalized = urllib.parse.urlunsplit((
        parsed.scheme.lower(),
        netloc,
        parsed.path or "/",
        parsed.query,
        "",
    ))

    return normalized, hostname, port or expected


def resolve_public_ips(hostname):
    infos = socket.getaddrinfo(
        hostname,
        None,
        type=socket.SOCK_STREAM
    )

    addresses = list(dict.fromkeys(item[4][0] for item in infos))

    return [
        address
        for address in addresses
        if ip_address(address).is_global
    ]


def check_one_port(host, port):
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return port, "OPEN"
    except OSError:
        return port, "CLOSED / FILTERED"


def tls_certificate_info(ip, hostname, port=443, timeout=4):
    """Verify the TLS certificate and use the DNS hostname for SNI."""
    context = ssl.create_default_context()

    try:
        with socket.create_connection((ip, port), timeout=timeout) as raw:
            with context.wrap_socket(
                raw,
                server_hostname=hostname
            ) as tls:
                cert = tls.getpeercert() or {}
                tls_version = tls.version()

        issuer = "Unknown"

        for group in cert.get("issuer", ()):
            for key, value in group:
                if key == "organizationName":
                    issuer = value

        sans = [
            value
            for kind, value in cert.get("subjectAltName", ())
            if kind == "DNS"
        ][:8]

        return {
            "Issuer": issuer,
            "Expires": cert.get("notAfter", "Unknown"),
            "DNS SANs": ", ".join(sans) if sans else "None listed",
            "TLS Version": tls_version,
        }

    except (OSError, ssl.SSLError, ValueError) as exc:
        return {"TLS Check": f"Could not verify certificate: {exc}"}


def threat_intel_scanner():
    print_header()
    panel("Website / IP Diagnostics")

    print(paint(
        "  Only continue if you own or are authorized to test the target.",
        "warning"
    ))

    target = safe_input("\n  TARGET > ")

    if not target:
        return

    if safe_input("  Confirm authorization? Type YES > ").upper() != "YES":
        show_message("Diagnostics cancelled.", "warning")
        pause()
        return

    output = []

    try:
        url, hostname, web_port = normalize_target(target)
        info("NORMALIZED URL", url)
        output.append({"field": "Target", "value": url})

        addresses = resolve_public_ips(hostname)

        if not addresses:
            raise ValueError(
                "No public IP address resolved. Private/local targets are not scanned."
            )

        ip = addresses[0]

        panel("DNS Results")

        for address in addresses:
            info("PUBLIC IP", address, "secondary")
            output.append({"field": "Resolved IP", "value": address})

        try:
            ptr = socket.gethostbyaddr(ip)[0]
        except OSError:
            ptr = "No PTR record"

        info("REVERSE DNS", ptr)
        output.append({"field": "Reverse DNS", "value": ptr})

        panel("HTTP Security Headers")

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT},
                method="GET"
            )

            with urllib.request.urlopen(request, timeout=8) as response:
                headers = response.headers

                values = {
                    "HTTP Status": response.status,
                    "Final URL": response.geturl(),
                    "Server Header": headers.get("Server", "Undisclosed"),
                    "HSTS": (
                        "Present"
                        if headers.get("Strict-Transport-Security")
                        else "Missing"
                    ),
                    "CSP": (
                        "Present"
                        if headers.get("Content-Security-Policy")
                        else "Missing"
                    ),
                    "X-Frame-Options": (
                        "Present"
                        if headers.get("X-Frame-Options")
                        else "Missing"
                    ),
                }

                for key, value in values.items():
                    info(key, value)
                    output.append({"field": key, "value": value})

        except Exception as exc:
            show_message(f"HTTP check failed: {exc}", "warning")
            output.append({"field": "HTTP Check", "value": str(exc)})

        panel("Small TCP Port Check")

        with ThreadPoolExecutor(max_workers=len(COMMON_PORTS)) as pool:
            port_results = list(
                pool.map(
                    lambda p: check_one_port(ip, p),
                    COMMON_PORTS
                )
            )

        for port, state in port_results:
            info(
                f"TCP PORT {port}",
                state,
                "success" if state == "OPEN" else "muted"
            )
            output.append({
                "field": f"TCP port {port}",
                "value": state
            })

        panel("TLS Certificate Verification")

        if web_port == 443:
            cert = tls_certificate_info(ip, hostname, 443)

            for key, value in cert.items():
                info(key, value, "secondary")
                output.append({
                    "field": f"TLS {key}",
                    "value": value
                })
        else:
            info(
                "TLS",
                "Skipped because target URL does not use port 443",
                "muted"
            )

    except Exception as exc:
        show_message(f"Diagnostic failed: {exc}", "danger")
        output.append({
            "field": "Diagnostic Error",
            "value": str(exc)
        })

    save_last_results("Website Diagnostics", output)
    pause()


# ------------------------------ NETWORK TEST ------------------------------

def internet_connection_checker():
    print_header()
    panel("Network Diagnostics")
    output = []

    try:
        socket.gethostbyname("example.com")
        dns = "CONNECTED"
    except OSError:
        dns = "FAILED"

    info(
        "DNS CONNECTIVITY",
        dns,
        "success" if dns == "CONNECTED" else "danger"
    )

    try:
        start = time.perf_counter()

        with socket.create_connection(("1.1.1.1", 443), timeout=4):
            pass

        latency = (time.perf_counter() - start) * 1000
        status = "CONNECTED"

        info("INTERNET STATUS", status, "success")
        info("TCP LATENCY", f"{latency:.2f} ms", "success")

        output.extend([
            {"field": "Internet Status", "value": status},
            {"field": "TCP Latency", "value": f"{latency:.2f} ms"},
        ])

    except OSError:
        show_message("Internet connection test failed.", "danger")
        output.append({
            "field": "Internet Status",
            "value": "OFFLINE"
        })
        save_last_results("Network Test", output)
        pause()
        return

    try:
        public_ip = fetch_json(
            "https://api.ipify.org?format=json"
        ).get("ip", "Unavailable")
    except Exception:
        public_ip = "Unavailable"

    info("PUBLIC IP", public_ip, "secondary")
    output.append({"field": "Public IP", "value": public_ip})

    panel("Optional Speed Test")

    try:
        import speedtest

        tester = speedtest.Speedtest()
        print(paint(
            "  Finding best speed-test server...",
            "secondary"
        ))

        tester.get_best_server()
        down = tester.download() / 1_000_000
        up = tester.upload() / 1_000_000

        info("DOWNLOAD", f"{down:.2f} Mbps", "success")
        info("UPLOAD", f"{up:.2f} Mbps", "success")

        output.extend([
            {"field": "Download", "value": f"{down:.2f} Mbps"},
            {"field": "Upload", "value": f"{up:.2f} Mbps"},
        ])

    except ImportError:
        show_message(
            "Optional: python -m pip install speedtest-cli",
            "warning"
        )

    except Exception as exc:
        show_message(f"Speed test failed: {exc}", "warning")

    save_last_results("Network Test", output)
    pause()


# ------------------------------ STATISTICS + EXPORTS ------------------------------

def build_statistics():
    unique_ids = {r["discord_id"] for r in RECORDS}
    unique_users = {r["username"].casefold() for r in RECORDS}
    unique_ips = {r["ip_address"] for r in RECORDS if r["ip_address"]}

    valid = invalid = 0

    for r in RECORDS:
        if not r["ip_address"]:
            continue

        try:
            ip_address(r["ip_address"])
            valid += 1
        except ValueError:
            invalid += 1

    return [
        {"field": "Files loaded", "value": len(LOADED_FILES)},
        {"field": "Total records", "value": len(RECORDS)},
        {"field": "Unique Discord IDs", "value": len(unique_ids)},
        {"field": "Unique usernames", "value": len(unique_users)},
        {"field": "Unique IP values", "value": len(unique_ips)},
        {"field": "Valid IP values", "value": valid},
        {"field": "Invalid IP values", "value": invalid},
        {"field": "Duplicates", "value": DUPLICATES},
        {"field": "Recovered rows", "value": RECOVERED_ROWS},
        {"field": "Skipped rows", "value": INVALID_ROWS},
        {"field": "Read failures", "value": READ_FAILURES},
    ]


def display_statistics():
    print_header()
    panel("Dataset Statistics")

    rows = build_statistics()

    for item in rows:
        info(item["field"], f"{item['value']:,}")

    panel("Loaded Files")

    for name in LOADED_FILES:
        print(paint("  ◈ " + name, "secondary"))

    save_last_results("Dataset Statistics", rows)
    pause()


def protect_spreadsheet_value(value):
    value = str(value)

    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value

    return value


def export_results():
    print_header()
    panel("Export Center")

    info("LAST RESULT SET", LAST_EXPORT_NAME)
    info("AVAILABLE ROWS", len(LAST_RESULTS))

    print()
    menu_item("1", "Export last results as CSV", "Spreadsheet format")
    menu_item("2", "Export last results as TXT", "Readable text")
    menu_item("3", "Export statistics as CSV", "Dataset statistics")
    menu_item("4", "Export statistics as TXT", "Dataset statistics")
    menu_item("0", "Return", "Back to dashboard")

    choice = safe_input("\nkitsint/export > ")

    if choice == "0":
        return

    if choice in ("3", "4"):
        rows = build_statistics()
        name = "dataset_statistics"
        title = "Dataset Statistics"

    elif choice in ("1", "2"):
        rows = LAST_RESULTS
        name = safe_filename(LAST_EXPORT_NAME)
        title = LAST_EXPORT_NAME

        if not rows:
            show_message("No results available to export.", "warning")
            pause()
            return

    else:
        show_message("Invalid option.", "warning")
        pause()
        return

    os.makedirs(EXPORT_DIR, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ext = "csv" if choice in ("1", "3") else "txt"
    path = os.path.join(EXPORT_DIR, f"{name}_{stamp}.{ext}")

    try:
        if ext == "csv":
            keys = list(dict.fromkeys(
                key
                for row in rows
                for key in row
            ))

            with open(
                path,
                "x",
                encoding="utf-8-sig",
                newline=""
            ) as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()

                for row in rows:
                    writer.writerow({
                        key: protect_spreadsheet_value(value)
                        for key, value in row.items()
                    })

        else:
            with open(path, "x", encoding="utf-8") as f:
                f.write(
                    f"KITSINT - {title}\n"
                    f"Exported: {timestamp()}\n"
                    f"{'=' * 55}\n\n"
                )

                for row in rows:
                    if "field" in row:
                        f.write(
                            f"{row['field']}: {row.get('value', '')}\n"
                        )
                    else:
                        for key, value in row.items():
                            f.write(f"{key}: {value}\n")

                        f.write("-" * 35 + "\n")

        show_message("Export completed successfully.", "success")
        info("SAVED TO", path, "secondary")

    except OSError as exc:
        show_message(f"Export failed: {exc}", "danger")

    pause()


# ------------------------------ HELP + RESTART + SELFTEST ------------------------------

def help_and_about():
    print_header()
    panel("KITSINT Documentation")

    details = [
        ("01", "User Lookup", "Search local dataset records."),
        ("02", "IP Intelligence", "Public RDAP and optional approximate GeoIP."),
        ("03", "My Current IP", "Display your public IP."),
        ("04", "Website Diagnostics", "Authorized DNS, HTTP, small port and TLS checks."),
        ("05", "Network Test", "Connectivity, latency and optional speed test."),
        ("06", "Watchlist", "Find local dataset matches."),
        ("07", "What's New", "Records added since last snapshot."),
        ("08", "Statistics", "Record and dataset integrity counts."),
        ("09", "Dataset Manager", "Inspect and reload CSV files."),
        ("10", "Export Center", "Save results to CSV or TXT."),
        ("11", "Settings", "Themes and appearance."),
        ("12", "Reload Datasets", "Reload local CSV files."),
        ("13", "Restart", "Restart KITSINT."),
        ("00", "Exit", "Close the application."),
    ]

    for number, name, desc in details:
        print()
        print(paint(f"  [{number}] {name}", "primary", True))
        print(paint(f"       {desc}", "muted"))

    panel("File Locations")

    for label, path in (
        ("DATASETS", DATASETS_DIR),
        ("EXPORTS", EXPORT_DIR),
        ("SETTINGS", SETTINGS_FILE),
        ("DATABASE", DB_FILE),
        ("WATCHLIST", WATCHLIST_FILE),
        ("SNAPSHOT", SNAPSHOT_FILE),
        ("GEOLITE OPTIONAL", GEOLITE_FILE),
    ):
        info(label, path)

    panel("Dataset Format")
    print(paint(
        "  index,discord_id,username,ip_address,timestamp",
        "secondary"
    ))

    panel("Safety / Accuracy")
    print("  Use only synthetic or authorized records.")
    print("  IP geolocation is approximate network-level data.")
    print("  Shared IPs do not prove that accounts belong to one person.")
    print("  The alt-account correlation feature is not included.")
    print("  Only diagnose systems you own or are authorized to inspect.")

    panel("Optional Dependencies")
    print("  python -m pip install ipwhois speedtest-cli maxminddb")

    pause()


def restart_kitsint():
    print_header()
    show_message("Restarting KITSINT...", "secondary")

    try:
        sys.stdout.flush()
        sys.stderr.flush()

        os.execv(
            sys.executable,
            [
                sys.executable,
                os.path.abspath(__file__),
                *sys.argv[1:],
            ]
        )

    except OSError as error:
        show_message(f"Restart failed: {error}", "danger")
        input("\nPress Enter to return...")


def run_selftest():
    checks = []

    record = row_to_record([
        "1",
        "123",
        "alice",
        "1.2.3.4",
        "2024-01-01",
    ])

    checks.append((
        "CSV basic row",
        bool(record and record["username"] == "alice")
    ))

    mapped = row_to_record(
        ["u", "id", "alice", "1.2.3.4", "2024-01-01"],
        make_header_map([
            "index",
            "userid",
            "username",
            "ip",
            "when",
        ])
    )

    checks.append((
        "Header aliases",
        bool(mapped and mapped["discord_id"] == "id")
    ))

    checks.append((
        "Reject malformed row",
        row_to_record(["short"]) is None
    ))

    try:
        url, host, port = normalize_target("example.com")

        checks.append((
            "Normalize hostname",
            host == "example.com"
            and url.startswith("https://")
            and port == 443
        ))

    except Exception:
        checks.append(("Normalize hostname", False))

    try:
        normalize_target("https://user:pass@example.com")
        checks.append(("Reject URL credentials", False))

    except ValueError:
        checks.append(("Reject URL credentials", True))

    try:
        _, host, _ = normalize_target("2001:db8::1")
        checks.append(("IPv6 literal", host == "2001:db8::1"))

    except Exception:
        checks.append(("IPv6 literal", False))

    print()

    for name, ok in checks:
        print(
            f"  [{'OK' if ok else 'FAIL'}] "
            f"{paint(name, 'success' if ok else 'danger')}"
        )

    success = all(ok for _, ok in checks)

    show_message(
        "ALL CHECKS PASSED" if success else "SOME CHECKS FAILED",
        "success" if success else "danger"
    )

    raise SystemExit(0 if success else 1)


def run_cli_mode(arguments):
    if "--lookup" not in arguments:
        return False

    pos = arguments.index("--lookup")
    query = arguments[pos + 1] if pos + 1 < len(arguments) else ""

    load_datasets(show_summary=False)

    if not query:
        print(json.dumps({"error": "no query"}))
        return True

    matches = find_records(query)

    payload = [
        {
            k: r.get(k, "")
            for k in (
                "discord_id",
                "username",
                "ip_address",
                "timestamp",
                "source_file",
            )
        }
        for r in matches[:DISPLAY_LIMIT]
    ]

    if "--json" in arguments:
        print(json.dumps(payload, indent=2))

    elif not payload:
        print("No matches.")

    else:
        for row in payload:
            print(
                f"{row['discord_id']}  "
                f"{row['username']}  "
                f"{row['ip_address']}  "
                f"{row['timestamp']}"
            )

    return True


# ------------------------------ MAIN MENU ------------------------------

def main_menu():
    while True:
        print_header()
        print(paint("  [ SYSTEM DASHBOARD ]", "secondary", True))
        print()

        menu_item("01", "User Lookup", "Local Discord ID / username / IP search")
        menu_item("02", "IP Intelligence", "Public IP RDAP information")
        menu_item("03", "My Current IP", "Your public IP address")
        menu_item("04", "Website Diagnostics", "Authorized DNS / HTTP / ports / TLS")
        menu_item("05", "Network Test", "Connectivity / latency / speed")

        print()
        line()

        menu_item("06", "Watchlist", "Track entries in your local dataset")
        menu_item("07", "What's New", "Records added since last run")
        menu_item("08", "Dataset Statistics", "Record and data-quality counts")
        menu_item("09", "Dataset Manager", "Inspect local CSV datasets")
        menu_item("10", "Export Center", "Save lookup results")
        menu_item("11", "Settings", "Themes and appearance")
        menu_item("12", "Help & About", "Documentation")

        print()
        line()

        menu_item("13", "Reload Datasets", "Reload CSV records")
        menu_item("14", "Restart KITSINT", "Restart the application")
        menu_item("00", "Exit", "Close KITSINT")

        status_bar()

        choice = safe_input("\nkitsint/nightfall > ").lower()

        actions = {
            "1": discord_user_lookup,
            "01": discord_user_lookup,
            "2": ip_lookup,
            "02": ip_lookup,
            "3": my_current_ip,
            "03": my_current_ip,
            "4": threat_intel_scanner,
            "04": threat_intel_scanner,
            "5": internet_connection_checker,
            "05": internet_connection_checker,
            "6": watchlist_menu,
            "06": watchlist_menu,
            "7": whats_new_module,
            "07": whats_new_module,
            "8": display_statistics,
            "08": display_statistics,
            "9": dataset_manager,
            "09": dataset_manager,
            "10": export_results,
            "11": settings_menu,
            "12": help_and_about,
            "13": lambda: (
                print_header(),
                reload_datasets(),
                pause()
            ),
            "14": restart_kitsint,
        }

        if choice in ("0", "00"):
            print_header()
            show_message("KITSINT session terminated.", "secondary")
            return

        action = actions.get(choice)

        if action:
            action()
        else:
            show_message("Invalid selection.", "warning")
            time.sleep(0.5)


def main():
    load_settings()

    if "--selftest" in sys.argv:
        run_selftest()

    if run_cli_mode(sys.argv):
        return

    print_header()
    panel("Boot Sequence")
    print(paint("  Initializing KITSINT NIGHTFALL...", "secondary"))
    time.sleep(0.2)

    load_datasets(show_summary=True)

    diff = compare_with_previous_snapshot()

    if diff is not None and diff["new_records"]:
        show_message(
            f"{len(diff['new_records']):,} new records since "
            f"{diff['previous_time']} (menu 07).",
            "warning"
        )

    take_snapshot()

    pause("\n  Initialization complete. Press ENTER to continue...")
    main_menu()


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print()
        print(paint("KITSINT closed.", "warning"))

    except SystemExit:
        raise

    except Exception as exc:
        print()
        print(paint(f"Unexpected KITSINT error: {exc}", "danger"))
        pause()
