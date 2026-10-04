import re
from pathlib import Path

import pandas as pd
import pdfplumber


pdf_path = "data/raw/airbus_financials/airbus_fy2022_results_press_release.pdf"
output_path = "data/processed/financial_actuals.csv"


# Les métriques que nous voulons récupérer dans les tableaux Airbus
metrics = {
    "Revenues": ("Revenue", "EUR_m"),
    "EBIT Adjusted": ("EBIT Adjusted", "EUR_m"),
    "EBIT (reported)": ("EBIT Reported", "EUR_m"),
    "Research & Development expenses": ("R&D Expenses", "EUR_m"),
    "Net Income": ("Net Income", "EUR_m"),
    "Earnings Per Share": ("EPS", "EUR_per_share"),
    "Free Cash Flow (FCF)": ("Free Cash Flow", "EUR_m"),
    "Free Cash Flow before M&A and": (
        "FCF before M&A and Customer Financing",
        "EUR_m",
    ),
    "Order intake": ("Order Intake", "EUR_m"),
    "Order book": ("Order Book", "EUR_m"),
    "Net Cash position": ("Net Cash", "EUR_m"),
    "Number of employees": ("Employees", "count"),
}


def clean_number(value):
    """
    Transforme par exemple :
    '58,763' -> 58763
    '5.40'   -> 5.4

    Si une cellule contient plusieurs valeurs séparées
    par un retour à la ligne, on garde la première.
    """
    first_value = value.split("\n")[0]
    cleaned_value = first_value.replace(",", "")

    return float(cleaned_value)


results = []


with pdfplumber.open(pdf_path) as pdf:

    # On parcourt toutes les pages du PDF
    for page in pdf.pages:

        tables = page.extract_tables()

        # On parcourt tous les tableaux trouvés sur la page
        for table in tables:

            if not table:
                continue

            header = table[0]

            if len(header) < 2:
                continue

            table_name = header[0]
            header_value = header[1]

            if table_name is None or header_value is None:
                continue

            # On garde uniquement les tableaux consolidés Airbus
            if table_name.strip() != "Consolidated Airbus":
                continue

            # On détecte automatiquement l'année
            year_match = re.search(r"20\d{2}", header_value)

            if not year_match:
                continue

            year = int(year_match.group())

            # On détermine le type de période
            if header_value.startswith("FY"):
                period = "FY"

            elif header_value.startswith("31 Dec"):
                period = "YE"

            else:
                continue

            # On parcourt toutes les lignes du tableau
            for row in table[1:]:

                if len(row) < 2:
                    continue

                raw_metric = row[0]
                raw_value = row[1]

                if raw_metric is None or raw_value is None:
                    continue

                # Certaines cellules contiennent plusieurs lignes.
                # On prend la première ligne pour identifier la métrique.
                metric_name = raw_metric.split("\n")[0].strip()

                # On vérifie si cette métrique nous intéresse
                for search_name, metric_info in metrics.items():

                    if metric_name.startswith(search_name):

                        final_name, unit = metric_info

                        value = clean_number(raw_value)

                        results.append(
                            {
                                "year": year,
                                "period": period,
                                "metric": final_name,
                                "value": value,
                                "unit": unit,
                            }
                        )

                        break


# Transformation en tableau pandas
df = pd.DataFrame(results)


# Sécurité contre d'éventuels doublons
df = df.drop_duplicates(
    subset=["year", "period", "metric"],
    keep="first",
)


# Création automatique du dossier processed s'il n'existe pas
Path("data/processed").mkdir(
    parents=True,
    exist_ok=True,
)


# Affichage du résultat dans le terminal
print(df)


# Création automatique du CSV
df.to_csv(
    output_path,
    index=False,
)


print("\nExtraction terminée.")
print(f"Fichier créé : {output_path}")