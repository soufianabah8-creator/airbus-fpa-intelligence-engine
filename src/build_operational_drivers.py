import re
from pathlib import Path

import pandas as pd
import pdfplumber


input_folder = Path(
    "data/raw/airbus_financials"
)

cumulative_output = Path(
    "data/processed/operational_drivers_cumulative.csv"
)

quarterly_output = Path(
    "data/processed/quarterly_operational_drivers.csv"
)


# --------------------------------------------------
# OUTILS
# --------------------------------------------------

def clean_number(value):

    return float(
        value
        .replace(",", "")
        .strip()
    )


def detect_file_period_and_year(filename):

    # Le "_" après la période est optionnel :
    # q1_2025 mais fy2025
    match = re.search(
        r"airbus_(q1|h1|9m|fy)_?"
        r"(20\d{2})_results_press_release\.pdf",
        filename.lower(),
    )

    if not match:
        return None, None

    period = match.group(1).upper()
    year = int(match.group(2))

    return period, year


def find_value(
    text,
    patterns,
):

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            return clean_number(
                match.group(1)
            )

    return None


# --------------------------------------------------
# REGEX DES DRIVERS
# --------------------------------------------------

delivery_patterns = [

    (
        r"(\d[\d,]*)"
        r"(?:\(\d+\))*"
        r"\s+commercial aircraft delivered"
    ),

    (
        r"A total of\s+"
        r"(\d[\d,]*)"
        r"(?:\(\d+\))*"
        r"\s+commercial aircraft were delivered"
    ),
]


gross_order_patterns = [

    (
        r"Gross commercial aircraft orders "
        r"(?:increased to|totalled|totaled)\s+"
        r"([\d,]+)"
    ),
]


net_order_patterns = [

    # Formulation classique :
    # "net orders of 889 aircraft after cancellations"

    (
        r"net orders (?:of\s+)?"
        r"([\d,]+)\s+aircraft "
        r"after cancellations"
    ),

    # Exemple Q1 2024 :
    # "with the same number of net orders"
    #
    # Ici net orders = gross orders.

    (
        r"Gross commercial aircraft orders "
        r"(?:increased to|totalled|totaled)\s+"
        r"([\d,]+).*?"
        r"with the same number of net orders"
    ),
]


backlog_patterns = [

    # Gère notamment :
    #
    # "amounted to 7,254 commercial aircraft"
    #
    # "amounted to a record 7,967
    # commercial aircraft"
    #
    # "amounted to 9,222(1)
    # commercial aircraft"
    #
    # "amounted to a year-end record of
    # 8,754 commercial aircraft"

    (
        r"order backlog "
        r"(?:amounted to|stood at)\s+"
        r"(?:"
            r"a\s+"
            r"(?:year-end\s+)?"
            r"record"
            r"(?:\s+of)?"
            r"\s+"
        r")?"
        r"([\d,]+)"
        r"(?:\s*\(\d+\))*"
        r"\s+commercial aircraft"
    ),
]


# --------------------------------------------------
# EXTRACTION DES PDF
# --------------------------------------------------

cumulative_rows = []


pdf_files = sorted(
    input_folder.glob(
        "airbus_*_results_press_release.pdf"
    )
)


for pdf_file in pdf_files:

    period, year = (
        detect_file_period_and_year(
            pdf_file.name
        )
    )

    if (
        period is None
        or year is None
    ):
        continue

    print(
        f"Lecture : {pdf_file.name}"
    )

    with pdfplumber.open(
        pdf_file
    ) as pdf:

        text = " ".join(
            page.extract_text() or ""
            for page in pdf.pages
        )


    text = re.sub(
        r"\s+",
        " ",
        text,
    )


    deliveries = find_value(
        text,
        delivery_patterns,
    )

    gross_orders = find_value(
        text,
        gross_order_patterns,
    )

    net_orders = find_value(
        text,
        net_order_patterns,
    )

    backlog = find_value(
        text,
        backlog_patterns,
    )


    drivers = [
        (
            "Commercial Aircraft Deliveries",
            deliveries,
            "flow",
        ),

        (
            "Gross Commercial Orders",
            gross_orders,
            "flow",
        ),

        (
            "Net Commercial Orders",
            net_orders,
            "flow",
        ),

        (
            "Commercial Aircraft Backlog",
            backlog,
            "snapshot",
        ),
    ]


    for (
        driver,
        value,
        driver_type,
    ) in drivers:

        if value is None:
            continue

        cumulative_rows.append(
            {
                "year": year,
                "period": period,
                "driver": driver,
                "driver_type": driver_type,
                "value": value,
                "unit": "aircraft",
                "source_file": pdf_file.name,
            }
        )


cumulative_df = pd.DataFrame(
    cumulative_rows
)


cumulative_df = cumulative_df.sort_values(
    by=[
        "year",
        "period",
        "driver",
    ]
)


# --------------------------------------------------
# CONTROLE QUALITE DES DONNEES CUMULEES
# --------------------------------------------------

expected_drivers = {
    "Commercial Aircraft Deliveries",
    "Gross Commercial Orders",
    "Net Commercial Orders",
    "Commercial Aircraft Backlog",
}


print(
    "\n--- OPERATIONAL DRIVERS DATA QUALITY ---"
)


for (
    year,
    period,
), period_data in cumulative_df.groupby(
    [
        "year",
        "period",
    ]
):

    found = set(
        period_data["driver"]
    )

    missing = (
        expected_drivers
        - found
    )

    print(
        f"\n{year} {period} : "
        f"{len(found)}/"
        f"{len(expected_drivers)} "
        "drivers trouves"
    )

    if not missing:

        print(
            "OK - Tous les drivers "
            "sont presents."
        )

    else:

        print(
            "ATTENTION - Drivers manquants :"
        )

        for driver in sorted(
            missing
        ):

            print(
                f"   - {driver}"
            )


# --------------------------------------------------
# EXPORT CUMULE
# --------------------------------------------------

cumulative_output.parent.mkdir(
    parents=True,
    exist_ok=True,
)


cumulative_df.to_csv(
    cumulative_output,
    index=False,
)


# --------------------------------------------------
# RECONSTRUCTION TRIMESTRIELLE
# --------------------------------------------------

quarterly_rows = []


flow_drivers = {
    "Commercial Aircraft Deliveries",
    "Gross Commercial Orders",
    "Net Commercial Orders",
}


def get_value(
    year,
    period,
    driver,
):

    selection = cumulative_df[
        (cumulative_df["year"] == year)
        & (
            cumulative_df["period"]
            == period
        )
        & (
            cumulative_df["driver"]
            == driver
        )
    ]

    if selection.empty:
        return None

    return float(
        selection.iloc[0]["value"]
    )


def get_source(
    year,
    period,
    driver,
):

    selection = cumulative_df[
        (cumulative_df["year"] == year)
        & (
            cumulative_df["period"]
            == period
        )
        & (
            cumulative_df["driver"]
            == driver
        )
    ]

    if selection.empty:
        return None

    return selection.iloc[0][
        "source_file"
    ]


period_structure = {

    "Q1": (
        "Q1",
        None,
        "Reported Q1",
    ),

    "Q2": (
        "H1",
        "Q1",
        "H1 - Q1",
    ),

    "Q3": (
        "9M",
        "H1",
        "9M - H1",
    ),

    "Q4": (
        "FY",
        "9M",
        "FY - 9M",
    ),
}


for year in sorted(
    cumulative_df["year"].unique()
):

    for (
        quarter,
        structure,
    ) in period_structure.items():

        current_period = structure[0]
        previous_period = structure[1]
        calculation = structure[2]


        # ------------------------------------------
        # FLUX
        # ------------------------------------------

        for driver in flow_drivers:

            current_value = get_value(
                year,
                current_period,
                driver,
            )

            if current_value is None:
                continue


            if previous_period is None:

                quarterly_value = (
                    current_value
                )

                data_type = "official"

                source_file = get_source(
                    year,
                    current_period,
                    driver,
                )

            else:

                previous_value = get_value(
                    year,
                    previous_period,
                    driver,
                )

                if previous_value is None:
                    continue

                quarterly_value = (
                    current_value
                    - previous_value
                )

                data_type = "calculated"

                source_file = (
                    get_source(
                        year,
                        current_period,
                        driver,
                    )
                    + " | "
                    + get_source(
                        year,
                        previous_period,
                        driver,
                    )
                )


            quarterly_rows.append(
                {
                    "year": year,
                    "quarter": quarter,
                    "driver": driver,
                    "driver_type": "flow",
                    "value": quarterly_value,
                    "unit": "aircraft",
                    "data_type": data_type,
                    "calculation": calculation,
                    "source_file": source_file,
                }
            )


        # ------------------------------------------
        # BACKLOG
        # ------------------------------------------
        # Le backlog est un stock.
        # On prend donc la valeur de fin de période.
        # On ne fait JAMAIS H1 - Q1 dessus.

        backlog = get_value(
            year,
            current_period,
            "Commercial Aircraft Backlog",
        )

        if backlog is not None:

            quarterly_rows.append(
                {
                    "year": year,
                    "quarter": quarter,
                    "driver": (
                        "Commercial Aircraft Backlog"
                    ),
                    "driver_type": "snapshot",
                    "value": backlog,
                    "unit": "aircraft",
                    "data_type": "official",
                    "calculation": (
                        f"End of {current_period}"
                    ),
                    "source_file": get_source(
                        year,
                        current_period,
                        (
                            "Commercial Aircraft "
                            "Backlog"
                        ),
                    ),
                }
            )


quarterly_df = pd.DataFrame(
    quarterly_rows
)


quarter_order = {
    "Q1": 1,
    "Q2": 2,
    "Q3": 3,
    "Q4": 4,
}


quarterly_df[
    "quarter_order"
] = quarterly_df[
    "quarter"
].map(
    quarter_order
)


quarterly_df = quarterly_df.sort_values(
    by=[
        "year",
        "quarter_order",
        "driver",
    ]
)


quarterly_df = quarterly_df.drop(
    columns=[
        "quarter_order",
    ]
)


# --------------------------------------------------
# CONTROLE QUALITE TRIMESTRIEL
# --------------------------------------------------

print(
    "\n--- QUARTERLY OPERATIONAL DRIVERS ---"
)


for (
    year,
    quarter,
), quarter_data in quarterly_df.groupby(
    [
        "year",
        "quarter",
    ],
    sort=False,
):

    found = set(
        quarter_data["driver"]
    )

    missing = (
        expected_drivers
        - found
    )

    print(
        f"\n{year} {quarter} : "
        f"{len(found)}/"
        f"{len(expected_drivers)} "
        "drivers trouves"
    )

    if not missing:

        print(
            "OK - Tous les drivers "
            "sont presents."
        )

    else:

        print(
            "ATTENTION - Drivers manquants :"
        )

        for driver in sorted(
            missing
        ):

            print(
                f"   - {driver}"
            )


# --------------------------------------------------
# EXPORT TRIMESTRIEL
# --------------------------------------------------

quarterly_df.to_csv(
    quarterly_output,
    index=False,
)


# --------------------------------------------------
# AFFICHAGE DES LIVRAISONS
# --------------------------------------------------

print(
    "\n--- LIVRAISONS TRIMESTRIELLES ---"
)


deliveries_view = quarterly_df[
    quarterly_df["driver"]
    == "Commercial Aircraft Deliveries"
][
    [
        "year",
        "quarter",
        "value",
        "data_type",
        "calculation",
    ]
]


print(
    deliveries_view.to_string(
        index=False
    )
)


print(
    f"\nFichier cree : "
    f"{cumulative_output}"
)

print(
    f"Fichier cree : "
    f"{quarterly_output}"
)