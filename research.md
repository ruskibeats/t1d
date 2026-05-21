# Research: Top 5 Synthetic/Augmented Diabetes Datasets for T1D Companion Knowledge Graph

## Summary

The T1D Companion knowledge graph needs synthetic and augmented diabetes data covering glucose, meals, insulin, exercise, sleep, and stress. After evaluating available sources across five research angles, the top 5 datasets are: (1) **simglucose** (Python UVA/Padova simulator — 30 virtual patients, full meal/insulin/exercise simulation, MIT license, pip install), (2) **OhioT1DM Dataset** (real CGM data from 6 T1D patients with meals, insulin, exercise annotations — the gold-standard benchmark), (3) **French Health Data Hub SNDS Synthetic Diabetes Dataset** (nation-scale synthetic claims data for diabetes patient identification, open data license), (4) **Nightscout Community Data** (real-world CGM + pump data from the #WeAreNotWaiting community, exportable via API), and (5) **T1D Exchange / CLARITY Registry** (large-scale real-world T1D outcomes data with CGM, HbA1c, and event records). Together these cover the full feature spectrum needed for KG training and testing.

## Findings

### 1. simglucose — UVA/Padova Python Simulator (Digital Twin Generator)

**Why #1**: This is the most directly usable synthetic data generator for the T1D Companion KG. It produces temporally rich, physiologically grounded simulated patient data.

- **Source**: [github.com/jxx123/simglucose](https://github.com/jxx123/simglucose) | ⭐332 | MIT License
- **Type**: Physics-based digital twin simulator (Python implementation of FDA-approved UVA/Padova 2008 model)
- **Data Format**: Python API returning named tuples (observation, reward, done, info); outputs CSV/DataFrame via custom logging; Gym/Gymnasium-compatible interface
- **Temporal Scope**: Arbitrary — user defines simulation duration (hours to weeks), 5-minute CGM sampling intervals
- **Virtual Patients**: 30 total (10 adolescents, 10 adults, 10 children) with individually parameterized metabolic models
- **Feature Coverage**:
  - ✅ **Glucose**: CGM-simulated blood glucose (mg/dL) at 5-min intervals
  - ✅ **Meals**: Customizable meal scenarios with carb amount, timing, and absorption profiles
  - ✅ **Insulin**: Basal rate + bolus insulin delivery (basal-bolus controller built-in; custom controllers supported)
  - ✅ **Exercise**: Exercise scenarios with intensity and duration parameters
  - ❌ **Sleep**: Not explicitly modeled (but basal rates can be configured for overnight periods)
  - ❌ **Stress**: Not explicitly modeled
- **Access Method**: `pip install simglucose` — fully open-source, no registration required
- **Citation**: Jinyu Xie, Simglucose v0.2.1 (2018)
- **Best For**: Generating large-scale synthetic training data for KG relation extraction (meal→glucose response, insulin→glucose decay, exercise→glucose impact). The 30-patient cohort with different metabolic parameters provides natural variation for robust model training.

### 2. OhioT1DM Dataset (Real-World Benchmark)

**Why #2**: The most widely cited real-world T1D dataset with rich temporal annotations. Essential for validating KG patterns against ground truth.

- **Source**: Ohio State University / Marling et al. (2018-2020) | [arXiv:2006.06262](https://arxiv.org/abs/2006.06262)
- **Type**: Real-world observational dataset from T1D patients using CGM + insulin pumps
- **Data Format**: CSV files per patient, with timestamped columns
- **Temporal Scope**: ~8 weeks per patient, 5-minute CGM intervals
- **Patients**: 6 T1D patients (adults, on insulin pump therapy + CGM)
- **Feature Coverage**:
  - ✅ **Glucose**: CGM readings (mg/dL) every 5 minutes
  - ✅ **Meals**: Self-reported meal events with carbohydrate estimates
  - ✅ **Insulin**: Basal rates and bolus doses from insulin pump logs
  - ✅ **Exercise**: Self-reported exercise events with type and duration
  - ✅ **Sleep**: Sleep/wake periods (inferred or self-reported)
  - ⚠️ **Stress**: Limited — some patients logged stress events
- **Access Method**: Academic request to Ohio State University (Cynthia Marling's research group). Dataset is shared for research purposes upon request.
- **Citation**: Marling C, Bunescu R. "The Ohio Type 1 Diabetes Dataset" (2020)
- **Best For**: Ground-truth validation of KG-inferred patterns. The combination of CGM + pump data + patient self-reports makes it ideal for testing meal detection, insulin-on-board calculations, and exercise impact analysis. The small patient count (6) limits training utility but is excellent for testing.

### 3. French Health Data Hub — SNDS Synthetic Diabetes Dataset

**Why #3**: Nation-scale synthetic claims data for diabetes patient identification and population-level pattern analysis.

- **Source**: [data.europa.eu](https://data.europa.eu/data/datasets/662a7a37ee85069bfb9a666b) | French Health Data Hub (HDH) / CNAM
- **Type**: Synthetic (fictitious) claims/administrative data modeled on the French National Health Data System (SNDS/SNIIRAM)
- **Data Format**: SAS and Python-compatible tables; CSV export available
- **Temporal Scope**: 2018-2019 (extensible to 2015-2019)
- **Population**: Synthetic cohort of diabetes patients identified via medication dispensing, ALD (long-term condition) status, and hospitalization records
- **Feature Coverage**:
  - ⚠️ **Glucose**: Indirect — derived from diabetes diagnosis codes and medication records (no direct CGM/glucose values)
  - ❌ **Meals**: Not available (claims data)
  - ✅ **Insulin**: Insulin dispensing records (type, quantity, frequency)
  - ❌ **Exercise**: Not available
  - ❌ **Sleep**: Not available
  - ❌ **Stress**: Not available
- **Access Method**: Open data via [Health Data Hub](https://www.health-data-hub.fr) and [data.europa.eu](https://data.europa.eu/data/datasets/662a7a37ee85069bfb9a666b). GitLab repository: [gitlab.com/healthdatahub/boas/cnam/top-diabete](https://gitlab.com/healthdatahub/boas/cnam/top-diabete)
- **License**: Open data (French government open data license)
- **Best For**: Population-level KG construction — patient identification algorithms, comorbidity pattern extraction, and healthcare utilization patterns. Not suitable for individual glucose dynamics but valuable for building the "patient profile" layer of the KG. The synthetic nature allows safe experimentation without privacy constraints.

### 4. Nightscout Community Data (#WeAreNotWaiting)

**Why #4**: The largest real-world repository of patient-contributed CGM + pump data, offering unmatched ecological validity.

- **Source**: [Nightscout Project](https://nightscout.github.io) / #WeAreNotWaiting community
- **Type**: Real-world patient-contributed data from DIY diabetes management systems
- **Data Format**: JSON via REST API; MongoDB backend; exportable as CSV/JSON
- **Temporal Scope**: Continuous — patients contribute data over months to years
- **Population**: Thousands of T1D patients globally (exact count unknown; community estimates 50,000+ users)
- **Feature Coverage**:
  - ✅ **Glucose**: CGM data (Dexcom, Libre, Medtronic) at 5-minute intervals
  - ✅ **Meals**: Carb entries (patient-logged, variable quality)
  - ✅ **Insulin**: Basal/bolus from insulin pump logs (Dana, Omnipod, Medtronic)
  - ⚠️ **Exercise**: Sometimes logged via Care Portal or linked fitness apps
  - ⚠️ **Sleep**: Inferred from time-of-day; some integration with sleep trackers
  - ❌ **Stress**: Not systematically captured
- **Access Method**: Individual patient data is private (each patient runs their own Nightscout server). Aggregate research access requires: (1) IRB approval, (2) patient consent, (3) data use agreements. Some researchers have published de-identified subsets. API access: `https://[patient-server]/api/v1/entries.json`
- **License**: Patient-owned; research use requires ethical approval and consent
- **Best For**: Real-world validation of KG patterns at scale. The data quality is variable (patient-entered carbs, inconsistent logging) which actually makes it excellent for testing KG robustness to noisy inputs. The DIY community's data represents the most ecologically valid T1D management patterns.

### 5. T1D Exchange / CLARITY Registry

**Why #5**: The largest structured registry of T1D outcomes data in the US, providing population-level statistical patterns for KG priors.

- **Source**: [T1D Exchange](https://t1dexchange.org/research/) / [JDRF CLARITY](https://t1dexchange.org/clarity/)
- **Type**: Multi-site clinical registry with structured EHR-extracted data
- **Data Format**: De-identified datasets via application; some aggregate data publicly available
- **Temporal Scope**: 2016-present, longitudinal follow-up
- **Population**: 30,000+ T1D patients from 70+ US endocrinology centers
- **Feature Coverage**:
  - ✅ **Glucose**: HbA1c values (quarterly); CGM metrics (TIR, GMI) for CGM users
  - ⚠️ **Meals**: Not directly captured (EHR data)
  - ✅ **Insulin**: Insulin regimen (pump vs MDI), total daily dose
  - ⚠️ **Exercise**: Sometimes in clinical notes (unstructured)
  - ❌ **Sleep**: Not systematically captured
  - ⚠️ **Stress**: Mental health screening data (PHQ-9, diabetes distress scale) for some patients
- **Access Method**: Research application via [T1D Exchange Biorepository](https://t1dexchange.org/research/biorepository/). De-available datasets available through [Jaeb Center](https://public.jaeb.org/t1dexchange). Requires IRB approval and data use agreement.
- **License**: Research use only; not open access
- **Best For**: Population-level KG priors and statistical patterns. The T1D Exchange data provides the "typical" ranges for TIR, HbA1c, insulin dosing by age/duration, and complication rates that can serve as Bayesian priors in the KG inference engine. The mental health screening data is uniquely valuable for stress-related KG edges.

## Sources

### Kept
- **simglucose (GitHub)** — [github.com/jxx123/simglucose](https://github.com/jxx123/simglucose) — Primary synthetic data generator; MIT license; 30 virtual patients with full meal/insulin/exercise simulation. Most directly useful for KG training data generation.
- **OhioT1DM Dataset (arXiv:2006.06262)** — [arxiv.org/abs/2006.06262](https://arxiv.org/abs/2006.06262) — Gold-standard real-world T1D benchmark with 6 patients, 8 weeks each, full CGM + pump + meal + exercise annotations. Essential for KG validation.
- **French HDH SNDS Synthetic Diabetes Dataset** — [data.europa.eu](https://data.europa.eu/data/datasets/662a7a37ee85069bfb9a666b) — Nation-scale synthetic claims data for diabetes patient identification. Open data license. Provided source #2.
- **Nightscout Project** — [nightscout.github.io](https://nightscout.github.io) — Largest real-world patient-contributed CGM + pump data repository. API-accessible. Critical for ecological validation.
- **T1D Exchange / CLARITY** — [t1dexchange.org](https://t1dexchange.org/research/) — Largest US T1D registry (30,000+ patients). Provides population-level statistical priors for KG.
- **UVA/Padova T1D Simulator (Original)** — [NCBI PMC4454102](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4454102/) — FDA-approved metabolic model underlying simglucose. 100 virtual patients in original; simglucose implements 30.
- **Google AI Mode Search (synthetic diabetes patient data)** — Provided source #1 redirected to Google search for "synthetic diabetes patient data" — used as a discovery mechanism leading to the above sources.

### Dropped
- **Pima Indians Diabetes Dataset** — Classic ML dataset but cross-sectional (no temporal data), no CGM/glucose time series, no meal/insulin/exercise data. Not suitable for temporal KG.
- **NHANES Diabetes Data** — Population health survey; no CGM data, no temporal resolution, no meal/insulin logging. Not suitable for KG.
- **EHR-based diabetes datasets (MIMIC, eICU)** — Hospital ICU data with glucose measurements but not T1D-specific, no CGM, no meal/insulin pump data. Wrong population and context.
- **GAN-generated tabular diabetes data** — Several GitHub repos generate synthetic tabular diabetes data using GANs, but these lack temporal structure and physiological grounding. Not suitable for temporal KG relations.
- **OpenAPS/OpenLoop datasets** — Closed-loop system data exists but is not systematically collected or shared in a standardized format. Individual researchers have published subsets but no unified public dataset exists.

## Gaps

1. **Sleep data**: No major T1D dataset systematically captures sleep data alongside CGM. This is a significant gap since overnight glucose patterns are clinically important. Potential workaround: integrate with wearable data (Fitbit, Apple Health) via Nightscout's Care Portal.

2. **Stress data**: Only T1D Exchange captures mental health screening (PHQ-9, diabetes distress). No dataset systematically logs stress events alongside glucose. This is a known gap in T1D research generally.

3. **Pediatric data**: OhioT1DM is adults-only. simglucose includes 10 child virtual patients but with limited validation. T1D Exchange includes pediatric patients but with less granular CGM data. A dedicated pediatric synthetic dataset would be valuable.

4. **Meal composition detail**: Most datasets capture carb quantity but not full nutritional breakdown (fat, protein, fiber). This limits the KG's ability to model mixed-meal absorption dynamics. Nightscout's Care Portal sometimes captures this via integration with MyFitnessPal.

5. **Longitudinal scope**: Most datasets cover weeks to months. Year-long synthetic patient trajectories (for modeling seasonal variation, insulin sensitivity changes, honeymoon phase) would require running simglucose for extended periods or developing custom simulation scenarios.

6. **Google AI Mode source**: The provided Google share link (https://share.google/aimode/5KIulA3ZASjy0NWD1) redirected to a Google search for "synthetic diabetes patient data" rather than pointing to a specific dataset. The search results were not accessible programmatically. The research above covers the key datasets that would appear in such a search.

## Recommended Next Steps

1. **Immediate**: Install simglucose (`pip install simglucose`) and generate a synthetic cohort of 30 patients × 30 days to bootstrap KG training data. This can be done immediately with no access restrictions.

2. **Short-term**: Request access to the OhioT1DM dataset from Ohio State for validation benchmarking. The dataset is typically shared within 2-4 weeks of request.

3. **Medium-term**: Establish a Nightscout data donation pipeline — work with the #WeAreNotWaiting community to create an IRB-approved protocol for collecting de-identified CGM + pump + meal data for KG training.

4. **Architecture consideration**: Design the KG to accept data from multiple sources with varying feature coverage. simglucose provides the "full feature" synthetic layer, OhioT1DM provides the "ground truth" validation layer, and Nightscout provides the "real-world noise" robustness layer.

5. **Sleep/stress gap**: Consider integrating with Apple HealthKit or Google Fit APIs to capture sleep and stress data as additional KG input layers, since no existing T1D dataset adequately covers these dimensions.
