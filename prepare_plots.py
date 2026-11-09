"""Step 3/3: converts the CSV exported by Earth Engine to the notebook's format.

    python prepare_plots.py data/series_sentinel_rdc.csv

Produces `data/parcelles.parquet`. The notebook crop_classification.ipynb then
switches to the real data on its own the next time it runs.
"""

import sys
from pathlib import Path

import pandas as pd

SORTIE = Path("data") / "parcelles.parquet"

BANDES_S2 = ["B2", "B3", "B4", "B8", "B11", "B12"]
BANDES_S1 = ["VV", "VH"]
MOIS = list(range(1, 13))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(f"Usage: python {Path(__file__).name} <csv exported by GEE>")

    source = Path(sys.argv[1])
    if not source.exists():
        raise SystemExit(f"{source} not found")

    donnees = pd.read_csv(source)
    print(f"{len(donnees)} rows read from {source}")

    attendues = [f"{bande}_{mois:02d}" for mois in MOIS for bande in BANDES_S2 + BANDES_S1]
    manquantes = [colonne for colonne in ["classe", "bloc"] + attendues
                  if colonne not in donnees.columns]
    if manquantes:
        raise SystemExit(f"Columns missing from the CSV: {manquantes}")

    donnees = donnees[["classe", "bloc"] + attendues]

    # sampleRegions drops points where a band is masked: we check it here
    # rather than let NaN values reach training.
    avant = len(donnees)
    donnees = donnees.dropna()
    if avant != len(donnees):
        print(f"⚠️  {avant - len(donnees)} points dropped (missing bands, clouds)")

    donnees["bloc"] = donnees["bloc"].astype(int)

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    donnees.to_parquet(SORTIE, index=False)

    print(f"\n{SORTIE} written: {len(donnees)} plots, {donnees['bloc'].nunique()} blocks")
    print(donnees["classe"].value_counts().to_string())

    minimum = donnees["classe"].value_counts().min()
    if minimum < 50:
        print(
            f"\n⚠️  The rarest class has only {minimum} points. "
            "Below about fifty, per-class scores no longer mean much."
        )


if __name__ == "__main__":
    main()
