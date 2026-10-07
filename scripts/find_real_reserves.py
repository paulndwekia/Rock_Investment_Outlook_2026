from pathlib import Path
import pandas as pd

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"

SEARCH_DIRS = [
    PROJECT / "data" / "canonical",
    PROJECT / "data" / "incoming",
    PROJECT / "data"
]

print("\n" + "=" * 90)
print("SEARCHING ROCK FILES FOR ACTUAL FOREX / RESERVE DATA")
print("=" * 90)

seen = set()

for folder in SEARCH_DIRS:

    if not folder.exists():
        continue

    for path in folder.rglob("*"):

        if not path.is_file():
            continue

        if path in seen:
            continue

        seen.add(path)

        name = path.name.lower()

        if not any(
            word in name
            for word in [
                "reserve",
                "forex",
                "foreign"
            ]
        ):
            continue

        print("\n" + "-" * 90)
        print("FILE:", path)
        print("-" * 90)

        try:

            if path.suffix.lower() == ".xlsx":

                xl = pd.ExcelFile(path)

                print(
                    "Sheets:",
                    xl.sheet_names
                )

                for sheet in xl.sheet_names:

                    df = pd.read_excel(
                        path,
                        sheet_name=sheet,
                        header=0
                    )

                    print(
                        f"\nSHEET: {sheet}"
                    )

                    print(
                        "Columns:",
                        list(df.columns)
                    )

                    print(
                        "Rows:",
                        len(df)
                    )

                    print(
                        "\nFirst 5 rows:"
                    )

                    print(
                        df.head(5).to_string(
                            index=False
                        )
                    )

            elif path.suffix.lower() == ".csv":

                df = pd.read_csv(
                    path,
                    low_memory=False
                )

                print(
                    "Columns:",
                    list(df.columns)
                )

                print(
                    "Rows:",
                    len(df)
                )

                print(
                    "\nFirst 5 rows:"
                )

                print(
                    df.head(5).to_string(
                        index=False
                    )
                )

        except Exception as exc:

            print(
                "ERROR:",
                exc
            )

print("\n" + "=" * 90)
print("SEARCH COMPLETE")
print("=" * 90)

print(
    "\nLook for a file whose columns contain something like:"
)

print(
    "Date | Reserve type | actual reserve/value measure"
)

print(
    "\nDo not rebuild the website yet."
)
