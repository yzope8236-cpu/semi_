# Public Datasets & Synthetic STDF Fixtures

This document outlines the external datasets and synthetic fixtures supported in the YieldScope environment.

## 1. Synthetic STDF Fixtures
- **Path:** `samples/stdf-golden/`
- **Purpose:** These files are purely synthetic and are strictly for binary STDF parser validation. They simulate edge cases, hardware bins, and specific failure modes.
- **Confidentiality:** Completely non-confidential and open-source. They do not contain any customer or proprietary test data.

## 2. WM-811K Wafer Maps
- **Purpose:** This dataset is designed for wafer-map visualization and spatial pattern classification (ML use). **It is NOT raw binary STDF tester output.**
- **Path:** Expected to be placed in `data/external/wm811k/` (not committed).
- **Download:** Available via Kaggle.
- **Citation/License:** Ensure compliance with the original dataset author’s license when utilizing this dataset for demonstrations.

## 3. Mixed-Type Wafer Defect Dataset
- **Purpose:** Useful for advanced visualization and multi-class defect ML demonstrations.
- **Path:** Expected to be placed in `data/external/mixed_defect/`.
- **Citation/License:** Check Kaggle or the primary publication for the specific citation and licensing constraints.

## 4. Semiconductor Sensor Quality Dataset
- **Purpose:** Used to demonstrate predictive modeling and time-series anomaly detection on sensor data.
- **Path:** Expected to be placed in `data/external/sensor_quality/`.
- **Citation/License:** Verify the original Kaggle/UCI license before usage.

## 5. Security & Confidentiality
> [!CAUTION]
> **Client and customer STDF/ATDF files MUST NEVER be committed to a public repository.**
> Always utilize the `data/raw/` or `data/external/` directories for proprietary files locally, as these directories are ignored by Git.

---
*Disclaimer: YieldScope does not claim that public Kaggle datasets are STDF files. Additionally, synthetic STDF fixtures are for basic validation and do not guarantee production compatibility with every tester vendor's STDF dialect. Machine Learning features demonstrated with these datasets are not production-trained models.*
