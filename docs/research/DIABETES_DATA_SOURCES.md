# Diabetes Data Sources for T1D Companion Knowledge Graph

*Research Date: 2026-05-19*  
*Task: #116*

---

## Executive Summary

Five primary data sources identified for T1D Companion knowledge graph training and validation:

1. **simglucose** (MIT License) - Physics-based UVA/Padovo simulator, 30 virtual patients, full meal/insulin/exercise
2. **OhioT1DM Dataset** - Real CGM + pump data from 6 T1D patients, 8 weeks each
3. **French HDH SNDS Synthetic** - Nation-scale synthetic claims data for population modeling
4. **Nightscout Community** - Real-world patient-contributed CGM + pump data (~50K users)
5. **T1D Exchange / CLARITY** - 30,000+ T1D registry for population priors

---

## Detailed Analysis

### 1. simglucose — UVA/Padova Python Simulator

**Best for**: Large-scale synthetic training data generation

| Attribute | Value |
|-----------|-------|
| Source | [github.com/jxx123/simglucose](https://github.com/jxx123/simglucose) |
| License | MIT |
| Patients | 30 (10 adolescent, 10 adult, 10 child) |
| Sampling | 5-minute CGM intervals |
| Features | Glucose, meals, insulin (basal/bolus), exercise |
| Access | `pip install simglucose` |

```python
# Quick start example
pip install simglucose
python -c "
from simglucose.simulation.simulator import Simulator
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.sensor.cgm import GaussianNoise
sim = Simulator(T1DPatient('adolescent#001'), GaussianNoise())
```

### 2. OhioT1DM Dataset

**Best for**: Ground-truth validation benchmarking

| Attribute | Value |
|-----------|-------|
| Source | Ohio State University (Cynthia Marling) |
| Papers | [arXiv:2006.06262](https://arxiv.org/abs/2006.06262) |
| Patients | 6 adults on CGM + insulin pump |
| Duration | ~8 weeks per patient |
| Features | CGM, meals, insulin, exercise, sleep |
| Access | Academic request |

### 3. French Health Data Hub SNDS Synthetic Diabetes Dataset

**Best for**: Population-level patient identification and comorbidity patterns

| Attribute | Value |
|-----------|-------|
| Source | [data.europa.eu](https://data.europa.eu/data/datasets/662a7a37ee85069bfb9a666b) |
| License | Open data |
| Records | Synthetic cohort |
| Features | Insulin dispensing, diagnosis codes, demographics |
| Access | Direct download |

### 4. Nightscout Community Data (#WeAreNotWaiting)

**Best for**: Real-world validation with noisy inputs

| Attribute | Value |
|-----------|-------|
| Source | [nightscout.github.io](https://nightscout.github.io) |
| Population | ~50,000 T1D patients |
| Features | CGM, carbs, insulin, sometimes exercise |
| Access | Individual server API (IRB required for aggregate) |

### 5. T1D Exchange / CLARITY Registry

**Best for**: Population priors and statistical baselines

| Attribute | Value |
|-----------|-------|
| Source | [t1dexchange.org](https://t1dexchange.org/research/) |
| Patients | 30,000+ |
| Features | HbA1c, TIR, insulin regimens, mental health screening |
| Access | Research application with IRB |

---

## HuggingFace Synthetic Diabetes Dataset Gap Analysis

[HuggingFace Dataset](https://huggingface.co/datasets/MaxPrestige/Synthetic-Diabetes-Dataset)

**Note**: This is a **cross-sectional** dataset (100K rows, one per patient, no temporal CGM data). It's complementary to the T1D Companion graph, not overlapping.

| Feature | HF Dataset | T1D Graph | Gap |
|---------|------------|-----------|-----|
| Glucose | ✅ Fasting/postprandial | ✅ CGM time series | HF lacks temporal dynamics |
| HbA1c | ✅ | ✅ | Covered |
| Insulin | ✅ Level | ✅ Basal/bolus/pump | Covered + details |
| Lipids (HDL/LDL/triglycerides) | ✅ | ❌ | **Missing** |
| Exercise | ✅ Weekly mins | ✅ Minutes/steps/distance | HF less granular |
| Sleep | ✅ Hours | ✅ Stages + score | HF basic |
| Demographics | ✅ Age/gender/ethnicity | ❌ | **Missing** |
| Clinical History | ✅ CV/HTN/family | ❌ | **Missing** |

### Key Integration Opportunities

1. **Lipid metrics** - Add to MetricType enum
2. **Demographics** - Integrate from user profile as node attributes
3. **Clinical history** - Add as patient metadata edges
4. **Population priors** - Use HF/T1D Exchange for Bayesian priors

---

## Recommended Implementation Order

1. **Immediate**: Generate synthetic data with simglucose (30 patients × 30 days)
2. **Short-term**: Request OhioT1DM access for validation
3. **Medium-term**: Explore Nightscout IRB protocol for real-world data
4. **Long-term**: Integrate lipid panel metrics and demographic risk factors

---

## References

- Xie, J. (2018). Simglucose v0.2.1. [GitHub](https://github.com/jxx123/simglucose)
- Marling, C., & Bunescu, R. (2020). The Ohio Type 1 Diabetes Dataset. arXiv:2006.06262
- French HDH SNDS Dataset. [data.europa.eu](https://data.europa.eu)
- Nightscout Project. [nightscout.github.io](https://nightscout.github.io)
- T1D Exchange. [t1dexchange.org](https://t1dexchange.org)