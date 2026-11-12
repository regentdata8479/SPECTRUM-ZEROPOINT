KITSINT: NIGHTFALL — Desktop GUI

1. Install Python 3.10 or newer.
2. Open this folder once and install dependencies:
   py -m pip install -r requirements.txt
3. Double-click "Launch KITSINT.bat".

The GUI opens as a separate desktop window; it does not show the old numbered terminal menu.
Place your own authorized CSV files in datasets/ using the filename pattern users_part_*.csv.
CSV data is not included in this package.

Optional:
- speedtest-cli enables the optional speed test.
- maxminddb plus a licensed GeoLite2-City.mmdb file enables offline approximate network geolocation.

Keep kitsint_backend.py and kitsint_gui.py in the same folder.
