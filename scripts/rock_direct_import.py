import os
import csv
import csv
import json
import re
import time
import hashlib
import shutil
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright

# ============================================================
# ROCK DATA PLUS - DIRECT REPOSITORY IMPORT
# ============================================================

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
RAW = PROJECT / "data" / "raw" / "rock_responses"
TABLES = PROJECT / "data" / "raw" / "tables"
EXPORTS = PROJECT / "data" / "exports"
SCREENSHOTS = PROJECT / "data" / "screenshots"

for folder in [RAW, TABLES, EXPORTS, SCREENSHOTS]:
    folder.mkdir(parents=True, exist_ok=True)

ROCK_URL = "https://www.rockdataplus.com/repository"
DEBUG_PORT = 9222

MODULES = [
    "Stock Market",
    "Agriculture",
    "Exchange Rates",
    "Inflation",
    "Historical PMI",
    "NSE Bond Index",
    "Treasury Bills",
    "Yield Curve",
    "Liquidity Indicators",
    "Forex Reserves",
    "Fuel Prices",
]

captured = {}
downloads = []


# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def safe_name(value):
    value = re.sub(r"[^\w\s.-]", "", value)
    return re.sub(r"\s+", "_", value.strip())[:100]


def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def chrome_path():
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) /
        "Google/Chrome/Application/chrome.exe",

        Path(os.environ.get("PROGRAMFILES(X86)", "")) /
        "Google/Chrome/Application/chrome.exe",

        Path(os.environ.get("LOCALAPPDATA", "")) /
        "Google/Chrome/Application/chrome.exe",
    ]

    for path in candidates:
        if path.exists():
            return path

    found = shutil.which("chrome")
    if found:
        return Path(found)

    raise FileNotFoundError(
        "Google Chrome could not be located."
    )


def chrome_is_running():
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
            capture_output=True,
            text=True
        )
        return "chrome.exe" in result.stdout.lower()
    except Exception:
        return False


def wait_for_debug_port(seconds=30):
    deadline = time.time() + seconds

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{DEBUG_PORT}/json/version",
                timeout=2
            ):
                return True
        except Exception:
            time.sleep(1)

    return False


def save_json_data(url, body, content_type):
    """
    Save data only when it comes from the Rock application's
    data/API traffic. Authentication/token endpoints are excluded.
    """
    lower = url.lower()

    # We specifically avoid saving authentication/session traffic.
    blocked = [
        "/auth/",
        "/token",
        "/session",
        "/user",
        "/users",
        "/health",
    ]

    if any(x in lower for x in blocked):
        return

    # Prefer Supabase/data/API responses.
    is_data_url = (
        "supabase" in lower
        or "/api/" in lower
        or "/rpc/" in lower
        or "repository" in lower
        or "market" in lower
    )

    if not is_data_url:
        return

    digest = hashlib.sha256(body).hexdigest()

    if digest in captured:
        return

    captured[digest] = {
        "url": url,
        "content_type": content_type,
    }

    name = (
        f"{timestamp()}_"
        f"{hashlib.md5(url.encode()).hexdigest()[:10]}.json"
    )

    path = RAW / name
    path.write_bytes(body)

    print(f"  ✓ Rock data captured: {name}")
    print(f"    {url[:130]}")


# ------------------------------------------------------------
# Find tabular data inside JSON
# ------------------------------------------------------------

def looks_like_table(value):
    if not isinstance(value, list):
        return False

    if len(value) < 3:
        return False

    dicts = [x for x in value if isinstance(x, dict)]

    if len(dicts) < 3:
        return False

    common = set(dicts[0].keys())

    for item in dicts[1:]:
        common &= set(item.keys())

    return len(common) >= 2


def find_tables(obj, path="root"):
    found = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            found.extend(
                find_tables(value, f"{path}_{safe_name(str(key))}")
            )

    elif isinstance(obj, list):
        if looks_like_table(obj):
            found.append((path, obj))

        for i, value in enumerate(obj[:20]):
            if isinstance(value, (dict, list)):
                found.extend(
                    find_tables(value, f"{path}_{i}")
                )

    return found


def convert_json_to_csv():
    print("\n" + "=" * 60)
    print("CONVERTING ROCK RESPONSES TO TABLES")
    print("=" * 60)

    converted = 0

    for json_file in RAW.glob("*.json"):

        try:
            data = json.loads(
                json_file.read_text(encoding="utf-8")
            )

            tables = find_tables(data)

            for number, (location, rows) in enumerate(tables):
                if not rows:
                    continue

                # Avoid extremely tiny metadata tables.
                if len(rows) < 3:
                    continue

                columns = set()

                for row in rows:
                    columns.update(row.keys())

                columns = sorted(columns)

                filename = (
                    f"{json_file.stem}_"
                    f"{safe_name(location)}_"
                    f"{number + 1}.csv"
                )

                output = TABLES / filename

                with output.open(
                    "w",
                    newline="",
                    encoding="utf-8-sig"
                ) as f:

                    writer = csv.DictWriter(
                        f,
                        fieldnames=columns,
                        extrasaction="ignore"
                    )

                    writer.writeheader()

                    for row in rows:
                        writer.writerow(row)

                print(
                    f"  ✓ {output.name} "
                    f"({len(rows):,} rows)"
                )

                converted += 1

        except Exception as exc:
            print(
                f"  Could not convert "
                f"{json_file.name}: {exc}"
            )

    print(f"\nConverted tables: {converted}")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    print("=" * 60)
    print("ROCK DATA PLUS — DIRECT DATA IMPORT")
    print("=" * 60)

    print("\nData source:")
    print("  ROCK DATA PLUS ONLY")

    print("\nProject:")
    print(PROJECT)

    if chrome_is_running():
        print("\nIMPORTANT:")
        print("Chrome is currently running.")
        print("Close ALL Chrome windows first.")
        print("\nThen run this script again.")
        input("\nPress ENTER to exit...")
        return

    chrome = chrome_path()

    user_data = (
        Path(os.environ["LOCALAPPDATA"])
        / "Google"
        / "Chrome"
        / "User Data"
    )

    print("\nStarting Chrome...")
    print("Opening the Rock Repository...")

    subprocess.Popen([
        str(chrome),
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={user_data}",
        "--profile-directory=Default",
        ROCK_URL,
    ])

    if not wait_for_debug_port():
        print("\nCould not connect to Chrome.")
        input("Press ENTER to exit...")
        return

    print("✓ Chrome automation connection ready.")

    with sync_playwright() as p:

        browser = p.chromium.connect_over_cdp(
            f"http://127.0.0.1:{DEBUG_PORT}"
        )

        context = browser.contexts[0]

        if context.pages:
            page = context.pages[0]
        else:
            page = context.new_page()

        # ----------------------------------------------------
        # Capture browser downloads
        # ----------------------------------------------------

        def on_download(download):
            try:
                filename = download.suggested_filename
                destination = EXPORTS / filename
                download.save_as(str(destination))

                downloads.append(filename)

                print(
                    f"  ✓ Download captured: "
                    f"{filename}"
                )

            except Exception as exc:
                print(
                    f"  Download error: {exc}"
                )

        page.on("download", on_download)

        # ----------------------------------------------------
        # Capture Rock network responses
        # ----------------------------------------------------

        def on_response(response):

            try:
                request = response.request

                # We only care about GET data responses.
                if request.method != "GET":
                    return

                content_type = (
                    response.headers.get(
                        "content-type",
                        ""
                    ).lower()
                )

                url = response.url

                # JSON/data responses.
                if (
                    "application/json" in content_type
                    or "text/json" in content_type
                    or url.lower().endswith(".json")
                ):
                    try:
                        body = response.body()

                        if len(body) > 100:
                            save_json_data(
                                url,
                                body,
                                content_type
                            )

                    except Exception:
                        pass

            except Exception:
                pass

        page.on("response", on_response)

        # ----------------------------------------------------
        # Open repository
        # ----------------------------------------------------

        try:
            page.goto(
                ROCK_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )
        except Exception as exc:
            print("Page-load message:", exc)

        print("\n" + "=" * 60)
        print("ROCK LOGIN")
        print("=" * 60)

        print("""
The Rock Repository is now open.

Log in normally in Chrome if Rock asks you to.

Do NOT enter your password into the terminal.

Once you can see the Repository dashboard,
come back here and press ENTER.
""")

        input("Press ENTER when Repository is ready... ")

        # ----------------------------------------------------
        # Wait for Rock data
        # ----------------------------------------------------

        print("\nWaiting for Rock data...")
        page.wait_for_timeout(10000)

        try:
            page.screenshot(
                path=str(
                    SCREENSHOTS /
                    f"repository_{timestamp()}.png"
                ),
                full_page=True
            )
        except Exception:
            pass

        # ----------------------------------------------------
        # Click modules to trigger their own data calls
        # ----------------------------------------------------

        for number, module in enumerate(
            MODULES,
            start=1
        ):

            print(
                f"\n[{number}/{len(MODULES)}] "
                f"{module}"
            )

            try:
                locator = page.get_by_text(
                    module,
                    exact=True
                )

                clicked = False

                for i in range(locator.count()):

                    item = locator.nth(i)

                    if item.is_visible():

                        item.scroll_into_view_if_needed()

                        item.click(
                            timeout=5000
                        )

                        clicked = True
                        break

                if clicked:

                    print("  ✓ Opened")

                    # Allow Rock to make its own data
                    # requests. We do not call its API.
                    page.wait_for_timeout(6000)

                    try:
                        page.evaluate(
                            "window.scrollTo(0,0)"
                        )
                    except Exception:
                        pass

                else:
                    print("  - Not visible")

            except Exception as exc:
                print(
                    f"  - Could not open: {exc}"
                )

        # ----------------------------------------------------
        # Extra waiting period for delayed responses
        # ----------------------------------------------------

        print(
            "\nWaiting for remaining Rock "
            "data responses..."
        )

        page.wait_for_timeout(10000)

        # ----------------------------------------------------
        # Convert captured JSON into CSV tables
        # ----------------------------------------------------

        convert_json_to_csv()

        # ----------------------------------------------------
        # Manifest
        # ----------------------------------------------------

        manifest = {
            "project": "Rock Investment Outlook 2026",
            "source": "Rock Data Plus",
            "repository": ROCK_URL,
            "collection_time": datetime.now().isoformat(),
            "modules_requested": MODULES,
            "raw_responses": len(list(RAW.glob("*.json"))),
            "derived_tables": len(list(TABLES.glob("*.csv"))),
            "browser_downloads": downloads,
            "external_data_used": False,
            "collection_method": (
                "Captured data responses generated by the "
                "authenticated Rock Data Plus Repository "
                "interface. No external market-data source "
                "was queried."
            )
        }

        manifest_path = (
            PROJECT /
            "data" /
            "rock_import_manifest.json"
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2
            ),
            encoding="utf-8"
        )

        print("\n" + "=" * 60)
        print("ROCK IMPORT COMPLETE")
        print("=" * 60)

        print("\nRaw Rock responses:")
        print(RAW)

        print("\nRock tables:")
        print(TABLES)

        print("\nDownloads:")
        print(EXPORTS)

        print("\nManifest:")
        print(manifest_path)

        print("\nThis is now our official Rock-data archive.")

        input(
            "\nPress ENTER to finish..."
        )


if __name__ == "__main__":
    main()
