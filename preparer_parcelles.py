"""Étape 3/3 — Convertit le CSV exporté par Earth Engine au format du notebook.

    python preparer_parcelles.py data/series_sentinel_rdc.csv

Produit `data/parcelles.parquet`. Le notebook classification_cultures.ipynb bascule
alors tout seul sur les vraies données à sa prochaine exécution.
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
        raise SystemExit(f"Usage : python {Path(__file__).name} <csv exporté par GEE>")

    source = Path(sys.argv[1])
    if not source.exists():
        raise SystemExit(f"{source} introuvable")

    donnees = pd.read_csv(source)
    print(f"{len(donnees)} lignes lues depuis {source}")

    attendues = [f"{bande}_{mois:02d}" for mois in MOIS for bande in BANDES_S2 + BANDES_S1]
    manquantes = [colonne for colonne in ["classe", "bloc"] + attendues
                  if colonne not in donnees.columns]
    if manquantes:
        raise SystemExit(f"Colonnes absentes du CSV : {manquantes}")

    donnees = donnees[["classe", "bloc"] + attendues]

    # sampleRegions écarte les points dont une bande est masquée : on le constate ici
    # plutôt que de laisser des NaN atteindre l'entraînement.
    avant = len(donnees)
    donnees = donnees.dropna()
    if avant != len(donnees):
        print(f"⚠️  {avant - len(donnees)} points écartés (bandes manquantes, nuages)")

    donnees["bloc"] = donnees["bloc"].astype(int)

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    donnees.to_parquet(SORTIE, index=False)

    print(f"\n{SORTIE} écrit : {len(donnees)} parcelles, {donnees['bloc'].nunique()} blocs")
    print(donnees["classe"].value_counts().to_string())

    minimum = donnees["classe"].value_counts().min()
    if minimum < 50:
        print(
            f"\n⚠️  La classe la plus rare n'a que {minimum} points. "
            "En dessous d'une cinquantaine, les scores par classe ne veulent plus dire grand-chose."
        )


if __name__ == "__main__":
    main()
