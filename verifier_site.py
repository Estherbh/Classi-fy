"""Démo : dit si un point donné porte du palmier.

    python verifier_site.py --lat 0.91624 --lon 24.46476
    python verifier_site.py --lat 0.91624 --lon 24.46476 --langue en

Charge le modèle produit par modele_binaire.py, va chercher sur Earth Engine les douze
mois de Sentinel-1 et Sentinel-2 du seul pixel qui contient ce point, construit les
mêmes 34 variables que l'entraînement, et affiche la probabilité de palmier.

Prérequis identiques à extraire_series_gee.py : un compte Earth Engine authentifié et
`data/modele_palmier.joblib` déjà écrit. Compter une trentaine de secondes, tout le
calcul se fait côté Google.
"""

import argparse
from functools import lru_cache
from pathlib import Path

import ee
import joblib
import pandas as pd

from extraire_series_gee import (ANNEE, BANDES_S1, BANDES_S2, MOIS, PROJET,
                                 construire_image)
from modele_binaire import construire_variables

FICHIER_MODELE = Path("data") / "modele_palmier.joblib"

COLONNES = [f"{bande}_{mois:02d}" for mois in MOIS for bande in BANDES_S2 + BANDES_S1]

# Emprise des 34 blocs d'entraînement. En dehors, le modèle répond quand même mais sa
# performance n'a jamais été mesurée : c'est la première des limites connues du README.
DOMAINE = {"lon_min": 12.1, "lon_max": 30.1, "lat_min": -4.9, "lat_max": 4.0}

TEXTES = {
    "fr": {
        "site": "Site       ",
        "extraction": "Extraction ",
        "en_cours": "Sentinel-1 et Sentinel-2, année {annee}...",
        "palmier": "Palmier    ",
        "verdict": "Verdict    ",
        "oui": "palmier",
        "non": "pas de palmier",
        "seuil": "seuil",
        "modele": "Modèle     ",
        "performance": "F1 macro {f1:.3f} ± {ecart:.3f} en validation spatiale",
        "image": "Image      ",
        "hors_domaine": (
            "Hors de l'emprise des 34 blocs d'entraînement, {lon_min} à {lon_max} est "
            "et {lat_min} à {lat_max} nord.\n"
            "    La réponse ci-dessous n'est adossée à aucune mesure de performance."
        ),
        "sans_modele": "{fichier} introuvable, lance d'abord modele_binaire.py",
        "sans_mesure": (
            "{n} bandes sans valeur sur ce point, dont {exemples}.\n"
            "Soit le point sort de la couverture Sentinel-1, soit il est masqué toute "
            "l'année. Essaie un point voisin."
        ),
    },
    "en": {
        "site": "Site       ",
        "extraction": "Extracting ",
        "en_cours": "Sentinel-1 and Sentinel-2, year {annee}...",
        "palmier": "Oil palm   ",
        "verdict": "Verdict    ",
        "oui": "oil palm",
        "non": "no oil palm",
        "seuil": "threshold",
        "modele": "Model      ",
        "performance": "macro F1 {f1:.3f} ± {ecart:.3f} under spatial validation",
        "image": "Imagery    ",
        "hors_domaine": (
            "Outside the 34 training blocks, {lon_min} to {lon_max} east and "
            "{lat_min} to {lat_max} north.\n"
            "    The answer below is backed by no measured performance."
        ),
        "sans_modele": "{fichier} not found, run modele_binaire.py first",
        "sans_mesure": (
            "{n} bands have no value at this point, including {exemples}.\n"
            "Either the point falls outside Sentinel-1 coverage, or it is masked all "
            "year. Try a nearby point."
        ),
    },
}


def hors_domaine(lat, lon):
    """Dit si le point sort de l'emprise sur laquelle le modèle a été validé."""
    return not (
        DOMAINE["lon_min"] <= lon <= DOMAINE["lon_max"]
        and DOMAINE["lat_min"] <= lat <= DOMAINE["lat_max"]
    )


class MesureImpossible(Exception):
    """Le pixel visé n'a de valeur pour au moins une bande sur aucun mois."""


@lru_cache(maxsize=1)
def charger_modele():
    """Modèle et métadonnées sauvegardés par modele_binaire.py, lus une seule fois."""
    return joblib.load(FICHIER_MODELE)


def mesurer(lat, lon, mots):
    """Renvoie les 96 mesures mensuelles du pixel qui contient ce point.

    `reduceRegion` avec le réducteur `first` à 10 m prend exactement le pixel visé,
    comme le faisait `sampleRegions` sur les 8 658 points d'entraînement.
    """
    point = ee.Geometry.Point([lon, lat])
    mesures = construire_image(point).reduceRegion(
        reducer=ee.Reducer.first(), geometry=point, scale=10
    ).getInfo()

    absentes = [colonne for colonne in COLONNES if mesures.get(colonne) is None]
    if absentes:
        raise MesureImpossible(
            mots["sans_mesure"].format(n=len(absentes), exemples=", ".join(absentes[:4]))
        )
    return pd.DataFrame([{colonne: mesures[colonne] for colonne in COLONNES}])


def probabilite_palmier(lat, lon, mots=TEXTES["en"]):
    """Probabilité de palmier sur un point, sans rien afficher.

    Partagée par ce script, l'interface de démonstration et le connecteur Claude,
    pour que les trois donnent exactement la même réponse. Earth Engine doit déjà
    être initialisé.
    """
    charge = charger_modele()
    modele = charge["modele"]
    variables = construire_variables(mesurer(lat, lon, mots))
    probabilites = dict(
        zip(modele.classes_, modele.predict_proba(variables[charge["variables"]])[0])
    )
    return probabilites["palmier"]


def main():
    analyseur = argparse.ArgumentParser(
        description="Probabilité de palmier sur un point donné."
    )
    analyseur.add_argument("--lat", type=float, required=True, help="latitude en degrés")
    analyseur.add_argument("--lon", type=float, required=True, help="longitude en degrés")
    analyseur.add_argument(
        "--seuil", type=float, default=0.5,
        help="probabilité à partir de laquelle on répond palmier (défaut 0.5)",
    )
    analyseur.add_argument("--langue", choices=sorted(TEXTES), default="fr")
    analyseur.add_argument("--projet", default=PROJET, help="projet Cloud Earth Engine")
    arguments = analyseur.parse_args()
    mots = TEXTES[arguments.langue]

    if not FICHIER_MODELE.exists():
        raise SystemExit(mots["sans_modele"].format(fichier=FICHIER_MODELE))
    charge = charger_modele()

    print(f"{mots['site']}: {arguments.lat:.5f}, {arguments.lon:.5f}")
    if hors_domaine(arguments.lat, arguments.lon):
        print("[!] " + mots["hors_domaine"].format(**DOMAINE))
    ee.Initialize(project=arguments.projet)
    print(f"{mots['extraction']}: " + mots["en_cours"].format(annee=ANNEE))

    try:
        probabilite = probabilite_palmier(arguments.lat, arguments.lon, mots)
    except MesureImpossible as erreur:
        raise SystemExit(str(erreur)) from None

    print(f"\n{mots['palmier']}: {probabilite:.2f}")
    print(
        f"{mots['verdict']}: {mots['oui'] if probabilite >= arguments.seuil else mots['non']}"
        f"  ({mots['seuil']} {arguments.seuil:.2f})"
    )
    print(
        f"{mots['modele']}: "
        + mots["performance"].format(
            f1=charge["f1_macro_spatial"], ecart=charge["ecart_type"]
        )
    )
    print(
        f"{mots['image']}: "
        f"https://www.google.com/maps/@{arguments.lat},{arguments.lon},2000m/data=!3m1!1e3"
    )


if __name__ == "__main__":
    main()
