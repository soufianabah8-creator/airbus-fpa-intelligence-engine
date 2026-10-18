from pathlib import Path

import pandas as pd


input_path = Path(
    "data/processed/financial_actuals.csv"
)

output_path = Path(
    "data/processed/quarterly_actuals.csv"
)


# KPI de flux :
# ils peuvent être reconstruits par différence
flow_metrics = {
    "Revenue",
    "EBIT Adjusted",
    "EBIT Reported",
    "R&D Expenses",
    "Net Income",
    "Free Cash Flow",
    "Guidance FCF",
}


df = pd.read_csv(input_path)

df = df[
    df["kpi_family"].isin(flow_metrics)
].copy()


quarterly_results = []


def get_period(year, period):

    return df[
        (df["year"] == year)
        & (df["period"] == period)
    ].copy()


def add_official_quarter(
    period_data,
    quarter,
):

    if period_data.empty:
        return

    output = period_data[
        [
            "year",
            "kpi_family",
            "metric",
            "value",
            "unit",
            "source_file",
        ]
    ].copy()

    output["quarter"] = quarter
    output["data_type"] = "official"
    output["calculation"] = f"Reported {quarter}"

    quarterly_results.append(output)


def add_calculated_quarter(
    current_period,
    previous_period,
    quarter,
    calculation,
):

    if (
        current_period.empty
        or previous_period.empty
    ):
        return

    merged = current_period.merge(
        previous_period,
        on="kpi_family",
        suffixes=("_current", "_previous"),
    )

    output = pd.DataFrame(
        {
            "year": merged["year_current"],
            "quarter": quarter,
            "kpi_family": merged["kpi_family"],
            "metric": merged["metric_current"],
            "value": (
                merged["value_current"]
                - merged["value_previous"]
            ),
            "unit": merged["unit_current"],
            "data_type": "calculated",
            "calculation": calculation,
            "source_file": (
                merged["source_file_current"]
                + " | "
                + merged["source_file_previous"]
            ),
        }
    )

    quarterly_results.append(output)


# --------------------------------------------------
# RECONSTRUCTION DES TRIMESTRES
# --------------------------------------------------

for year in sorted(df["year"].unique()):

    q1 = get_period(year, "Q1")
    h1 = get_period(year, "H1")
    m9 = get_period(year, "9M")
    fy = get_period(year, "FY")

    # Q1 = directement publié
    add_official_quarter(
        q1,
        "Q1",
    )

    # Q2 = H1 - Q1
    add_calculated_quarter(
        h1,
        q1,
        "Q2",
        "H1 - Q1",
    )

    # Q3 = 9M - H1
    add_calculated_quarter(
        m9,
        h1,
        "Q3",
        "9M - H1",
    )

    # Q4 = FY - 9M
    add_calculated_quarter(
        fy,
        m9,
        "Q4",
        "FY - 9M",
    )


# --------------------------------------------------
# DATASET FINAL
# --------------------------------------------------

quarterly_df = pd.concat(
    quarterly_results,
    ignore_index=True,
)


quarter_order = {
    "Q1": 1,
    "Q2": 2,
    "Q3": 3,
    "Q4": 4,
}


quarterly_df["quarter_order"] = (
    quarterly_df["quarter"]
    .map(quarter_order)
)


quarterly_df = quarterly_df.sort_values(
    by=[
        "year",
        "quarter_order",
        "kpi_family",
    ]
)


quarterly_df = quarterly_df.drop(
    columns="quarter_order"
)


# --------------------------------------------------
# DATA QUALITY CONTROL
# --------------------------------------------------

print(
    "\n--- QUARTERLY DATA QUALITY CONTROL ---"
)


for (
    year,
    quarter
), quarter_data in quarterly_df.groupby(
    ["year", "quarter"],
    sort=False,
):

    found = set(
        quarter_data["kpi_family"]
    )

    missing = flow_metrics - found

    print(
        f"\n{year} {quarter} : "
        f"{len(found)}/{len(flow_metrics)} "
        "KPI trouvés"
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


# --------------------------------------------------
# EXPORT
# --------------------------------------------------

output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)


quarterly_df.to_csv(
    output_path,
    index=False,
)


print(
    "\n--- QUARTERLY ACTUALS ---"
)

print(
    quarterly_df[
        [
            "year",
            "quarter",
            "kpi_family",
            "value",
            "unit",
            "data_type",
            "calculation",
        ]
    ].to_string(index=False)
)


print(
    f"\nFichier créé : {output_path}"
)