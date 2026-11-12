
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import csv
import kitsint_backend as core

APP_NAME = "SPECTRUM: ZEROPOINT"
BRAND = "SPECTRUM"
SUBTITLE = "Z E R O P O I N T   /   6.1"

try:
    import customtkinter as ctk
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        APP_NAME,
        "CustomTkinter is missing.\n\nInstall it with:\npy -m pip install customtkinter"
    )
    raise SystemExit(1)

BG = "#090D14"
PANEL = "#101824"
PANEL2 = "#151F2D"
CYAN = "#16D9E8"
CYAN_DARK = "#0C8795"
TEXT = "#E8F1F8"
MUTED = "#8192A5"
GREEN = "#37D69A"
RED = "#FF647C"
AMBER = "#F2B85B"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class SpectrumApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1280x800")
        self.minsize(1050, 680)
        self.configure(fg_color=BG)

        core.load_settings()

        self.current_page = None

        self._build_shell()
        self.show_page("Dashboard")

        self.after(150, self.boot_load)

    def _build_shell(self):

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0,
            fg_color="#0B111B"
        )

        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text=f"◈ {BRAND}",
            font=("Segoe UI", 25, "bold"),
            text_color=CYAN
        ).pack(anchor="w", padx=22, pady=(28, 0))

        ctk.CTkLabel(
            self.sidebar,
            text=SUBTITLE,
            font=("Consolas", 10),
            text_color=MUTED
        ).pack(anchor="w", padx=24, pady=(2, 28))

        self.nav = {}

        items = [
            ("Dashboard", "⌂"),
            ("User Lookup", "⌕"),
            ("IP Intelligence", "◎"),
            ("Website Diagnostics", "⌁"),
            ("Network Test", "⌁"),
            ("Watchlist", "☆"),
            ("What's New", "◷"),
            ("Datasets", "▤"),
            ("Statistics", "▥"),
            ("Export Center", "⇩"),
            ("Settings", "⚙"),
            ("About", "ⓘ")
        ]

        for name, symbol in items:

            b = ctk.CTkButton(
                self.sidebar,
                text=f"  {symbol}    {name}",
                anchor="w",
                height=39,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#172637",
                text_color="#B9C8D8",
                font=("Segoe UI", 13),
                command=lambda n=name: self.show_page(n)
            )

            b.pack(fill="x", padx=12, pady=2)
            self.nav[name] = b

        ctk.CTkFrame(
            self.sidebar,
            height=2,
            fg_color="#1D2C3B"
        ).pack(fill="x", padx=16, pady=(20, 12))

        self.side_status = ctk.CTkLabel(
            self.sidebar,
            text="● INITIALIZING",
            text_color=AMBER,
            font=("Consolas", 11)
        )

        self.side_status.pack(anchor="w", padx=22)

        ctk.CTkLabel(
            self.sidebar,
            text="LOCAL DATA • AUTHORIZED USE",
            text_color="#526477",
            font=("Consolas", 9)
        ).pack(side="bottom", anchor="w", padx=18, pady=18)

        self.main = ctk.CTkFrame(
            self,
            fg_color=BG,
            corner_radius=0
        )

        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self.top = ctk.CTkFrame(
            self.main,
            fg_color=BG,
            corner_radius=0,
            height=70
        )

        self.top.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=28,
            pady=(20, 4)
        )

        self.top.grid_columnconfigure(0, weight=1)

        self.page_title = ctk.CTkLabel(
            self.top,
            text="DASHBOARD",
            font=("Segoe UI", 24, "bold"),
            text_color=TEXT
        )

        self.page_title.grid(row=0, column=0, sticky="w")

        self.clock = ctk.CTkLabel(
            self.top,
            text="",
            font=("Consolas", 11),
            text_color=MUTED
        )

        self.clock.grid(row=0, column=1, sticky="e")

        self.content = ctk.CTkFrame(
            self.main,
            fg_color=BG,
            corner_radius=0
        )

        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=28,
            pady=(8, 24)
        )

        self.after(500, self._tick)

    def _tick(self):

        self.clock.configure(
            text=datetime.now().strftime("%Y-%m-%d   %H:%M:%S")
        )

        self.after(1000, self._tick)

    def clear(self):

        for w in self.content.winfo_children():
            w.destroy()

    def show_page(self, name):

        self.current_page = name
        self.page_title.configure(text=name.upper())

        for n, b in self.nav.items():

            b.configure(
                fg_color="#12313C" if n == name else "transparent",
                text_color=CYAN if n == name else "#B9C8D8"
            )

        self.clear()

        method = (
            "page_" +
            name.lower().replace(" ", "_").replace("'", "")
        )

        getattr(self, method, self.page_about)()

    def card(self, parent, title, value, sub=""):

        f = ctk.CTkFrame(
            parent,
            fg_color=PANEL,
            corner_radius=12,
            border_width=1,
            border_color="#1C2B3A"
        )

        ctk.CTkLabel(
            f,
            text=title.upper(),
            text_color=MUTED,
            font=("Consolas", 10, "bold")
        ).pack(anchor="w", padx=18, pady=(15, 4))

        ctk.CTkLabel(
            f,
            text=str(value),
            text_color=CYAN,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w", padx=18)

        if sub:

            ctk.CTkLabel(
                f,
                text=sub,
                text_color=MUTED,
                font=("Segoe UI", 10)
            ).pack(anchor="w", padx=18, pady=(2, 14))

        else:
            ctk.CTkLabel(f, text="", height=10).pack()

        return f

    def button(self, parent, text, command, kind="primary"):

        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            height=38,
            corner_radius=8,
            fg_color=CYAN_DARK if kind == "primary" else PANEL2,
            hover_color="#12616B" if kind == "primary" else "#24364A",
            text_color=TEXT,
            font=("Segoe UI", 12, "bold")
        )

    def entry(self, parent, placeholder):

        return ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            height=40,
            fg_color="#0D1520",
            border_color="#26394C",
            text_color=TEXT
        )

    def heading(self, parent, text, desc=None):

        ctk.CTkLabel(
            parent,
            text=text,
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT
        ).pack(anchor="w", pady=(0, 4))

        if desc:

            ctk.CTkLabel(
                parent,
                text=desc,
                font=("Segoe UI", 11),
                text_color=MUTED
            ).pack(anchor="w", pady=(0, 14))

    def table(self, parent, columns, rows, height=12):

        wrap = ctk.CTkFrame(
            parent,
            fg_color=PANEL,
            corner_radius=10
        )

        wrap.pack(fill="both", expand=True, pady=(12, 0))

        tree = ttk.Treeview(
            wrap,
            columns=columns,
            show="headings",
            height=height
        )

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background="#101824",
            foreground="#DDE8F2",
            fieldbackground="#101824",
            rowheight=29,
            borderwidth=0,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Treeview.Heading",
            background="#1A2938",
            foreground="#16D9E8",
            relief="flat",
            font=("Segoe UI", 10, "bold")
        )

        style.map(
            "Treeview",
            background=[("selected", "#14505B")]
        )

        for col in columns:

            tree.heading(
                col,
                text=col.replace("_", " ").upper()
            )

            tree.column(
                col,
                width=max(100, int(850 / max(1, len(columns)))),
                anchor="w"
            )

        sy = ttk.Scrollbar(
            wrap,
            orient="vertical",
            command=tree.yview
        )

        tree.configure(yscrollcommand=sy.set)

        tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(8, 0),
            pady=8
        )

        sy.pack(
            side="right",
            fill="y",
            padx=6,
            pady=8
        )

        for row in rows:
            tree.insert(
                "",
                "end",
                values=[row.get(c, "") for c in columns]
            )

        return tree

    def boot_load(self):

        def work():

            try:
                core.load_datasets(show_summary=False)
                core.take_snapshot()

            except Exception as e:
                self.after(0, lambda: self.notify(str(e), True))

            self.after(0, self.refresh_status)

            self.after(
                0,
                lambda: self.show_page(
                    self.current_page or "Dashboard"
                )
            )

        threading.Thread(
            target=work,
            daemon=True
        ).start()

    def refresh_status(self):

        self.side_status.configure(
            text="● DATA READY" if core.RECORDS else "● NO DATA LOADED",
            text_color=GREEN if core.RECORDS else AMBER
        )

    def notify(self, msg, error=False):

        if error:
            messagebox.showerror(APP_NAME, str(msg))
        else:
            messagebox.showinfo(APP_NAME, str(msg))

    def page_dashboard(self):

        self.heading(
            self.content,
            "Command overview",
            "SPECTRUM: ZEROPOINT  /  CSINT PANEL"
        )

        cards = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        cards.pack(fill="x", pady=8)
        cards.grid_columnconfigure((0, 1, 2, 3), weight=1)

        stats = [
            ("RECORDS", len(core.RECORDS), "Loaded local rows"),
            ("DATASETS", len(core.LOADED_FILES), "CSV source files"),
            ("WATCHLIST", len(core.load_watchlist()), "Saved entries"),
            (
                "EXPORTS",
                len(os.listdir(core.EXPORT_DIR))
                if os.path.isdir(core.EXPORT_DIR) else 0,
                "Generated files"
            )
        ]

        for i, (t, v, s) in enumerate(stats):

            self.card(
                cards,
                t,
                f"{v:,}",
                s
            ).grid(
                row=0,
                column=i,
                sticky="ew",
                padx=5
            )

        self.heading(
            self.content,
            "Quick actions",
            "Select a module from here or from the navigation rail."
        )

        actions = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        actions.pack(fill="x")

        for i, (label, page) in enumerate([
            ("Search local records", "User Lookup"),
            ("Inspect public IP metadata", "IP Intelligence"),
            ("Run website diagnostics", "Website Diagnostics"),
            ("Manage datasets", "Datasets")
        ]):

            self.button(
                actions,
                label,
                lambda p=page: self.show_page(p),
                "secondary"
            ).grid(
                row=i // 2,
                column=i % 2,
                sticky="ew",
                padx=6,
                pady=6
            )

        actions.grid_columnconfigure((0, 1), weight=1)

        note = ctk.CTkFrame(
            self.content,
            fg_color="#111D29",
            corner_radius=10
        )

        note.pack(fill="x", pady=16)

        ctk.CTkLabel(
            note,
            text="PRIVACY & SCOPE",
            text_color=CYAN,
            font=("Consolas", 11, "bold")
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            note,
            text=(
                
            ),
            text_color="#A7B7C8",
            wraplength=850,
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 14))

    def page_user_lookup(self):

        self.heading(
            self.content,
            "Local record search",
            "Search your  CSV dataset by ID, username, or IP."
        )

        row = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        row.pack(fill="x")

        self.search_entry = self.entry(
            row,
            "Enter ID, username, or IP address"
        )

        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8)
        )

        self.button(
            row,
            "SEARCH",
            self.do_search
        ).pack(side="left")

        self.search_count = ctk.CTkLabel(
            self.content,
            text="No search performed",
            text_color=MUTED
        )

        self.search_count.pack(anchor="w", pady=10)

        self.results = self.table(
            self.content,
            (
                "discord_id",
                "username",
                "ip_address",
                "timestamp",
                "source_file"
            ),
            []
        )

        self.search_entry.bind(
            "<Return>",
            lambda e: self.do_search()
        )

    def do_search(self):

        q = self.search_entry.get().strip()

        if not q:
            return

        rows = core.find_records(q)[:core.DISPLAY_LIMIT]

        core.save_last_results(
            "User Lookup",
            [
                {
                    k: r.get(k, "")
                    for k in (
                        "discord_id",
                        "username",
                        "ip_address",
                        "timestamp",
                        "source_file"
                    )
                }
                for r in rows
            ]
        )

        for item in self.results.get_children():
            self.results.delete(item)

        for r in rows:

            self.results.insert(
                "",
                "end",
                values=[
                    r.get(k, "")
                    for k in (
                        "discord_id",
                        "username",
                        "ip_address",
                        "timestamp",
                        "source_file"
                    )
                ]
            )

        self.search_count.configure(
            text=f"{len(rows):,} result(s) shown  •  maximum {core.DISPLAY_LIMIT}"
        )

    def run_bg(self, fn, done):

        def worker():

            try:
                result = fn()

            except Exception as e:
                result = e

            self.after(
                0,
                lambda: done(result)
            )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def page_ip_intelligence(self):

        self.heading(
            self.content,
            "IP Lookup",
            "RDAP registry metadata and optional approximate network geolocation."
        )

        row = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        row.pack(fill="x")

        self.ip_entry = self.entry(
            row,
            "Public IP address"
        )

        self.ip_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8)
        )

        self.button(
            row,
            "LOOK UP",
            self.do_ip
        ).pack(side="left")

        self.ip_output = ctk.CTkTextbox(
            self.content,
            fg_color=PANEL,
            text_color=TEXT,
            corner_radius=10
        )

        self.ip_output.pack(
            fill="both",
            expand=True,
            pady=14
        )

        self.ip_output.insert(
            "end",
            "Enter a valid IP address to query public RDAP data.\n\n"
        )

    def do_ip(self):

        raw = self.ip_entry.get().strip()

        def work():

            from ipaddress import ip_address
            from ipwhois import IPWhois

            parsed = ip_address(raw)

            if not parsed.is_global:
                raise ValueError(
                    "Only globally routable public IPs are supported."
                )

            result = IPWhois(
                str(parsed)
            ).lookup_rdap(depth=1)

            net = result.get("network") or {}

            rows = [
                ("IP Address", str(parsed)),
                ("IP Version", f"IPv{parsed.version}"),
                ("Country Name", result.get("asn_country_code") or "Unknown"),
                ("Approx. Geo", core.geoip_lookup(str(parsed))),
                ("ASN", result.get("asn") or "Unknown"),
                ("Organization", result.get("asn_description") or "Unknown"),
                ("Network Name", net.get("name") or "Unknown"),
                ("CIDR", net.get("cidr") or result.get("asn_cidr") or "Unknown"),
                ("Network Type", net.get("type") or "Unknown"),
                ("Connection Estimate", core.detect_ip_type(result))
            ]

            try:
                rows.append(
                    (
                        "Reverse DNS",
                        __import__("socket").gethostbyaddr(str(parsed))[0]
                    )
                )

            except OSError:
                rows.append(("Reverse DNS", "No PTR record"))

            core.save_last_results(
                "IP Lookup",
                [{"field": k, "value": v} for k, v in rows]
            )

            return rows

        self.ip_output.delete("1.0", "end")
        self.ip_output.insert("end", "Looking up IP Address…")

        def done(res):

            self.ip_output.delete("1.0", "end")

            if isinstance(res, Exception):

                self.ip_output.insert(
                    "end",
                    f"Lookup failed: {res}"
                )

            else:

                for k, v in res:
                    self.ip_output.insert(
                        "end",
                        f"{k:<24} {v}\n\n"
                    )

                self.ip_output.insert(
                    "end",
                )

        self.run_bg(work, done)

    def page_website_diagnostics(self):

        self.heading(
            self.content,
            "Website diagnostics",
            
        )

        self.diag_entry = self.entry(
            self.content,
            "https://your-domain.example"
        )

        self.diag_entry.pack(fill="x", pady=5)

        self.auth_var = tk.BooleanVar(value=False)

        ctk.CTkCheckBox(
            self.content,
            text="I am super tuff and wanna search a websites info.",
            variable=self.auth_var,
            text_color=TEXT,
            fg_color=CYAN_DARK
        ).pack(anchor="w", pady=8)

        self.button(
            self.content,
            "RUN LIMITED DIAGNOSTICS",
            self.do_diag
        ).pack(anchor="w", pady=6)

        self.diag_output = ctk.CTkTextbox(
            self.content,
            fg_color=PANEL,
            text_color=TEXT,
            corner_radius=10
        )

        self.diag_output.pack(
            fill="both",
            expand=True,
            pady=12
        )

        self.diag_output.insert(
            "end",
            "Checks: DNS resolution, HTTP security headers, a small fixed "
            "set of common TCP ports, and verified TLS certificate details. "
            "Private/local targets are excluded."
        )

    def do_diag(self):

        if not self.auth_var.get():

            messagebox.showwarning(
                "Authorization required",
                "Confirm that ur tuff"
            )

            return

        target = self.diag_entry.get().strip()

        self.diag_output.delete("1.0", "end")
        self.diag_output.insert("end", "Running limited checks…\n")

        def work():

            url, host, port = core.normalize_target(target)
            ips = core.resolve_public_ips(host)

            if not ips:
                raise ValueError(
                    "No public IP address resolved; private/local targets are not scanned."
                )

            ip = ips[0]

            rows = [
                ("Target", url),
                ("Resolved public IPs", ", ".join(ips))
            ]

            try:

                req = __import__(
                    "urllib.request",
                    fromlist=["Request"]
                ).Request(
                    url,
                    headers={"User-Agent": core.USER_AGENT}
                )

                with __import__(
                    "urllib.request",
                    fromlist=["urlopen"]
                ).urlopen(req, timeout=8) as resp:

                    h = resp.headers

                    rows += [
                        ("HTTP status", resp.status),
                        ("Server", h.get("Server", "Undisclosed")),
                        (
                            "HSTS",
                            "Present" if h.get("Strict-Transport-Security") else "Missing"
                        ),
                        (
                            "CSP",
                            "Present" if h.get("Content-Security-Policy") else "Missing"
                        ),
                        (
                            "X-Frame-Options",
                            "Present" if h.get("X-Frame-Options") else "Missing"
                        )
                    ]

            except Exception as e:
                rows.append(("HTTP check", str(e)))

            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(
                max_workers=len(core.COMMON_PORTS)
            ) as pool:

                ports = list(
                    pool.map(
                        lambda p: core.check_one_port(ip, p),
                        core.COMMON_PORTS
                    )
                )

            rows += [
                (f"TCP {p}", s)
                for p, s in ports
            ]

            if port == 443:

                rows += list(
                    core.tls_certificate_info(
                        ip,
                        host,
                        443
                    ).items()
                )

            core.save_last_results(
                "Website Diagnostics",
                [{"field": k, "value": v} for k, v in rows]
            )

            return rows

        def done(res):

            self.diag_output.delete("1.0", "end")

            if isinstance(res, Exception):

                self.diag_output.insert(
                    "end",
                    f"Diagnostics failed: {res}"
                )

            else:

                for k, v in res:

                    self.diag_output.insert(
                        "end",
                        f"{k:<25} {v}\n\n"
                    )

        self.run_bg(work, done)

    def page_network_test(self):

        self.heading(
            self.content,
            "Network diagnostics",
            "Connectivity and latency checks. Optional speed test can be run if installed."
        )

        self.button(
            self.content,
            "TEST CONNECTION",
            self.do_network
        ).pack(anchor="w")

        self.net_output = ctk.CTkTextbox(
            self.content,
            fg_color=PANEL,
            text_color=TEXT,
            corner_radius=10
        )

        self.net_output.pack(
            fill="both",
            expand=True,
            pady=12
        )

    def do_network(self):

        self.net_output.delete("1.0", "end")
        self.net_output.insert("end", "Testing connectivity…")

        def work():

            import socket
            import time

            rows = []

            try:
                socket.gethostbyname("example.com")
                rows.append(("DNS", "CONNECTED"))

            except OSError:
                rows.append(("DNS", "FAILED"))

            start = time.perf_counter()

            with socket.create_connection(
                ("1.1.1.1", 443),
                timeout=4
            ):
                pass

            rows.append(
                (
                    "TCP latency",
                    f"{(time.perf_counter() - start) * 1000:.2f} ms"
                )
            )

            try:

                rows.append(
                    (
                        "Public IP",
                        core.fetch_json(
                            "https://api.ipify.org?format=json"
                        ).get("ip", "Unavailable")
                    )
                )

            except Exception:
                rows.append(("Public IP", "Unavailable"))

            try:

                import speedtest

                tester = speedtest.Speedtest()
                tester.get_best_server()

                rows.extend([
                    (
                        "Download",
                        f"{tester.download() / 1_000_000:.2f} Mbps"
                    ),
                    (
                        "Upload",
                        f"{tester.upload() / 1_000_000:.2f} Mbps"
                    )
                ])

            except ImportError:
                rows.append(
                    ("Speed test", "Optional package not installed")
                )

            except Exception as e:
                rows.append(("Speed test", str(e)))

            core.save_last_results(
                "Network Test",
                [{"field": k, "value": v} for k, v in rows]
            )

            return rows

        def done(res):

            self.net_output.delete("1.0", "end")

            if isinstance(res, Exception):

                self.net_output.insert(
                    "end",
                    f"Network test failed: {res}"
                )

            else:

                for k, v in res:

                    self.net_output.insert(
                        "end",
                        f"{k:<20} {v}\n\n"
                    )

        self.run_bg(work, done)

    def page_watchlist(self):

        self.heading(
            self.content,
            "Local watchlist",
            "Entries are checked only on your local dataset."
        )

        row = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        row.pack(fill="x")

        self.watch_entry = self.entry(
            row,
            "Add username or ID"
        )

        self.watch_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8)
        )

        self.button(
            row,
            "ADD",
            self.add_watch
        ).pack(side="left")

        self.watch_box = ctk.CTkTextbox(
            self.content,
            fg_color=PANEL,
            text_color=TEXT,
            corner_radius=10
        )

        self.watch_box.pack(
            fill="both",
            expand=True,
            pady=12
        )

        self.render_watch()

    def render_watch(self):

        self.watch_box.delete("1.0", "end")

        for item in core.load_watchlist():
            self.watch_box.insert("end", item + "\n")

    def add_watch(self):

        v = self.watch_entry.get().strip().casefold()

        if v:

            entries = core.load_watchlist()
            entries.append(v)

            core.save_watchlist(entries)

            self.watch_entry.delete(0, "end")
            self.render_watch()

    def page_whats_new(self):

        self.heading(
            self.content,
            "What's new",
            "Compare the loaded dataset with the previous local snapshot."
        )

        self.button(
            self.content,
            "COMPARE SNAPSHOT",
            self.do_snapshot
        ).pack(anchor="w")

        self.snapshot_output = ctk.CTkTextbox(
            self.content,
            fg_color=PANEL,
            text_color=TEXT,
            corner_radius=10
        )

        self.snapshot_output.pack(
            fill="both",
            expand=True,
            pady=12
        )

    def do_snapshot(self):

        result = core.compare_with_previous_snapshot()

        self.snapshot_output.delete("1.0", "end")

        if result is None:

            self.snapshot_output.insert(
                "end",
                "No previous snapshot exists. A new snapshot has been created."
            )

            core.take_snapshot()
            return

        new = result["new_records"]

        self.snapshot_output.insert(
            "end",
            f"Previous snapshot: {result['previous_time']}\n"
            f"Previous records: {result['previous_count']}\n"
            f"Current records: {len(core.RECORDS)}\n"
            f"New records: {len(new)}\n\n"
        )

        for r in new[:core.DISPLAY_LIMIT]:

            self.snapshot_output.insert(
                "end",
                f"{r['username']}  |  {r['discord_id']}  |  {r['timestamp']}\n"
            )

        core.save_last_results(
            "Whats New",
            [
                {
                    "username": r["username"],
                    "discord_id": r["discord_id"],
                    "ip_address": r["ip_address"],
                    "timestamp": r["timestamp"]
                }
                for r in new[:core.DISPLAY_LIMIT]
            ]
        )

        core.take_snapshot()

    def page_datasets(self):

        self.heading(
            self.content,
            "Dataset manager",
            "Place users_part_*.csv files in the datasets folder, then reload."
        )

        ctk.CTkLabel(
            self.content,
            text=core.DATASETS_DIR,
            text_color=CYAN,
            font=("Consolas", 11)
        ).pack(anchor="w", pady=5)

        self.button(
            self.content,
            "OPEN DATASETS FOLDER",
            lambda: os.startfile(core.DATASETS_DIR)
        ).pack(anchor="w", pady=5)

        self.button(
            self.content,
            "RELOAD CSV DATASETS",
            self.reload_data
        ).pack(anchor="w", pady=5)

        self.dataset_table = self.table(
            self.content,
            (
                "filename",
                "status",
                "valid_records",
                "invalid_rows",
                "duplicates"
            ),
            []
        )

        self.render_datasets()

    def render_datasets(self):

        for x in self.dataset_table.get_children():
            self.dataset_table.delete(x)

        for r in core.FILE_STATS:

            self.dataset_table.insert(
                "",
                "end",
                values=[
                    r.get(k, "")
                    for k in (
                        "filename",
                        "status",
                        "valid_records",
                        "invalid_rows",
                        "duplicates"
                    )
                ]
            )

    def reload_data(self):

        def work():

            core.load_datasets(show_summary=False)
            return True

        def done(res):

            if isinstance(res, Exception):
                self.notify(res, True)

            else:
                self.refresh_status()
                self.show_page("Datasets")

        self.run_bg(work, done)

    def page_statistics(self):

        self.heading(
            self.content,
            "Dataset statistics",
            "Integrity and summary information for the currently loaded local records."
        )

        rows = core.build_statistics()

        self.table(
            self.content,
            ("field", "value"),
            rows,
            height=16
        )

    def page_export_center(self):

        self.heading(
            self.content,
            "Export center",
            "Export the latest result set or dataset statistics."
        )

        self.export_status = ctk.CTkLabel(
            self.content,
            text=(
                f"Latest result set: {core.LAST_EXPORT_NAME}  "
                f"•  {len(core.LAST_RESULTS)} rows"
            ),
            text_color=MUTED
        )

        self.export_status.pack(anchor="w", pady=8)

        self.button(
            self.content,
            "EXPORT LAST RESULTS AS CSV",
            lambda: self.export_rows(
                core.LAST_RESULTS,
                core.LAST_EXPORT_NAME,
                "csv"
            )
        ).pack(anchor="w", pady=5)

        self.button(
            self.content,
            "EXPORT LAST RESULTS AS TXT",
            lambda: self.export_rows(
                core.LAST_RESULTS,
                core.LAST_EXPORT_NAME,
                "txt"
            ),
            "secondary"
        ).pack(anchor="w", pady=5)

        self.button(
            self.content,
            "EXPORT STATISTICS AS CSV",
            lambda: self.export_rows(
                core.build_statistics(),
                "dataset_statistics",
                "csv"
            )
        ).pack(anchor="w", pady=5)

        self.button(
            self.content,
            "EXPORT STATISTICS AS TXT",
            lambda: self.export_rows(
                core.build_statistics(),
                "dataset_statistics",
                "txt"
            ),
            "secondary"
        ).pack(anchor="w", pady=5)

    def export_rows(self, rows, name, ext):

        if not rows:

            messagebox.showwarning(
                APP_NAME,
                "There are no rows to export yet."
            )

            return

        os.makedirs(core.EXPORT_DIR, exist_ok=True)

        path = filedialog.asksaveasfilename(
            initialdir=core.EXPORT_DIR,
            initialfile=(
                f"{core.safe_filename(name)}_"
                f"{datetime.now():%Y%m%d_%H%M%S}.{ext}"
            ),
            defaultextension="." + ext,
            filetypes=(
                [("CSV", "*.csv")]
                if ext == "csv"
                else [("Text", "*.txt")]
            )
        )

        if not path:
            return

        try:

            if ext == "csv":

                keys = list(
                    dict.fromkeys(
                        k
                        for r in rows
                        for k in r
                    )
                )

                with open(
                    path,
                    "w",
                    encoding="utf-8-sig",
                    newline=""
                ) as f:

                    w = csv.DictWriter(
                        f,
                        fieldnames=keys
                    )

                    w.writeheader()

                    for r in rows:

                        w.writerow({
                            k: core.protect_spreadsheet_value(v)
                            for k, v in r.items()
                        })

            else:

                with open(
                    path,
                    "w",
                    encoding="utf-8"
                ) as f:

                    f.write(
                        f"{APP_NAME} - {name}\n"
                        f"Exported: {core.timestamp()}\n\n"
                    )

                    for r in rows:

                        for k, v in r.items():
                            f.write(f"{k}: {v}\n")

                        f.write("\n")

            self.notify(
                f"Export saved:\n{path}"
            )

        except OSError as e:
            self.notify(e, True)

    def page_settings(self):

        self.heading(
            self.content,
            "Appearance & settings",
            "Preferences are saved in kitsint_settings.json."
        )

        self.theme_var = tk.StringVar(
            value=core.SETTINGS.get("theme", "cyan")
        )

        ctk.CTkLabel(
            self.content,
            text="Accent theme",
            text_color=TEXT
        ).pack(anchor="w", pady=(10, 4))

        ctk.CTkOptionMenu(
            self.content,
            values=["cyan", "purple", "red", "green"],
            variable=self.theme_var
        ).pack(anchor="w")

        self.button(
            self.content,
            "SAVE SETTINGS",
            self.save_gui_settings
        ).pack(anchor="w", pady=14)

    def save_gui_settings(self):

        core.SETTINGS["theme"] = self.theme_var.get()
        core.save_settings()

        self.notify("Settings saved.")

    def page_about(self):

        self.heading(
            self.content,
            APP_NAME,
            "Version 6.1 • Desktop interface"
        )

        text = (
            "SPECTRUM: ZEROPOINT is a CSINT Panel with CSV loading, "
            "search, exports, watchlist, snapshots, public RDAP lookups and "
            "low-volume diagnostics.\n\n"
            "Privacy and accuracy:\n"
            "• Website diagnostics are unrestricted to public targets and "
            "common ports.\n\n"
            "Data folders are stored beside this application: datasets/, "
            "exports/, SQLite database, settings, watchlist and snapshot."
        )

        box = ctk.CTkTextbox(
            self.content,
            fg_color=PANEL,
            text_color=TEXT,
            corner_radius=10
        )

        box.pack(fill="both", expand=True)
        box.insert("end", text)
        box.configure(state="disabled")


if __name__ == "__main__":

    app = SpectrumApp()
    app.mainloop()
