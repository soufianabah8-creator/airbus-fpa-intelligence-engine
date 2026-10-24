from pathlib import Path

import pandas as pd


financial_path = Path(
    "data/processed/quarterly_financial_analysis.csv"
)

drivers_path = Path(
    "data/processed/quarterly_operational_drivers.csv"
)

output_path = Path(
    "data/processed/quarterly_driver_analysis.csv"
)


# --------------------------------------------------
# LECTURE DES DONNEES
# --------------------------------------------------

financials = pd.read_csv(
    financial_path
)

drivers = pd.read_csv(
    drivers_path
)


# --------------------------------------------------
# PASSAGE DES DRIVERS EN FORMAT LARGE
# --------------------------------------------------
# Avant :
#
# 2025 | Q1 | Commercial Aircraft Deliveries | 136
# 2025 | Q1 | Net Commercial Orders          | 204
#
# Après :
#
# 2025 | Q1 | Deliveries | Net Orders | Backlog | ...


drivers_wide = (
    drivers.pivot_table(
        index=[
            "year",
            "quarter",
        ],
        columns="driver",
        values="value",
        aggfunc="first",
    )
    .reset_index()
)


drivers_wide.columns.name = None


drivers_wide = drivers_wide.rename(
    columns={
        "Commercial Aircraft Deliveries": (
            "deliveries"
        ),
        "Gross Commercial Orders": (
            "gross_orders"
        ),
        "Net Commercial Orders": (
            "net_orders"
        ),
        "Commercial Aircraft Backlog": (
            "backlog"
        ),
    }
)


# --------------------------------------------------
# FUSION FINANCE + OPERATIONS
# --------------------------------------------------

analysis = financials.merge(
    drivers_wide,
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


analysis[
    "quarter_number"
] = analysis[
    "quarter"
].map(
    quarter_order
)


analysis = analysis.sort_values(
    by=[
        "year",
        "quarter_number",
    ]
).reset_index(
    drop=True
)


# --------------------------------------------------
# ANALYSE DES LIVRAISONS
# --------------------------------------------------

analysis[
    "deliveries_yoy_pct"
] = (
    (
        analysis["deliveries"]
        / analysis["deliveries"].shift(4)
    )
    - 1
) * 100


analysis[
    "deliveries_qoq_pct"
] = (
    (
        analysis["deliveries"]
        / analysis["deliveries"].shift(1)
    )
    - 1
) * 100


# --------------------------------------------------
# COMMANDES
# --------------------------------------------------
# Pour les commandes nettes, on évite volontairement
# un % YoY.
#
# Les commandes peuvent être faibles, nulles,
# voire négatives après annulations.
#
# Un écart absolu est donc plus lisible.


analysis[
    "net_orders_yoy_change"
] = (
    analysis["net_orders"]
    - analysis["net_orders"].shift(4)
)


analysis[
    "gross_orders_yoy_change"
] = (
    analysis["gross_orders"]
    - analysis["gross_orders"].shift(4)
)


# --------------------------------------------------
# BACKLOG
# --------------------------------------------------

analysis[
    "backlog_yoy_pct"
] = (
    (
        analysis["backlog"]
        / analysis["backlog"].shift(4)
    )
    - 1
) * 100


# --------------------------------------------------
# ORDER-TO-DELIVERY RATIO
# --------------------------------------------------
# Exemple :
#
# ratio = 2
# → Airbus reçoit 2 commandes nettes
#   pour 1 avion livré sur le trimestre.


analysis[
    "net_order_to_delivery_ratio"
] = (
    analysis["net_orders"]
    / analysis["deliveries"]
)


# --------------------------------------------------
# REVENUE PAR LIVRAISON - PROXY
# --------------------------------------------------
# ATTENTION :
#
# Revenue = chiffre d'affaires consolidé Airbus.
#
# Deliveries = uniquement avions commerciaux.
#
# Donc ce ratio N'EST PAS le prix moyen d'un avion.
#
# Il sert uniquement de proxy analytique pour voir
# si le CA évolue plus vite ou moins vite que
# le volume de livraisons.


analysis[
    "revenue_per_delivery_proxy_eur_m"
] = (
    analysis["Revenue"]
    / analysis["deliveries"]
)


# --------------------------------------------------
# ECART ENTRE CROISSANCE DU CA ET LIVRAISONS
# --------------------------------------------------
# Exemple :
#
# Revenue YoY       +20 %
# Deliveries YoY    +10 %
#
# Gap = +10 pts
#
# Cela suggère que le CA évolue plus vite
# que les seuls volumes de livraisons.
#
# Ce n'est PAS une preuve de causalité :
# mix, prix, FX, services et autres divisions
# peuvent également intervenir.


analysis[
    "revenue_vs_deliveries_growth_gap_pts"
] = (
    analysis["revenue_yoy_pct"]
    - analysis["deliveries_yoy_pct"]
)


# --------------------------------------------------
# ARRONDIS
# --------------------------------------------------

percentage_columns = [
    "deliveries_yoy_pct",
    "deliveries_qoq_pct",
    "backlog_yoy_pct",
    "net_order_to_delivery_ratio",
    "revenue_per_delivery_proxy_eur_m",
    "revenue_vs_deliveries_growth_gap_pts",
]


analysis[
    percentage_columns
] = analysis[
    percentage_columns
].round(1)


# --------------------------------------------------
# COLONNES FINALES
# --------------------------------------------------

columns = [
    "year",
    "quarter",
    "period",

    "Revenue",
    "revenue_yoy_pct",

    "EBIT Adjusted",
    "ebit_adjusted_margin_pct",
    "ebit_adjusted_yoy_pct",

    "Free Cash Flow",

    "deliveries",
    "deliveries_yoy_pct",
    "deliveries_qoq_pct",

    "gross_orders",
    "gross_orders_yoy_change",

    "net_orders",
    "net_orders_yoy_change",

    "backlog",
    "backlog_yoy_pct",

    "net_order_to_delivery_ratio",

    "revenue_per_delivery_proxy_eur_m",

    "revenue_vs_deliveries_growth_gap_pts",
]


analysis = analysis[
    columns
]


# --------------------------------------------------
# EXPORT
# --------------------------------------------------

output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)


analysis.to_csv(
    output_path,
    index=False,
)


# --------------------------------------------------
# AFFICHAGE
# --------------------------------------------------

print(
    "\n--- FINANCIAL & OPERATIONAL DRIVER ANALYSIS ---"
)


display_columns = [
    "period",
    "Revenue",
    "revenue_yoy_pct",
    "deliveries",
    "deliveries_yoy_pct",
    "EBIT Adjusted",
    "ebit_adjusted_margin_pct",
    "net_orders",
    "backlog",
    "revenue_vs_deliveries_growth_gap_pts",
]


print(
    analysis[
        display_columns
    ].to_string(
        index=False
    )
)


print(
    f"\nFichier cree : {output_path}"
)