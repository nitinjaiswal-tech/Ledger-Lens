# Ledger Lens — Development Roadmap
**Problem Statement:** SIH26102 — Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation.  
**Platform:** Ledger Lens (AI-Powered MPLADS Risk Intelligence & Monitoring Platform)  

---

## Strategic Phasing Overview

```text
Phase 1: Foundation & Data Audit  ──►  Phase 2: Financial & Delay Anomaly Detection
                                                     │
                                                     ▼
Phase 4: FastAPI & PostgreSQL     ◄──  Phase 3: NLP Similarity & Risk Scoring Engine
        │
        ▼
Phase 5: Next.js Officer Dashboard ──►  Phase 6: OCR, Evidence Timeline & Notifications
```

---

## Phase Breakdown

### PHASE 1: Dataset Understanding, Data Cleaning & Validation
*Objective: Establish ground truth, audit schemas, and build resilient data ingestion pipelines.*

- [x] **Raw Data Inspection & Discovery**: Audit official MPLADS/eSAKSHI data in `data/raw/`.
- [x] **Exploratory Data Analysis Notebook**: Deliver `notebooks/01_data_understanding.ipynb` covering schema, distributions, and nulls.
- [x] **Data Dictionary**: Deliver `docs/DATA_DICTIONARY.md` detailing column roles, types, and domain utility.
- [ ] **Data Cleaning Pipeline**:
  - Implement automated parsing for Indian currency formatting and Unicode symbols (`₹`).
  - Strip summary trailer records (`'Grand Total'`).
  - Normalize text casing, state codes, and constituency strings.
- [ ] **Data Validation Module**:
  - Pydantic v2 data models for rigorous schema enforcement and provenance tracking.
  - Verification test suite for data integrity.

---

### PHASE 2: Financial Anomaly Detection, Delay & Progress Analysis
*Objective: Implement core statistical and machine learning anomaly detection sub-engines.*

- [ ] **Financial Anomaly Detection Engine**:
  - Implement unsupervised **Isolation Forest** on allocation and expenditure parameters.
  - Implement statistical Z-score / IQR bounds to identify extreme deviations.
  - State-level baseline distribution modeling for relative allocation benchmarks.
- [ ] **Timeline & Delay Detection**:
  - Calculation of sanction-to-work order latency and execution duration.
  - Delay hazard scoring for stalled projects based on historical completion baselines.
- [ ] **Progress Analysis & Velocity Tracking**:
  - Milestone velocity and burn-rate tracking across project categories.
- [ ] **Payment–Progress Consistency Engine**:
  - Compute financial disbursement vs physical execution delta ($Delta = \% \text{Disbursed} - \% \text{Completed}$).
  - Flag severe front-loading or premature fund releases.

---

### PHASE 3: NLP Similarity Detection, Compliance Checks & Risk Scoring
*Objective: Build intelligent text deduplication, rule compliance verification, and composite scoring.*

- [ ] **Similar Work Detection using NLP**:
  - Implement **Sentence Transformers** (`all-MiniLM-L6-v2`) to generate semantic embeddings of work titles and descriptions.
  - Implement Cosine Similarity thresholding combined with geographic proximity to detect duplicate/overlapping works.
- [ ] **Rule-Based Compliance Engine**:
  - Codify official MPLADS statutory guidelines (spending limits, non-permissible items, trust/society caps).
  - Deterministic compliance rule checks with actionable violation tags.
- [ ] **Composite Risk Scoring Engine**:
  - Multi-factor risk aggregation algorithm combining financial, timeline, progress, similarity, and compliance signals.
  - Normalized risk scoring scale ($0 - 100$) with calibrated severity tiers (`LOW`, `MEDIUM`, `HIGH`).

---

### PHASE 4: Explainable Alerts, FastAPI Backend & PostgreSQL Integration
*Objective: Build high-performance backend infrastructure with explainable AI outputs.*

- [ ] **PostgreSQL Database Schema & ORM**:
  - Design normalized database schema in SQLAlchemy 2.0.
  - Create tables for States, Constituencies, MPs, Projects, Milestones, Risk Signals, and Officer Reviews.
  - Database migration workflows with Alembic.
- [ ] **Explainable AI (XAI) & Evidence Generation**:
  - Generate structured, natural-language explanation cards ("Why Was It Flagged?").
  - Provide specific metric deltas and contributing factor weights.
- [ ] **FastAPI Backend Services**:
  - Build RESTful endpoints for national summaries, MP profiles, project queries, risk breakdowns, and review submissions.
  - Implement query filtering, pagination, and caching.
  - Automated API documentation via OpenAPI/Swagger.

---

### PHASE 5: Next.js Officer Dashboard & Verification Workflow
*Objective: Deliver a high-impact, modern web application for monitoring officers.*

- [ ] **Next.js & Tailwind Dashboard Foundation**:
  - Modern, responsive design system with dark/light theme support and rich visual hierarchy.
  - Executive Overview with key risk indicators, allocation distributions, and anomaly counts.
- [ ] **Project Detail & Risk Explorer**:
  - Interactive project detail pages with dynamic risk gauge, metric breakdowns, and milestone progression.
  - Triage Inbox enabling officers to filter by risk tier, state, and category.
- [ ] **Interactive Risk Map**:
  - Leaflet-based geospatial visualization for State and Lok Sabha Constituency risk clusters.
- [ ] **Human Verification & Decision Workflow**:
  - Officer case review interface with status actions:
    - `Verified` (Valid risk requiring follow-up)
    - `False Signal` (Legitimate variance explained by context)
    - `Action Required` (Immediate physical inspection / audit required)
    - `Resolved` (Corrective action documented and closed)
  - Audit trail recording officer notes, timestamps, and resolution history.

---

### PHASE 6: Advanced Intelligence, Document OCR & Notifications
*Objective: Advanced capabilities for multimodal evidence analysis and proactive monitoring.*

- [ ] **Evidence Timeline Visualizer**:
  - Interactive visual chronology of project events, sanctions, payment installments, and flagged anomalies.
- [ ] **Investigation Assistant**:
  - AI-assisted case dossier builder summarizing key risk factors for field inspection teams.
- [ ] **OCR & Document Intelligence**:
  - Automated extraction of sanction letters, utilization certificates, and contractor invoices using OCR.
  - Cross-verification of invoice amounts against recorded digital ledger entries.
- [ ] **Image-Based Evidence Analysis**:
  - Computer vision verification for geotagged site inspection photos to validate physical progress against claims.
- [ ] **Notification & Alert Dispatch System**:
  - Automated email/webhook notifications to district authorities when critical risk thresholds are breached.
