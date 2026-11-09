"""Produces the file of geolocated predictions that feeds the map.

    python map_predictions.py

Writes `data/predictions_test.geojson`: one point per plot of the test fold, with its
actual class, the model's prediction, the probability and the confusion-matrix
category.

The coordinates are not in parcelles.parquet: the Earth Engine export was run
with `geometries=False`. They are therefore taken from echantillons_rdc.geojson,
row by row. This matching was checked in two ways: the order of the class and
block pairs agrees on all 8,658 rows, and the band values of several randomly
drawn points agree with a fresh Earth Engine sampling at the corresponding
coordinates. The check below replays the first of these two checks on every
run.
"""

from pathlib import Path

import geopandas as gpd
import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold

from binary_model import construire_variables

DOSSIER = Path("data")
FICHIER_PARCELLES = DOSSIER / "parcelles.parquet"
FICHIER_POINTS = DOSSIER / "echantillons_rdc.geojson"
SORTIE = DOSSIER / "predictions_test.geojson"
FICHIER_MODELE = DOSSIER / "modele_palmier.joblib"

# Category labels stored in the output file and read back by the map scripts.
CATEGORIES = {
    ("palmier", "palmier"): "Palmier détecté",
    ("palmier", "pas_de_palmier"): "Palmier manqué",
    ("pas_de_palmier", "palmier"): "Fausse alerte",
    ("pas_de_palmier", "pas_de_palmier"): "Correctement écarté",
}


def modele_retenu():
    """Blank copy of the model selected by binary_model.py, same settings."""
    if not FICHIER_MODELE.exists():
        raise SystemExit(f"{FICHIER_MODELE} not found, run binary_model.py first")
    return clone(joblib.load(FICHIER_MODELE)["modele"])


def charger():
    """Joins measurements and coordinates back together, after checking the matching."""
    parcelles = pd.read_parquet(FICHIER_PARCELLES)
    points = gpd.read_file(FICHIER_POINTS)

    if len(parcelles) != len(points):
        raise SystemExit(
            f"{len(parcelles)} plots against {len(points)} points: "
            "the two files do not come from the same sampling."
        )
    concordant = (
        (parcelles["classe"].values == points["classe"].values)
        & (parcelles["bloc"].values == points["bloc"].values)
    )
    if not concordant.all():
        raise SystemExit(
            f"Matching broken on {(~concordant).sum()} rows. "
            "Rerun the Earth Engine export including the coordinates."
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

    # Same split and same model as the evaluation, so that the map shows exactly
    # the plots and answers on which the published numbers were measured. The model
    # is read back from the saved file rather than hard-coded: binary_model.py
    # chooses the algorithm on each run, and the map must follow that choice.
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

    print(f"{len(app)} training plots, {len(test)} test plots")
    print(f"{resultat['bloc'].nunique()} test blocks: "
          f"{sorted(resultat['bloc'].unique().tolist())}")
    print(f"\nextent: {resultat.total_bounds.round(2).tolist()}")
    print()
    print(resultat["categorie"].value_counts().to_string())
    print(f"\n{SORTIE} written")


if __name__ == "__main__":
    main()
