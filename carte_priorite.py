"""Produit la carte de priorité de vérification destinée aux réseaux sociaux.

    python carte_priorite.py                 version française
    python carte_priorite.py --langue en     version anglaise

Écrit `portfolio/carte-priorite.png`, ou `carte-priorite-en.png` en anglais.

Cette image répond à une autre question que carte_resultats.py. Celle-là montrait si
le modèle a eu raison ; celle-ci montre à quoi sert sa probabilité quand il faut
décider où aller sur le terrain. Deux panneaux : une maquette de carte de mission sur
un bloc, et la part de palmier réellement présent dans chaque tranche de probabilité.

Le second panneau est le garde-fou du premier. Une carte de priorité seule laisse
croire qu'une couleur vaut une confirmation ; les barres disent qu'au-dessus de 0,8
neuf parcelles sur dix sont vraiment du palmier, et qu'entre 0,4 et 0,8 c'est à peu
près une sur deux.

Les prédictions sont calculées hors pli sur les 8 658 parcelles : chaque parcelle est
prédite par un modèle qui n'a jamais vu son bloc. Le fichier
`data/predictions_hors_pli.geojson` sert de cache, il est recalculé s'il manque.
"""

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from carte_resultats import (ENCRE, ENCRE_DOUCE, ENCRE_PALE, FOND, TERRE, TRAIT,
                             contours_pays)

DOSSIER = Path("data")
HORS_PLI = DOSSIER / "predictions_hors_pli.geojson"
GRILLE = DOSSIER / "palmier_grille" / "Grid_OilPalm2016-2021.shp"
ECHANTILLONS = DOSSIER / "echantillons_rdc.geojson"

# Bloc montré en maquette : 200 parcelles, 0,88 de rappel, proche de la moyenne des 34.
# Emprise 18,86 à 19,76 est et 2,70 à 3,59 nord, soit le Sud-Ubangi.
BLOC = 34546

# Trois niveaux de priorité, pas quatre couleurs de matrice : la décision de terrain
# n'a que trois issues, on y va d'abord, on regarde ensuite, on laisse.
# Sarcelle et ambre sont la paire déjà validée du projet. Le gris est délibérément
# effacé, c'est son rôle, et il garde 15,6 d'écart avec la sarcelle en vision protan.
HAUT = "#0AA5AE"
MOYEN = "#C9761B"
BAS = "#C6CFC9"
BAS_TRAIT = "#A8B4AD"
ALERTE = "#B91C1C"
PISTE = "#E2E8E4"

SEUIL_HAUT = 0.8
SEUIL_BAS = 0.4

# Tranches affichées en barres, de la plus haute à la plus basse.
TRANCHES = [(0.8, 1.001), (0.6, 0.8), (0.4, 0.6), (0.2, 0.4), (0.0, 0.2)]

TEXTES = {
    "fr": {
        "sortie": "carte-priorite.png",
        "titre": "Où regarder en premier",
        "chapeau": (
            "Le modèle rend une probabilité, pas un verdict. Trier les parcelles par "
            "cette probabilité transforme l'imagerie satellite\nen ordre de "
            "vérification pour une mission de terrain. Maquette, sur des parcelles "
            "tenues à l'écart de l'apprentissage."
        ),
        "oeil_carte": "MAQUETTE DE CARTE",
        "titre_carte": "Sud-Ubangi, RDC",
        "sous_carte": "{n} parcelles d'un bloc d'évaluation de 100 km",
        "oeil_barres": "CE QUE VAUT LE CLASSEMENT",
        "titre_barres": "{n} parcelles, 34 blocs",
        "sous_barres": "Part de palmier réellement présent, par tranche de probabilité",
        # Les trois entrées tiennent sur une seule ligne : en français elles doivent
        # rester courtes, la ligne complète débordait de la figure.
        "niveaux": [
            "À vérifier d'abord   0,8 et plus",
            "À regarder ensuite   0,4 à 0,8",
            "Mis de côté   moins de 0,4",
        ],
        "parcelles": "{n} parcelles · {p} %",
        "moyenne": "moyenne des {n} parcelles, {p} %",
        "lecture": (
            "Au-dessus de 0,8, neuf parcelles sur dix sont vraiment\n"
            "du palmier. Entre 0,4 et 0,8, à peu près une sur deux :\n"
            "c'est cette tranche que le terrain tranche."
        ),
        "portee": (
            "Maquette sur des blocs d'évaluation.\n"
            "Ce n'est pas une carte du palmier en RDC."
        ),
        "reperage": "Le bloc montré, parmi les 34",
        "attributions": (
            "Étiquettes : Descals et al. 2024, Global Oil Palm extent maps, Zenodo, "
            "CC BY 4.0.\nImagerie : Copernicus Sentinel-1 et Sentinel-2, ESA.   "
            "Contours : USDOS LSIB, domaine public."
        ),
        "pourcent": "{v:.0f} %",
        "tranche": "{lo:.1f} à {hi:.1f}",
        "milliers": " ",
    },
    "en": {
        "sortie": "carte-priorite-en.png",
        "titre": "Where to look first",
        "chapeau": (
            "The model returns a probability, not a verdict. Sorting plots by that "
            "probability turns satellite imagery into\na verification order for a field "
            "mission. Prototype, on plots held out of training."
        ),
        "oeil_carte": "MAP PROTOTYPE",
        "titre_carte": "Sud-Ubangi, DR Congo",
        "sous_carte": "{n} plots in one 100 km evaluation block",
        "oeil_barres": "WHAT THE RANKING IS WORTH",
        "titre_barres": "{n} plots, 34 blocks",
        "sous_barres": "Share that really is oil palm, by probability band",
        "niveaux": [
            "Verify first   probability 0.8 and above",
            "Second look   0.4 to 0.8",
            "Set aside   below 0.4",
        ],
        "parcelles": "{n} plots · {p}%",
        "moyenne": "average across all {n} plots, {p}%",
        "lecture": (
            "Above 0.8, nine plots in ten really are oil palm.\n"
            "Between 0.4 and 0.8, close to one in two: that band\n"
            "is the one field work has to settle."
        ),
        "portee": (
            "Prototype on evaluation blocks.\n"
            "This is not a map of oil palm in the DRC."
        ),
        "reperage": "The block shown, among the 34",
        "attributions": (
            "Labels: Descals et al. 2024, Global Oil Palm extent maps, Zenodo, "
            "CC BY 4.0.\nImagery: Copernicus Sentinel-1 and Sentinel-2, ESA.   "
            "Boundaries: USDOS LSIB, public domain."
        ),
        "pourcent": "{v:.0f}%",
        "tranche": "{lo:.1f} to {hi:.1f}",
        "milliers": ",",
    },
}


def predictions_hors_pli():
    """Probabilité de chaque parcelle, prédite par un modèle qui ignore son bloc.

    carte_resultats.py travaille sur un seul pli, soit 1 790 parcelles : assez pour
    comparer deux blocs, trop peu pour remplir cinq tranches de probabilité. Ici les
    cinq plis sont parcourus et chaque parcelle reçoit la probabilité du modèle
    entraîné sans elle, ce qui couvre les 8 658 parcelles et les 34 blocs.
    """
    if HORS_PLI.exists():
        return gpd.read_file(HORS_PLI)

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import GroupKFold

    from modele_binaire import construire_variables
    from predictions_carte import charger

    parcelles = charger()
    X = construire_variables(parcelles)
    blocs = parcelles["bloc"]
    y = parcelles["classe"].map(
        lambda classe: "pas_de_palmier" if classe == "pas_de_palmier" else "palmier"
    )

    probabilites = np.zeros(len(parcelles))
    for app, test in GroupKFold(5).split(X, y, groups=blocs):
        modele = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.08, random_state=0
        )
        modele.fit(X.iloc[app], y.iloc[app])
        colonne = list(modele.classes_).index("palmier")
        probabilites[test] = modele.predict_proba(X.iloc[test])[:, colonne]

    resultat = gpd.GeoDataFrame(
        {
            "bloc": blocs.values,
            "palmier": (y == "palmier").astype(int).values,
            "probabilite": probabilites.round(4),
        },
        geometry=gpd.points_from_xy(parcelles["lon"], parcelles["lat"]),
        crs="EPSG:4326",
    )
    resultat.to_file(HORS_PLI, driver="GeoJSON")
    print(f"{HORS_PLI} écrit, {len(resultat)} parcelles")
    return resultat


def dessiner_carte(axes, extrait, mots):
    """Maquette de carte de mission : les parcelles d'un bloc, par niveau de priorité."""
    minx, miny, maxx, maxy = extrait.total_bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    portee = max(maxx - minx, maxy - miny) + 0.10
    axes.set_xlim(cx - portee / 2, cx + portee / 2)
    axes.set_ylim(cy - portee / 2, cy + portee / 2)
    axes.set_aspect("equal")
    axes.set_facecolor(TERRE)

    # Du moins prioritaire au plus prioritaire : ce qu'il faut voir passe au-dessus.
    niveaux = [
        (extrait["probabilite"] < SEUIL_BAS, BAS, BAS_TRAIT, 26, 3),
        ((extrait["probabilite"] >= SEUIL_BAS) & (extrait["probabilite"] < SEUIL_HAUT),
         MOYEN, "white", 54, 4),
        (extrait["probabilite"] >= SEUIL_HAUT, HAUT, "white", 72, 5),
    ]
    for masque, couleur, contour, taille, rang in niveaux:
        sel = extrait[masque]
        if sel.empty:
            continue
        axes.scatter(
            sel.geometry.x, sel.geometry.y,
            s=taille, c=couleur, edgecolors=contour, linewidths=0.9,
            zorder=rang, alpha=0.95,
        )

    for cote in axes.spines.values():
        cote.set_color(TRAIT)
        cote.set_linewidth(1)
    axes.set_xticks([])
    axes.set_yticks([])

    axes.text(0, 1.135, " ".join(mots["oeil_carte"]), transform=axes.transAxes,
              fontsize=9.5, fontweight="bold", color=HAUT, va="bottom", ha="left")
    axes.text(0, 1.062, mots["titre_carte"], transform=axes.transAxes, fontsize=15,
              fontweight="bold", color=ENCRE, va="bottom", ha="left")
    axes.text(0, 1.012, mots["sous_carte"].format(n=len(extrait)),
              transform=axes.transAxes, fontsize=10.5, color=ENCRE_DOUCE,
              va="bottom", ha="left")

    # Barre d'échelle : un degré de longitude vaut environ 111 km près de l'équateur.
    km = 25
    long_barre = km / 111.0
    x0 = axes.get_xlim()[0] + portee * 0.06
    y0 = axes.get_ylim()[0] + portee * 0.06
    axes.plot([x0, x0 + long_barre], [y0, y0], color=ENCRE, linewidth=2.4,
              solid_capstyle="butt", zorder=6)
    axes.text(x0 + long_barre / 2, y0 + portee * 0.018, f"{km} km", fontsize=8.5,
              color=ENCRE, ha="center", va="bottom", zorder=6)


def nombre(valeur, mots):
    """Séparateur de milliers propre à la langue : espace en français, virgule en anglais."""
    return f"{valeur:,}".replace(",", mots["milliers"])


def dessiner_barres(axes, points, mots):
    """Part de palmier réellement présent dans chaque tranche de probabilité.

    La couleur d'une barre est celle du niveau de priorité auquel sa tranche
    appartient : les deux panneaux parlent alors de la même chose.
    """
    total = len(points)
    positions = list(range(len(TRANCHES)))[::-1]

    for rang, (lo, hi) in zip(positions, TRANCHES):
        sel = points[(points["probabilite"] >= lo) & (points["probabilite"] < hi)]
        part = sel["palmier"].mean()
        couleur = HAUT if lo >= SEUIL_HAUT else MOYEN if lo >= SEUIL_BAS else BAS

        axes.barh(rang, 1.0, height=0.62, color=PISTE, zorder=1)
        axes.barh(rang, part, height=0.62, color=couleur, zorder=2,
                  edgecolor=BAS_TRAIT if couleur is BAS else "none", linewidth=0.8)
        axes.text(part + 0.018, rang, mots["pourcent"].format(v=part * 100),
                  va="center", ha="left", fontsize=13, fontweight="bold", color=ENCRE,
                  zorder=3)
        axes.text(-0.025, rang + 0.20, mots["tranche"].format(lo=lo, hi=min(hi, 1.0)),
                  va="center", ha="right", fontsize=11, fontweight="bold", color=ENCRE)
        axes.text(-0.025, rang - 0.22,
                  mots["parcelles"].format(n=nombre(len(sel), mots),
                                           p=round(len(sel) / total * 100)),
                  va="center", ha="right", fontsize=9, color=ENCRE_PALE)

    # Repère : sans lui, 91 % n'a rien à quoi se comparer.
    moyenne = points["palmier"].mean()
    axes.axvline(moyenne, color=ENCRE_PALE, linewidth=1.1, linestyle=(0, (4, 3)),
                 zorder=4, ymin=0.05)
    axes.text(moyenne, -0.58,
              mots["moyenne"].format(n=nombre(total, mots), p=round(moyenne * 100)),
              va="center", ha="center", fontsize=9, color=ENCRE_PALE)

    axes.set_xlim(-0.30, 1.14)
    axes.set_ylim(-0.72, len(TRANCHES) - 0.18)
    axes.axis("off")

    axes.text(0, 1.135, " ".join(mots["oeil_barres"]), transform=axes.transAxes,
              fontsize=9.5, fontweight="bold", color=MOYEN, va="bottom", ha="left")
    axes.text(0, 1.062, mots["titre_barres"].format(n=nombre(total, mots)),
              transform=axes.transAxes, fontsize=15, fontweight="bold", color=ENCRE,
              va="bottom", ha="left")
    axes.text(0, 1.012, mots["sous_barres"], transform=axes.transAxes, fontsize=10.5,
              color=ENCRE_DOUCE, va="bottom", ha="left")


def dessiner_reperage(axes, pays, tuiles, mots):
    """Les 34 blocs du bassin du Congo, avec un cadre sur celui qui est montré."""
    pays.plot(ax=axes, color="#DFE6E1", zorder=1)
    pays.boundary.plot(ax=axes, color="#93A49B", linewidth=0.8, zorder=2)
    tuiles.plot(ax=axes, color=ENCRE_PALE, alpha=0.45, zorder=3)

    centre = tuiles[tuiles["ID"] == BLOC].geometry.iloc[0].centroid
    axes.add_patch(Rectangle((centre.x - 1.15, centre.y - 1.15), 2.3, 2.3,
                             fill=False, edgecolor=HAUT, linewidth=1.8, zorder=5))

    axes.set_xlim(11.0, 32.0)
    axes.set_ylim(-6.5, 5.5)
    axes.set_aspect("equal")
    axes.set_xticks([])
    axes.set_yticks([])
    axes.set_facecolor(FOND)
    for cote in axes.spines.values():
        cote.set_color(TRAIT)
        cote.set_linewidth(1)
    axes.text(0, 1.06, mots["reperage"], transform=axes.transAxes, fontsize=10,
              fontweight="bold", color=ENCRE, va="bottom", ha="left")


def main():
    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--langue", choices=sorted(TEXTES), default="fr")
    mots = TEXTES[analyseur.parse_args().langue]
    sortie = Path("portfolio") / mots["sortie"]

    points = predictions_hors_pli()
    extrait = points[points["bloc"] == BLOC]
    if extrait.empty:
        raise SystemExit(f"le bloc {BLOC} est absent de {HORS_PLI}")

    pays = contours_pays()
    tuiles = gpd.read_file(GRILLE)
    tuiles["ID"] = tuiles["ID"].astype(int)
    tuiles = tuiles[tuiles["ID"].isin(points["bloc"].unique().tolist())]

    figure = plt.figure(figsize=(10.0, 8.6), dpi=300)
    figure.patch.set_facecolor(FOND)

    figure.text(0.05, 0.977, mots["titre"], fontsize=25, fontweight="bold",
                color=ENCRE, va="top")
    figure.text(0.05, 0.927, mots["chapeau"], fontsize=11.5, color=ENCRE_DOUCE,
                va="top", linespacing=1.5)

    cote = 0.355
    hauteur = cote * 10.0 / 8.6
    carte = figure.add_axes([0.05, 0.335, cote, hauteur])
    dessiner_carte(carte, extrait, mots)

    barres = figure.add_axes([0.505, 0.335, 0.435, hauteur])
    dessiner_barres(barres, points, mots)

    poignees = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=taille,
               markerfacecolor=couleur, markeredgecolor=contour, markeredgewidth=0.9,
               label=texte)
        for (couleur, contour, taille), texte in zip(
            [(HAUT, "white", 10.5), (MOYEN, "white", 9), (BAS, BAS_TRAIT, 7)],
            mots["niveaux"],
        )
    ]
    figure.legend(handles=poignees, loc="upper left", bbox_to_anchor=(0.042, 0.288),
                  ncol=3, frameon=False, fontsize=11, handletextpad=0.5,
                  columnspacing=1.5, labelcolor=ENCRE)

    reperage = figure.add_axes([0.05, 0.085, 0.245, 0.107])
    dessiner_reperage(reperage, pays, tuiles, mots)

    figure.text(0.375, 0.212, mots["lecture"], fontsize=10.5, color=ENCRE_DOUCE,
                va="top", linespacing=1.6)
    figure.text(0.375, 0.117, mots["portee"], fontsize=10.5, color=ALERTE,
                va="top", fontweight="bold", linespacing=1.6)
    figure.text(0.05, 0.048, mots["attributions"], fontsize=8.5, color=ENCRE_PALE,
                va="top", linespacing=1.6)

    sortie.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(sortie, facecolor=FOND, dpi=300)
    print(f"{sortie} écrit")


if __name__ == "__main__":
    main()
