"""Step 2 (account-free variant): extracts the Sentinel-2 time series from AWS Open Data.

Alternative to extract_series_gee.py: requires **no account**, neither Google Earth
Engine nor Copernicus. Sentinel-2 L2A images are published with anonymous access on
AWS (sentinel-cogs bucket), searchable through Element 84's STAC API.

    python extract_series_local.py
    python extract_series_local.py --fenetres 3   # quick test on 3 areas

Directly produces `data/parcelles.parquet`, the format expected by the notebook.

Limitation compared with the Earth Engine variant: no Sentinel-1 radar, whose
AWS bucket is paid. Without radar, palm and forest remain hard to separate.
"""

import argparse
import json
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform as transformer_coords
from rasterio.windows import Window

DOSSIER = Path("data")
GRILLE = DOSSIER / "palmier_grille" / "Grid_OilPalm2016-2021.shp"
RASTERS = DOSSIER / "palmier_extent"
SORTIE = DOSSIER / "parcelles.parquet"
# Progress log: each tile is written to it as soon as it is done. A full
# extraction takes an hour and depends on the network; without this file, the slightest
# interruption would force a restart from scratch.
JOURNAL = DOSSIER / "extraction_en_cours.csv"

API_STAC = "https://earth-search.aws.element84.com/v1/search"

RDC = (12.2, -13.5, 31.3, 5.4)
ANNEE = 2021
NUAGES_MAX = 40

# Mapping between the names expected by the notebook and the STAC names.
BANDES = {
    "B2": "blue", "B3": "green", "B4": "red",
    "B8": "nir", "B11": "swir16", "B12": "swir22",
}
MOIS = list(range(1, 13))

ETIQUETTES = {0: "pas_de_palmier", 1: "palmier_industriel", 2: "palmier_villageois"}

# A 512-pixel window at 10 m covers ~5 km. Grouping points into small windows
# rather than scattering them is what makes the extraction workable: all the
# points of a window fall in the same internal block of the COG, so a single
# network request serves them all. Scattered, it would take hundreds of thousands.
FENETRE_PX = 512
POINTS_PAR_CLASSE = 100

# 3 = cloud shadow, 8/9 = probable cloud, 10 = cirrus, 11 = snow.
SCL_MAUVAIS = {3, 8, 9, 10, 11}

ALEA = np.random.default_rng(42)

# Without these timeouts, GDAL waits forever if an AWS server stops responding
# mid-read: the script hangs on a single request, using no CPU and writing
# nothing. It happened, hence these safeguards.
OPTIONS_GDAL = {
    "GDAL_HTTP_CONNECTTIMEOUT": 15,
    "GDAL_HTTP_TIMEOUT": 30,
    "GDAL_HTTP_MAX_RETRY": 3,
    "GDAL_HTTP_RETRY_DELAY": 2,
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_CACHEMAX": 512,
}


def interroger_stac(bbox, debut, fin, limite=20):
    """Searches for low-cloud Sentinel-2 scenes covering an extent."""
    requete = {
        "collections": ["sentinel-2-l2a"],
        "bbox": list(bbox),
        "datetime": f"{debut}T00:00:00Z/{fin}T00:00:00Z",
        "query": {"eo:cloud_cover": {"lt": NUAGES_MAX}},
        "limit": limite,
    }
    demande = urllib.request.Request(
        API_STAC,
        data=json.dumps(requete).encode(),
        headers={"Content-Type": "application/json"},
    )
    for tentative in range(3):
        try:
            reponse = json.loads(urllib.request.urlopen(demande, timeout=120).read())
            return reponse.get("features", [])
        except (urllib.error.URLError, TimeoutError):
            if tentative == 2:
                return []
    return []


def choisir_fenetre(donnees):
    """Finds the area richest in palm within a tile.

    A randomly chosen window would almost always land on forest: palm
    covers only a fraction of a percent of the pixels.
    """
    hauteur, largeur = donnees.shape
    if hauteur < FENETRE_PX or largeur < FENETRE_PX:
        return None

    # Palm density per block, computed on a decimated version to stay fast.
    pas = FENETRE_PX // 8
    grossier = (donnees[::pas, ::pas] > 0).astype(np.float32)
    cote = max(1, FENETRE_PX // pas)
    n_lignes = grossier.shape[0] // cote
    n_colonnes = grossier.shape[1] // cote
    if n_lignes == 0 or n_colonnes == 0:
        return None
    blocs = grossier[: n_lignes * cote, : n_colonnes * cote]
    densite = blocs.reshape(n_lignes, cote, n_colonnes, cote).sum(axis=(1, 3))

    meilleur = np.unravel_index(np.argmax(densite), densite.shape)
    if densite[meilleur] == 0:
        return None
    ligne = min(meilleur[0] * cote * pas, hauteur - FENETRE_PX)
    colonne = min(meilleur[1] * cote * pas, largeur - FENETRE_PX)
    return Window(colonne, ligne, FENETRE_PX, FENETRE_PX)


def points_de_la_fenetre(chemin, identifiant):
    """Draws labelled points in the densest area of a tile."""
    with rasterio.open(chemin) as source:
        fenetre = choisir_fenetre(source.read(1))
        if fenetre is None:
            return None, None
        extrait = source.read(1, window=fenetre)
        transformation = source.window_transform(fenetre)
        bbox = rasterio.windows.bounds(fenetre, source.transform)

    points = []
    for valeur, etiquette in ETIQUETTES.items():
        lignes, colonnes = np.nonzero(extrait == valeur)
        if not len(lignes):
            continue
        tirage = ALEA.choice(
            len(lignes), size=min(POINTS_PAR_CLASSE, len(lignes)), replace=False
        )
        for index in tirage:
            longitude, latitude = transformation * (
                colonnes[index] + 0.5, lignes[index] + 0.5
            )
            points.append(
                {
                    "classe": etiquette,
                    "bloc": int(identifiant),
                    "lon": longitude,
                    "lat": latitude,
                }
            )
    return points, bbox


def lire_scene(scene, longitudes, latitudes):
    """Reads the six bands of a scene at the given points, clouds masked.

    Returns an array (n_points, 6) in 0-1 reflectance, with NaN where the pixel is
    cloudy or outside the extent.
    """
    with rasterio.open(scene["assets"]["scl"]["href"]) as source:
        coords_x, coords_y = transformer_coords(
            "EPSG:4326", source.crs, longitudes, latitudes
        )
        classification = np.array(
            [valeur[0] for valeur in source.sample(zip(coords_x, coords_y))]
        )
    valide = ~np.isin(classification, list(SCL_MAUVAIS))
    if not valide.any():
        return None

    mesures = np.full((len(longitudes), len(BANDES)), np.nan, dtype=np.float32)
    for indice, nom_stac in enumerate(BANDES.values()):
        with rasterio.open(scene["assets"][nom_stac]["href"]) as source:
            coords_x, coords_y = transformer_coords(
                "EPSG:4326", source.crs, longitudes, latitudes
            )
            brut = np.array(
                [valeur[0] for valeur in source.sample(zip(coords_x, coords_y))],
                dtype=np.float32,
            )
        # 0 = outside the scene's extent (Sentinel-2 tiles are partly empty).
        brut[brut == 0] = np.nan
        mesures[:, indice] = brut / 10000.0

    mesures[~valide] = np.nan
    return mesures


def traiter_fenetre(points, bbox):
    """Builds the 12 monthly series for all the points of a window."""
    longitudes = [point["lon"] for point in points]
    latitudes = [point["lat"] for point in points]
    mensuel = {}

    for mois in MOIS:
        debut = f"{ANNEE}-{mois:02d}-01"
        fin = (
            f"{ANNEE + 1}-01-01" if mois == 12 else f"{ANNEE}-{mois + 1:02d}-01"
        )
        scenes = interroger_stac(bbox, debut, fin)
        scenes.sort(key=lambda s: s["properties"].get("eo:cloud_cover", 100))

        # Stop as soon as one scene covers all the points: no need to stack
        # more, and each one costs network requests.
        cumul = None
        for scene in scenes[:3]:
            try:
                mesures = lire_scene(scene, longitudes, latitudes)
            except (rasterio.errors.RasterioIOError, OSError) as erreur:
                # One unreadable scene must not doom the whole extraction.
                print(f"    scene {scene['id']} skipped: {erreur}", flush=True)
                continue
            if mesures is None:
                continue
            cumul = mesures if cumul is None else np.where(np.isnan(cumul), mesures, cumul)
            if not np.isnan(cumul).any():
                break
        mensuel[mois] = cumul

    return mensuel


def assembler(points, mensuel):
    """Assembles the measurements into rows in the notebook's format."""
    # Annual median per point: used to fill fully cloudy months.
    empile = np.stack(
        [m for m in mensuel.values() if m is not None], axis=0
    ) if any(m is not None for m in mensuel.values()) else None
    if empile is None:
        return []
    with np.errstate(all="ignore"):
        secours = np.nanmedian(empile, axis=0)

    lignes = []
    for index, point in enumerate(points):
        if np.isnan(secours[index]).any():
            continue  # Point never seen cloud-free all year.
        ligne = {"classe": point["classe"], "bloc": point["bloc"]}
        for mois in MOIS:
            mesures = mensuel[mois]
            valeurs = (
                secours[index]
                if mesures is None or np.isnan(mesures[index]).any()
                else mesures[index]
            )
            for position, nom in enumerate(BANDES):
                ligne[f"{nom}_{mois:02d}"] = float(valeurs[position])
        lignes.append(ligne)
    return lignes


def main():
    analyseur = argparse.ArgumentParser()
    analyseur.add_argument(
        "--fenetres", type=int, default=None,
        help="limits the number of tiles processed (for a quick test)",
    )
    arguments = analyseur.parse_args()

    if not GRILLE.exists():
        raise SystemExit(
            f"{GRILLE} not found, download and unzip the Zenodo files "
            "into data/ (see sample_oil_palm.py)."
        )

    import geopandas as gpd

    grille = gpd.read_file(GRILLE)
    tuiles = grille.cx[RDC[0]:RDC[2], RDC[1]:RDC[3]]["ID"].astype(int).tolist()
    if arguments.fenetres:
        tuiles = tuiles[: arguments.fenetres]

    DOSSIER.mkdir(parents=True, exist_ok=True)
    deja_faites = set()
    if JOURNAL.exists():
        deja_faites = set(pd.read_csv(JOURNAL)["bloc"].unique())
        print(f"Resuming: {len(deja_faites)} tiles already extracted, they will be skipped")

    restantes = [t for t in tuiles if t not in deja_faites]
    print(f"{len(restantes)} tiles to process\n", flush=True)

    with rasterio.Env(**OPTIONS_GDAL):
        for numero, identifiant in enumerate(restantes, 1):
            chemin = RASTERS / f"GlobalOilPalm_OP-extent_{identifiant}.tif"
            if not chemin.exists():
                continue
            points, bbox = points_de_la_fenetre(chemin, identifiant)
            if not points:
                print(
                    f"[{numero}/{len(restantes)}] tile {identifiant}: "
                    "no palm, skipped",
                    flush=True,
                )
                continue

            mensuel = traiter_fenetre(points, bbox)
            lignes = assembler(points, mensuel)
            if lignes:
                pd.DataFrame(lignes).to_csv(
                    JOURNAL, mode="a", header=not JOURNAL.exists(), index=False
                )
            perdus = len(points) - len(lignes)
            print(
                f"[{numero}/{len(restantes)}] tile {identifiant}: "
                f"{len(lignes)} points kept"
                + (f", {perdus} lost (clouds all year)" if perdus else ""),
                flush=True,
            )

    if not JOURNAL.exists():
        raise SystemExit("No usable point, check the network connection.")

    donnees = pd.read_csv(JOURNAL)
    donnees.to_parquet(SORTIE, index=False)

    print(f"\n{SORTIE} written: {len(donnees)} plots, {donnees['bloc'].nunique()} blocks")
    print(donnees["classe"].value_counts().to_string())
    print("\nNow rerun crop_classification.ipynb: it will switch over on its own.")


if __name__ == "__main__":
    main()
