"""Produces the verification priority map for social media.

    python priority_map.py                 French version
    python priority_map.py --langue en     English version

Writes `portfolio/priority-map-fr.png`, or `priority-map.png` in English.

This image answers a different question from results_map.py. That one showed whether
the model was right; this one shows what its probability is for when deciding
where to go in the field. Two panels: a mock-up of a mission map over
one block, and the share of palm actually present in each probability band.

The second panel is the safeguard for the first. A priority map alone suggests
that a colour amounts to a confirmation; the bars say that above 0.8
more than nine plots in ten really are palm, and that between 0.4 and 0.8 it is
about two in three.

Predictions are computed out of fold on all 8,658 plots: each plot is
predicted by a model that never saw its block. The file
`data/predictions_hors_pli.geojson` serves as a cache, it is recomputed if missing.
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

from results_map import (ENCRE, ENCRE_DOUCE, ENCRE_PALE, FOND, TERRE, TRAIT,
                             contours_pays)

DOSSIER = Path("data")
HORS_PLI = DOSSIER / "predictions_hors_pli.geojson"
GRILLE = DOSSIER / "palmier_grille" / "Grid_OilPalm2016-2021.shp"
ECHANTILLONS = DOSSIER / "echantillons_rdc.geojson"

# Block shown in the mock-up: 200 plots, 0.88 recall, close to the average of the 34.
# Extent 18.86 to 19.76 east and 2.70 to 3.59 north, i.e. Sud-Ubangi.
BLOC = 34546

# Three priority levels, not four matrix colours: the field decision
# has only three outcomes, go first, look later, leave.
# Teal and amber are the project's already validated pair. The grey is deliberately
# muted, that is its role, and it keeps a 15.6 difference from teal under protan vision.
HAUT = "#0AA5AE"
MOYEN = "#C9761B"
BAS = "#C6CFC9"
BAS_TRAIT = "#A8B4AD"
ALERTE = "#B91C1C"
PISTE = "#E2E8E4"

SEUIL_HAUT = 0.8
SEUIL_BAS = 0.4

# Bands shown as bars, from highest to lowest.
TRANCHES = [(0.8, 1.001), (0.6, 0.8), (0.4, 0.6), (0.2, 0.4), (0.0, 0.2)]

TEXTES = {
    "fr": {
        "sortie": "priority-map-fr.png",
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
        # The three entries fit on a single line: in French they must
        # stay short, the full line overflowed the figure.
        "niveaux": [
            "À vérifier d'abord   0,8 et plus",
            "À regarder ensuite   0,4 à 0,8",
            "Mis de côté   moins de 0,4",
        ],
        "parcelles": "{n} parcelles · {p} %",
        "moyenne": "moyenne des {n} parcelles, {p} %",
        "lecture": (
            "Au-dessus de 0,8, plus de neuf parcelles sur dix sont\n"
            "du palmier. Entre 0,4 et 0,8, environ deux sur trois :\n"
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
        "sortie": "priority-map.png",
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
            "Above 0.8, more than nine plots in ten are oil palm.\n"
            "Between 0.4 and 0.8, about two in three: that band\n"
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
    """Probability of each plot, predicted by a model that never saw its block.

    results_map.py works on a single fold, i.e. 1,790 plots: enough to
    compare two blocks, too few to fill five probability bands. Here all
    five folds are run and each plot gets the probability of the model
    trained without it, which covers all 8,658 plots and 34 blocks.
    """
    if HORS_PLI.exists():
        return gpd.read_file(HORS_PLI)

    from sklearn.model_selection import GroupKFold

    from binary_model import construire_variables
    from map_predictions import charger, modele_retenu

    parcelles = charger()
    X = construire_variables(parcelles)
    blocs = parcelles["bloc"]
    y = parcelles["classe"].map(
        lambda classe: "pas_de_palmier" if classe == "pas_de_palmier" else "palmier"
    )

    probabilites = np.zeros(len(parcelles))
    for app, test in GroupKFold(5).split(X, y, groups=blocs):
        modele = modele_retenu()
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
    print(f"{HORS_PLI} written, {len(resultat)} plots")
    return resultat


def dessiner_carte(axes, extrait, mots):
    """Mission map mock-up: the plots of one block, by priority level."""
    minx, miny, maxx, maxy = extrait.total_bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    portee = max(maxx - minx, maxy - miny) + 0.10
    axes.set_xlim(cx - portee / 2, cx + portee / 2)
    axes.set_ylim(cy - portee / 2, cy + portee / 2)
    axes.set_aspect("equal")
    axes.set_facecolor(TERRE)

    # From lowest to highest priority: what must be seen is drawn on top.
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

    # Scale bar: one degree of longitude is about 111 km near the equator.
    km = 25
    long_barre = km / 111.0
    x0 = axes.get_xlim()[0] + portee * 0.06
    y0 = axes.get_ylim()[0] + portee * 0.06
    axes.plot([x0, x0 + long_barre], [y0, y0], color=ENCRE, linewidth=2.4,
              solid_capstyle="butt", zorder=6)
    axes.text(x0 + long_barre / 2, y0 + portee * 0.018, f"{km} km", fontsize=8.5,
              color=ENCRE, ha="center", va="bottom", zorder=6)


def nombre(valeur, mots):
    """Language-specific thousands separator: space in French, comma in English."""
    return f"{valeur:,}".replace(",", mots["milliers"])


def dessiner_barres(axes, points, mots):
    """Share of palm actually present in each probability band.

    A bar's colour is that of the priority level its band belongs to:
    the two panels then speak about the same thing.
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

    # Reference line: without it, 91% has nothing to compare with.
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
    """The 34 blocks of the Congo Basin, with a frame around the one shown."""
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
    analyseur.add_argument("--langue", choices=sorted(TEXTES), default="fr",
                           help="image language, fr or en")
    mots = TEXTES[analyseur.parse_args().langue]
    sortie = Path("portfolio") / mots["sortie"]

    points = predictions_hors_pli()
    extrait = points[points["bloc"] == BLOC]
    if extrait.empty:
        raise SystemExit(f"block {BLOC} is missing from {HORS_PLI}")

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
    print(f"{sortie} written")


if __name__ == "__main__":
    main()
