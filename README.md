# Classi-fy

Détection du palmier à huile dans le bassin du Congo à partir de séries temporelles Sentinel-1 et Sentinel-2. Entraîné sur 34 blocs, dont 24 en République démocratique du Congo.

[English version](README.en.md)

---

## Résultat

Classification binaire, palmier contre pas de palmier, évaluée en validation croisée **spatiale** sur 34 blocs géographiques disjoints.

| Indicateur | Valeur |
|---|---|
| F1 macro (validation spatiale, 5 plis) | **0,817 ± 0,022** |
| F1 macro (validation aléatoire) | 0,835 ± 0,011 |
| Optimisme de la validation aléatoire | +0,018 |
| Plancher (modèle toujours majoritaire) | 0,378 |
| Justesse globale | 0,83 |

Le chiffre à retenir est **0,817**. Il est mesuré sur des régions que le modèle n'a jamais vues pendant son apprentissage.

L'optimisme de +0,018 signifie que le modèle ne perd que 1,8 point en changeant complètement de région. Il s'appuie sur un signal transportable et non sur des particularités locales.

### Détail par classe

| Classe | Précision | Rappel | F1 | Effectif |
|---|---|---|---|---|
| palmier | 0,86 | 0,87 | 0,87 | 1 090 |
| pas_de_palmier | 0,80 | 0,78 | 0,79 | 700 |

### Matrice de confusion

Lignes : la réalité. Colonnes : la prédiction du modèle.

| | prédit palmier | prédit pas de palmier |
|---|---|---|
| **était palmier** | 951 | 139 |
| **était sans palmier** | 157 | 543 |

Lecture : sur 1 090 palmeraies réelles, le modèle en retrouve 951 et en rate 139. Sur 700 zones sans palmier, il en signale 157 à tort.

---

## Données d'entraînement

### Étiquettes

**Descals et al. 2024, Global Oil Palm extent maps.**
Zenodo : [10.5281/zenodo.13379129](https://zenodo.org/records/13379129), sous licence CC BY 4.0.

Cartes matricielles à 10 m de résolution couvrant la période 2016 à 2021, accompagnées de 18 812 points de validation terrain. Trois valeurs de pixel :

| Valeur | Classe |
|---|---|
| 0 | pas de palmier |
| 1 | palmier industriel |
| 2 | palmier villageois |

Fichiers utilisés :

- `Grid_OilPalm2016-2021.zip` : la grille des tuiles de 100 km, qui sert de découpage spatial
- `GlobalOilPalm_OP-extent_<id>.tif` : les rasters d'extension, un par tuile

Pourquoi cette source. C'est la seule couche ouverte, étiquetée, à 10 m et validée sur le terrain qui couvre le bassin du Congo. Les alternatives envisagées ne convenaient pas : la carte cacao de Kalischek et al. (*Nature Food*, 2023) et le jeu COLD-CI couvrent la Côte d'Ivoire et le Ghana, pas la RDC ; le [WorldCereal Reference Data Module](https://rdm.esa-worldcereal.org/) est orienté céréales et compte peu de points en Afrique centrale.

### Échantillonnage

- Sélection : boîte englobante 12,2° à 31,3° est, -13,5° à 5,4° nord, croisée avec la grille de tuiles
- 34 tuiles de 100 km contiennent du palmier, couvrant 12,1° à 30,1° est et -4,9° à 4,0° nord
- Un point tous les 200 m au maximum, soit un pixel sur 20 dans chaque direction : deux pixels voisins d'une même plantation sont quasi identiques et gonfleraient le jeu sans ajouter d'information
- Tirage équilibré entre les trois classes, dans la fenêtre la plus dense en palmier de chaque tuile
- Graine aléatoire fixée à 42

Résultat : **8 658 points répartis sur 34 blocs**.

| Classe | Effectif |
|---|---|
| pas_de_palmier | 3 400 |
| palmier_industriel | 2 728 |
| palmier_villageois | 2 530 |

### Répartition géographique réelle

La sélection se fait par **boîte rectangulaire, pas par frontière nationale**. L'emprise choisie déborde donc sur les pays voisins, et le jeu d'entraînement n'est pas exclusivement congolais. Vérification faite tuile par tuile contre les frontières `USDOS/LSIB_SIMPLE/2017` :

| Pays | Blocs | Points | Part |
|---|---|---|---|
| **République démocratique du Congo** | 24 | 6 214 | **71,8 %** |
| République du Congo | 4 | 936 | 10,8 % |
| République centrafricaine | 2 | 508 | 5,9 % |
| Cameroun | 1 | 300 | 3,5 % |
| Tanzanie | 1 | 300 | 3,5 % |
| Burundi | 1 | 200 | 2,3 % |
| Angola | 1 | 200 | 2,3 % |

En RDC, les blocs se répartissent d'ouest en est : la façade atlantique du Kongo Central, la cuvette centrale entre 18° et 22° est, le nord de la Tshopo et du Bas-Uélé, puis les blocs orientaux entre 28° et 29° est, du côté du Sud-Kivu et du Tanganyika.

Ce débordement n'affaiblit pas le modèle, il élargit son domaine : la validation croisée spatiale porte sur l'ensemble du bassin du Congo et non sur un seul pays. Mais il interdit de présenter le résultat comme un modèle strictement congolais, et il est énoncé ici pour cette raison.

### Imagerie

Année de référence : **2021**, dernière année couverte par la carte Descals.

| Capteur | Collection Earth Engine | Bandes | Rôle |
|---|---|---|---|
| Sentinel-2 L2A | `COPERNICUS/S2_SR_HARMONIZED` | B2, B3, B4, B8, B11, B12 | couleur et vigueur de la végétation |
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | VV, VH | structure de la canopée |

Traitement :

- Masquage des nuages, ombres, cirrus et neige par la bande de classification SCL (valeurs 3, 8, 9, 10, 11)
- Scènes retenues sous 80 % de couverture nuageuse
- Sentinel-1 filtré en mode IW, double polarisation VV et VH
- Une médiane mensuelle par bande, soit 12 composites
- Repli sur la médiane annuelle là où un mois est entièrement masqué, sinon la saison des pluies vide des mois entiers et l'échantillonnage supprime les points concernés

Chaque point porte donc **96 mesures**, soit 12 mois × 8 bandes.

---

## Méthodologie

### La chaîne, en quatre étapes indépendantes

```
echantillonner_palmier.py    rasters Zenodo        -> data/echantillons_rdc.geojson
extraire_series_gee.py       Sentinel-1 et -2      -> CSV dans Google Drive
preparer_parcelles.py        CSV                   -> data/parcelles.parquet
modele_binaire.py            parquet               -> data/modele_palmier.joblib
```

Chaque étape est lançable seule et reprend là où la précédente s'est arrêtée.

### Variables explicatives

Les 96 réflectances brutes ne sont pas données au modèle. Elles sont résumées en **34 variables annuelles**, beaucoup plus stables d'une image à l'autre.

**Indices normalisés**, calculés mois par mois puis résumés par leur moyenne, écart type, minimum, maximum et amplitude :

| Indice | Formule | Ce qu'il capte |
|---|---|---|
| NDVI | (B8 − B4) / (B8 + B4) | vigueur de la végétation |
| NDWI | (B3 − B8) / (B3 + B8) | teneur en eau du couvert |
| NBR | (B8 − B12) / (B8 + B12) | structure de la canopée |

**Statistiques par bande** : moyenne et écart type annuels des 8 bandes.

**Signature radar** : moyenne et écart type de l'écart VV − VH sur l'année.

**Mois du pic de NDVI**.

### Protocole de validation

La validation croisée classique surestime fortement la performance en télédétection. Deux parcelles voisines partagent le même sol, la même météo et souvent la même image : avec un tirage aléatoire, des parcelles quasi identiques se retrouvent des deux côtés du découpage et le modèle est évalué sur ce qu'il a déjà vu.

Le protocole retenu est donc un **découpage spatial par blocs** : `StratifiedGroupKFold` à 5 plis, où le groupe est la tuile de 100 km. Chaque tuile est entièrement d'un seul côté du découpage, et chaque tuile est examinée exactement une fois au fil des 5 plis.

Les deux découpages sont calculés à chaque exécution. Leur écart, appelé ici **optimisme**, quantifie la fuite spatiale et sert de contrôle de fiabilité : au-delà de 0,10, le score annoncé n'est pas défendable.

### Modèles comparés

`RandomForestClassifier` et `HistGradientBoostingClassifier`, tous deux évalués en validation spatiale. Le gradient boosting est retenu. Les deux donnent 0,815, l'écart n'est pas significatif : la performance vient des variables, pas de l'algorithme.

---

## Le rôle décisif du radar

Le classement des variables par importance de permutation est sans ambiguïté.

| Variable | Perte de F1 quand elle est mélangée |
|---|---|
| **vv_vh_moy** | **0,172** |
| B8_moy | 0,027 |
| VH_moy | 0,012 |
| B11_moy | 0,011 |
| B2_moy | 0,011 |
| VV_moy | 0,009 |

L'écart entre les deux polarisations radar porte **6,3 fois** plus de signal que la meilleure variable optique.

L'explication est physique. Le palmier et la forêt tropicale sont deux couverts fermés, verts toute l'année, dont l'amplitude saisonnière du NDVI est presque identique, 0,04 contre 0,03. L'optique ne peut pas les séparer. Le radar ne mesure pas la couleur mais la structure : une palmeraie a des arbres alignés, de hauteur homogène, et renvoie un écho régulier là où une forêt naturelle renvoie un écho désordonné.

### Effet mesuré

| Configuration | F1 spatial | Optimisme |
|---|---|---|
| Optique seule, 3 classes | 0,405 | +0,225 |
| Optique et radar, 3 classes | 0,561 | +0,066 |
| Optique et radar, binaire | **0,817** | **+0,018** |

L'effondrement de l'optimisme, de 0,225 à 0,018, est aussi important que la hausse du score. Il indique que le modèle a cessé de s'accrocher à des indices locaux.

---

## Zone de validité

Les 34 blocs d'entraînement couvrent **12,1° à 30,1° est et -4,9° à 4,0° nord**, soit toute la largeur du bassin du Congo, de la façade atlantique jusqu'aux Grands Lacs. La validation croisée spatiale mesure directement le transfert d'une région à l'autre à l'intérieur de cette emprise, et l'optimisme de +0,018 dit qu'il se fait sans perte notable.

Le domaine de validité est donc le **bassin du Congo en forêt tropicale humide**, et non un pays. Il couvre 24 blocs en RDC et 10 chez six voisins, ce qui est une force pour la généralisation : le modèle a été testé sur des contextes nationaux différents et n'a pas décroché.

En revanche, une caractéristique de l'échantillonnage restreint sa portée et doit être comprise avant tout usage. Les tuiles retenues sont celles où Descals détecte du palmier, et à l'intérieur de chaque tuile l'échantillonnage vise la fenêtre la plus dense. **La classe « pas de palmier » représente donc ce qui entoure les palmeraies**, essentiellement de la forêt et des cultures voisines. Elle ne représente pas l'ensemble d'un territoire national.

Ce que le modèle n'a jamais vu :

- savane sèche du Katanga et du Kasaï méridional
- zones urbaines et périurbaines
- reliefs et forêts d'altitude du Kivu
- grands plans d'eau et zones marécageuses étendues
- toute la moitié sud de la RDC, aucun bloc ne descend sous -4,9° de latitude

Sur ces milieux, son comportement est inconnu, non pas mauvais mais non mesuré. C'est le mécanisme qui explique la première limite ci-dessous.

---

## Usages possibles

### Ce que le modèle sait faire aujourd'hui

**Vérifier un site précis.** Sur une parcelle ou des coordonnées données, il répond si du palmier est présent, avec une précision de 0,86. Sur 100 alertes, 86 sont justes.

**Prioriser des missions de terrain.** Le modèle produit une probabilité, pas seulement une réponse. Classer les sites suspects par probabilité décroissante et vérifier les premiers permet de concentrer un budget de patrouille limité là où le rendement est le meilleur.

**Contrôler une déclaration.** Une concession ou un exploitant affirme qu'aucune plantation n'occupe une parcelle : le modèle fournit un avis indépendant, appuyé sur de l'imagerie publique et daté.

**Pré-filtrer avant photo-interprétation.** Sur un lot de sites à examiner à l'œil, écarter d'abord ceux que le modèle juge sans palmier avec une forte confiance réduit la charge humaine, à condition d'accepter les 13 % de palmeraies manquées.

**Documenter un rapport.** Les chiffres sont mesurés en validation spatiale et la méthode est reproductible, donc défendables devant un bailleur ou un partenaire scientifique.

### Applications concrètes pour la conservation

- surveillance des limites de parcs et de leurs zones tampons
- détection d'expansion de plantations dans des concessions suivies
- appui chiffré aux rapports de déforestation liés au palmier
- ciblage des patrouilles et des missions de vérification

### Ce que le modèle ne sait pas faire

**Produire une carte nationale.** Voir la limite 1 ci-dessous, c'est le point le plus important de ce document.

**Distinguer industriel et villageois.** Voir la limite 2.

**Dater une plantation ou détecter un changement.** Le modèle est entraîné sur une seule année. Comparer deux années demanderait de le réentraîner et de valider cette comparaison, ce qui n'a pas été fait.

**Estimer une surface.** Il classe des points, pas des polygones. Convertir en hectares exigerait une segmentation et une validation de surface distinctes.

---

## Pistes d'amélioration

Classées par gain attendu, du plus rentable au plus coûteux.

**1. Élargir et rééquilibrer la classe négative.**
C'est le chantier prioritaire, celui qui débloquerait la cartographie. Il faut échantillonner des tuiles sans aucun palmier, savane, ville, montagne, marécage, et respecter la rareté réelle du palmier plutôt que 60,7 %. Effet attendu : effondrement du taux de fausse alerte sur les milieux que le modèle n'a jamais vus.

**2. Ajuster le seuil de décision.**
Le modèle sort une probabilité, actuellement tranchée à 0,5. Remonter ce seuil échange du rappel contre de la précision. Pour une carte nationale, un seuil à 0,8 ou 0,9 réduirait fortement les faux positifs au prix de quelques palmeraies manquées. Le bon réglage dépend du coût relatif des deux erreurs dans ton usage, il se choisit et ne se devine pas.

**3. Ajouter le relief.**
Le modèle numérique de terrain Copernicus ou SRTM fournit altitude et pente. Le palmier à huile ne pousse ni en altitude ni sur forte pente. Deux variables gratuites, immédiates à extraire dans Earth Engine, qui élimineraient mécaniquement une partie des faux positifs en zone de relief.

**4. Introduire des variables de texture.**
Écart type local, matrices de cooccurrence sur le radar, statistiques de voisinage. C'est la seule voie pour séparer palmier industriel et palmier villageois, puisque leur différence est géométrique. Bénéfice attendu aussi sur la distinction palmeraie contre forêt.

**5. Étendre à plusieurs années.**
Rejouer l'extraction sur 2019 à 2023 multiplierait le volume d'apprentissage, mesurerait la stabilité du modèle dans le temps et ouvrirait la détection de changement, donc le suivi d'expansion.

**6. Collecter des étiquettes de terrain.**
Les étiquettes actuelles proviennent d'un modèle, celui de Descals, dont les erreurs sont héritées sans contrôle. Des relevés faits avec les fermiers et les équipes de terrain fourniraient une vérité indépendante, et permettraient enfin de mesurer la performance réelle plutôt que la concordance avec un autre modèle.

**7. Densifier la série radar.**
Le modèle utilise des médianes mensuelles. Sentinel-1 repasse tous les six à douze jours : une résolution temporelle plus fine, ou des statistiques de variabilité entre passages, pourrait porter davantage d'information de structure.

---

## Limites connues

Elles sont énoncées ici parce qu'elles conditionnent l'usage du modèle.

**1. Le jeu ne reflète pas la rareté réelle du palmier.**
L'échantillonnage a délibérément visé la fenêtre la plus dense en palmier de chaque tuile, d'où 60,7 % de palmier dans le jeu. Sur la RDC entière, le palmier occupe une fraction de pourcent du territoire. Le taux de fausse alerte de 22 % sur les zones sans palmier est acceptable ici, mais appliqué à un pays entier il produirait un volume de faux positifs supérieur aux vraies détections. **Le modèle n'est pas validé pour produire une carte nationale.** Il répond à la question « cette parcelle contient-elle du palmier », pas à la question « où est le palmier en RDC ».

**2. Palmier industriel et palmier villageois ne sont pas séparables.**
En trois classes, le modèle plafonne à 0,561 et confond les deux types dans un tiers des cas. Ce qui les distingue est la géométrie des plantations, taille des blocs et régularité des alignements, information absente d'une analyse par pixel. Il faudrait des variables de texture et de voisinage.

**3. Les étiquettes sont elles-mêmes une prédiction.**
La couche Descals est le produit d'un modèle, avec ses propres erreurs. Elles sont héritées ici sans correction.

**4. Une seule année.**
Tout est calé sur 2021. Le comportement du modèle sur d'autres années n'a pas été mesuré.

**5. La variante sans compte est nettement inférieure.**
`extraire_series_local.py` évite toute inscription en lisant Sentinel-2 sur le bucket AWS ouvert, mais le bucket Sentinel-1 est payant. Sans radar, le résultat plafonne à 0,405. Une tuile, la 33506, s'est même révélée inexploitable en optique seule, couverte de nuages les douze mois de l'année. Le radar, qui traverse les nuages, a résolu ce cas.

---

## Technologies

| Domaine | Outil | Version |
|---|---|---|
| Langage | Python | 3.14.5 |
| Imagerie satellite | Google Earth Engine (`earthengine-api`) | 1.7.38 |
| Apprentissage | scikit-learn | 1.7.2 |
| Données tabulaires | pandas | 2.3.3 |
| Calcul numérique | numpy | 2.3.5 |
| Données géospatiales | geopandas | 1.1.4 |
| Rasters | rasterio | 1.5.0 |
| Géométries | shapely | 2.1.2 |
| Format colonne | pyarrow | 22.0.0 |
| Graphiques | matplotlib | 3.10.8 |
| Sérialisation | joblib | 1.5.2 |
| Exploration | Jupyter Notebook | |

Sources d'imagerie : Copernicus Sentinel-1 et Sentinel-2, via Google Earth Engine. Une variante locale interroge l'API STAC d'Element 84 sur le bucket AWS Open Data `sentinel-cogs`.

---

## Reproduire le résultat

### Prérequis

```bash
pip install earthengine-api scikit-learn pandas numpy geopandas rasterio pyarrow matplotlib joblib
earthengine authenticate
```

Un compte Google Earth Engine est nécessaire, gratuit pour un usage non commercial. Renseigner ensuite l'identifiant du projet Cloud dans `extraire_series_gee.py`.

### Étape 1, les points étiquetés

Télécharger depuis [Zenodo 10.5281/zenodo.13379129](https://zenodo.org/records/13379129) et décompresser dans `data/` :

- `Grid_OilPalm2016-2021.zip` vers `data/palmier_grille/`
- les rasters d'extension vers `data/palmier_extent/`

```bash
python echantillonner_palmier.py
```

Produit `data/echantillons_rdc.geojson`, 8 658 points sur 34 blocs.

### Étape 2, les séries temporelles

```bash
python extraire_series_gee.py
```

L'export tourne côté Google et rend la main immédiatement. Compter une dizaine de minutes. Le CSV arrive dans Google Drive, dossier `Classify`. Le suivre sur [code.earthengine.google.com/tasks](https://code.earthengine.google.com/tasks).

### Étape 3, la mise en forme

Télécharger le CSV dans `data/`, puis :

```bash
python preparer_parcelles.py data/series_sentinel_rdc.csv
```

### Étape 4, le modèle

```bash
python modele_binaire.py
```

Affiche l'évaluation complète et écrit `data/modele_palmier.joblib`.

### Variante sans aucun compte

```bash
python extraire_series_local.py
```

Remplace les étapes 2 et 3 en lisant Sentinel-2 sur AWS Open Data. Compter une heure. Ne fournit pas le radar, donc plafonne à 0,405. Utile pour valider la chaîne, pas pour produire un résultat.

---

## Structure du dépôt

| Fichier | Rôle |
|---|---|
| `echantillonner_palmier.py` | étape 1, tirage des points étiquetés dans les rasters Zenodo |
| `extraire_series_gee.py` | étape 2, extraction Sentinel-1 et Sentinel-2 via Earth Engine |
| `extraire_series_local.py` | étape 2, variante sans compte, Sentinel-2 seul depuis AWS |
| `preparer_parcelles.py` | étape 3, conversion du CSV Earth Engine au format parquet |
| `modele_binaire.py` | étape 4, modèle final palmier contre pas de palmier |
| `classification_cultures.ipynb` | notebook d'analyse, comparaison des découpages et évaluation à 3 classes |
| `organiser_fermiers_py.ipynb` | organisation des listes de fermiers, hors chaîne de classification |

Le dossier `data/` est exclu du dépôt. Il contient les rasters, les séries extraites et des données personnelles de fermiers, qui ne doivent jamais être publiées.

---

## Références

- Descals, A. et al. (2024). *Global Oil Palm extent maps*. Zenodo. [10.5281/zenodo.13379129](https://zenodo.org/records/13379129), CC BY 4.0
- Kalischek, N. et al. (2023). Cocoa plantations are associated with deforestation in Côte d'Ivoire and Ghana. *Nature Food*, 4, 384-393. [Article](https://www.nature.com/articles/s43016-023-00751-8), [code](https://github.com/D1noFuzi/cocoamapping)
- ESA WorldCereal Reference Data Module. [rdm.esa-worldcereal.org](https://rdm.esa-worldcereal.org/)
- Copernicus Sentinel-1 et Sentinel-2, European Space Agency
