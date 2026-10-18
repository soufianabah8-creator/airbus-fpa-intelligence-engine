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
        "EUR_m",
    ),

    "EBIT Adjusted": (
        "EBIT Adjusted",
        "EBIT Adjusted",
        "EUR_m",
    ),

    "EBIT (reported)": (
        "EBIT Reported",
        "EBIT Reported",
        "EUR_m",
    ),

    "Research & Development expenses": (
        "R&D Expenses",
        "R&D Expenses",
        "EUR_m",
    ),

    "Net Income": (
        "Net Income",
        "Net Income",
        "EUR_m",
    ),

    "Earnings Per Share": (
        "EPS",
        "EPS",
        "EUR_per_share",
    ),

    "Free Cash Flow (FCF)": (
        "Free Cash Flow",
        "Free Cash Flow",
        "EUR_m",
    ),

    "Free Cash Flow before M&A and Customer Financing": (
        "FCF before M&A and Customer Financing",
        "Guidance FCF",
        "EUR_m",
    ),

    "Free Cash Flow before Customer Financing": (
        "FCF before Customer Financing",
        "Guidance FCF",
        "EUR_m",
    ),

    "Order intake": (
        "Order Intake",
        "Order Intake",
        "EUR_m",
    ),

    "Order book": (
        "Order Book",
        "Order Book",
        "EUR_m",
    ),

    "Net Cash position": (
        "Net Cash",
        "Net Cash",
        "EUR_m",
    ),

    "Number of employees": (
        "Employees",
        "Employees",
        "count",
    ),
}


def normalize_key(value):

    return re.sub(
        r"[^a-zA-Z0-9]",
        "",
        value,
    ).lower()


def clean_number(value):

    first_value = value.split("\n")[0]

    cleaned_value = (
        first_value
        .replace(",", "")
        .strip()
    )

    if (
        cleaned_value.startswith("(")
        and cleaned_value.endswith(")")
    ):
        cleaned_value = (
            "-"
            + cleaned_value[1:-1]
        )

    return float(cleaned_value)


def detect_period(header_value):

    key = normalize_key(header_value)

    if key.startswith("fy"):
        return "FY"

    if key.startswith("q1"):
        return "Q1"

    if (
        key.startswith("h1")
        or key.startswith("hy")
    ):
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


def detect_file_period_and_year(filename):

    match = re.search(
        r"airbus_(q1|h1|9m|fy)_(20\d{2})_results_press_release\.pdf",
        filename.lower(),
    )

    if not match:
        return None, None

    file_period = match.group(1).upper()
    year = int(match.group(2))

    return file_period, year


def add_result(
    year,
    period,
    final_name,
    kpi_family,
    value,
    unit,
    source_file,
):

    results.append(
        {
            "year": year,
            "period": period,
            "metric": final_name,
            "kpi_family": kpi_family,
            "value": value,
            "unit": unit,
            "source_file": source_file,
        }
    )


def extract_text_value(
    text,
    pattern,
):

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    try:
        return clean_number(
            match.group(1)
        )

    except ValueError:
        return None


def extract_from_text_fallback(
    pdf,
    pdf_file,
    year,
    period,
):

    print(
        f"  -> Fallback texte utilise "
        f"pour {pdf_file.name}"
    )

    full_text = " ".join(
        page.extract_text() or ""
        for page in pdf.pages
    )

    full_text = re.sub(
        r"\s+",
        " ",
        full_text,
    )


    text_metrics = [
        (
            r"Revenues,\s*in millions\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "Revenue",
            "Revenue",
            "EUR_m",
        ),

        (
            r"EBIT Adjusted,\s*in millions\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "EBIT Adjusted",
            "EBIT Adjusted",
            "EUR_m",
        ),

        (
            r"EBIT \(reported\),\s*in millions\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "EBIT Reported",
            "EBIT Reported",
            "EUR_m",
        ),

        (
            r"Research\s*&\s*Development expenses,"
            r"\s*in(?:\s+millions)?\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "R&D Expenses",
            "R&D Expenses",
            "EUR_m",
        ),

        (
            r"Net Income(?:\(\d+\))?,"
            r"\s*in millions\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "Net Income",
            "Net Income",
            "EUR_m",
        ),

        (
            r"Earnings Per Share\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "EPS",
            "EPS",
            "EUR_per_share",
        ),

        (
            r"Free Cash Flow \(FCF\),"
            r"\s*in millions\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "Free Cash Flow",
            "Free Cash Flow",
            "EUR_m",
        ),
    ]


    for (
        pattern,
        final_name,
        kpi_family,
        unit,
    ) in text_metrics:

        value = extract_text_value(
            full_text,
            pattern,
        )

        if value is not None:

            add_result(
                year,
                period,
                final_name,
                kpi_family,
                value,
                unit,
                pdf_file.name,
            )


    guidance_patterns = [
        (
            r"Free Cash Flow before M&A and\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "FCF before M&A and Customer Financing",
        ),

        (
            r"Free Cash Flow before M&A and "
            r"Customer Financing,\s*in millions\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "FCF before M&A and Customer Financing",
        ),

        (
            r"Free Cash Flow before "
            r"Customer Financing,\s*in millions\s+"
            r"(\(?-?[\d,]+(?:\.\d+)?\)?)",
            "FCF before Customer Financing",
        ),
    ]


    for (
        pattern,
        metric_name,
    ) in guidance_patterns:

        value = extract_text_value(
            full_text,
            pattern,
        )

        if value is not None:

            add_result(
                year,
                period,
                metric_name,
                "Guidance FCF",
                value,
                "EUR_m",
                pdf_file.name,
            )

            break


    end_period_map = {
        "Q1": "Q1_END",
        "H1": "H1_END",
        "9M": "9M_END",
    }

    end_period = end_period_map.get(
        period
    )


    if end_period:

        net_cash = extract_text_value(
            full_text,
            (
                r"Net Cash position,"
                r"\s*in millions of Euro\s+"
                r"(\(?-?[\d,]+(?:\.\d+)?\)?)"
            ),
        )

        if net_cash is not None:

            add_result(
                year,
                end_period,
                "Net Cash",
                "Net Cash",
                net_cash,
                "EUR_m",
                pdf_file.name,
            )


        employees = extract_text_value(
            full_text,
            (
                r"Number of employees\s+"
                r"(\(?-?[\d,]+(?:\.\d+)?\)?)"
            ),
        )

        if employees is not None:

            add_result(
                year,
                end_period,
                "Employees",
                "Employees",
                employees,
                "count",
                pdf_file.name,
            )


results = []


pdf_files = sorted(
    input_folder.glob(
        "airbus_*_results_press_release.pdf"
    )
)


for pdf_file in pdf_files:

    print(
        f"Lecture : {pdf_file.name}"
    )

    file_period, file_year = (
        detect_file_period_and_year(
            pdf_file.name
        )
    )

    with pdfplumber.open(
        pdf_file
    ) as pdf:

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

                if (
                    table_key
                    != "consolidatedairbus"
                ):
                    continue

                year_match = re.search(
                    r"20\d{2}",
                    header_value,
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
                        metric_info,
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
                                unit,
                            ) = metric_info

                            try:

                                value = clean_number(
                                    raw_value
                                )

                            except ValueError:

                                continue

                            add_result(
                                year,
                                period,
                                final_name,
                                kpi_family,
                                value,
                                unit,
                                pdf_file.name,
                            )

                            break


        # Fallback pour les anciens PDF mal structures
        if (
            file_period
            in {"Q1", "H1", "9M"}
            and file_year is not None
        ):

            source_results = [
                row
                for row in results
                if (
                    row["source_file"]
                    == pdf_file.name
                )
            ]

            # Q1 / H1 / 9M doivent normalement
            # produire 8 KPI de flux + 2 snapshots.
            if len(source_results) < 10:

                extract_from_text_fallback(
                    pdf,
                    pdf_file,
                    file_year,
                    file_period,
                )


df = pd.DataFrame(
    results
)


df = df.drop_duplicates(
    subset=[
        "year",
        "period",
        "metric",
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


print(
    "\n--- DATA QUALITY CONTROL ---"
)


for (
    year,
    period,
), period_data in df.groupby(
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
        f"{len(expected)} KPI trouves"
    )

    if not missing:

        print(
            "OK - Toutes les metriques "
            "attendues sont presentes."
        )

    else:

        print(
            "ATTENTION - Metriques manquantes :"
        )

        for metric in sorted(
            missing
        ):

            print(
                f"   - {metric}"
            )


df = df.sort_values(
    by=[
        "year",
        "period",
        "kpi_family",
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
    "\n--- EXTRACTION TERMINEE ---"
)

print(
    df
)

print(
    f"\nFichier cree : {output_path}"
)