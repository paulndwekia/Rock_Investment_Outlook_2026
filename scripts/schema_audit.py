from pathlib import Path
import pandas as pd
import json

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
CANONICAL = PROJECT / "data" / "canonical"
OUT = PROJECT / "analysis"

OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    "treasury_bills.xlsx",
    "nse_bond_index.xlsx",
    "forex_reserves.xlsx",
    "inflation_data.xlsx",
]

print("\n" + "=" * 100)
print("ROCK DATASET SCHEMA AUDIT")
print("=" * 100)

audit = {}

for filename in TARGETS:

    path = CANONICAL / filename

    print("\n" + "=" * 100)
    print("FILE:", filename)
    print("=" * 100)

    if not path.exists():
        print("NOT FOUND:", path)
        continue

    try:

        xl = pd.ExcelFile(path)

        print("Sheets:", xl.sheet_names)

        file_info = {
            "file": filename,
            "sheets": {}
        }

        for sheet in xl.sheet_names:

            print("\n" + "-" * 90)
            print("SHEET:", sheet)
            print("-" * 90)

            raw = pd.read_excel(
                path,
                sheet_name=sheet,
                header=None
            )

            print(
                "Shape:",
                f"{len(raw):,} rows x {len(raw.columns)} columns"
            )

            # Show first 12 rows exactly as exported.
            print("\nFIRST 12 RAW ROWS:")
            print(
                raw.head(12).to_string(
                    index=True,
                    header=False,
                    max_cols=20
                )
            )

            # Detect likely header rows.
            candidates = []

            for i in range(
                min(20, len(raw))
            ):

                values = [
                    str(v).strip().lower()
                    for v in raw.iloc[i].tolist()
                    if pd.notna(v)
                ]

                if not values:
                    continue

                joined = " | ".join(values)

                keywords = [
                    "date",
                    "rate",
                    "yield",
                    "maturity",
                    "tenor",
                    "price",
                    "index",
                    "inflation",
                    "exchange",
                    "currency",
                    "reserve",
                    "value",
                    "amount",
                    "category",
                    "security"
                ]

                score = sum(
                    1
                    for keyword in keywords
                    if keyword in joined
                )

                if score > 0:
                    candidates.append({
                        "row": i,
                        "score": score,
                        "values": values
                    })

            print("\nLIKELY HEADER ROWS:")

            if candidates:

                for candidate in candidates:

                    print(
                        f"ROW {candidate['row']} "
                        f"(score {candidate['score']}):"
                    )

                    print(
                        "  ",
                        " | ".join(
                            candidate["values"]
                        )
                    )

            else:

                print("  None detected")

            # Read with a few candidate header rows.
            structures = []

            for header_row in [
                0, 1, 2, 3, 4, 5, 6, 7
            ]:

                if header_row >= len(raw):
                    continue

                try:

                    df = pd.read_excel(
                        path,
                        sheet_name=sheet,
                        header=header_row
                    )

                    # Remove entirely empty columns.
                    df = df.dropna(
                        axis=1,
                        how="all"
                    )

                    cols = [
                        str(c)
                        for c in df.columns
                    ]

                    meaningful = sum(
                        any(
                            keyword in c.lower()
                            for keyword in [
                                "date",
                                "rate",
                                "yield",
                                "maturity",
                                "tenor",
                                "price",
                                "index",
                                "inflation",
                                "exchange",
                                "currency",
                                "reserve",
                                "value",
                                "amount",
                                "security",
                                "category"
                            ]
                        )
                        for c in cols
                    )

                    structures.append({
                        "header_row": header_row,
                        "columns": cols,
                        "meaningful_column_count": meaningful
                    })

                except Exception:
                    pass

            structures = sorted(
                structures,
                key=lambda x: (
                    x["meaningful_column_count"],
                    -x["header_row"]
                ),
                reverse=True
            )

            print("\nBEST HEADER CANDIDATES:")

            for structure in structures[:3]:

                print(
                    f"Header row {structure['header_row']} "
                    f"| meaningful columns "
                    f"{structure['meaningful_column_count']}"
                )

                for col in structure["columns"]:
                    print(
                        "   -",
                        repr(col)
                    )

            file_info["sheets"][sheet] = {
                "raw_rows": len(raw),
                "raw_columns": len(raw.columns),
                "header_candidates": candidates,
                "best_structures": structures[:3]
            }

        audit[filename] = file_info

    except Exception as exc:

        print(
            "ERROR:",
            exc
        )

        audit[filename] = {
            "error": str(exc)
        }

path = OUT / "rock_schema_audit.json"

path.write_text(
    json.dumps(
        audit,
        indent=2,
        default=str
    ),
    encoding="utf-8"
)

print("\n" + "=" * 100)
print("SCHEMA AUDIT COMPLETE")
print("=" * 100)

print("\nSaved:")
print(path)

print(
    "\nDo NOT rebuild the database yet. "
    "We will use these actual Rock column structures "
    "to create explicit dataset-specific loaders."
)
