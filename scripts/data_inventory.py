from pathlib import Path
import pandas as pd
import json
from datetime import datetime

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
RAW = PROJECT / "data" / "incoming"
OUT = PROJECT / "data" / "processed"

OUT.mkdir(parents=True, exist_ok=True)

rows = []

files = sorted(
    list(RAW.glob("*.xlsx")) +
    list(RAW.glob("*.xls")) +
    list(RAW.glob("*.csv"))
)

print("\nROCK DATA INVENTORY")
print("=" * 70)

for file in files:

    info = {
        "file": file.name,
        "type": file.suffix.lower(),
        "size_mb": round(file.stat().st_size / 1024 / 1024, 2),
        "sheets": "",
        "rows": "",
        "columns": "",
        "column_names": "",
        "date_min": "",
        "date_max": "",
        "error": ""
    }

    try:

        if file.suffix.lower() == ".csv":

            df = pd.read_csv(
                file,
                nrows=200000
            )

            info["sheets"] = "CSV"
            info["rows"] = len(df)
            info["columns"] = len(df.columns)
            info["column_names"] = " | ".join(
                map(str, df.columns)
            )

        else:

            xl = pd.ExcelFile(file)

            info["sheets"] = " | ".join(
                xl.sheet_names
            )

            info["columns"] = len(
                pd.read_excel(
                    file,
                    sheet_name=xl.sheet_names[0],
                    nrows=5
                ).columns
            )

            info["column_names"] = " | ".join(
                map(
                    str,
                    pd.read_excel(
                        file,
                        sheet_name=xl.sheet_names[0],
                        nrows=5
                    ).columns
                )
            )

            total_rows = 0

            for sheet in xl.sheet_names:

                try:
                    part = pd.read_excel(
                        file,
                        sheet_name=sheet
                    )
                    total_rows += len(part)

                except Exception:
                    pass

            info["rows"] = total_rows

        # Try to detect date columns.
        try:

            if file.suffix.lower() == ".csv":
                sample = pd.read_csv(
                    file,
                    nrows=1000
                )
            else:
                sample = pd.read_excel(
                    file,
                    sheet_name=0,
                    nrows=1000
                )

            for col in sample.columns:

                name = str(col).lower()

                if (
                    "date" in name
                    or "period" in name
                    or "year" in name
                ):

                    converted = pd.to_datetime(
                        sample[col],
                        errors="coerce"
                    )

                    valid = converted.dropna()

                    if len(valid):
                        info["date_min"] = str(
                            valid.min().date()
                        )
                        info["date_max"] = str(
                            valid.max().date()
                        )
                        break

        except Exception:
            pass

        print(
            f"✓ {file.name} | "
            f"{info['rows']} rows | "
            f"{info['columns']} cols"
        )

    except Exception as exc:

        info["error"] = str(exc)

        print(
            f"✗ {file.name} | ERROR: {exc}"
        )

    rows.append(info)

inventory = pd.DataFrame(rows)

output = OUT / "rock_data_inventory.csv"

inventory.to_csv(
    output,
    index=False
)

summary = {
    "generated": datetime.now().isoformat(),
    "source": "Rock Data Plus",
    "files_found": len(files),
    "csv_files": sum(
        f.suffix.lower() == ".csv"
        for f in files
    ),
    "excel_files": sum(
        f.suffix.lower() in [".xlsx", ".xls"]
        for f in files
    ),
    "inventory_file": str(output)
}

(OUT / "rock_inventory_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("\n" + "=" * 70)
print("INVENTORY COMPLETE")
print("=" * 70)

print("\nInventory:")
print(output)

print("\nSummary:")
print(OUT / "rock_inventory_summary.json")
