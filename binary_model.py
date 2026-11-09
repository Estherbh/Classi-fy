"""Step 4/4: trains and evaluates the final model, palm against no palm.

    python binary_model.py

Reads `data/parcelles.parquet` produced by prepare_plots.py and writes
`data/modele_palmier.joblib`.

Why two classes and not three. The notebook crop_classification.ipynb evaluates
Descals' three classes and tops out at 0.561 macro F1: industrial palm and
smallholder palm are confused with each other in a third of cases, because what
tells them apart is the geometry of the plantations, not the per-pixel signal. Merging
the two answers the operational question, where is there palm, and raises the
macro F1 to 0.817.

The features and the cross-validation are identical to the notebook's, so that
the two numbers stay comparable.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import (GroupKFold, StratifiedGroupKFold, StratifiedKFold,
                                     cross_val_score)

DOSSIER = Path("data")
FICHIER_PARCELLES = DOSSIER / "parcelles.parquet"
FICHIER_MODELE = DOSSIER / "modele_palmier.joblib"

# Six Sentinel-2 optical bands, two Sentinel-1 radar bands.
BANDES = ["B2", "B3", "B4", "B8", "B11", "B12", "VV", "VH"]
MOIS = list(range(1, 13))
CLASSES = ["palmier", "pas_de_palmier"]


def _indice(df, bande_a, bande_b):
    """Normalised index (a - b) / (a + b), computed month by month."""
    return pd.DataFrame(
        {
            mois: (df[f"{bande_a}_{mois:02d}"] - df[f"{bande_b}_{mois:02d}"])
            / (df[f"{bande_a}_{mois:02d}"] + df[f"{bande_b}_{mois:02d}"])
            for mois in MOIS
        }
    )


def construire_variables(df):
    """Summarises the 96 monthly measurements into 34 annual features.

    Identical to the notebook's function. Raw reflectances change from one
    image to the next; indices and their annual statistics do not.
    """
    variables = pd.DataFrame(index=df.index)
    series = {
        "ndvi": _indice(df, "B8", "B4"),
        "ndwi": _indice(df, "B3", "B8"),
        "nbr": _indice(df, "B8", "B12"),
    }
    for nom, serie in series.items():
        variables[f"{nom}_moy"] = serie.mean(axis=1)
        variables[f"{nom}_ecart_type"] = serie.std(axis=1)
        variables[f"{nom}_min"] = serie.min(axis=1)
        variables[f"{nom}_max"] = serie.max(axis=1)
        variables[f"{nom}_amplitude"] = variables[f"{nom}_max"] - variables[f"{nom}_min"]
    variables["mois_pic_ndvi"] = series["ndvi"].idxmax(axis=1)

    manquantes = [b for b in BANDES if f"{b}_01" not in df.columns]
    if manquantes:
        raise SystemExit(
            f"Bands missing from {FICHIER_PARCELLES}: {manquantes}.\n"
            "The final model requires Sentinel-1 radar: rerun the extraction with "
            "extract_series_gee.py, the local variant only provides optical data."
        )

    for bande in BANDES:
        colonnes = [f"{bande}_{mois:02d}" for mois in MOIS]
        variables[f"{bande}_moy"] = df[colonnes].mean(axis=1)
        variables[f"{bande}_ecart_type"] = df[colonnes].std(axis=1)

    # VV - VH difference: the regular rows of a plantation return a radar echo
    # different from that of a natural forest, where optical data sees no
    # difference. It is by far the most discriminating feature of the model.
    ecart = pd.DataFrame(
        {mois: df[f"VV_{mois:02d}"] - df[f"VH_{mois:02d}"] for mois in MOIS}
    )
    variables["vv_vh_moy"] = ecart.mean(axis=1)
    variables["vv_vh_ecart_type"] = ecart.std(axis=1)
    return variables


def plancher(y):
    """Macro F1 of a model that would always answer the majority class.

    It is the threshold below which a model adds nothing. It depends on the
    composition of the dataset, so it must be recomputed, not assumed.
    """
    part = y.value_counts(normalize=True).max()
    f1_majoritaire = 2 * part / (part + 1)
    return f1_majoritaire / len(CLASSES)


def main():
    if not FICHIER_PARCELLES.exists():
        raise SystemExit(
            f"{FICHIER_PARCELLES} not found, run prepare_plots.py first"
        )

    parcelles = pd.read_parquet(FICHIER_PARCELLES)
    X = construire_variables(parcelles)
    blocs = parcelles["bloc"]
    # Descals' two palm types become a single class.
    y = parcelles["classe"].map(
        lambda classe: "pas_de_palmier" if classe == "pas_de_palmier" else "palmier"
    )

    print(f"{len(parcelles)} plots, {blocs.nunique()} blocks, {X.shape[1]} features")
    print(y.value_counts().to_string())
    print(f"\nFloor (always-majority model): macro F1 = {plancher(y):.3f}")

    # Random split against spatial split. The gap between the two is the share of
    # optimism due to the similarity of neighbouring plots: it tells whether the
    # reported score will hold on a region never seen.
    temoin = RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1)
    aleatoire = cross_val_score(
        temoin, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0),
        scoring="f1_macro",
    )
    spatial = cross_val_score(
        temoin, X, y, cv=StratifiedGroupKFold(5, shuffle=True, random_state=0),
        groups=blocs, scoring="f1_macro",
    )
    print(f"\nRandom split  : F1 = {aleatoire.mean():.3f} (± {aleatoire.std():.3f})")
    print(f"Spatial split : F1 = {spatial.mean():.3f} (± {spatial.std():.3f})")
    print(f"Optimism      : {aleatoire.mean() - spatial.mean():+.3f}")

    candidats = {
        "Random forest": RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2, random_state=0, n_jobs=-1
        ),
        "Gradient boosting": HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.08, random_state=0
        ),
    }
    resultats = {}
    for nom, candidat in candidats.items():
        scores = cross_val_score(
            candidat, X, y, cv=GroupKFold(5), groups=blocs, scoring="f1_macro"
        )
        resultats[nom] = scores.mean()
        print(f"{nom:20s} F1 = {scores.mean():.3f} (± {scores.std():.3f})")

    meilleur = max(resultats, key=resultats.get)
    modele = candidats[meilleur]
    print(f"\nSelected: {meilleur}")

    app, test = next(GroupKFold(5).split(X, y, groups=blocs))
    modele.fit(X.iloc[app], y.iloc[app])
    predictions = modele.predict(X.iloc[test])
    print(f"\nTraining: {len(app)} / Test: {len(test)} (disjoint blocks)\n")
    print(classification_report(y.iloc[test], predictions, zero_division=0))

    matrice = confusion_matrix(y.iloc[test], predictions, labels=CLASSES)
    print("Confusion matrix (rows = actual, columns = predicted)")
    print(pd.DataFrame(matrice, index=CLASSES, columns=CLASSES).to_string())

    importance = permutation_importance(
        modele, X.iloc[test], y.iloc[test], n_repeats=10, random_state=0,
        n_jobs=-1, scoring="f1_macro",
    )
    classement = (
        pd.Series(importance.importances_mean, index=X.columns)
        .sort_values(ascending=False)
        .head(6)
    )
    print("\nMost discriminating features")
    print(classement.to_string())

    # Retrain on all plots before saving: the delivered model must have seen
    # every region, including those that served as test.
    modele.fit(X, y)
    joblib.dump(
        {
            "modele": modele,
            "variables": list(X.columns),
            "classes": CLASSES,
            "f1_macro_spatial": float(spatial.mean()),
            "ecart_type": float(spatial.std()),
        },
        FICHIER_MODELE,
    )
    print(f"\nModel saved: {FICHIER_MODELE}")


if __name__ == "__main__":
    main()
