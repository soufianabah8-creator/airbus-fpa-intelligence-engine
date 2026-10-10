import re
from pathlib import Path

import pandas as pd
import pdfplumber


input_folder = Path("data/raw/airbus_financials")
output_path = Path("data/processed/financial_actuals.csv")


metrics = {
    "Revenues": (
        "Revenue",
        "Revenue",
        "EUR_m"
    ),

    "EBIT Adjusted": (
        "EBIT Adjusted",
        "EBIT Adjusted",
        "EUR_m"
    ),

    "EBIT (reported)": (
        "EBIT Reported",
        "EBIT Reported",
        "EUR_m"
    ),

    "Research & Development expenses": (
        "R&D Expenses",
        "R&D Expenses",
        "EUR_m"
    ),

    "Net Income": (
        "Net Income",
        "Net Income",
        "EUR_m"
    ),

    "Earnings Per Share": (
        "EPS",
        "EPS",
        "EUR_per_share"
    ),

    "Free Cash Flow (FCF)": (
        "Free Cash Flow",
        "Free Cash Flow",
        "EUR_m"
    ),

    "Free Cash Flow before M&A and Customer Financing": (
        "FCF before M&A and Customer Financing",
        "Guidance FCF",
        "EUR_m"
    ),

    "Free Cash Flow before Customer Financing": (
        "FCF before Customer Financing",
        "Guidance FCF",
        "EUR_m"
    ),

    "Order intake": (
        "Order Intake",
        "Order Intake",
        "EUR_m"
    ),

    "Order book": (
        "Order Book",
        "Order Book",
        "EUR_m"
    ),

    "Net Cash position": (
        "Net Cash",
        "Net Cash",
        "EUR_m"
    ),

    "Number of employees": (
        "Employees",
        "Employees",
        "count"
    ),
}


def normalize_key(value):

    return re.sub(
        r"[^a-zA-Z0-9]",
        "",
        value
    ).lower()


def clean_number(value):

    first_value = value.split("\n")[0]

    cleaned_value = (
        first_value
        .replace(",", "")
        .strip()
    )

    # Permet aussi de gérer un nombre écrit (2,485)
    if (
        cleaned_value.startswith("(")
        and cleaned_value.endswith(")")
    ):
        cleaned_value = "-" + cleaned_value[1:-1]

    return float(cleaned_value)


def detect_period(header_value):

    key = normalize_key(header_value)

    if key.startswith("fy"):
        return "FY"

    if key.startswith("q1"):
        return "Q1"

    if key.startswith("h1") or key.startswith("hy"):
        return "H1"

    if key.startswith("9m"):
        return "9M"

    if key.startswith("31dec"):
        return "YE"

    if (
        key.startswith("31march")
        or key.startswith("31mar")
    ):
        return "Q1_END"

    if key.startswith("30june"):
        return "H1_END"

    if (
        key.startswith("30september")
        or key.startswith("30sep")
    ):
        return "9M_END"

    return None


results = []


# Maintenant on prend FY, Q1, H1, 9M...
pdf_files = sorted(
    input_folder.glob(
        "airbus_*_results_press_release.pdf"
    )
)


for pdf_file in pdf_files:

    print(f"Lecture : {pdf_file.name}")

    with pdfplumber.open(pdf_file) as pdf:

        for page in pdf.pages:

            tables = page.extract_tables()

            for table in tables:

                if not table:
                    continue

                header = table[0]

                if len(header) < 2:
                    continue

                table_name = header[0]
                header_value = header[1]

                if (
                    table_name is None
                    or header_value is None
                ):
                    continue

                table_key = normalize_key(
                    table_name
                )

                if table_key != "consolidatedairbus":
                    continue

                year_match = re.search(
                    r"20\d{2}",
                    header_value
                )

                if not year_match:
                    continue

                year = int(
                    year_match.group()
                )

                period = detect_period(
                    header_value
                )

                if period is None:
                    continue

                for row in table[1:]:

                    if len(row) < 2:
                        continue

                    raw_metric = row[0]
                    raw_value = row[1]

                    if (
                        raw_metric is None
                        or raw_value is None
                    ):
                        continue

                    metric_key = normalize_key(
                        raw_metric
                    )

                    for (
                        search_name,
                        metric_info
                    ) in metrics.items():

                        search_key = normalize_key(
                            search_name
                        )

                        if metric_key.startswith(
                            search_key
                        ):

                            (
                                final_name,
                                kpi_family,
                                unit
                            ) = metric_info

                            value = clean_number(
                                raw_value
                            )

                            results.append(
                                {
                                    "year": year,
                                    "period": period,
                                    "metric": final_name,
                                    "kpi_family": kpi_family,
                                    "value": value,
                                    "unit": unit,
                                    "source_file": pdf_file.name,
                                }
                            )

                            break


df = pd.DataFrame(results)


df = df.drop_duplicates(
    subset=[
        "year",
        "period",
        "metric"
    ],
    keep="first",
)


# -----------------------------------------
# DATA QUALITY CONTROL
# -----------------------------------------

expected_by_period = {

    "FY": {
        "Revenue",
        "EBIT Adjusted",
        "EBIT Reported",
        "R&D Expenses",
        "Net Income",
        "EPS",
        "Free Cash Flow",
        "Guidance FCF",
        "Order Intake",
    },

    "YE": {
        "Order Book",
        "Net Cash",
        "Employees",
    },

    "Q1": {
        "Revenue",
        "EBIT Adjusted",
        "EBIT Reported",
        "R&D Expenses",
        "Net Income",
        "EPS",
        "Free Cash Flow",
        "Guidance FCF",
    },

    "Q1_END": {
        "Net Cash",
        "Employees",
    },

    "H1": {
        "Revenue",
        "EBIT Adjusted",
        "EBIT Reported",
        "R&D Expenses",
        "Net Income",
        "EPS",
        "Free Cash Flow",
        "Guidance FCF",
    },

    "H1_END": {
        "Net Cash",
        "Employees",
    },

    "9M": {
        "Revenue",
        "EBIT Adjusted",
        "EBIT Reported",
        "R&D Expenses",
        "Net Income",
        "EPS",
        "Free Cash Flow",
        "Guidance FCF",
    },

    "9M_END": {
        "Net Cash",
        "Employees",
    },
}


print("\n--- DATA QUALITY CONTROL ---")


for (year, period), period_data in df.groupby(
    ["year", "period"]
):

    expected = expected_by_period.get(
        period
    )

    if expected is None:
        continue

    found = set(
        period_data["kpi_family"]
    )

    missing = expected - found

    print(
        f"\n{year} {period} : "
        f"{len(found & expected)}/"
        f"{len(expected)} KPI trouvés"
    )

    if not missing:

        print(
            "✅ Toutes les métriques "
            "attendues sont présentes."
        )

    else:

        print(
            "⚠️ Métriques manquantes :"
        )

        for metric in sorted(missing):

            print(
                f"   - {metric}"
            )


df = df.sort_values(
    by=[
        "year",
        "period",
        "kpi_family"
    ]
)


output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)


df.to_csv(
    output_path,
    index=False,
)


print(
    "\n--- EXTRACTION TERMINÉE ---"
)

print(df)

print(
    f"\nFichier créé : {output_path}"
)