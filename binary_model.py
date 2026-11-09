"""Étape 4/4 : entraîne et évalue le modèle final, palmier contre pas de palmier.

    python binary_model.py

Lit `data/parcelles.parquet` produit par prepare_plots.py et écrit
`data/modele_palmier.joblib`.

Pourquoi deux classes et non trois. Le notebook crop_classification.ipynb évalue
les trois classes de Descals et plafonne à 0,561 de F1 macro : palmier industriel et
palmier villageois se confondent l'un avec l'autre dans un tiers des cas, parce que ce
qui les distingue est la géométrie des plantations et non le signal par pixel. Fusionner
les deux répond à la question opérationnelle, où y a-t-il du palmier, et fait passer le
F1 macro à 0,817.

Les variables et la validation croisée sont identiques à celles du notebook, pour que
les deux chiffres restent comparables.
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

# Six bandes optiques Sentinel-2, deux bandes radar Sentinel-1.
BANDES = ["B2", "B3", "B4", "B8", "B11", "B12", "VV", "VH"]
MOIS = list(range(1, 13))
CLASSES = ["palmier", "pas_de_palmier"]


def _indice(df, bande_a, bande_b):
    """Indice normalisé (a - b) / (a + b), calculé mois par mois."""
    return pd.DataFrame(
        {
            mois: (df[f"{bande_a}_{mois:02d}"] - df[f"{bande_b}_{mois:02d}"])
            / (df[f"{bande_a}_{mois:02d}"] + df[f"{bande_b}_{mois:02d}"])
            for mois in MOIS
        }
    )


def construire_variables(df):
    """Résume les 96 mesures mensuelles en 34 variables annuelles.

    Reprend à l'identique la fonction du notebook. Les réflectances brutes changent
    d'une image à l'autre ; les indices et leurs statistiques annuelles, non.
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
            f"Bandes absentes de {FICHIER_PARCELLES} : {manquantes}.\n"
            "Le modèle final exige le radar Sentinel-1 : refais l'extraction avec "
            "extract_series_gee.py, la variante locale ne fournit que l'optique."
        )

    for bande in BANDES:
        colonnes = [f"{bande}_{mois:02d}" for mois in MOIS]
        variables[f"{bande}_moy"] = df[colonnes].mean(axis=1)
        variables[f"{bande}_ecart_type"] = df[colonnes].std(axis=1)

    # Écart VV - VH : les alignements réguliers d'une palmeraie renvoient un écho radar
    # différent de celui d'une forêt naturelle, là où l'optique ne voit aucune
    # différence. C'est de loin la variable la plus discriminante du modèle.
    ecart = pd.DataFrame(
        {mois: df[f"VV_{mois:02d}"] - df[f"VH_{mois:02d}"] for mois in MOIS}
    )
    variables["vv_vh_moy"] = ecart.mean(axis=1)
    variables["vv_vh_ecart_type"] = ecart.std(axis=1)
    return variables


def plancher(y):
    """F1 macro d'un modèle qui répondrait toujours la classe majoritaire.

    C'est le seuil en dessous duquel un modèle n'apporte rien. Il dépend de la
    composition du jeu, donc il doit être recalculé et non supposé.
    """
    part = y.value_counts(normalize=True).max()
    f1_majoritaire = 2 * part / (part + 1)
    return f1_majoritaire / len(CLASSES)


def main():
    if not FICHIER_PARCELLES.exists():
        raise SystemExit(
            f"{FICHIER_PARCELLES} introuvable, lance d'abord prepare_plots.py"
        )

    parcelles = pd.read_parquet(FICHIER_PARCELLES)
    X = construire_variables(parcelles)
    blocs = parcelles["bloc"]
    # Les deux types de palmier de Descals deviennent une seule classe.
    y = parcelles["classe"].map(
        lambda classe: "pas_de_palmier" if classe == "pas_de_palmier" else "palmier"
    )

    print(f"{len(parcelles)} parcelles, {blocs.nunique()} blocs, {X.shape[1]} variables")
    print(y.value_counts().to_string())
    print(f"\nPlancher (modèle toujours majoritaire) : F1 macro = {plancher(y):.3f}")

    # Découpage aléatoire contre découpage spatial. L'écart entre les deux est la part
    # d'optimisme due à la ressemblance entre parcelles voisines : c'est lui qui dit si
    # le score annoncé tiendra sur une région jamais vue.
    temoin = RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1)
    aleatoire = cross_val_score(
        temoin, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0),
        scoring="f1_macro",
    )
    spatial = cross_val_score(
        temoin, X, y, cv=StratifiedGroupKFold(5, shuffle=True, random_state=0),
        groups=blocs, scoring="f1_macro",
    )
    print(f"\nDécoupage aléatoire : F1 = {aleatoire.mean():.3f} (± {aleatoire.std():.3f})")
    print(f"Découpage spatial   : F1 = {spatial.mean():.3f} (± {spatial.std():.3f})")
    print(f"Optimisme           : {aleatoire.mean() - spatial.mean():+.3f}")

    candidats = {
        "Forêt aléatoire": RandomForestClassifier(
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
    print(f"\nRetenu : {meilleur}")

    app, test = next(GroupKFold(5).split(X, y, groups=blocs))
    modele.fit(X.iloc[app], y.iloc[app])
    predictions = modele.predict(X.iloc[test])
    print(f"\nApprentissage : {len(app)} / Test : {len(test)} (blocs disjoints)\n")
    print(classification_report(y.iloc[test], predictions, zero_division=0))

    matrice = confusion_matrix(y.iloc[test], predictions, labels=CLASSES)
    print("Matrice de confusion (lignes = réel, colonnes = prédit)")
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
    print("\nVariables les plus discriminantes")
    print(classement.to_string())

    # Réentraînement sur l'ensemble des parcelles avant sauvegarde : le modèle livré
    # doit avoir vu toutes les régions, y compris celles qui servaient de test.
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
    print(f"\nModèle sauvegardé : {FICHIER_MODELE}")


if __name__ == "__main__":
    main()
