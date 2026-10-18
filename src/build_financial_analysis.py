from pathlib import Path

import pandas as pd


input_path = Path(
    "data/processed/quarterly_actuals.csv"
)

output_path = Path(
    "data/processed/quarterly_financial_analysis.csv"
)


# --------------------------------------------------
# LECTURE DES ACTUALS TRIMESTRIELS
# --------------------------------------------------

df = pd.read_csv(input_path)


# --------------------------------------------------
# PASSAGE DU FORMAT LONG AU FORMAT LARGE
# --------------------------------------------------
# Avant :
# 2025 | Q1 | Revenue       | 13542
# 2025 | Q1 | EBIT Adjusted | 624
#
# Après :
# 2025 | Q1 | Revenue | EBIT Adjusted | Net Income | ...


financials = (
    df.pivot_table(
        index=[
            "year",
            "quarter",
        ],
        columns="kpi_family",
        values="value",
        aggfunc="first",
    )
    .reset_index()
)


financials.columns.name = None


# --------------------------------------------------
# INFORMATIONS DE TRAÇABILITÉ
# --------------------------------------------------

metadata = (
    df.groupby(
        [
            "year",
            "quarter",
        ],
        as_index=False,
    )
    .agg(
        data_type=(
            "data_type",
            "first",
        ),
        calculation=(
            "calculation",
            "first",
        ),
    )
)


financials = financials.merge(
    metadata,
    on=[
        "year",
        "quarter",
    ],
    how="left",
)


# --------------------------------------------------
# ORDRE CHRONOLOGIQUE
# --------------------------------------------------

quarter_order = {
    "Q1": 1,
    "Q2": 2,
    "Q3": 3,
    "Q4": 4,
}


financials["quarter_number"] = (
    financials["quarter"]
    .map(quarter_order)
)


financials["period"] = (
    financials["year"].astype(str)
    + "-"
    + financials["quarter"]
)


financials = financials.sort_values(
    by=[
        "year",
        "quarter_number",
    ]
).reset_index(drop=True)


# --------------------------------------------------
# MARGES
# --------------------------------------------------

financials[
    "ebit_adjusted_margin_pct"
] = (
    financials["EBIT Adjusted"]
    / financials["Revenue"]
    * 100
)


financials[
    "rd_pct_revenue"
] = (
    financials["R&D Expenses"]
    / financials["Revenue"]
    * 100
)


# --------------------------------------------------
# ANALYSE YoY
# Comparaison avec le même trimestre de l'année
# précédente : Q2 2026 vs Q2 2025 par exemple.
# --------------------------------------------------

financials[
    "revenue_yoy_pct"
] = (
    (
        financials["Revenue"]
        / financials["Revenue"].shift(4)
    )
    - 1
) * 100


financials[
    "ebit_adjusted_yoy_pct"
] = (
    (
        financials["EBIT Adjusted"]
        / financials["EBIT Adjusted"].shift(4)
    )
    - 1
) * 100


financials[
    "net_income_yoy_pct"
] = (
    (
        financials["Net Income"]
        / financials["Net Income"].shift(4)
    )
    - 1
) * 100


financials[
    "ebit_margin_yoy_change_pts"
] = (
    financials["ebit_adjusted_margin_pct"]
    - financials[
        "ebit_adjusted_margin_pct"
    ].shift(4)
)


# Pour le FCF, on préfère un écart absolu.
# Un % serait trompeur quand le FCF passe
# de négatif à positif.

financials[
    "fcf_yoy_change_eur_m"
] = (
    financials["Free Cash Flow"]
    - financials[
        "Free Cash Flow"
    ].shift(4)
)


# --------------------------------------------------
# ANALYSE QoQ
# Utile, mais secondaire car Airbus est saisonnier.
# --------------------------------------------------

financials[
    "revenue_qoq_pct"
] = (
    (
        financials["Revenue"]
        / financials["Revenue"].shift(1)
    )
    - 1
) * 100


financials[
    "ebit_adjusted_qoq_pct"
] = (
    (
        financials["EBIT Adjusted"]
        / financials[
            "EBIT Adjusted"
        ].shift(1)
    )
    - 1
) * 100


# --------------------------------------------------
# ARRONDIS
# --------------------------------------------------

percentage_columns = [
    "ebit_adjusted_margin_pct",
    "rd_pct_revenue",
    "revenue_yoy_pct",
    "ebit_adjusted_yoy_pct",
    "net_income_yoy_pct",
    "ebit_margin_yoy_change_pts",
    "revenue_qoq_pct",
    "ebit_adjusted_qoq_pct",
]


financials[
    percentage_columns
] = financials[
    percentage_columns
].round(1)


# --------------------------------------------------
# ORDRE FINAL DES COLONNES
# --------------------------------------------------

columns = [
    "year",
    "quarter",
    "period",
    "data_type",
    "calculation",
    "Revenue",
    "EBIT Adjusted",
    "ebit_adjusted_margin_pct",
    "EBIT Reported",
    "Net Income",
    "Free Cash Flow",
    "Guidance FCF",
    "R&D Expenses",
    "rd_pct_revenue",
    "revenue_yoy_pct",
    "ebit_adjusted_yoy_pct",
    "ebit_margin_yoy_change_pts",
    "net_income_yoy_pct",
    "fcf_yoy_change_eur_m",
    "revenue_qoq_pct",
    "ebit_adjusted_qoq_pct",
]


financials = financials[
    columns
]


# --------------------------------------------------
# EXPORT
# --------------------------------------------------

output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)


financials.to_csv(
    output_path,
    index=False,
)


print(
    "\n--- QUARTERLY FINANCIAL ANALYSIS ---"
)

print(
    financials.to_string(
        index=False
    )
)

print(
    f"\nFichier cree : {output_path}"
)