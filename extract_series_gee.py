"""Step 2/3: extracts the Sentinel-2 and Sentinel-1 time series at the sampled points.

Runs on Google Earth Engine and exports a CSV to your Google Drive.

Prerequisites, once:

    pip install earthengine-api
    earthengine authenticate

Then set PROJET below to your Earth Engine Cloud project
(https://console.cloud.google.com/earth-engine) and run:

    python extract_series_gee.py

The script returns immediately: the export runs on Google's side. Allow 20 min to
2 h depending on load. Track it at https://code.earthengine.google.com/tasks
"""

import json
from pathlib import Path

import ee

PROJET = "citric-gradient-479805-a5"

ENTREE = Path("data") / "echantillons_rdc.geojson"
DOSSIER_DRIVE = "Classify"
NOM_EXPORT = "series_sentinel_rdc"

# The palm map describes 2016-2021: we take the last year covered.
ANNEE = 2021

# Sentinel-2 bands expected by the notebook (visible, near and shortwave infrared).
BANDES_S2 = ["B2", "B3", "B4", "B8", "B11", "B12"]
# Sentinel-1: radar backscatter. It carries the vertical structure of the canopy,
# the only signal that truly separates palm, cocoa and forest, all three
# saturated in NDVI all year round.
BANDES_S1 = ["VV", "VH"]

MOIS = list(range(1, 13))


def masquer_nuages(image):
    """Masks clouds, shadows and cirrus using the SCL classification band."""
    scl = image.select("SCL")
    # 3 = cloud shadow, 8 = cloud medium probability, 9 = high probability,
    # 10 = cirrus, 11 = snow.
    mauvais = (
        scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)).Or(scl.eq(11))
    )
    return image.updateMask(mauvais.Not())


def composite_mensuel(collection, debut, fin, secours, bandes):
    """Monthly median; where everything is masked, falls back to the annual median.

    Without this safety net, one cloudy rainy season is enough to empty a whole month,
    and `sampleRegions` then simply drops the point concerned.

    The fallback is applied band by band: `unmask` rejects a multi-band
    replacement image, it only accepts a single band.
    """
    mensuelle = collection.filterDate(debut, fin)
    # A month with no acquisition at all gives a median with no bands, on which
    # `select` fails. This really happens: Sentinel-1 does not cover the whole
    # DRC every month. We then switch entirely to the annual median.
    mois = ee.Image(
        ee.Algorithms.If(mensuelle.size().gt(0), mensuelle.median(), secours)
    )
    return ee.Image.cat(
        [mois.select([bande]).unmask(secours.select([bande])) for bande in bandes]
    )


def construire_image(zone):
    """Stacks 12 months × (6 optical bands + 2 radar bands) into a single image."""
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(zone)
        .filterDate(f"{ANNEE}-01-01", f"{ANNEE + 1}-01-01")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .map(masquer_nuages)
        # Reflectance in 0-1, as in the notebook.
        .select(BANDES_S2)
        # An arithmetic operation returns an image without the original's
        # properties, date included. Without this copy, filterDate finds nothing
        # in composite_mensuel, and all twelve months fall back to the
        # annual median: this is what happened for 100% of the points.
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
            "Set PROJET to your Earth Engine Cloud project.\n"
            "You can find it at https://console.cloud.google.com/earth-engine"
        )
    if not ENTREE.exists():
        raise SystemExit(f"{ENTREE} not found, run sample_oil_palm.py first")

    ee.Initialize(project=PROJET)

    points = ee.FeatureCollection(json.loads(ENTREE.read_text(encoding="utf-8")))
    print(f"{points.size().getInfo()} points loaded")

    image = construire_image(points.geometry())
    colonnes = ["classe", "bloc"] + [
        f"{bande}_{mois:02d}" for mois in MOIS for bande in BANDES_S2 + BANDES_S1
    ]

    echantillons = image.sampleRegions(
        collection=points,
        properties=["classe", "bloc"],
        scale=10,
        tileScale=4,  # splits the computation: avoids running out of memory
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
        f"\nExport started: {NOM_EXPORT}.csv → Google Drive / {DOSSIER_DRIVE}\n"
        "Track it at: https://code.earthengine.google.com/tasks\n"
        "Once finished, download the CSV into data/ and run prepare_plots.py"
    )


if __name__ == "__main__":
    main()
