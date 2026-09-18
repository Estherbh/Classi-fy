"""Connecteur MCP : donne à Claude l'accès au modèle de détection du palmier à huile.

Enregistrement dans Claude Code, une seule fois, visible de cette seule machine :

    claude mcp add classify --scope local -- python C:/EPx/Classify/mcp_classify.py

Claude peut alors répondre à « y a-t-il du palmier en 0,913, 24,466 ? » en appelant
l'outil check_oil_palm. Le calcul est celui de verifier_site.py, importé et non
recopié : le script, l'interface et Claude donnent toujours la même réponse.

Le serveur échange avec Claude sur l'entrée et la sortie standard. Il ne doit donc
rien écrire d'autre sur la sortie standard : un simple print casserait le protocole.
"""
import os
from functools import lru_cache
from pathlib import Path

# Les chemins data/ du projet sont relatifs : on se place à la racine du projet, quel
# que soit le dossier depuis lequel Claude Code lance le serveur. Avant les imports du
# projet, qui résolvent ces chemins.
os.chdir(Path(__file__).resolve().parent)

import ee  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from extraire_series_gee import PROJET  # noqa: E402
from verifier_site import (DOMAINE, MesureImpossible, charger_modele,  # noqa: E402
                           hors_domaine, probabilite_palmier)

SEUIL = 0.5

serveur = MCPServer(
    name="classify",
    instructions=(
        "Research prototype that estimates whether a given location has oil palm, from "
        "free Sentinel-1 radar and Sentinel-2 optical imagery. It was evaluated only on 34 "
        "blocks of the Congo Basin. Always tell the user whether a point is inside that "
        "tested area, and never present results as a map of oil palm."
    ),
)


@lru_cache(maxsize=1)
def initialiser():
    """Connexion Earth Engine et chargement du modèle, au premier appel seulement.

    Pas au démarrage : Claude Code attend que le serveur réponde vite, et la connexion à
    Earth Engine prend quelques secondes.
    """
    ee.Initialize(project=PROJET)
    return charger_modele()


@serveur.tool()
def check_oil_palm(latitude: float, longitude: float) -> dict:
    """Estimate the probability that oil palm grows at one location.

    Reads twelve months of 2021 Sentinel-1 and Sentinel-2 imagery for the 10 m pixel at
    the given coordinates and runs the trained classifier on it. Takes 5 to 30 seconds.

    Returns the probability, the verdict at a 0.5 threshold, and whether the point lies
    inside the 34 blocks where the model was evaluated. Outside them, no performance was
    ever measured: report the number as unverified. Inside them, on regions it had never
    seen, the model found 90 in 100 plantations and 87 in 100 of its palm alerts were right.

    Args:
        latitude: Decimal degrees, between -90 and 90.
        longitude: Decimal degrees, between -180 and 180.
    """
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        # ToolError et non ValueError : mcp 2.x ne transmet à Claude que le message des
        # erreurs prévues, les autres arrivent comme un plantage anonyme.
        raise ToolError("Latitude must be between -90 and 90, longitude between -180 and 180.")

    charge = initialiser()
    try:
        probabilite = float(probabilite_palmier(latitude, longitude))
    except MesureImpossible as erreur:
        raise ToolError(str(erreur)) from None

    dans_zone = not hors_domaine(latitude, longitude)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "oil_palm_probability": round(probabilite, 3),
        "verdict": "oil palm" if probabilite >= SEUIL else "no oil palm",
        "threshold": SEUIL,
        "inside_tested_area": dans_zone,
        "tested_area": (f"34 blocks within {DOMAINE['lon_min']} to {DOMAINE['lon_max']} east, "
                        f"{DOMAINE['lat_min']} to {DOMAINE['lat_max']} north"),
        "reliability": (
            "Evaluated area. On unseen regions: 90 in 100 plantations found, 87 in 100 palm alerts right."
            if dans_zone else
            "Outside the evaluated area. No measured performance: treat this probability as unverified."
        ),
        "model_macro_f1_unseen_regions": round(charge["f1_macro_spatial"], 3),
        "satellite_view": f"https://www.google.com/maps/@{latitude},{longitude},2000m/data=!3m1!1e3",
    }


if __name__ == "__main__":
    serveur.run()
