"""Produit la carte des résultats destinée au portfolio et aux réseaux sociaux.

    python results_map.py                 version française
    python results_map.py --langue en     version anglaise

Lit `data/predictions_test.geojson` et écrit `portfolio/test-blocks-map-fr.png`, ou
`test-blocks-map.png` en anglais.

La carte montre deux blocs de test côte à côte, le meilleur et le pire, pour rendre
visible ce que l'écart type de 0,015 entre plis signifie sur le terrain. Les quatre
couleurs sont les quatre cases de la matrice de confusion.

Les mentions de licence et la portée du résultat sont gravées dans l'image et non
laissées au texte d'accompagnement : une image partagée sur un réseau social circule
sans sa légende.
"""

import argparse
import json
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

# Palette validée sur toutes les paires : écart minimal 10,4 en vision déficiente,
# 15,3 en vision normale. Froid pour les décisions correctes, chaud pour les erreurs.
# La paire critique est ambre contre rouge, les deux types d'erreur : ils n'ont pas le
# même coût opérationnel, les confondre viderait la carte de son intérêt. Un rouge plus
# vif tombe sous le plancher, ne pas l'éclaircir.
COULEURS = {
    "Palmier détecté": "#0AA5AE",
    "Correctement écarté": "#2C5FBF",
    "Fausse alerte": "#C9761B",
    "Palmier manqué": "#B91C1C",
}
# Clés de données, toujours en français : elles viennent du fichier de prédictions.
ORDRE = ["Palmier détecté", "Correctement écarté", "Fausse alerte", "Palmier manqué"]

ENCRE = "#0F1A15"
ENCRE_DOUCE = "#4B5C54"
ENCRE_PALE = "#74857C"
FOND = "#FCFCFB"
TERRE = "#ECF0ED"
TRAIT = "#C3CDC6"

TEXTES = {
    "fr": {
        "sortie": "test-blocks-map-fr.png",
        "titre": "Le même modèle, deux régions",
        "chapeau": (
            "Prédictions de palmier à huile sur deux blocs de 100 km tenus à l'écart de "
            "l'apprentissage, le meilleur et le pire\ndes sept blocs d'évaluation. Chaque "
            "point est une parcelle, sa couleur dit si le modèle a eu raison."
        ),
        "meilleur": "LE MEILLEUR CAS",
        "pire": "LE PIRE CAS",
        "region_meilleur": "Cuvette centrale",
        "region_pire": "Sud-Kivu",
        "manquees": "{n} palmeraies manquées sur {total}",
        "categories": {
            "Palmier détecté": "Palmier détecté",
            "Correctement écarté": "Correctement écarté",
            "Fausse alerte": "Fausse alerte",
            "Palmier manqué": "Palmier manqué",
        },
        "reperage": "Les 34 blocs, bassin du Congo",
        "reperage_legende": "gris : apprentissage      rouge : test",
        "lecture": (
            "Bleus : décisions correctes.\n"
            "Ambre et rouge : erreurs, ce sont elles\n"
            "qui demanderaient une vérification humaine."
        ),
        "portee": (
            "Démonstration sur deux blocs d'évaluation.\n"
            "Ce n'est pas une carte du palmier en RDC."
        ),
        "attributions": (
            "Étiquettes : Descals et al. 2024, Global Oil Palm extent maps, Zenodo, "
            "CC BY 4.0.\nImagerie : Copernicus Sentinel-1 et Sentinel-2, ESA.   "
            "Contours : USDOS LSIB, domaine public."
        ),
        "pourcent": "{v:.0f} %",
    },
    "en": {
        "sortie": "test-blocks-map.png",
        "titre": "One model, two regions",
        "chapeau": (
            "Oil palm predictions on two 100 km blocks held out of training, the best and "
            "the worst\nof the seven evaluation blocks. Each dot is a plot, its colour says "
            "whether the model got it right."
        ),
        "meilleur": "THE BEST CASE",
        "pire": "THE WORST CASE",
        "region_meilleur": "Central basin",
        "region_pire": "South Kivu",
        "manquees": "{n} palm plots missed out of {total}",
        "categories": {
            "Palmier détecté": "Palm detected",
            "Correctement écarté": "Correctly excluded",
            "Fausse alerte": "False alarm",
            "Palmier manqué": "Palm missed",
        },
        "reperage": "The 34 blocks, Congo Basin",
        "reperage_legende": "grey: training      red: test",
        "lecture": (
            "Blues: correct decisions.\n"
            "Amber and red: errors, these are the ones\n"
            "that would need human verification."
        ),
        "portee": (
            "Demonstration on two evaluation blocks.\n"
            "This is not a map of oil palm in the DRC."
        ),
        "attributions": (
            "Labels: Descals et al. 2024, Global Oil Palm extent maps, Zenodo, "
            "CC BY 4.0.\nImagery: Copernicus Sentinel-1 and Sentinel-2, ESA.   "
            "Boundaries: USDOS LSIB, public domain."
        ),
        "pourcent": "{v:.0f}%",
    },
}

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
    from extract_series_gee import PROJET

    ee.Initialize(project=PROJET)
    frontieres = (
        ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
        .filter(ee.Filter.inList("country_na", PAYS))
        .map(lambda f: ee.Feature(f.geometry().simplify(5000), {"nom": f.get("country_na")}))
    )
    CONTOURS.write_text(json.dumps(frontieres.getInfo()), encoding="utf-8")
    print(f"contours récupérés et mis en cache dans {CONTOURS}")
    return gpd.read_file(CONTOURS)


def dessiner_bloc(axes, points, bloc, etiquette, titre, sous_titre, portee, accent):
    """Un panneau : les points d'un bloc de test, colorés par case de la matrice.

    `portee` impose la même largeur en degrés aux deux panneaux : sans cela ils
    seraient à des échelles différentes et la comparaison serait faussée.
    """
    extrait = points[points["bloc"] == bloc]
    minx, miny, maxx, maxy = extrait.total_bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    axes.set_xlim(cx - portee / 2, cx + portee / 2)
    axes.set_ylim(cy - portee / 2, cy + portee / 2)
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

    # L'interlettrage se fait à la main : matplotlib ne l'expose pas.
    axes.text(0, 1.155, " ".join(etiquette), transform=axes.transAxes, fontsize=9.5,
              fontweight="bold", color=accent, va="bottom", ha="left")
    axes.text(0, 1.075, titre, transform=axes.transAxes, fontsize=15,
              fontweight="bold", color=ENCRE, va="bottom", ha="left")
    axes.text(0, 1.018, sous_titre, transform=axes.transAxes, fontsize=10.5,
              color=ENCRE_DOUCE, va="bottom", ha="left")

    # Barre d'échelle : un degré de longitude vaut environ 111 km près de l'équateur.
    km = 25
    long_barre = km / 111.0
    x0 = axes.get_xlim()[0] + portee * 0.06
    y0 = axes.get_ylim()[0] + portee * 0.06
    axes.plot([x0, x0 + long_barre], [y0, y0], color=ENCRE, linewidth=2.4,
              solid_capstyle="butt", zorder=6)
    axes.text(x0 + long_barre / 2, y0 + portee * 0.018, f"{km} km", fontsize=8.5,
              color=ENCRE, ha="center", va="bottom", zorder=6)


def dessiner_proportions(axes, points, bloc, gabarit):
    """Barre empilée : la composition du bloc, dans l'ordre de la légende.

    Elle relie la carte à la matrice de confusion et permet de comparer les deux
    blocs d'un coup d'œil, ce que la dispersion des points ne montre pas bien.
    """
    extrait = points[points["bloc"] == bloc]
    total = len(extrait)
    depart = 0.0
    for categorie in ORDRE:
        part = (extrait["categorie"] == categorie).sum() / total
        if part == 0:
            continue
        # Un fin liseré de fond sépare les segments, comme sur les autres visuels.
        axes.barh(0, part, left=depart, height=1, color=COULEURS[categorie],
                  edgecolor=FOND, linewidth=1.6)
        if part > 0.09:
            axes.text(depart + part / 2, 0, gabarit.format(v=part * 100), ha="center",
                      va="center", fontsize=8.5, color="white", fontweight="bold")
        depart += part

    axes.set_xlim(0, 1)
    axes.set_ylim(-0.5, 0.5)
    axes.axis("off")


def dessiner_reperage(axes, pays, tuiles, blocs_test, mis_en_avant, mots):
    """Carte de repérage : les 34 blocs, apprentissage et test distingués."""
    pays.plot(ax=axes, color="#DFE6E1", zorder=1)
    pays.boundary.plot(ax=axes, color="#93A49B", linewidth=0.8, zorder=2)

    tuiles[~tuiles["ID"].isin(blocs_test)].plot(
        ax=axes, color=ENCRE_PALE, alpha=0.45, zorder=3)
    tuiles[tuiles["ID"].isin(blocs_test)].plot(
        ax=axes, color=COULEURS["Palmier manqué"], alpha=0.9, zorder=4)

    for bloc in mis_en_avant:
        centre = tuiles[tuiles["ID"] == bloc].geometry.iloc[0].centroid
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
    axes.text(0, 1.06, mots["reperage"], transform=axes.transAxes,
              fontsize=10, fontweight="bold", color=ENCRE, va="bottom", ha="left")
    axes.text(0, -0.14, mots["reperage_legende"], transform=axes.transAxes,
              fontsize=8.5, color=ENCRE_PALE, va="top", ha="left")


def main():
    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--langue", choices=sorted(TEXTES), default="fr")
    mots = TEXTES[analyseur.parse_args().langue]
    sortie = Path("portfolio") / mots["sortie"]

    points = gpd.read_file(PREDICTIONS)
    pays = contours_pays()
    tuiles = gpd.read_file(GRILLE)
    tuiles["ID"] = tuiles["ID"].astype(int)
    tuiles = tuiles[tuiles["ID"].isin(
        gpd.read_file(DOSSIER / "echantillons_rdc.geojson")["bloc"].unique().tolist()
    )]

    blocs_test = sorted(points["bloc"].unique().tolist())
    meilleur, pire = 34542, 36100

    # 300 points par pouce : 3 000 pixels de large, net sur un ecran haute densite
    # ou l'image est affichee autour de 1 100 pixels logiques.
    figure = plt.figure(figsize=(10.0, 9.0), dpi=300)
    figure.patch.set_facecolor(FOND)

    figure.text(0.05, 0.978, mots["titre"], fontsize=25, fontweight="bold",
                color=ENCRE, va="top")
    figure.text(0.05, 0.930, mots["chapeau"], fontsize=11.5, color=ENCRE_DOUCE,
                va="top", linespacing=1.5)

    # Rectangles carrés : l'aspect égal les remplit exactement, donc les barres de
    # proportions dessous s'alignent sur les cartes au pixel près.
    cote = 0.375
    hauteur = cote * 10.0 / 9.0
    gauche = figure.add_axes([0.05, 0.365, cote, hauteur])
    droite = figure.add_axes([0.465, 0.365, cote, hauteur])

    n_g = points[points["bloc"] == meilleur]
    n_d = points[points["bloc"] == pire]

    # Même largeur en degrés des deux côtés, sinon les échelles diffèrent.
    portee = max(
        max(g.total_bounds[2] - g.total_bounds[0], g.total_bounds[3] - g.total_bounds[1])
        for g in (n_g, n_d)
    ) + 0.12

    for axes, bloc, groupe, etiquette, region, accent in (
        (gauche, meilleur, n_g, mots["meilleur"], mots["region_meilleur"],
         COULEURS["Palmier détecté"]),
        (droite, pire, n_d, mots["pire"], mots["region_pire"],
         COULEURS["Palmier manqué"]),
    ):
        dessiner_bloc(
            axes, points, bloc, etiquette, region,
            mots["manquees"].format(
                n=(groupe["categorie"] == "Palmier manqué").sum(),
                total=(groupe["classe_reelle"] == "palmier").sum(),
            ),
            portee, accent,
        )

    for rect, bloc in ((0.05, meilleur), (0.465, pire)):
        barre = figure.add_axes([rect, 0.318, cote, 0.022])
        dessiner_proportions(barre, points, bloc, mots["pourcent"])

    reperage = figure.add_axes([0.05, 0.092, 0.28, 0.122])
    dessiner_reperage(reperage, pays, tuiles, blocs_test, [meilleur, pire], mots)

    poignees = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=9.5,
               markerfacecolor=COULEURS[c], markeredgecolor="white",
               markeredgewidth=0.9, label=mots["categories"][c])
        for c in ORDRE
    ]
    figure.legend(
        handles=poignees, loc="upper left", bbox_to_anchor=(0.05, 0.288),
        ncol=4, frameon=False, fontsize=11.5, handletextpad=0.5,
        columnspacing=1.6, labelcolor=ENCRE,
    )

    figure.text(0.42, 0.208, mots["lecture"], fontsize=10.5, color=ENCRE_DOUCE,
                va="top", linespacing=1.6)
    figure.text(0.42, 0.122, mots["portee"], fontsize=10.5,
                color=COULEURS["Palmier manqué"], va="top", fontweight="bold",
                linespacing=1.6)
    figure.text(0.05, 0.052, mots["attributions"], fontsize=8.5, color=ENCRE_PALE,
                va="top", linespacing=1.6)

    sortie.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(sortie, facecolor=FOND, dpi=300)
    print(f"{sortie} écrit")


if __name__ == "__main__":
    main()
