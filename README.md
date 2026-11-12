# SPECTRUM: ZEROPOINT
![SPECTRUM: ZEROPOINT](spectrum-zero-point%20V6-1.png)
**OSINT & CSINT Desktop Investigation Toolkit**

SPECTRUM: ZEROPOINT is a Python-based desktop application designed to bring multiple information-gathering and network diagnostic tools together in one interface.

## Features

- **Dashboard** — Overview of application status and loaded datasets.
- **Local Dataset Search** — Search locally stored CSV records.
- **IP Information** — Public IP address RDAP, ASN, and network information.
- **Website Diagnostics** — DNS lookups, HTTP security headers, TLS certificate information, and limited TCP port checks.
- **Network Diagnostics** — Connectivity, latency, and optional internet speed testing.
- **Dataset Manager** — Load and manage local CSV datasets.
- **Statistics** — View information about loaded datasets.
- **Watchlist** — Keep track of locally saved investigation entries.
- **Snapshots** — Save local snapshots.
- **Export Center** — Export supported investigation results.
- **Settings** — Configure application preferences.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Internet connection for online lookups
- Required Python dependencies

## Installation

### 1. Download the project

Clone the repository:

```bash
git clone https://github.com/regentdata8479/SPECTRUM-ZEROPOINT.git
```

Or download the repository as a ZIP file from GitHub.

### 2. Open the project folder

Open the extracted `SPECTRUM-ZEROPOINT` directory.

### 3. Install dependencies

Open PowerShell in the project directory and run:

```powershell
py -m pip install -r requirements.txt
```

### 4. Launch the application

Run:

```powershell
py KITSINT.pyw
```

The application should open in its own desktop window.

## Dataset Setup

SPECTRUM supports local CSV datasets.

Place your authorized CSV files inside:

```text
datasets/
```

Supported source-file naming pattern:

```text
users_part_*.csv
```

Dataset files are not included in this repository.

## Project Structure

```text
SPECTRUM-ZEROPOINT/
│
├── KITSINT.pyw
├── kitsint_backend.py
├── requirements.txt
├── README.txt
├── .gitignore
│
├── datasets/
├── exports/
└── kitsint.db
```

The `datasets`, `exports`, and database files are generated or maintained locally and are not included in the public repository.

## Responsible Use

SPECTRUM: ZEROPOINT is intended for educational purposes, authorized investigations, and systems you own or have explicit permission to inspect.

- Only investigate data you are authorized to access.
- Only run network diagnostics against systems you own or have permission to test.
- Respect privacy and applicable laws.
- Do not use the application to harass, stalk, or target individuals.
- Do not upload private datasets, credentials, API keys, or personal information to public repositories.

## Disclaimer

This software is provided for educational and informational purposes.

The developer is not responsible for misuse, unauthorized access, or damage resulting from use of this software.

## Author

**GitHub:** [@regentdata8479](https://github.com/regentdata8479)

## Repository

[ SPECTRUM: ZEROPOINT on GitHub](https://github.com/regentdata8479/SPECTRUM-ZEROPOINT)
