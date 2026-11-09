"""Step 1/3: samples labelled points from the DRC oil palm rasters.

Produces `data/echantillons_rdc.geojson`, to upload to Google Earth Engine
for step 2 (extraction of the Sentinel-1 / Sentinel-2 time series).

Requires no account: everything runs locally on the GeoTIFFs already downloaded
from Zenodo (https://zenodo.org/records/13379129).

    python sample_oil_palm.py
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from shapely.geometry import Point

DOSSIER = Path("data")
GRILLE = DOSSIER / "palmier_grille" / "Grid_OilPalm2016-2021.shp"
RASTERS = DOSSIER / "palmier_extent"
SORTIE = DOSSIER / "echantillons_rdc.geojson"

# DRC extent: lon_min, lat_min, lon_max, lat_max
RDC = (12.2, -13.5, 31.3, 5.4)

# Values of the Descals et al. 2024 raster.
ETIQUETTES = {0: "pas_de_palmier", 1: "palmier_industriel", 2: "palmier_villageois"}

# One pixel out of PAS in each direction. At 10 m, a step of 20 gives one point every
# 200 m: two neighbouring pixels of the same plantation are nearly identical, keeping
# both inflates the dataset without adding information.
PAS = 20

# Per tile and per class. 34 tiles × 3 classes × 100 ≈ 10,000 points at most,
# a volume that fits comfortably in an Earth Engine export.
POINTS_PAR_CLASSE = 100

ALEA = np.random.default_rng(42)


def echantillonner_tuile(chemin, identifiant):
    """Returns the points drawn in one tile, balanced across the three classes."""
    with rasterio.open(chemin) as source:
        donnees = source.read(1)[::PAS, ::PAS]
        transformation = source.transform

    points = []
    for valeur, etiquette in ETIQUETTES.items():
        lignes, colonnes = np.nonzero(donnees == valeur)
        if not len(lignes):
            continue
        tirage = ALEA.choice(
            len(lignes), size=min(POINTS_PAR_CLASSE, len(lignes)), replace=False
        )
        for index in tirage:
            # Back to full-resolution indices, then to the pixel centre.
            longitude, latitude = transformation * (
                colonnes[index] * PAS + 0.5,
                lignes[index] * PAS + 0.5,
            )
            points.append(
                {
                    "classe": etiquette,
                    # The 100 km tile serves as the spatial block: it is what
                    # will split training and test without leakage.
                    "bloc": int(identifiant),
                    "geometry": Point(longitude, latitude),
                }
            )
    return points


def main():
    if not GRILLE.exists():
        raise FileNotFoundError(
            f"{GRILLE} not found, download Grid_OilPalm2016-2021.zip "
            "from https://zenodo.org/records/13379129 and unzip it into data/."
        )

    grille = gpd.read_file(GRILLE)
    tuiles = grille.cx[RDC[0]:RDC[2], RDC[1]:RDC[3]]
    print(f"{len(tuiles)} tiles over the DRC")

    points = []
    for identifiant in tuiles["ID"].astype(int):
        chemin = RASTERS / f"GlobalOilPalm_OP-extent_{identifiant}.tif"
        if not chemin.exists():
            print(f"  tile {identifiant}: raster missing, skipped")
            continue
        tires = echantillonner_tuile(chemin, identifiant)
        points.extend(tires)
        print(f"  tile {identifiant}: {len(tires)} points")

    echantillons = gpd.GeoDataFrame(points, crs="EPSG:4326")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    echantillons.to_file(SORTIE, driver="GeoJSON")

    print(f"\n{len(echantillons)} points written to {SORTIE}")
    print(echantillons["classe"].value_counts().to_string())
    print(f"\n{echantillons['bloc'].nunique()} distinct spatial blocks")


if __name__ == "__main__":
    main()
