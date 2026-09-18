"""Interface locale de démonstration : une carte, un clic, la probabilité de palmier.

    python interface_demo.py

Ouvre http://127.0.0.1:8000 dans le navigateur. Le serveur n'écoute que sur cette
machine : aucun autre appareil ne peut s'y connecter, même sur le même réseau.

Le calcul est celui de verifier_site.py, importé et non recopié : l'interface, le
script et le connecteur Claude donnent donc toujours la même réponse. Compter 20 à
30 secondes par point, le temps qu'Earth Engine assemble les douze mois d'images.
"""
import glob
import threading
import time
import webbrowser
from functools import lru_cache
from pathlib import Path

import ee
import geopandas as gpd
import rasterio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from extraire_series_gee import ANNEE, PROJET, masquer_nuages
from verifier_site import (DOMAINE, MesureImpossible, charger_modele, hors_domaine,
                           probabilite_palmier)

# 127.0.0.1 et non 0.0.0.0 : c'est ce qui rend l'interface privée.
HOTE, PORT = "127.0.0.1", 8000
DOSSIER_PAGE = Path(__file__).parent / "interface"
SEUIL = 0.5

app = FastAPI(title="Classi-fy, démonstration locale", docs_url=None, redoc_url=None)


class Demande(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


@lru_cache(maxsize=1)
def blocs_testes():
    """Emprise des tuiles de 100 km qui portent au moins un point d'entraînement."""
    points = gpd.read_file("data/echantillons_rdc.geojson")
    blocs = []
    for chemin in sorted(glob.glob("data/palmier_extent/*.tif")):
        with rasterio.open(chemin) as source:
            b = source.bounds
        if len(points.cx[b.left:b.right, b.bottom:b.top]):
            blocs.append([[b.bottom, b.left], [b.top, b.right]])
    return blocs


def vignette(lat, lon):
    """Adresse d'une vignette Sentinel-2 de 1,4 km autour du point, ou None."""
    try:
        zone = ee.Geometry.Point([lon, lat]).buffer(700).bounds()
        image = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                 .filterBounds(zone)
                 .filterDate(f"{ANNEE}-01-01", f"{ANNEE + 1}-01-01")
                 .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
                 .map(masquer_nuages).median())
        return image.getThumbURL({"region": zone, "dimensions": 600, "format": "png",
                                  "bands": ["B4", "B3", "B2"], "min": 200, "max": 2200})
    except ee.EEException:
        # La vignette n'est qu'une illustration : son échec ne doit pas masquer la réponse.
        return None


@app.get("/")
def page():
    return FileResponse(DOSSIER_PAGE / "index.html")


@app.get("/logo.png")
def logo():
    return FileResponse(DOSSIER_PAGE / "logo.png")


@app.get("/api/zone")
def zone():
    charge = charger_modele()
    return {
        "blocs": blocs_testes(),
        "domaine": DOMAINE,
        "f1": round(charge["f1_macro_spatial"], 3),
        "ecart_type": round(charge["ecart_type"], 3),
        "seuil": SEUIL,
    }


@app.post("/api/verifier")
def verifier(demande: Demande):
    debut = time.perf_counter()
    try:
        probabilite = probabilite_palmier(demande.lat, demande.lon)
    except MesureImpossible as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from None
    return {
        "lat": demande.lat,
        "lon": demande.lon,
        "probabilite": round(float(probabilite), 3),
        "palmier": bool(probabilite >= SEUIL),
        "dans_zone": not hors_domaine(demande.lat, demande.lon),
        "vignette": vignette(demande.lat, demande.lon),
        "duree": round(time.perf_counter() - debut, 1),
    }


def main():
    print("Connexion à Earth Engine et chargement du modèle...")
    ee.Initialize(project=PROJET)
    charger_modele()
    print(f"{len(blocs_testes())} blocs testés chargés")
    adresse = f"http://{HOTE}:{PORT}"
    print(f"Interface prête : {adresse}  (Ctrl+C pour arrêter)")
    threading.Timer(1.5, lambda: webbrowser.open(adresse)).start()
    uvicorn.run(app, host=HOTE, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
