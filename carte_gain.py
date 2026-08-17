"""Produit la courbe de gain de mission destinée aux réseaux sociaux.

    python carte_gain.py                 version française
    python carte_gain.py --langue en     version anglaise

Écrit `portfolio/gain-mission.png`, ou `gain-mission-en.png` en anglais.

La question posée est celle d'un chef de mission, pas celle d'un modélisateur : si on
visite les parcelles dans l'ordre du modèle, combien de palmeraies trouve-t-on après
un quart des visites, après la moitié. La courbe répond en une lecture, et les deux
courbes de référence disent ce que vaut la réponse : l'ordre parfait donne la borne
haute, l'ordre au hasard donne ce qu'on obtiendrait sans modèle.

L'image porte aussi ce que la courbe agrégée cache. Le rappel bloc par bloc, à droite,
montre que la médiane à 0,89 recouvre quatre blocs sous 0,70 : le gain n'est pas le
même partout, et c'est cette dispersion que la suite du projet doit réduire.

Les probabilités viennent de `data/predictions_hors_pli.geojson`, produit par
carte_priorite.py : chaque parcelle est prédite par un modèle qui n'a jamais vu son
bloc.
"""

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from carte_priorite import HORS_PLI, nombre, predictions_hors_pli
from carte_resultats import ENCRE, ENCRE_DOUCE, ENCRE_PALE, FOND, TRAIT

MODELE = "#0AA5AE"
FAIBLE = "#B91C1C"
PARFAIT = "#4B5C54"
HASARD = "#93A49B"
VOILE = "#DCEEEF"
PISTE = "#E2E8E4"

# Seuil de décision du modèle, celui qui produit les 0,87 de rappel annoncés.
SEUIL = 0.5
# Un bloc sous ce rappel est compté à part : c'est la queue que le projet doit traiter.
RAPPEL_BAS = 0.70

TEXTES = {
    "fr": {
        "sortie": "gain-mission.png",
        "titre": "La moitié des palmeraies en un tiers des visites",
        "chapeau": (
            "Les parcelles sont classées par la probabilité rendue par le modèle, puis "
            "visitées en partant du haut de la liste.\n{n} parcelles tenues à l'écart de "
            "l'apprentissage, réparties sur 34 blocs du bassin du Congo."
        ),
        "x": "Part des parcelles visitées",
        "y": "Part des palmeraies trouvées",
        "ordre_modele": "ordre du modèle",
        "ordre_parfait": "ordre parfait",
        "ordre_hasard": "ordre au hasard",
        "reperes": "la moitié des palmeraies",
        "tuiles": [
            ("{v} %", "de la liste à parcourir pour trouver\n"
                      "la moitié des palmeraies. L'ordre parfait\n"
                      "en demanderait {parfait} %, le hasard 50 %."),
            ("{v} %", "pour en trouver neuf sur dix. Au hasard,\n"
                      "il faudrait visiter 90 % de la liste."),
        ],
        "titre_blocs": "Le gain varie selon les régions",
        "sous_blocs": (
            "Part des palmeraies signalées, bloc par\nbloc. Chaque point est un des "
            "34 blocs.\nMédiane {mediane} %, mais {bas} blocs sous {seuil} %."
        ),
        "mediane": "médiane {v} %",
        "portee": (
            "Échantillon d'évaluation : six parcelles sur dix sont du palmier, par "
            "construction.\nSur un terrain où le palmier est plus rare, le gain comme "
            "les fausses alertes changent."
        ),
        "attributions": (
            "Étiquettes : Descals et al. 2024, Global Oil Palm extent maps, Zenodo, "
            "CC BY 4.0.\nImagerie : Copernicus Sentinel-1 et Sentinel-2, ESA."
        ),
        "milliers": " ",
    },
    "en": {
        "sortie": "gain-mission-en.png",
        "titre": "Half the palm plots in a third of the visits",
        "chapeau": (
            "Plots are ranked by the probability the model returns, then visited from "
            "the top of the list.\n{n} plots held out of training, spread across 34 "
            "blocks of the Congo Basin."
        ),
        "x": "Share of plots visited",
        "y": "Share of palm plots found",
        "ordre_modele": "model's order",
        "ordre_parfait": "perfect order",
        "ordre_hasard": "random order",
        "reperes": "half the palm plots",
        "tuiles": [
            ("{v}%", "of the list to walk through to find\n"
                     "half the palm plots. A perfect order\n"
                     "would need {parfait}%, random order 50%."),
            ("{v}%", "to find nine in ten. At random, you\n"
                     "would have to visit 90% of the list."),
        ],
        "titre_blocs": "Not the same gain everywhere",
        "sous_blocs": (
            "Share of palm plots flagged, block by\nblock. Each dot is one of the "
            "34 blocks.\nMedian {mediane}%, but {bas} blocks below {seuil}%."
        ),
        "mediane": "median {v}%",
        "portee": (
            "Evaluation sample: six plots in ten are oil palm, by construction.\n"
            "On ground where palm is rarer, both the gain and the false alarms change."
        ),
        "attributions": (
            "Labels: Descals et al. 2024, Global Oil Palm extent maps, Zenodo, "
            "CC BY 4.0.\nImagery: Copernicus Sentinel-1 and Sentinel-2, ESA."
        ),
        "milliers": ",",
    },
}


def courbe(points):
    """Part cumulée de palmeraies trouvées, en visitant dans l'ordre du modèle."""
    tri = points.sort_values("probabilite", ascending=False)
    trouvees = np.cumsum(tri["palmier"].values) / tri["palmier"].sum()
    visitees = np.arange(1, len(tri) + 1) / len(tri)
    return visitees, trouvees


def dessiner_courbe(axes, visitees, trouvees, prevalence, mots):
    """Les trois ordres de visite : le parfait, celui du modèle, le hasard."""
    axes.set_facecolor(FOND)

    # Ordre parfait : toutes les palmeraies d'abord, donc une pente de 1 / prévalence
    # jusqu'à épuisement. C'est la borne que rien ne peut dépasser.
    x_parfait = np.array([0, prevalence, 1])
    y_parfait = np.array([0, 1, 1])
    axes.plot(x_parfait, y_parfait, color=PARFAIT, linewidth=1.4,
              linestyle=(0, (5, 3)), zorder=3)
    axes.plot([0, 1], [0, 1], color=HASARD, linewidth=1.4, linestyle=(0, (2, 3)),
              zorder=2)

    axes.fill_between(visitees, visitees, trouvees, color=VOILE, zorder=1)
    axes.plot(visitees, trouvees, color=MODELE, linewidth=3.0, zorder=4,
              solid_capstyle="round")

    # Repère de lecture : la moitié des palmeraies, et ce qu'elle coûte en visites.
    cout = float(np.interp(0.5, trouvees, visitees))
    axes.plot([0, 0.5], [0.5, 0.5], color=ENCRE_PALE, linewidth=1.0,
              linestyle=(0, (1, 2)), zorder=3)
    for x, couleur in ((cout, MODELE), (0.5, HASARD)):
        axes.plot([x, x], [0, 0.5], color=couleur, linewidth=1.0,
                  linestyle=(0, (1, 2)), zorder=3)
        axes.scatter([x], [0.5], s=70, color=couleur, edgecolors=FOND, linewidths=1.6,
                     zorder=5)
    axes.text(0.012, 0.515, mots["reperes"], fontsize=9.5, color=ENCRE_PALE,
              va="bottom", ha="left")

    # Étiquettes directes : trois courbes, aucune légende à décoder.
    axes.text(0.60, 0.615, mots["ordre_modele"], fontsize=12, fontweight="bold",
              color=MODELE, va="center", ha="left")
    axes.text(prevalence * 0.52, 0.90, mots["ordre_parfait"], fontsize=10,
              color=PARFAIT, va="bottom", ha="center", rotation=52,
              rotation_mode="anchor")
    axes.text(0.905, 0.855, mots["ordre_hasard"], fontsize=10, color=HASARD,
              va="top", ha="right", rotation=39, rotation_mode="anchor")

    axes.set_xlim(0, 1.005)
    axes.set_ylim(0, 1.03)
    axes.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    axes.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axes.set_xticklabels(["0", "25 %", "50 %", "75 %", "100 %"]
                         if mots["milliers"] != "," else
                         ["0", "25%", "50%", "75%", "100%"])
    axes.set_yticklabels(["0", "25 %", "50 %", "75 %", "100 %"]
                         if mots["milliers"] != "," else
                         ["0", "25%", "50%", "75%", "100%"])
    axes.tick_params(colors=ENCRE_PALE, labelsize=9.5, length=0, pad=6)
    for cote, visible in (("left", True), ("bottom", True),
                          ("right", False), ("top", False)):
        axes.spines[cote].set_visible(visible)
        axes.spines[cote].set_color(TRAIT)
    axes.set_xlabel(mots["x"], fontsize=10.5, color=ENCRE_DOUCE, labelpad=10)
    axes.set_ylabel(mots["y"], fontsize=10.5, color=ENCRE_DOUCE, labelpad=10)


def dessiner_blocs(axes, rappels, mots):
    """Rappel bloc par bloc : la dispersion que la courbe agrégée ne montre pas."""
    axes.set_facecolor(FOND)
    axes.barh(0, 1.0, height=0.30, left=0, color=PISTE, zorder=1)

    mediane = float(np.median(rappels))
    # Décalage vertical alterné : sans lui les blocs proches se recouvrent.
    for rang, valeur in enumerate(np.sort(rappels)):
        faible = valeur < RAPPEL_BAS
        axes.scatter([valeur], [(rang % 2) * 0.16 - 0.08], s=64,
                     color=FAIBLE if faible else MODELE, edgecolors=FOND,
                     linewidths=1.4, zorder=4 if faible else 3, alpha=0.95)

    axes.plot([mediane, mediane], [-0.30, 0.30], color=ENCRE, linewidth=1.6, zorder=5)
    axes.text(mediane, 0.40, mots["mediane"].format(v=round(mediane * 100)),
              fontsize=9.5, color=ENCRE, va="bottom", ha="center", fontweight="bold")

    axes.set_xlim(0.42, 1.03)
    axes.set_ylim(-0.62, 0.62)
    axes.set_yticks([])
    axes.set_xticks([0.5, 0.75, 1.0])
    axes.set_xticklabels(["50 %", "75 %", "100 %"] if mots["milliers"] != "," else
                         ["50%", "75%", "100%"])
    axes.tick_params(colors=ENCRE_PALE, labelsize=9, length=0, pad=5)
    for cote in ("left", "right", "top"):
        axes.spines[cote].set_visible(False)
    axes.spines["bottom"].set_color(TRAIT)


def main():
    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--langue", choices=sorted(TEXTES), default="fr")
    mots = TEXTES[analyseur.parse_args().langue]
    sortie = Path("portfolio") / mots["sortie"]

    points = gpd.read_file(HORS_PLI) if HORS_PLI.exists() else predictions_hors_pli()
    visitees, trouvees = courbe(points)
    prevalence = points["palmier"].mean()

    cout_moitie = float(np.interp(0.5, trouvees, visitees))
    cout_neuf = float(np.interp(0.9, trouvees, visitees))
    rappels = np.array([
        (groupe.loc[groupe["palmier"] == 1, "probabilite"] >= SEUIL).mean()
        for _, groupe in points.groupby("bloc")
    ])

    figure = plt.figure(figsize=(10.0, 8.0), dpi=300)
    figure.patch.set_facecolor(FOND)

    figure.text(0.062, 0.968, mots["titre"], fontsize=25, fontweight="bold",
                color=ENCRE, va="top")
    figure.text(0.062, 0.905, mots["chapeau"].format(n=nombre(len(points), mots)),
                fontsize=11.5, color=ENCRE_DOUCE, va="top", linespacing=1.5)

    axes_courbe = figure.add_axes([0.088, 0.245, 0.435, 0.535])
    dessiner_courbe(axes_courbe, visitees, trouvees, prevalence, mots)

    # Colonne de droite : les deux chiffres que la courbe met une lecture à extraire,
    # puis la dispersion entre blocs.
    gauche = 0.585
    for haut, (gabarit, legende), valeur in zip(
        (0.790, 0.605), mots["tuiles"], (cout_moitie, cout_neuf)
    ):
        figure.text(gauche, haut, gabarit.format(v=round(valeur * 100)), fontsize=34,
                    fontweight="bold", color=MODELE, va="top")
        figure.text(gauche, haut - 0.062,
                    legende.format(parfait=round(prevalence * 50)),
                    fontsize=10.5, color=ENCRE_DOUCE, va="top", linespacing=1.55)

    figure.text(gauche, 0.450, mots["titre_blocs"], fontsize=13.5, fontweight="bold",
                color=ENCRE, va="top")
    figure.text(gauche, 0.408, mots["sous_blocs"].format(
        mediane=round(float(np.median(rappels)) * 100),
        bas=int((rappels < RAPPEL_BAS).sum()),
        seuil=round(RAPPEL_BAS * 100)),
        fontsize=10.5, color=ENCRE_DOUCE, va="top", linespacing=1.55)

    axes_blocs = figure.add_axes([gauche, 0.238, 0.345, 0.075])
    dessiner_blocs(axes_blocs, rappels, mots)

    figure.text(0.062, 0.155, mots["portee"], fontsize=10.5, color=FAIBLE,
                va="top", fontweight="bold", linespacing=1.6)
    figure.text(0.062, 0.062, mots["attributions"], fontsize=8.5, color=ENCRE_PALE,
                va="top", linespacing=1.6)

    sortie.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(sortie, facecolor=FOND, dpi=300)
    print(f"{sortie} écrit")


if __name__ == "__main__":
    main()
