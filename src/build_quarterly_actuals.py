from pathlib import Path

import pandas as pd


input_path = Path(
    "data/processed/financial_actuals.csv"
)

output_path = Path(
    "data/processed/quarterly_actuals.csv"
)


# Ces KPI sont des flux :
# on peut donc calculer Q2 = H1 - Q1
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


# On récupère uniquement les données 2026 Q1 et H1
q1 = df[
    (df["year"] == 2026)
    & (df["period"] == "Q1")
    & (df["kpi_family"].isin(flow_metrics))
].copy()


h1 = df[
    (df["year"] == 2026)
    & (df["period"] == "H1")
    & (df["kpi_family"].isin(flow_metrics))
].copy()


# -----------------------------------------
# Q1 OFFICIEL
# -----------------------------------------

q1_output = q1[
    [
        "year",
        "kpi_family",
        "metric",
        "value",
        "unit",
        "source_file",
    ]
].copy()


q1_output["quarter"] = "Q1"
q1_output["data_type"] = "official"
q1_output["calculation"] = "Reported Q1"


# -----------------------------------------
# CALCUL Q2 = H1 - Q1
# -----------------------------------------

q2 = h1.merge(
    q1,
    on="kpi_family",
    suffixes=("_h1", "_q1"),
)


q2["value"] = (
    q2["value_h1"]
    - q2["value_q1"]
)


q2_output = pd.DataFrame(
    {
        "year": q2["year_h1"],
        "quarter": "Q2",
        "kpi_family": q2["kpi_family"],
        "metric": q2["metric_h1"],
        "value": q2["value"],
        "unit": q2["unit_h1"],
        "data_type": "calculated",
        "calculation": "H1 - Q1",
        "source_file": (
            q2["source_file_h1"]
            + " | "
            + q2["source_file_q1"]
        ),
    }
)


# -----------------------------------------
# DATASET FINAL
# -----------------------------------------

q1_output = q1_output[
    [
        "year",
        "quarter",
        "kpi_family",
        "metric",
        "value",
        "unit",
        "data_type",
        "calculation",
        "source_file",
    ]
]


quarterly_df = pd.concat(
    [
        q1_output,
        q2_output,
    ],
    ignore_index=True,
)


quarterly_df = quarterly_df.sort_values(
    by=[
        "year",
        "quarter",
        "kpi_family",
    ]
)


# -----------------------------------------
# DATA QUALITY CONTROL
# -----------------------------------------

print(
    "\n--- QUARTERLY DATA QUALITY CONTROL ---"
)


for quarter in ["Q1", "Q2"]:

    quarter_data = quarterly_df[
        quarterly_df["quarter"] == quarter
    ]

    found = set(
        quarter_data["kpi_family"]
    )

    missing = flow_metrics - found

    print(
        f"\n2026 {quarter} : "
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