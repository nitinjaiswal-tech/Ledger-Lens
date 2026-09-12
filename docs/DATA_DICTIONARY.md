# Ledger Lens — Data Dictionary & Dataset Report
**Problem Statement:** SIH26102 — Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation.  
**Platform:** Ledger Lens (AI-Powered MPLADS Risk Intelligence & Monitoring Platform)  
**Status:** Phase 1 Initial Data Audit  

---

## 1. Dataset Overview

- **Source File:** `data/raw/Allocated Limit for Honble MPs.csv`
- **File Type:** CSV (Comma-Separated Values, UTF-8 Encoded)
- **File Size:** 36,148 bytes (35.30 KB)
- **Total Raw Records:** 544 rows × 5 columns
- **Data Entity Scope:** Member of Parliament (18th Lok Sabha) Allocated MPLADS Budget Limits
- **Data Provenance:** Official export from MPLADS / eSAKSHI administrative portal

---

## 2. Column-by-Column Data Dictionary

| Column Name in Dataset | Detected Data Type | Meaning / Inferred Role | Missing Value % | Financial Analysis | Progress Analysis | Timeline Analysis | Similarity Detection | Risk Scoring |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Sr. No.` | `String` / `Ordinal` | Serial sequence number (`1` to `543`, with row `544` containing `'Grand Total'`). | 0.00% | No | No | No | No | No |
| `State` | `String` (Categorical) | State or Union Territory of the parliamentary constituency (36 distinct States/UTs). | 0.00% | Yes | No | No | No | Yes |
| `Hon'ble Members of Parliaments` | `String` (Categorical) | Full name of the elected Member of Parliament (Lok Sabha). | 0.00% | Yes | No | No | No | Yes |
| `Constituency` | `String` (Categorical) | Official name of the Lok Sabha Parliamentary Constituency (542 distinct names; reservation qualifiers `(SC)`, `(ST)` embedded). | 0.00% | Yes | No | No | No | Yes |
| `Allocated AMOUNT ( ₹ )` | `String` formatted as currency (`INR`) | Cumulative MPLADS fund allocation limit authorized for the representative/constituency (₹4.90 Cr to ₹32.75 Cr for individual MPs; modal limit is ₹14.70 Cr). | 0.00%* | Yes | No | No | No | Yes |

*\*Note: 1 row in the raw file represents the Grand Total trailer (`83,33,99,05,622.01`). There are zero null values in individual MP records.*

---

## 3. Detailed Column Specification

### 3.1. `Sr. No.`
- **Detected Type:** `object` (`string`)
- **Inferred Role:** Row identifier index.
- **Range / Unique Values:** Values `'1'` through `'543'`, plus trailer `'Grand Total'`.
- **Validation Notes:** Non-numeric entry `'Grand Total'` at row 543 requires filtering during ingestion.
- **Analytical Utility:** Not used in risk modeling; purely operational.

### 3.2. `State`
- **Detected Type:** `object` (`string`)
- **Inferred Role:** Administrative State / Union Territory of India.
- **Cardinality:** 36 States/UTs + 1 whitespace value (in summary row).
- **Distribution Highlights:** Top states by MP count: Uttar Pradesh (80), Maharashtra (49), West Bengal (42), Bihar (40), Tamil Nadu (39).
- **Analytical Utility:**
  - **Financial Analysis:** Enables state-level allocation aggregations and inter-state budget allocation disparity analysis.
  - **Risk Scoring:** State-level baseline comparisons for allocation limits.
  - **Dashboard:** Spatial filtering and state-level KPI breakdown.

### 3.3. `Hon'ble Members of Parliaments`
- **Detected Type:** `object` (`string`)
- **Inferred Role:** Name of the Member of Parliament (Lok Sabha).
- **Cardinality:** 543 distinct MP names + 1 whitespace value (in summary row).
- **Validation Notes:** Casing is inconsistent (mix of ALL-CAPS, Title Case, and honorific titles e.g. `Adv`).
- **Analytical Utility:**
  - **Financial Analysis:** MP-level allocation limit tracking.
  - **Risk Scoring:** Tracking individual allocation deviations against peer MPs in the same state/party/term.

### 3.4. `Constituency`
- **Detected Type:** `object` (`string`)
- **Inferred Role:** Lok Sabha Parliamentary Constituency.
- **Cardinality:** 542 distinct constituencies (e.g. `NANDED` appears twice due to seat transitions).
- **Validation Notes:** Contains embedded reservation labels (e.g. `ALMORA(SC)`, `NANDURBAR(ST)`) and state code disambiguators (e.g. `AURANGABAD_BR`, `HAMIRPUR_UP`).
- **Analytical Utility:**
  - **Financial Analysis:** Constituency-level fund tracking.
  - **Risk Scoring:** Flagging abnormal budget allocations.
  - **Geographic Mapping:** Integration with Lok Sabha GIS boundary shapefiles / GeoJSON.

### 3.5. `Allocated AMOUNT ( ₹ )`
- **Detected Type:** `object` (`string`), converted to `float64` / `Decimal` (INR).
- **Inferred Role:** Total authorized MPLADS limit allocated to the MP/Constituency.
- **Distribution Summary (Excluding Grand Total):**
  - **Count:** 543 MPs
  - **Total Fund Allocated:** ₹83,33,99,05,622.01 (₹8,333.99 Crore)
  - **Baseline / Mode:** ₹14,70,00,000.00 (₹14.70 Crore for 382 MPs / 70.35%)
  - **Minimum:** ₹4,90,00,000.00 (₹4.90 Crore - Basirhat, WB)
  - **Maximum:** ₹32,74,77,390.86 (₹32.75 Crore - Malkajgiri, Telangana)
  - **Mean:** ₹15,34,80,489.17 (₹15.35 Crore)
  - **Median:** ₹14,70,00,000.00 (₹14.70 Crore)
  - **Standard Deviation:** ₹2,47,94,401.76 (₹2.48 Crore)
- **Analytical Utility:**
  - **Financial Analysis:** Core metric for allocation benchmarking.
  - **Risk Scoring:** Used with Isolation Forest / Z-score to surface high/low allocation deviations for officer review.

---

## 4. Unmet Analytical Domains (Data Gaps in Current File)

The current file provides macro-level MP allocation limits. The following granular domains require project-level / work-level eSAKSHI exports:

| Analytical Domain | Required Fields Currently Missing | Impact on Ledger Lens Engine |
| :--- | :--- | :--- |
| **Project / Work Level Tracking** | Work ID, Project Title, Description, Sector / Category, Recommendation Date | Project-specific granularity cannot be performed without work-level records. |
| **Timeline & Delay Analysis** | Administrative Sanction Date, Work Order Date, Target Completion Date, Actual Completion Date | Milestone slippage & timeline risk flags require date fields. |
| **Progress & Execution** | Physical Progress (%), Milestone Status, Completion Certificate flag | Payment-progress inconsistency checks require physical progress data. |
| **Financial Disbursements & Vendors** | Installment Amount, Disbursement Date, UC (Utilization Certificate) status, Implementing Agency Name, Contractor / Vendor ID | Financial anomaly detection at payment level requires transaction rows. |
| **Duplicate Work NLP** | Work Description text, Location / Village / Landmark text | Sentence-Transformer semantic similarity requires textual work descriptions. |

---

## 5. Quality & Ingestion Recommendations

1. **Ingestion Filter:** Explicitly strip summary/trailer rows where `Sr. No.` contains `'Grand Total'`.
2. **Text Normalization:** Implement string cleaning for MP Names (trim whitespace, title-casing) and Constituency names (extract reservation status `(SC)` / `(ST)` into separate metadata columns).
3. **Numeric Cast:** Clean currency formatting (strip `₹`, commas, whitespace) and store as `NUMERIC(15, 2)` in PostgreSQL.
4. **Data Enrichment Strategy:** Ingest secondary work-level eSAKSHI CSV/JSON tables as they are released to unlock Phase 2 & Phase 3 modules.
