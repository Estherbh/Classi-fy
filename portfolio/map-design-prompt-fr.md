# Prompt de design pour la carte

À copier tel quel dans Gemini, ChatGPT ou tout autre assistant.

## Pourquoi ce prompt demande du code et non une image

Un modèle de génération d'images ne peut pas produire cette carte : il inventerait les
1 790 points, leurs positions et leurs couleurs. Le résultat serait une jolie image de
données fausses, dans une étude de cas dont tout l'argument est la rigueur de mesure.

Le prompt ci-dessous demande donc du **code Python**, qui dessine les vraies données.
Les chiffres réels y sont inscrits pour que rien ne soit deviné.

---

## Le prompt

Tu es directeur artistique et développeur de visualisation de données. Produis un
script Python avec matplotlib qui génère une image PNG de 2 000 pixels de large,
destinée à un portfolio de data scientist et à une publication LinkedIn.

### Le sujet

Un modèle d'apprentissage automatique détecte les plantations de palmier à huile dans
le bassin du Congo à partir d'imagerie satellite Sentinel-1 et Sentinel-2. L'image
compare son comportement sur deux régions d'évaluation : celle où il réussit le mieux
et celle où il échoue le plus. Le message est l'honnêteté sur la variabilité
géographique, pas la performance.

### Les données, à ne pas inventer

Le script lit un fichier GeoJSON nommé `predictions_test.geojson`. Chaque entité est un
point avec ces propriétés :

- `bloc` : identifiant entier de la région
- `classe_reelle` : `palmier` ou `pas_de_palmier`
- `prediction` : `palmier` ou `pas_de_palmier`
- `probabilite_palmier` : nombre entre 0 et 1
- `categorie` : `Palmier détecté`, `Correctement écarté`, `Fausse alerte`, ou
  `Palmier manqué`

Deux blocs à afficher côte à côte :

| Panneau | Bloc | Étiquette | Région | Chiffre à annoncer |
|---|---|---|---|---|
| gauche | 34542 | LE MEILLEUR CAS | Cuvette centrale | 4 palmeraies manquées sur 200 |
| droite | 36100 | LE PIRE CAS | Sud-Kivu | 70 palmeraies manquées sur 200 |

Composition du bloc 34542 : 65 % palmier détecté, 27 % correctement écarté, 6 % fausse
alerte, 2 % palmier manqué.
Composition du bloc 36100 : 43 %, 28 %, 5 %, 23 % dans le même ordre.

### La palette, à respecter exactement

Elle a été validée pour le daltonisme, écart minimal 10,4 en vision déficiente et 15,3
en vision normale sur toutes les paires. Ne la modifie pas.

| Catégorie | Couleur | Rôle |
|---|---|---|
| Palmier détecté | `#0AA5AE` | famille froide, décision correcte |
| Correctement écarté | `#2C5FBF` | famille froide, décision correcte |
| Fausse alerte | `#C9761B` | famille chaude, erreur |
| Palmier manqué | `#B91C1C` | famille chaude, erreur |

La paire critique est ambre contre rouge. Un rouge plus vif, `#DC2626` par exemple,
tombe à 14,2 en vision normale et devient indistinguable de l'ambre : ne l'éclaircis pas.

Le principe est que les deux bonnes réponses partagent la famille froide et les deux
erreurs la famille chaude, avec un vrai écart à l'intérieur de chaque paire. Un lecteur
doit distinguer instantanément une fausse alerte d'une palmeraie manquée : ces deux
erreurs n'ont pas du tout le même coût opérationnel.

Neutres : encre `#0F1A15`, texte secondaire `#4B5C54`, texte tertiaire `#74857C`, fond
de page `#FCFCFB`, fond des cartes `#ECF0ED`, filets `#C3CDC6`.

### La mise en page

De haut en bas :

1. Titre : « Le même modèle, deux régions », très gras, environ 25 points, encre pleine
2. Sous-titre sur deux lignes, texte secondaire, qui précise que ce sont deux blocs de
   100 km tenus à l'écart de l'apprentissage, le meilleur et le pire des sept blocs
   d'évaluation
3. Deux panneaux carrés côte à côte, chacun précédé de trois lignes : l'étiquette de cas
   en capitales espacées et colorée, le nom de la région en gras, puis le chiffre
4. Sous chaque panneau, une barre empilée fine montrant la composition en pourcentages,
   alignée exactement sur la largeur de la carte
5. Une légende horizontale à quatre entrées, pastilles rondes
6. Une carte de repérage montrant les 34 blocs, gris pour l'apprentissage, rouge pour
   les sept blocs de test, avec un cadre noir autour des deux blocs détaillés
7. Deux blocs de texte à droite de la carte de repérage
8. Les attributions en pied de page

### Les règles de dessin

- Les deux panneaux doivent couvrir **la même étendue en degrés**, sinon les échelles
  diffèrent et la comparaison est faussée
- Les points d'erreur sont dessinés plus grands et au-dessus des points corrects : ce
  sont eux que la carte doit rendre visibles
- Contour blanc fin autour de chaque point, pour qu'ils restent lisibles quand ils se
  chevauchent
- Barre d'échelle de 25 km dans chaque panneau, un degré valant environ 111 km
- Aucun chiffre sur les points individuels, la carte deviendrait illisible
- Filets discrets, pas de grille, pas de graduations d'axes

### Deux mentions obligatoires, gravées dans l'image

Elles ne doivent pas être laissées au texte d'accompagnement : une image partagée sur un
réseau social circule sans sa légende.

1. En rouge et en gras : « Démonstration sur deux blocs d'évaluation. Ce n'est pas une
   carte du palmier en RDC. »
2. En petit et en gris : « Étiquettes : Descals et al. 2024, Global Oil Palm extent maps,
   Zenodo, CC BY 4.0. Imagerie : Copernicus Sentinel-1 et Sentinel-2, ESA. Contours :
   USDOS LSIB, domaine public. »

### Les contraintes de sortie

- 2 000 pixels de large, 200 points par pouce
- Taille de texte lisible sur un téléphone, aucun texte sous 8 points
- Vérifie qu'aucun élément n'en chevauche un autre et qu'aucun texte n'est coupé aux
  bords : c'est le défaut le plus fréquent sur ce type de figure
- Le script doit s'exécuter sans intervention et écrire le fichier PNG
