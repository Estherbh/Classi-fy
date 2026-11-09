"""Étape 1/3 : échantillonne des points étiquetés dans les rasters palmier de la RDC.

Produit `data/echantillons_rdc.geojson`, à téléverser dans Google Earth Engine
pour l'étape 2 (extraction des séries Sentinel-1 / Sentinel-2).

Ne demande aucun compte : tout se fait en local sur les GeoTIFF déjà téléchargés
depuis Zenodo (https://zenodo.org/records/13379129).

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

# Emprise RDC : lon_min, lat_min, lon_max, lat_max
RDC = (12.2, -13.5, 31.3, 5.4)

# Valeurs du raster Descals et al. 2024.
ETIQUETTES = {0: "pas_de_palmier", 1: "palmier_industriel", 2: "palmier_villageois"}

# Un pixel sur PAS dans chaque direction. À 10 m, un pas de 20 donne un point tous
# les 200 m : deux pixels voisins d'une même plantation sont quasi identiques, les
# garder tous les deux gonfle le jeu sans ajouter d'information.
PAS = 20

# Par tuile et par classe. 34 tuiles × 3 classes × 100 ≈ 10 000 points au maximum,
# volume qui passe confortablement dans un export Earth Engine.
POINTS_PAR_CLASSE = 100

ALEA = np.random.default_rng(42)


def echantillonner_tuile(chemin, identifiant):
    """Retourne les points tirés dans une tuile, équilibrés entre les trois classes."""
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
            # Retour aux indices pleine résolution, puis au centre du pixel.
            longitude, latitude = transformation * (
                colonnes[index] * PAS + 0.5,
                lignes[index] * PAS + 0.5,
            )
            points.append(
                {
                    "classe": etiquette,
                    # La tuile de 100 km sert de bloc spatial : c'est elle qui
                    # découpera apprentissage et test sans fuite.
                    "bloc": int(identifiant),
                    "geometry": Point(longitude, latitude),
                }
            )
    return points


def main():
    if not GRILLE.exists():
        raise FileNotFoundError(
            f"{GRILLE} introuvable, télécharge Grid_OilPalm2016-2021.zip "
            "depuis https://zenodo.org/records/13379129 et décompresse-le dans data/."
        )

    grille = gpd.read_file(GRILLE)
    tuiles = grille.cx[RDC[0]:RDC[2], RDC[1]:RDC[3]]
    print(f"{len(tuiles)} tuiles sur la RDC")

    points = []
    for identifiant in tuiles["ID"].astype(int):
        chemin = RASTERS / f"GlobalOilPalm_OP-extent_{identifiant}.tif"
        if not chemin.exists():
            print(f"  tuile {identifiant} : raster absent, ignorée")
            continue
        tires = echantillonner_tuile(chemin, identifiant)
        points.extend(tires)
        print(f"  tuile {identifiant} : {len(tires)} points")

    echantillons = gpd.GeoDataFrame(points, crs="EPSG:4326")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    echantillons.to_file(SORTIE, driver="GeoJSON")

    print(f"\n{len(echantillons)} points écrits dans {SORTIE}")
    print(echantillons["classe"].value_counts().to_string())
    print(f"\n{echantillons['bloc'].nunique()} blocs spatiaux distincts")


if __name__ == "__main__":
    main()
