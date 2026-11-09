"""Étape 2 (variante sans compte) : extrait les séries Sentinel-2 depuis AWS Open Data.

Alternative à extract_series_gee.py : ne demande **aucun compte**, ni Google Earth
Engine, ni Copernicus. Les images Sentinel-2 L2A sont publiées en accès anonyme sur
AWS (bucket sentinel-cogs), interrogeables via l'API STAC d'Element 84.

    python extract_series_local.py
    python extract_series_local.py --fenetres 3   # essai rapide sur 3 zones

Produit directement `data/parcelles.parquet`, le format attendu par le notebook.

Limite par rapport à la variante Earth Engine : pas de radar Sentinel-1, dont le
bucket AWS est payant. Sans le radar, palmier et forêt restent difficiles à séparer.
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
# Journal d'avancement : chaque tuile y est écrite dès qu'elle est terminée. Une
# extraction complète dure une heure et dépend du réseau ; sans ce fichier, la moindre
# coupure obligerait à tout recommencer.
JOURNAL = DOSSIER / "extraction_en_cours.csv"

API_STAC = "https://earth-search.aws.element84.com/v1/search"

RDC = (12.2, -13.5, 31.3, 5.4)
ANNEE = 2021
NUAGES_MAX = 40

# Correspondance entre les noms attendus par le notebook et les noms STAC.
BANDES = {
    "B2": "blue", "B3": "green", "B4": "red",
    "B8": "nir", "B11": "swir16", "B12": "swir22",
}
MOIS = list(range(1, 13))

ETIQUETTES = {0: "pas_de_palmier", 1: "palmier_industriel", 2: "palmier_villageois"}

# Une fenêtre de 512 pixels à 10 m couvre ~5 km. Regrouper les points dans de petites
# fenêtres plutôt que de les disperser est ce qui rend l'extraction praticable : tous
# les points d'une fenêtre tombent dans le même bloc interne du COG, donc une seule
# requête réseau les sert tous. Dispersés, il en faudrait des centaines de milliers.
FENETRE_PX = 512
POINTS_PAR_CLASSE = 100

# 3 = ombre de nuage, 8/9 = nuage probable, 10 = cirrus, 11 = neige.
SCL_MAUVAIS = {3, 8, 9, 10, 11}

ALEA = np.random.default_rng(42)

# Sans ces délais, GDAL attend indéfiniment si un serveur AWS cesse de répondre en
# cours de lecture : le script reste bloqué sur une seule requête, sans consommer de
# processeur ni rien écrire. C'est arrivé, d'où ces garde-fous.
OPTIONS_GDAL = {
    "GDAL_HTTP_CONNECTTIMEOUT": 15,
    "GDAL_HTTP_TIMEOUT": 30,
    "GDAL_HTTP_MAX_RETRY": 3,
    "GDAL_HTTP_RETRY_DELAY": 2,
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_CACHEMAX": 512,
}


def interroger_stac(bbox, debut, fin, limite=20):
    """Cherche les scènes Sentinel-2 peu nuageuses couvrant une emprise."""
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
    """Repère la zone la plus riche en palmier dans une tuile.

    Une fenêtre prise au hasard tomberait presque toujours sur de la forêt : le palmier
    n'occupe qu'une fraction de pourcent des pixels.
    """
    hauteur, largeur = donnees.shape
    if hauteur < FENETRE_PX or largeur < FENETRE_PX:
        return None

    # Densité de palmier par bloc, calculée sur une version décimée pour rester rapide.
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
    """Tire des points étiquetés dans la zone la plus dense d'une tuile."""
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
    """Lit les six bandes d'une scène aux points donnés, nuages masqués.

    Retourne un tableau (n_points, 6) en réflectance 0-1, avec NaN là où le pixel est
    nuageux ou hors emprise.
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
        # 0 = hors emprise de la scène (les tuiles Sentinel-2 sont partiellement vides).
        brut[brut == 0] = np.nan
        mesures[:, indice] = brut / 10000.0

    mesures[~valide] = np.nan
    return mesures


def traiter_fenetre(points, bbox):
    """Construit les 12 séries mensuelles pour tous les points d'une fenêtre."""
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

        # On s'arrête dès qu'une scène couvre tous les points : inutile d'en empiler
        # d'autres, et chacune coûte des requêtes réseau.
        cumul = None
        for scene in scenes[:3]:
            try:
                mesures = lire_scene(scene, longitudes, latitudes)
            except (rasterio.errors.RasterioIOError, OSError) as erreur:
                # Une scène illisible ne doit pas condamner toute l'extraction.
                print(f"    scène {scene['id']} ignorée : {erreur}", flush=True)
                continue
            if mesures is None:
                continue
            cumul = mesures if cumul is None else np.where(np.isnan(cumul), mesures, cumul)
            if not np.isnan(cumul).any():
                break
        mensuel[mois] = cumul

    return mensuel


def assembler(points, mensuel):
    """Assemble les mesures en lignes au format du notebook."""
    # Médiane annuelle par point : sert à combler les mois entièrement nuageux.
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
            continue  # Point jamais vu sans nuage de toute l'année.
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
        help="limite le nombre de tuiles traitées (pour un essai rapide)",
    )
    arguments = analyseur.parse_args()

    if not GRILLE.exists():
        raise SystemExit(
            f"{GRILLE} introuvable, télécharge et décompresse les fichiers Zenodo "
            "dans data/ (voir sample_oil_palm.py)."
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
        print(f"Reprise : {len(deja_faites)} tuiles déjà extraites, elles seront sautées")

    restantes = [t for t in tuiles if t not in deja_faites]
    print(f"{len(restantes)} tuiles à traiter\n", flush=True)

    with rasterio.Env(**OPTIONS_GDAL):
        for numero, identifiant in enumerate(restantes, 1):
            chemin = RASTERS / f"GlobalOilPalm_OP-extent_{identifiant}.tif"
            if not chemin.exists():
                continue
            points, bbox = points_de_la_fenetre(chemin, identifiant)
            if not points:
                print(
                    f"[{numero}/{len(restantes)}] tuile {identifiant} : "
                    "pas de palmier, ignorée",
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
                f"[{numero}/{len(restantes)}] tuile {identifiant} : "
                f"{len(lignes)} points retenus"
                + (f", {perdus} perdus (nuages toute l'année)" if perdus else ""),
                flush=True,
            )

    if not JOURNAL.exists():
        raise SystemExit("Aucun point exploitable, vérifie la connexion réseau.")

    donnees = pd.read_csv(JOURNAL)
    donnees.to_parquet(SORTIE, index=False)

    print(f"\n{SORTIE} écrit : {len(donnees)} parcelles, {donnees['bloc'].nunique()} blocs")
    print(donnees["classe"].value_counts().to_string())
    print("\nRelance maintenant crop_classification.ipynb : il basculera seul.")


if __name__ == "__main__":
    main()
