"""Produit le fichier de prédictions géolocalisées qui alimente la carte.

    python predictions_carte.py

Écrit `data/predictions_test.geojson` : un point par parcelle du pli de test, avec sa
classe réelle, la prédiction du modèle, la probabilité et la catégorie de la matrice de
confusion.

Les coordonnées ne figurent pas dans parcelles.parquet : l'export Earth Engine a été
lancé avec `geometries=False`. Elles sont donc reprises de echantillons_rdc.geojson,
ligne à ligne. Cet appariement a été vérifié de deux façons, l'ordre des couples classe
et bloc concorde sur les 8 658 lignes, et les valeurs de bandes de plusieurs points
tirés au hasard concordent avec un nouvel échantillonnage Earth Engine aux coordonnées
correspondantes. Le contrôle ci-dessous rejoue la première de ces deux vérifications à
chaque exécution.
"""

from pathlib import Path

import geopandas as gpd
import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold

from modele_binaire import construire_variables

DOSSIER = Path("data")
FICHIER_PARCELLES = DOSSIER / "parcelles.parquet"
FICHIER_POINTS = DOSSIER / "echantillons_rdc.geojson"
SORTIE = DOSSIER / "predictions_test.geojson"
FICHIER_MODELE = DOSSIER / "modele_palmier.joblib"

CATEGORIES = {
    ("palmier", "palmier"): "Palmier détecté",
    ("palmier", "pas_de_palmier"): "Palmier manqué",
    ("pas_de_palmier", "palmier"): "Fausse alerte",
    ("pas_de_palmier", "pas_de_palmier"): "Correctement écarté",
}


def modele_retenu():
    """Copie vierge du modèle retenu par modele_binaire.py, mêmes réglages."""
    if not FICHIER_MODELE.exists():
        raise SystemExit(f"{FICHIER_MODELE} introuvable, lance d'abord modele_binaire.py")
    return clone(joblib.load(FICHIER_MODELE)["modele"])


def charger():
    """Recolle les mesures et les coordonnées, après contrôle de l'appariement."""
    parcelles = pd.read_parquet(FICHIER_PARCELLES)
    points = gpd.read_file(FICHIER_POINTS)

    if len(parcelles) != len(points):
        raise SystemExit(
            f"{len(parcelles)} parcelles contre {len(points)} points : "
            "les deux fichiers ne viennent pas du même échantillonnage."
        )
    concordant = (
        (parcelles["classe"].values == points["classe"].values)
        & (parcelles["bloc"].values == points["bloc"].values)
    )
    if not concordant.all():
        raise SystemExit(
            f"Appariement rompu sur {(~concordant).sum()} lignes. "
            "Relance l'export Earth Engine en incluant les coordonnées."
        )

    parcelles = parcelles.copy()
    parcelles["lon"] = points.geometry.x.values
    parcelles["lat"] = points.geometry.y.values
    return parcelles


def main():
    parcelles = charger()
    X = construire_variables(parcelles)
    blocs = parcelles["bloc"]
    y = parcelles["classe"].map(
        lambda classe: "pas_de_palmier" if classe == "pas_de_palmier" else "palmier"
    )

    # Même découpage et même modèle que l'évaluation, pour que la carte montre
    # exactement les parcelles et les réponses sur lesquelles les chiffres publiés ont
    # été mesurés. Le modèle est relu dans le fichier sauvegardé plutôt qu'écrit en
    # dur : modele_binaire.py choisit l'algorithme à chaque exécution, et la carte
    # doit suivre ce choix.
    app, test = next(GroupKFold(5).split(X, y, groups=blocs))
    modele = modele_retenu()
    modele.fit(X.iloc[app], y.iloc[app])

    predictions = modele.predict(X.iloc[test])
    colonne_palmier = list(modele.classes_).index("palmier")
    probabilites = modele.predict_proba(X.iloc[test])[:, colonne_palmier]

    resultat = gpd.GeoDataFrame(
        {
            "bloc": blocs.iloc[test].values,
            "classe_reelle": y.iloc[test].values,
            "prediction": predictions,
            "probabilite_palmier": probabilites.round(4),
            "categorie": [
                CATEGORIES[(reel, predit)]
                for reel, predit in zip(y.iloc[test].values, predictions)
            ],
        },
        geometry=gpd.points_from_xy(
            parcelles["lon"].iloc[test], parcelles["lat"].iloc[test]
        ),
        crs="EPSG:4326",
    )
    resultat.to_file(SORTIE, driver="GeoJSON")

    print(f"{len(app)} parcelles d'apprentissage, {len(test)} de test")
    print(f"{resultat['bloc'].nunique()} blocs de test : "
          f"{sorted(resultat['bloc'].unique().tolist())}")
    print(f"\nemprise : {resultat.total_bounds.round(2).tolist()}")
    print()
    print(resultat["categorie"].value_counts().to_string())
    print(f"\n{SORTIE} écrit")


if __name__ == "__main__":
    main()
