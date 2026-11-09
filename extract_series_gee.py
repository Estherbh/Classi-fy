"""Étape 2/3 : extrait les séries Sentinel-2 et Sentinel-1 sur les points échantillonnés.

Tourne sur Google Earth Engine et exporte un CSV dans ton Google Drive.

Prérequis, une seule fois :

    pip install earthengine-api
    earthengine authenticate

Puis renseigne PROJET ci-dessous avec ton projet Cloud Earth Engine
(https://console.cloud.google.com/earth-engine) et lance :

    python extract_series_gee.py

Le script rend la main immédiatement : l'export tourne côté Google. Compte 20 min à
2 h selon la charge. Suis-le sur https://code.earthengine.google.com/tasks
"""

import json
from pathlib import Path

import ee

PROJET = "citric-gradient-479805-a5"

ENTREE = Path("data") / "echantillons_rdc.geojson"
DOSSIER_DRIVE = "Classify"
NOM_EXPORT = "series_sentinel_rdc"

# La carte palmier décrit la période 2016-2021 : on prend la dernière année couverte.
ANNEE = 2021

# Bandes Sentinel-2 attendues par le notebook (visible, proche et moyen infrarouge).
BANDES_S2 = ["B2", "B3", "B4", "B8", "B11", "B12"]
# Sentinel-1 : rétrodiffusion radar. C'est elle qui porte la structure verticale de la
# canopée, le seul signal qui sépare vraiment palmier, cacao et forêt, toutes trois
# saturées en NDVI toute l'année.
BANDES_S1 = ["VV", "VH"]

MOIS = list(range(1, 13))


def masquer_nuages(image):
    """Masque nuages, ombres et cirrus via la bande de classification SCL."""
    scl = image.select("SCL")
    # 3 = ombre de nuage, 8 = nuage moyennement probable, 9 = très probable,
    # 10 = cirrus, 11 = neige.
    mauvais = (
        scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)).Or(scl.eq(11))
    )
    return image.updateMask(mauvais.Not())


def composite_mensuel(collection, debut, fin, secours, bandes):
    """Médiane du mois ; là où tout est masqué, on retombe sur la médiane annuelle.

    Sans ce filet, une saison des pluies couverte suffit à vider un mois entier, et
    `sampleRegions` supprime alors purement et simplement le point concerné.

    Le repli se fait bande par bande : `unmask` refuse une image de remplacement à
    plusieurs bandes, elle n'en accepte qu'une seule.
    """
    mensuelle = collection.filterDate(debut, fin)
    # Un mois sans aucune acquisition donne une médiane sans aucune bande, sur laquelle
    # `select` échoue. Le cas se produit vraiment : Sentinel-1 ne survole pas toute la
    # RDC tous les mois. On bascule alors entièrement sur la médiane annuelle.
    mois = ee.Image(
        ee.Algorithms.If(mensuelle.size().gt(0), mensuelle.median(), secours)
    )
    return ee.Image.cat(
        [mois.select([bande]).unmask(secours.select([bande])) for bande in bandes]
    )


def construire_image(zone):
    """Empile 12 mois × (6 bandes optiques + 2 bandes radar) en une seule image."""
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(zone)
        .filterDate(f"{ANNEE}-01-01", f"{ANNEE + 1}-01-01")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .map(masquer_nuages)
        # Réflectance en 0-1, comme dans le notebook.
        .select(BANDES_S2)
        # Une opération arithmétique rend une image sans les propriétés de
        # l'originale, date comprise. Sans cette copie, filterDate ne trouve plus
        # rien dans composite_mensuel, et les douze mois retombent tous sur la
        # médiane annuelle : c'est ce qui s'est produit pour 100 % des points.
        .map(lambda image: image.divide(10000)
             .copyProperties(image, ["system:time_start"]))
    )
    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(zone)
        .filterDate(f"{ANNEE}-01-01", f"{ANNEE + 1}-01-01")
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select(BANDES_S1)
    )

    secours_s2 = s2.median()
    secours_s1 = s1.median()

    couches = []
    for mois in MOIS:
        debut = ee.Date.fromYMD(ANNEE, mois, 1)
        fin = debut.advance(1, "month")
        suffixe = f"_{mois:02d}"
        couches.append(
            composite_mensuel(s2, debut, fin, secours_s2, BANDES_S2).rename(
                [f"{bande}{suffixe}" for bande in BANDES_S2]
            )
        )
        couches.append(
            composite_mensuel(s1, debut, fin, secours_s1, BANDES_S1).rename(
                [f"{bande}{suffixe}" for bande in BANDES_S1]
            )
        )
    return ee.Image.cat(couches)


def main():
    if PROJET == "à-remplir":
        raise SystemExit(
            "Renseigne PROJET avec ton projet Cloud Earth Engine.\n"
            "Tu le trouves sur https://console.cloud.google.com/earth-engine"
        )
    if not ENTREE.exists():
        raise SystemExit(f"{ENTREE} introuvable, lance d'abord sample_oil_palm.py")

    ee.Initialize(project=PROJET)

    points = ee.FeatureCollection(json.loads(ENTREE.read_text(encoding="utf-8")))
    print(f"{points.size().getInfo()} points chargés")

    image = construire_image(points.geometry())
    colonnes = ["classe", "bloc"] + [
        f"{bande}_{mois:02d}" for mois in MOIS for bande in BANDES_S2 + BANDES_S1
    ]

    echantillons = image.sampleRegions(
        collection=points,
        properties=["classe", "bloc"],
        scale=10,
        tileScale=4,  # découpe le calcul : évite les dépassements de mémoire
        geometries=False,
    )

    tache = ee.batch.Export.table.toDrive(
        collection=echantillons,
        description=NOM_EXPORT,
        folder=DOSSIER_DRIVE,
        fileNamePrefix=NOM_EXPORT,
        fileFormat="CSV",
        selectors=colonnes,
    )
    tache.start()

    print(
        f"\nExport lancé : {NOM_EXPORT}.csv → Google Drive / {DOSSIER_DRIVE}\n"
        "Suivi : https://code.earthengine.google.com/tasks\n"
        "Une fois terminé, télécharge le CSV dans data/ et lance prepare_plots.py"
    )


if __name__ == "__main__":
    main()
