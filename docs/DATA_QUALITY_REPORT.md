# Ledger Lens — Data Quality & Preprocessing Report
**Problem Statement:** SIH26102 — Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation.  
**Phase:** Phase 1 — Data Cleaning, Validation & Quality Assurance  
**Generated On:** 2026-09-11  

---

## 1. Executive Summary & Source Files Processed

| Parameter | Specification |
| :--- | :--- |
| **Source Raw File** | `data/raw/Allocated Limit for Honble MPs.csv` |
| **Source File Size** | 36,148 bytes (35.30 KB) |
| **Original Raw Dimensions** | **544 rows × 5 columns** |
| **Processed Primary Dimensions** | **543 operational rows × 12 columns** |
| **Processed Parquet File** | `data/processed/allocated_limit_mps_cleaned.parquet` (34.38 KB) |
| **Processed CSV File** | `data/processed/allocated_limit_mps_cleaned.csv` (56.29 KB) |
| **Metadata Audit File** | `data/processed/summary_totals_metadata.json` (280 bytes) |
| **Data Provenance** | Official export from the MPLADS / eSAKSHI administrative portal |
| **National Allocated Fund Total** | **₹83,33,99,05,622.01** (Reconciled with 0.00 delta) |

---

## 2. Column Standardization & Transformation Map

All column names have been standardized into uniform, lowercased `snake_case` tokens. The exact mapping and transformations are documented below:

| Original Column Name | Standardized Column Name | Target Data Type | Transformation & Extraction Applied |
| :--- | :--- | :--- | :--- |
| `Sr. No.` | `sr_no` | `Integer` | Cast string index to sequential integer; trailer `'Grand Total'` isolated. |
| `State` | `state` | `String` (Categorical) | Stripped leading/trailing whitespace; standard title casing preserved. |
| `Hon'ble Members of Parliaments` | `mp_name` | `String` (Categorical) | Stripped whitespace; preserved official legal name strings. |
| `Constituency` | `constituency` | `String` (Categorical) | Original raw constituency string preserved for direct provenance. |
| *[Derived Feature]* | `constituency_clean` | `String` | Reservation tags `(SC)`/`(ST)` and state tags `_BR`/`_UP` stripped. |
| `Allocated AMOUNT ( ₹ )` | `allocated_amount_inr` | `Float64` (`Numeric`) | Stripped `₹` symbol, comma grouping, and whitespace; parsed to float. |
| *[Derived Flag]* | `is_reserved_sc` | `Boolean` | `True` if constituency name contains `(SC)` reservation tag. |
| *[Derived Flag]* | `is_reserved_st` | `Boolean` | `True` if constituency name contains `(ST)` reservation tag. |
| *[Quality Flag]* | `is_missing_amount` | `Boolean` | `True` if raw amount was blank, `NaN`, or empty. |
| *[Quality Flag]* | `is_invalid_amount` | `Boolean` | `True` if amount failed numerical parsing or was negative. |
| *[Quality Flag]* | `is_duplicate_constituency` | `Boolean` | `True` if constituency name appears > 1 time in dataset. |
| *[Composite Flag]* | `is_data_quality_issue` | `Boolean` | `True` if any data quality or anomaly flag is active. |

---

## 3. Missing-Value Analysis

| Column Name | Missing Count (Raw) | Missing Percentage (%) | Cleaning / Imputation Strategy |
| :--- | :---: | :---: | :--- |
| `sr_no` | 0 | 0.00% | No missing values in data records. |
| `state` | 0* | 0.00% | No missing values in data records (*1 whitespace in Grand Total trailer). |
| `mp_name` | 0* | 0.00% | No missing values in data records (*1 whitespace in Grand Total trailer). |
| `constituency` | 0* | 0.00% | No missing values in data records (*1 whitespace in Grand Total trailer). |
| `allocated_amount_inr` | 1 | 0.18% | **Preserved without synthetic imputation.** Flagged via `is_missing_amount = True`. |

### Specific Ground Truth for the 1 Missing Amount:
- **Record:** Row index 107 (Sr. No. 108): `State: Maharashtra`, `MP: CHAVAN VASANTRAO BALWANTRAO`, `Constituency: NANDED`.
- **Reason:** Shri Chavan Vasantrao Balwantrao was elected in the 2024 General Elections and passed away in August 2024. In the official government ledger, his entry has `NaN` for current allocation limit, while the by-election transition representative (Shri Ravindra Vasantrao Chavan, Row 389) has the allocated limit of ₹14,70,00,000.
- **Handling:** **We did NOT synthesize or fabricate a replacement amount.** The missingness is preserved, set to `0.0`, and explicitly flagged as `is_missing_amount = True` and `is_data_quality_issue = True`.

---

## 4. Duplicate Record Analysis

1. **Exact Duplicate Rows:** **0 exact duplicates** detected across all columns.
2. **Domain Entity Duplicates (Constituencies):**
   - Exactly **1 constituency** (`NANDED`, Maharashtra) appears **2 times** in the dataset:
     - Record 1 (Sr. No. 108): `CHAVAN VASANTRAO BALWANTRAO` (Allocated: `NaN`)
     - Record 2 (Sr. No. 390): `Ravindra Vasantrao Chavan` (Allocated: `₹14,70,00,000.00`)
   - **Handling:** Both records are preserved in the dataset and marked with `is_duplicate_constituency = True`. No records were deleted.

---

## 5. Invalid-Value Analysis

1. **Negative Amounts:** 0 records with negative allocation amounts ($amount < 0$).
2. **Malformed Numbers:** 0 malformed numerical strings among valid data entries.
3. **Invalid Dates:** Not applicable (the macro allocation dataset does not contain date fields).
4. **Summary Trailer Row:** Row 543 contains `'Grand Total'` with aggregate sum `83,33,99,05,622.01`. This row was isolated into metadata rather than deleted or mixed with MP records.

---

## 6. Records Partitioned / Removed Analysis

> [!IMPORTANT]
> **No operational data records were deleted.**
> 
> - **Total Raw Rows:** 544
> - **Operational MP Records in Cleaned Dataset:** 543
> - **Summary Trailer Record Partitioned into Metadata:** 1 (Row 543: `'Grand Total'`)
> 
> **Exact Reason for Partitioning the Grand Total Row:**  
> The `'Grand Total'` row is a table footer containing the cumulative sum of all 543 MP allocations. If left inside the operational data table, it would double the calculated sum to ₹16,667.98 Crore, distort statistical distributions, and skew anomaly detection baselines. It has been preserved inside `data/processed/summary_totals_metadata.json` for reconciliation auditing.

---

## 7. Data Quality Flags Summary

| Data Quality Flag | Description | Active Records Count | Percentage of MP Records (%) |
| :--- | :--- | :---: | :---: |
| `is_missing_amount` | Allocation amount is `NaN` or unrecorded in official export | 1 | 0.18% |
| `is_invalid_amount` | Allocation amount is negative or malformed | 0 | 0.00% |
| `is_duplicate_constituency` | Parliamentary constituency appears more than once | 2 | 0.37% |
| `is_reserved_sc` | Constituency is reserved for Scheduled Castes (SC) | 84 | 15.47% |
| `is_reserved_st` | Constituency is reserved for Scheduled Tribes (ST) | 47 | 8.66% |
| `is_data_quality_issue` | Composite indicator (`is_missing_amount` OR `is_invalid_amount` OR `is_duplicate_constituency`) | 2 | 0.37% |

---

## 8. Capability Matrix Based on Available Data

| Ledger Lens Analytical Capability | Supported by Cleaned Dataset? | Available Supporting Fields | Data Gaps / Limitations |
| :--- | :---: | :--- | :--- |
| **MP & Constituency Budget Benchmarking** | **YES** | `mp_name`, `state`, `constituency`, `allocated_amount_inr` | Fully supported for 18th Lok Sabha representatives. |
| **Financial Outlier / Anomaly Detection** | **YES** | `allocated_amount_inr`, `state` | Isolation Forest, Z-Score, and IQR on allocation limits supported. |
| **State-Level Budget Disparity Analysis** | **YES** | `state`, `allocated_amount_inr` | Regional aggregations and variance mapping supported. |
| **Constituency Reservation Analytics** | **YES** | `is_reserved_sc`, `is_reserved_st`, `constituency_clean` | Disparity audit across reserved vs unreserved seats supported. |
| **Project-Level Delay & Timeline Analysis** | **NO** | *None* | Requires project sanction dates, start dates, completion deadlines. |
| **Payment vs Physical Progress Delta** | **NO** | *None* | Requires installment disbursement records and physical completion (%). |
| **Duplicate / Similar Work NLP** | **NO** | *None* | Requires project titles, scope descriptions, and sanction categories. |
| **Contractor & Implementing Agency Audit** | **NO** | *None* | Requires vendor IDs, contractor names, and billing records. |

---

## 9. Fields Requiring Manual Verification by Officers

1. **`NANDED` (Maharashtra) Duplicate Records:** The two records for Nanded (Sr. No. 108 and Sr. No. 390) reflect a parliamentary seat transition. Monitoring officers should verify that past expenditure under the earlier tenure is properly carried forward to the current representative's ledger.
2. **Allocation Outliers (High/Low Extremes):**
   - High allocations (e.g. Malkajgiri, Telangana: ₹32.75 Cr; Nizamabad, Telangana: ₹28.14 Cr; Bolpur, West Bengal: ₹27.57 Cr) require verification against unspent carry-forward balances from previous terms.
   - Low allocations (e.g. Basirhat, West Bengal: ₹4.90 Cr; Shillong, Meghalaya: ₹9.80 Cr; Nowgong, Assam: ₹9.80 Cr) require desk review for pending tranche releases.
