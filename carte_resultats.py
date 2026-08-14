"""Produit la carte des résultats destinée au portfolio et aux réseaux sociaux.

    python carte_resultats.py

Lit `data/predictions_test.geojson` et écrit `portfolio/carte-blocs-test.png`.

La carte montre deux blocs de test côte à côte, le meilleur et le pire, pour rendre
visible ce que l'écart type de 0,022 entre plis signifie sur le terrain. Les quatre
couleurs sont les quatre cases de la matrice de confusion.

Les mentions de licence et la portée du résultat sont gravées dans l'image et non
laissées au texte d'accompagnement : une image partagée sur un réseau social circule
sans sa légende.
"""

import json
import urllib.request
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

DOSSIER = Path("data")
PREDICTIONS = DOSSIER / "predictions_test.geojson"
CONTOURS = DOSSIER / "contours_pays.geojson"
GRILLE = DOSSIER / "palmier_grille" / "Grid_OilPalm2016-2021.shp"
SORTIE = Path("portfolio") / "carte-blocs-test.png"

# Palette validée sur toutes les paires : écart minimal 13,4 en vision déficiente,
# 19,1 en vision normale. Froid pour les décisions correctes, chaud pour les erreurs.
COULEURS = {
    "Palmier détecté": "#0AA5AE",
    "Correctement écarté": "#2C5FBF",
    "Fausse alerte": "#C9761B",
    "Palmier manqué": "#C2255C",
}
ORDRE = ["Palmier détecté", "Correctement écarté", "Fausse alerte", "Palmier manqué"]

ENCRE = "#0F1A15"
ENCRE_DOUCE = "#4B5C54"
ENCRE_PALE = "#74857C"
FOND = "#FCFCFB"
TERRE = "#ECF0ED"
TRAIT = "#C3CDC6"

PAYS = [
    "Dem Rep of the Congo", "Rep of the Congo", "Central African Rep", "Cameroon",
    "Gabon", "Angola", "Zambia", "Tanzania", "Burundi", "Rwanda", "Uganda",
    "South Sudan", "Eq. Guinea", "Malawi", "Kenya", "Sudan", "Chad", "Nigeria",
]


def contours_pays():
    """Contours simplifiés, récupérés une fois puis mis en cache localement.

    Source USDOS LSIB, domaine public, via Earth Engine.
    """
    if CONTOURS.exists():
        return gpd.read_file(CONTOURS)

    import ee
    from extraire_series_gee import PROJET

    ee.Initialize(project=PROJET)
    frontieres = (
        ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
        .filter(ee.Filter.inList("country_na", PAYS))
        .map(lambda f: ee.Feature(f.geometry().simplify(5000), {"nom": f.get("country_na")}))
    )
    donnees = frontieres.getInfo()
    CONTOURS.write_text(json.dumps(donnees), encoding="utf-8")
    print(f"contours récupérés et mis en cache dans {CONTOURS}")
    return gpd.read_file(CONTOURS)


def dessiner_bloc(axes, points, bloc, titre, sous_titre):
    """Un panneau : les points d'un bloc de test, colorés par case de la matrice."""
    extrait = points[points["bloc"] == bloc]
    minx, miny, maxx, maxy = extrait.total_bounds
    marge = 0.06
    axes.set_xlim(minx - marge, maxx + marge)
    axes.set_ylim(miny - marge, maxy + marge)
    axes.set_aspect("equal")
    axes.set_facecolor(TERRE)

    for categorie in ORDRE:
        sel = extrait[extrait["categorie"] == categorie]
        if sel.empty:
            continue
        # Les erreurs sont dessinées plus grandes et par-dessus : ce sont elles
        # que la carte doit rendre visibles.
        erreur = categorie in ("Fausse alerte", "Palmier manqué")
        axes.scatter(
            sel.geometry.x, sel.geometry.y,
            s=58 if erreur else 34,
            c=COULEURS[categorie],
            edgecolors="white",
            linewidths=0.9 if erreur else 0.6,
            zorder=4 if erreur else 3,
            alpha=0.95,
        )

    for cote in axes.spines.values():
        cote.set_color(TRAIT)
        cote.set_linewidth(1)
    axes.set_xticks([])
    axes.set_yticks([])

    axes.text(0, 1.085, titre, transform=axes.transAxes, fontsize=14,
              fontweight="bold", color=ENCRE, va="bottom", ha="left")
    axes.text(0, 1.02, sous_titre, transform=axes.transAxes, fontsize=10.5,
              color=ENCRE_DOUCE, va="bottom", ha="left")

    # Barre d'échelle : un degré de longitude vaut environ 111 km près de l'équateur.
    largeur = axes.get_xlim()[1] - axes.get_xlim()[0]
    km = 25
    long_barre = km / 111.0
    x0 = axes.get_xlim()[0] + largeur * 0.06
    y0 = axes.get_ylim()[0] + (axes.get_ylim()[1] - axes.get_ylim()[0]) * 0.06
    axes.plot([x0, x0 + long_barre], [y0, y0], color=ENCRE, linewidth=2.4,
              solid_capstyle="butt", zorder=6)
    axes.text(x0 + long_barre / 2, y0 + largeur * 0.018, f"{km} km", fontsize=8.5,
              color=ENCRE, ha="center", va="bottom", zorder=6)


def dessiner_reperage(axes, pays, tuiles, blocs_test, mis_en_avant):
    """Carte de repérage : les 34 blocs, apprentissage et test distingués."""
    pays.plot(ax=axes, color="#DFE6E1", zorder=1)
    pays.boundary.plot(ax=axes, color="#93A49B", linewidth=0.8, zorder=2)

    apprentissage = tuiles[~tuiles["ID"].isin(blocs_test)]
    test = tuiles[tuiles["ID"].isin(blocs_test)]
    apprentissage.plot(ax=axes, color=ENCRE_PALE, alpha=0.45, zorder=3)
    test.plot(ax=axes, color="#C2255C", alpha=0.9, zorder=4)

    for bloc in mis_en_avant:
        forme = tuiles[tuiles["ID"] == bloc]
        centre = forme.geometry.iloc[0].centroid
        axes.add_patch(Rectangle(
            (centre.x - 1.15, centre.y - 1.15), 2.3, 2.3,
            fill=False, edgecolor=ENCRE, linewidth=1.5, zorder=5,
        ))

    axes.set_xlim(11.0, 32.0)
    axes.set_ylim(-6.5, 5.5)
    axes.set_aspect("equal")
    axes.set_xticks([])
    axes.set_yticks([])
    axes.set_facecolor(FOND)
    for cote in axes.spines.values():
        cote.set_color(TRAIT)
        cote.set_linewidth(1)
    axes.text(0, 1.06, "Les 34 blocs, bassin du Congo", transform=axes.transAxes,
              fontsize=10, fontweight="bold", color=ENCRE, va="bottom", ha="left")
    axes.text(0, -0.14,
              "gris : apprentissage      cramoisi : test      cadre : blocs ci-dessus",
              transform=axes.transAxes, fontsize=8.5, color=ENCRE_PALE,
              va="top", ha="left")


def main():
    points = gpd.read_file(PREDICTIONS)
    pays = contours_pays()
    tuiles = gpd.read_file(GRILLE)
    tuiles["ID"] = tuiles["ID"].astype(int)

    blocs_test = sorted(points["bloc"].unique().tolist())
    meilleur, pire = 34542, 36100
    tuiles = tuiles[tuiles["ID"].isin(
        gpd.read_file(DOSSIER / "echantillons_rdc.geojson")["bloc"].unique().tolist()
    )]

    figure = plt.figure(figsize=(10.0, 8.4), dpi=200)
    figure.patch.set_facecolor(FOND)

    figure.text(0.05, 0.965,
                "Le même modèle, deux régions",
                fontsize=25, fontweight="bold", color=ENCRE, va="top")
    figure.text(0.05, 0.917,
                "Prédictions de palmier à huile sur deux blocs de 100 km tenus à l'écart "
                "de l'apprentissage.\nChaque point est une parcelle, sa couleur dit si le "
                "modèle a eu raison.",
                fontsize=11.5, color=ENCRE_DOUCE, va="top", linespacing=1.5)

    gauche = figure.add_axes([0.05, 0.415, 0.375, 0.395])
    droite = figure.add_axes([0.465, 0.415, 0.375, 0.395])

    n_g = points[points["bloc"] == meilleur]
    n_d = points[points["bloc"] == pire]
    dessiner_bloc(
        gauche, points, meilleur, "Cuvette centrale",
        f"{(n_g['categorie'] == 'Palmier manqué').sum()} palmeraies manquées "
        f"sur {(n_g['classe_reelle'] == 'palmier').sum()}",
    )
    dessiner_bloc(
        droite, points, pire, "Sud-Kivu",
        f"{(n_d['categorie'] == 'Palmier manqué').sum()} palmeraies manquées "
        f"sur {(n_d['classe_reelle'] == 'palmier').sum()}",
    )

    reperage = figure.add_axes([0.05, 0.115, 0.30, 0.165])
    dessiner_reperage(reperage, pays, tuiles, blocs_test, [meilleur, pire])

    poignees = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=9.5,
               markerfacecolor=COULEURS[c], markeredgecolor="white",
               markeredgewidth=0.9, label=c)
        for c in ORDRE
    ]
    figure.legend(
        handles=poignees, loc="upper left", bbox_to_anchor=(0.05, 0.365),
        ncol=4, frameon=False, fontsize=11.5, handletextpad=0.5,
        columnspacing=1.6, labelcolor=ENCRE,
    )

    figure.text(
        0.40, 0.245,
        "Bleus : décisions correctes.\n"
        "Ambre et cramoisi : erreurs, ce sont elles\n"
        "qui demanderaient une vérification humaine.",
        fontsize=10.5, color=ENCRE_DOUCE, va="top", linespacing=1.6,
    )
    figure.text(
        0.40, 0.135,
        "Démonstration sur deux blocs d'évaluation.\n"
        "Ce n'est pas une carte du palmier en RDC.",
        fontsize=10.5, color="#C2255C", va="top", fontweight="bold", linespacing=1.6,
    )
    figure.text(
        0.05, 0.048,
        "Étiquettes : Descals et al. 2024, Global Oil Palm extent maps, Zenodo, CC BY 4.0.\n"
        "Imagerie : Copernicus Sentinel-1 et Sentinel-2, ESA.   "
        "Contours : USDOS LSIB, domaine public.",
        fontsize=8.5, color=ENCRE_PALE, va="top", linespacing=1.6,
    )

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(SORTIE, facecolor=FOND, dpi=200)
    print(f"{SORTIE} écrit")
    print(f"blocs de test : {blocs_test}")


if __name__ == "__main__":
    main()
