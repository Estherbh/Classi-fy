# Classi-fy

Oil palm detection across the Congo Basin from Sentinel-1 and Sentinel-2 time series. Trained on 34 blocks, 24 of them in the Democratic Republic of the Congo.

[Version française](README.md)

---

## Result

Binary classification, palm against no palm, evaluated with **spatial** cross-validation over 34 disjoint geographic blocks.

| Metric | Value |
|---|---|
| Macro F1 (spatial validation, 5 folds) | **0.817 ± 0.022** |
| Macro F1 (random validation) | 0.835 ± 0.011 |
| Optimism of random validation | +0.018 |
| Floor (always-majority model) | 0.378 |
| Overall accuracy | 0.83 |

The number to report is **0.817**. It is measured on regions the model never saw during training.

An optimism of +0.018 means the model loses only 1.8 points when moving to a completely different region. It relies on a transferable signal rather than on local artefacts.

### Per class

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| palm | 0.86 | 0.87 | 0.87 | 1,090 |
| no palm | 0.80 | 0.78 | 0.79 | 700 |

### Confusion matrix

Rows: ground truth. Columns: model prediction.

| | predicted palm | predicted no palm |
|---|---|---|
| **was palm** | 951 | 139 |
| **was not palm** | 157 | 543 |

Reading: out of 1,090 real palm plots, the model finds 951 and misses 139. Out of 700 palm-free areas, it wrongly flags 157.

---

## Training data

### Labels

**Descals et al. 2024, Global Oil Palm extent maps.**
Zenodo: [10.5281/zenodo.13379129](https://zenodo.org/records/13379129), licensed CC BY 4.0.

Raster maps at 10 m resolution covering 2016 to 2021, together with 18,812 field validation points. Three pixel values:

| Value | Class |
|---|---|
| 0 | no palm |
| 1 | industrial palm |
| 2 | smallholder palm |

Files used:

- `Grid_OilPalm2016-2021.zip`: the 100 km tile grid, which doubles as the spatial split
- `GlobalOilPalm_OP-extent_<id>.tif`: the extent rasters, one per tile

Why this source. It is the only open, labelled, 10 m, field-validated layer covering the Congo Basin. The alternatives considered did not fit: the cocoa map by Kalischek et al. (*Nature Food*, 2023) and the COLD-CI dataset cover Côte d'Ivoire and Ghana, not the DRC; the [WorldCereal Reference Data Module](https://rdm.esa-worldcereal.org/) is cereal-oriented and holds few points in Central Africa.

### Sampling

- Selection: bounding box 12.2° to 31.3° east, -13.5° to 5.4° north, intersected with the tile grid
- 34 tiles of 100 km contain palm, spanning 12.1° to 30.1° east and -4.9° to 4.0° north
- One point every 200 m at most, that is one pixel in 20 along each axis: two neighbouring pixels of the same plantation are nearly identical and would inflate the dataset without adding information
- Balanced draw across the three classes, within the palm-densest window of each tile
- Random seed fixed at 42

Result: **8,658 points across 34 blocks**.

| Class | Count |
|---|---|
| no palm | 3,400 |
| industrial palm | 2,728 |
| smallholder palm | 2,530 |

### Actual geographic spread

Selection is done by **bounding box, not by national border**. The chosen extent therefore spills into neighbouring countries, and the training set is not exclusively Congolese. Checked tile by tile against the `USDOS/LSIB_SIMPLE/2017` boundaries:

| Country | Blocks | Points | Share |
|---|---|---|---|
| **Democratic Republic of the Congo** | 24 | 6,214 | **71.8 %** |
| Republic of the Congo | 4 | 936 | 10.8 % |
| Central African Republic | 2 | 508 | 5.9 % |
| Cameroon | 1 | 300 | 3.5 % |
| Tanzania | 1 | 300 | 3.5 % |
| Burundi | 1 | 200 | 2.3 % |
| Angola | 1 | 200 | 2.3 % |

Within the DRC the blocks run west to east: the Atlantic side of Kongo Central, the central basin between 18° and 22° east, northern Tshopo and Bas-Uélé, then the eastern blocks between 28° and 29° east, towards South Kivu and Tanganyika.

This spill does not weaken the model, it widens its domain: spatial cross-validation covers the Congo Basin rather than a single country. But it forbids presenting the result as a strictly Congolese model, and it is stated here for that reason.

### Imagery

Reference year: **2021**, the last year covered by the Descals map.

| Sensor | Earth Engine collection | Bands | Role |
|---|---|---|---|
| Sentinel-2 L2A | `COPERNICUS/S2_SR_HARMONIZED` | B2, B3, B4, B8, B11, B12 | colour and vegetation vigour |
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | VV, VH | canopy structure |

Processing:

- Clouds, shadows, cirrus and snow masked through the SCL classification band (values 3, 8, 9, 10, 11)
- Scenes kept below 80 % cloud cover
- Sentinel-1 filtered to IW mode, dual VV and VH polarisation
- One monthly median per band, giving 12 composites
- Fallback to the annual median wherever a month is fully masked, otherwise the rainy season empties entire months and the sampling step drops the affected points

Each point therefore carries **96 measurements**, that is 12 months by 8 bands.

---

## Methodology

### The pipeline, four independent steps

```
echantillonner_palmier.py    Zenodo rasters        -> data/echantillons_rdc.geojson
extraire_series_gee.py       Sentinel-1 and -2     -> CSV in Google Drive
preparer_parcelles.py        CSV                   -> data/parcelles.parquet
modele_binaire.py            parquet               -> data/modele_palmier.joblib
```

Each step runs on its own and resumes where the previous one stopped.

### Features

The 96 raw reflectance values are not fed to the model. They are summarised into **34 annual features**, far more stable from one image to the next.

**Normalised indices**, computed month by month then summarised by mean, standard deviation, minimum, maximum and amplitude:

| Index | Formula | What it captures |
|---|---|---|
| NDVI | (B8 − B4) / (B8 + B4) | vegetation vigour |
| NDWI | (B3 − B8) / (B3 + B8) | canopy water content |
| NBR | (B8 − B12) / (B8 + B12) | canopy structure |

**Per-band statistics**: annual mean and standard deviation of the 8 bands.

**Radar signature**: mean and standard deviation of the VV − VH difference over the year.

**Month of NDVI peak**.

### Validation protocol

Standard cross-validation heavily overestimates performance in remote sensing. Two neighbouring plots share the same soil, the same weather and often the same image: with a random split, nearly identical plots land on both sides and the model is scored on what it has already seen.

The protocol used is therefore a **spatial block split**: `StratifiedGroupKFold` with 5 folds, where the group is the 100 km tile. Each tile sits entirely on one side of the split, and each tile is tested exactly once across the 5 folds.

Both splits are computed on every run. Their difference, called **optimism** here, quantifies spatial leakage and acts as a reliability check: beyond 0.10, the reported score is not defensible.

### Models compared

`RandomForestClassifier` and `HistGradientBoostingClassifier`, both evaluated under spatial validation. Gradient boosting is selected. Both reach 0.815, a difference that is not meaningful: performance comes from the features, not from the algorithm.

---

## The decisive role of radar

Permutation importance leaves no ambiguity.

| Feature | F1 loss when shuffled |
|---|---|
| **vv_vh_moy** | **0.172** |
| B8_moy | 0.027 |
| VH_moy | 0.012 |
| B11_moy | 0.011 |
| B2_moy | 0.011 |
| VV_moy | 0.009 |

The difference between the two radar polarisations carries **6.3 times** more signal than the best optical feature.

The explanation is physical. Palm and tropical forest are both closed canopies, green all year, with nearly identical NDVI seasonal amplitude, 0.04 against 0.03. Optical imagery cannot separate them. Radar measures structure rather than colour: a plantation has aligned trees of uniform height and returns a regular echo, where natural forest returns a disordered one.

### Measured effect

| Configuration | Spatial F1 | Optimism |
|---|---|---|
| Optical only, 3 classes | 0.405 | +0.225 |
| Optical and radar, 3 classes | 0.561 | +0.066 |
| Optical and radar, binary | **0.817** | **+0.018** |

The collapse of optimism, from 0.225 to 0.018, matters as much as the score increase. It shows the model stopped relying on local shortcuts.

---

## Area of validity

The 34 training blocks span **12.1° to 30.1° east and -4.9° to 4.0° north**, the full width of the Congo Basin, from the Atlantic side to the Great Lakes. Spatial cross-validation measures transfer between regions inside that extent directly, and an optimism of +0.018 says it happens without meaningful loss.

The domain of validity is therefore the **Congo Basin in humid tropical forest**, not a country. It spans 24 blocks in the DRC and 10 across six neighbours, which is a strength for generalisation: the model was tested across different national contexts and did not break down.

One feature of the sampling does restrict its reach, however, and must be understood before any use. The selected tiles are those where Descals detects palm, and within each tile the sampling targets the densest window. **The "no palm" class therefore represents what surrounds palm plantations**, mostly forest and neighbouring crops. It does not represent any national territory as a whole.

What the model has never seen:

- dry savanna of Katanga and southern Kasaï
- urban and peri-urban areas
- highlands and montane forests of the Kivu
- large water bodies and extensive wetlands
- the entire southern half of the DRC, no block reaches below -4.9° latitude

On those environments its behaviour is unknown, not poor but unmeasured. This is the mechanism behind the first limitation below.

---

## Possible uses

### What the model can do today

**Check a specific site.** Given a plot or a set of coordinates, it reports whether palm is present, with a precision of 0.86. Out of 100 alerts, 86 are correct.

**Prioritise field missions.** The model outputs a probability, not just an answer. Ranking suspect sites by decreasing probability and checking the top ones concentrates a limited patrol budget where the return is highest.

**Audit a declaration.** A concession or an operator claims no plantation occupies a plot: the model provides an independent, dated opinion grounded in public imagery.

**Pre-filter before photo-interpretation.** On a batch of sites to review by eye, first discarding those the model confidently judges palm-free reduces the human workload, provided the 13 % of missed plantations are acceptable.

**Support a report.** The figures are measured under spatial validation and the method is reproducible, hence defensible before a funder or a scientific partner.

### Concrete conservation applications

- monitoring park boundaries and their buffer zones
- detecting plantation expansion inside tracked concessions
- quantified support for palm-driven deforestation reporting
- targeting patrols and verification missions

### What the model cannot do

**Produce a national map.** See limitation 1 below, the most important point in this document.

**Tell industrial from smallholder palm.** See limitation 2.

**Date a plantation or detect change.** The model is trained on a single year. Comparing two years would require retraining and validating that comparison, which has not been done.

**Estimate an area.** It classifies points, not polygons. Converting to hectares would require separate segmentation and area validation.

---

## Improvement paths

Ordered by expected payoff, from most to least cost-effective.

**1. Broaden and rebalance the negative class.**
This is the priority, the one that would unlock mapping. It means sampling tiles with no palm at all, savanna, cities, mountains, wetlands, and honouring the real scarcity of palm instead of 60.7 %. Expected effect: collapse of the false alarm rate on environments the model has never seen.

**2. Tune the decision threshold.**
The model outputs a probability, currently cut at 0.5. Raising that threshold trades recall for precision. For a national map, a threshold of 0.8 or 0.9 would sharply cut false positives at the cost of a few missed plantations. The right setting depends on the relative cost of the two errors in your use case, it is chosen rather than guessed.

**3. Add terrain.**
The Copernicus or SRTM digital elevation model provides altitude and slope. Oil palm grows neither at altitude nor on steep slopes. Two free features, immediate to extract in Earth Engine, that would mechanically remove part of the false positives in hilly terrain.

**4. Introduce texture features.**
Local standard deviation, grey-level co-occurrence matrices on radar, neighbourhood statistics. This is the only route to separating industrial from smallholder palm, since their difference is geometric. Expected benefit on the palm against forest distinction as well.

**5. Extend to several years.**
Replaying the extraction over 2019 to 2023 would multiply the training volume, measure the model's stability over time and open up change detection, hence expansion monitoring.

**6. Collect field labels.**
The current labels come from a model, that of Descals, whose errors are inherited unchecked. Surveys carried out with farmers and field teams would provide independent ground truth, and would finally allow measuring real performance rather than agreement with another model.

**7. Densify the radar series.**
The model uses monthly medians. Sentinel-1 revisits every six to twelve days: a finer temporal resolution, or variability statistics between passes, could carry more structural information.

---

## Known limitations

They are stated here because they govern how the model may be used.

**1. The dataset does not reflect the real scarcity of palm.**
Sampling deliberately targeted the palm-densest window of each tile, hence 60.7 % palm in the dataset. Across the whole DRC, palm covers a fraction of a percent of the territory. The 22 % false alarm rate on palm-free areas is acceptable here, but applied to an entire country it would produce more false positives than true detections. **The model is not validated for national mapping.** It answers "does this plot contain palm", not "where is palm in the DRC".

**2. Industrial and smallholder palm are not separable.**
In the three-class setting the model plateaus at 0.561 and confuses the two types one third of the time. What distinguishes them is plantation geometry, block size and row regularity, information absent from a per-pixel analysis. Texture and neighbourhood features would be required.

**3. The labels are themselves a prediction.**
The Descals layer is the output of a model, with its own errors. They are inherited here without correction.

**4. A single year.**
Everything is anchored on 2021. Behaviour on other years has not been measured.

**5. The account-free variant is clearly inferior.**
`extraire_series_local.py` avoids any registration by reading Sentinel-2 from the open AWS bucket, but the Sentinel-1 bucket is paid. Without radar the result plateaus at 0.405. One tile, 33506, even proved unusable with optical data alone, clouded over for all twelve months. Radar, which sees through clouds, resolved that case.

---

## Technologies

| Area | Tool | Version |
|---|---|---|
| Language | Python | 3.14.5 |
| Satellite imagery | Google Earth Engine (`earthengine-api`) | 1.7.38 |
| Machine learning | scikit-learn | 1.7.2 |
| Tabular data | pandas | 2.3.3 |
| Numerical computing | numpy | 2.3.5 |
| Geospatial data | geopandas | 1.1.4 |
| Rasters | rasterio | 1.5.0 |
| Geometries | shapely | 2.1.2 |
| Columnar format | pyarrow | 22.0.0 |
| Plotting | matplotlib | 3.10.8 |
| Serialisation | joblib | 1.5.2 |
| Exploration | Jupyter Notebook | |

Imagery sources: Copernicus Sentinel-1 and Sentinel-2, through Google Earth Engine. A local variant queries the Element 84 STAC API against the AWS Open Data bucket `sentinel-cogs`.

---

## Reproducing the result

### Prerequisites

```bash
pip install earthengine-api scikit-learn pandas numpy geopandas rasterio pyarrow matplotlib joblib
earthengine authenticate
```

A Google Earth Engine account is required, free for non-commercial use. Then set your Cloud project identifier in `extraire_series_gee.py`.

### Step 1, the labelled points

Download from [Zenodo 10.5281/zenodo.13379129](https://zenodo.org/records/13379129) and unpack into `data/`:

- `Grid_OilPalm2016-2021.zip` into `data/palmier_grille/`
- the extent rasters into `data/palmier_extent/`

```bash
python echantillonner_palmier.py
```

Produces `data/echantillons_rdc.geojson`, 8,658 points across 34 blocks.

### Step 2, the time series

```bash
python extraire_series_gee.py
```

The export runs on Google's side and returns immediately. Allow about ten minutes. The CSV lands in Google Drive, folder `Classify`. Track it at [code.earthengine.google.com/tasks](https://code.earthengine.google.com/tasks).

### Step 3, formatting

Download the CSV into `data/`, then:

```bash
python preparer_parcelles.py data/series_sentinel_rdc.csv
```

### Step 4, the model

```bash
python modele_binaire.py
```

Prints the full evaluation and writes `data/modele_palmier.joblib`.

### Account-free variant

```bash
python extraire_series_local.py
```

Replaces steps 2 and 3 by reading Sentinel-2 from AWS Open Data. Allow one hour. Provides no radar, hence plateaus at 0.405. Useful to validate the pipeline, not to produce a result.

---

## Repository layout

| File | Role |
|---|---|
| `echantillonner_palmier.py` | step 1, draws labelled points from the Zenodo rasters |
| `extraire_series_gee.py` | step 2, Sentinel-1 and Sentinel-2 extraction through Earth Engine |
| `extraire_series_local.py` | step 2, account-free variant, Sentinel-2 only from AWS |
| `preparer_parcelles.py` | step 3, converts the Earth Engine CSV to parquet |
| `modele_binaire.py` | step 4, final palm against no-palm model |
| `predictions_carte.py` | geolocated predictions for the test fold, feeding the map |
| `carte_resultats.py` | map of the four confusion-matrix cases, PNG output |
| `classification_cultures.ipynb` | analysis notebook, split comparison and three-class evaluation |
| `organiser_fermiers_py.ipynb` | farmer list organisation, outside the classification pipeline |

The `data/` folder is excluded from the repository. It holds the rasters, the extracted series and personal farmer data, which must never be published.

---

## References

- Descals, A. et al. (2024). *Global Oil Palm extent maps*. Zenodo. [10.5281/zenodo.13379129](https://zenodo.org/records/13379129), CC BY 4.0
- Kalischek, N. et al. (2023). Cocoa plantations are associated with deforestation in Côte d'Ivoire and Ghana. *Nature Food*, 4, 384-393. [Paper](https://www.nature.com/articles/s43016-023-00751-8), [code](https://github.com/D1noFuzi/cocoamapping)
- ESA WorldCereal Reference Data Module. [rdm.esa-worldcereal.org](https://rdm.esa-worldcereal.org/)
- Copernicus Sentinel-1 and Sentinel-2, European Space Agency
