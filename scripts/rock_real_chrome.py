from pathlib import Path
from datetime import datetime
import csv
import json
import re
import time
from playwright.sync_api import sync_playwright

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
DATA = PROJECT / "data"
RAW = DATA / "raw" / "rock_responses"
TABLES = DATA / "raw" / "tables"
SHOTS = DATA / "screenshots"
PROFILE = PROJECT / ".rock_chrome"

for p in [RAW, TABLES, SHOTS, PROFILE]:
    p.mkdir(parents=True, exist_ok=True)

URL = "https://www.rockdataplus.com/repository"

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

def safe(x):
    x = re.sub(r"[^\w\s.-]", "", x)
    return re.sub(r"\s+", "_", x.strip())[:80]

def save_screen(page, name):
    try:
        page.screenshot(
            path=str(
                SHOTS / f"{safe(name)}_{datetime.now():%Y%m%d_%H%M%S}.png"
            ),
            full_page=True
        )
    except Exception:
        pass

def save_tables(page, module):
    tables = page.locator("table")

    for i in range(tables.count()):
        try:
            table = tables.nth(i)
            rows = table.locator("tr")

            if rows.count() == 0:
                continue

            path = TABLES / (
                f"{safe(module)}_{datetime.now():%Y%m%d_%H%M%S}_{i+1}.csv"
            )

            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)

                for r in range(rows.count()):
                    cells = rows.nth(r).locator("th,td")
                    values = [
                        cells.nth(c).inner_text().strip()
                        for c in range(cells.count())
                    ]

                    if values:
                        writer.writerow(values)

            print("  ✓ table saved:", path.name)

        except Exception as e:
            print("  table error:", e)

def click_text(page, text):
    try:
        loc = page.get_by_text(text, exact=True)

        for i in range(loc.count()):
            item = loc.nth(i)

            if item.is_visible():
                item.scroll_into_view_if_needed()
                item.click(timeout=5000)
                return True
    except Exception:
        pass

    return False

def save_rock_response(response, seen):
    try:
        url = response.url.lower()
        content_type = response.headers.get("content-type", "").lower()

        if "json" not in content_type:
            return

        # Never save authentication/session responses.
        blocked = [
            "/auth/",
            "/token",
            "/session",
            "/user"
        ]

        if any(x in url for x in blocked):
            return

        body = response.body()

        if len(body) < 100:
            return

        import hashlib
        digest = hashlib.sha256(body).hexdigest()

        if digest in seen:
            return

        seen.add(digest)

        path = RAW / (
            f"{datetime.now():%Y%m%d_%H%M%S}_"
            f"{len(seen):04d}.json"
        )

        path.write_bytes(body)

        print("  ✓ Rock response:", path.name)

    except Exception:
        pass

def main():

    print("=" * 60)
    print("ROCK DATA PLUS — REAL GOOGLE CHROME")
    print("=" * 60)

    with sync_playwright() as p:

        # IMPORTANT:
        # channel="chrome" means installed Google Chrome,
        # NOT Chrome for Testing / Playwright Chromium.
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            accept_downloads=True,
            viewport={"width": 1600, "height": 900},
        )

        page = context.pages[0] if context.pages else context.new_page()

        seen = set()

        page.on(
            "response",
            lambda response: save_rock_response(response, seen)
        )

        print("\nOpening Rock Data Plus...")
        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("""
============================================================
ROCK DATA PLUS LOGIN
============================================================

A normal Google Chrome window is now open.

Log into Rock Data Plus normally.
Google should no longer reject the browser because this
uses the installed Chrome browser rather than Chrome for Testing.

After you reach the Repository dashboard and see:

    Analysis complete
    Ready for Analysis

return to this terminal and press ENTER.
""")

        input("Press ENTER when the Repository is ready... ")

        try:
            page.get_by_text(
                "Stock Market",
                exact=True
            ).first.wait_for(
                state="visible",
                timeout=30000
            )
        except Exception:
            print("\nRepository not detected.")
            save_screen(page, "repository_problem")
            input("Press ENTER to close...")
            context.close()
            return

        print("\n✓ Repository detected.")

        for number, module in enumerate(MODULES, 1):

            print(f"\n[{number}/{len(MODULES)}] {module}")

            if click_text(page, module):
                print("  ✓ opened")
                page.wait_for_timeout(5000)

                if module == "Stock Market":

                    for category in [
                        "Equities Trading",
                        "Bonds Trading",
                        "Market Indices"
                    ]:
                        if click_text(page, category):
                            print("  ✓", category)

                    page.wait_for_timeout(7000)

                save_tables(page, module)
                save_screen(page, module)

            else:
                print("  - not found")

        page.wait_for_timeout(10000)

        manifest = {
            "project": "Rock Investment Outlook 2026",
            "source": "Rock Data Plus",
            "repository": URL,
            "collection_date": datetime.now().isoformat(),
            "modules": MODULES,
            "rock_responses_captured": len(seen),
            "tables_saved": len(list(TABLES.glob("*.csv"))),
            "external_data_used": False
        }

        (DATA / "rock_manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        print("\n" + "=" * 60)
        print("ROCK DATA COLLECTION COMPLETE")
        print("=" * 60)

        print("\nSaved in:")
        print(DATA)

        input("\nPress ENTER to close Chrome...")

        context.close()

if __name__ == "__main__":
    main()
