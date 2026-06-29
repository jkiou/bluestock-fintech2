# Sprint 1 Retrospective - Nifty 100 Financial Intelligence Platform

## Sprint Overview
* **Theme**: Data Foundation & Database Scaffold
* **Duration**: Days 1 to 7 (Sprint 1)
* **Goal**: Establish a unified, production-grade SQLite relational database (`nifty100.db`) containing cleaned, normalized, and validated fundamental and supplementary financial data for 92 Nifty 100 companies.

---

## Achievements & Key Metrics
- **All 12 datasets ingested successfully**: We loaded the 7 core Excel files and 5 supplementary Excel files.
- **Relational Integrity Verified**: Designed a robust schema with strict primary/foreign key connections and unique indexes. Run-time checks verified **0 Foreign Key violations** (`PRAGMA foreign_key_check` returned 0 rows).
- **Data Quality & Validation**: Successfully filtered out duplicate records and invalid inputs (such as orphan company records or non-annual TTM records) without breaking the ingest pipeline.
- **Audit Logs Generated**: Audited every table load with a persistent log in `load_audit.csv`.

### Final Ingest Rowcounts (Parity Check)
| Table Name | Original Excel Rows | Loaded Database Rows | Rejected (Dups/Validation) | Notes |
| :--- | :---: | :---: | :---: | :--- |
| `companies` | 92 | 92 | 0 | Master reference table. |
| `profitandloss` | 1,276 | 1,070 | 206 | Filtered out non-annual TTM and orphan records. |
| `balancesheet` | 1,312 | 1,140 | 172 | Cleaned out orphan rows. |
| `cashflow` | 1,187 | 1,056 | 131 | Cleaned out orphan rows. |
| `analysis` | 20 | 4 | 16 | Kept only matching companies with active ref data. |
| `documents` | 1,585 | 1,456 | 129 | Normalized calendar years and dropped orphans. |
| `prosandcons` | 16 | 14 | 2 | Cleaned out orphans. |
| `sectors` | 92 | 92 | 0 | Macro and sub-sector mappings. |
| `stock_prices` | 5,520 | 5,520 | 0 | Monthly historical pricing data. |
| `market_cap` | 552 | 552 | 0 | Valuation multiples and annual market caps. |
| `financial_ratios`| 1,184 | 1,041 | 143 | Cleaned out duplicate and orphan records. |
| `peer_groups` | 56 | 56 | 0 | 11 peer group benchmark mappings. |

---

## Data Quality Spot Checks & Parity Results
We ran database validation spot checks on 5 random companies (`TCS`, `RELIANCE`, `INFY`, `HDFCBANK`, `ABB`). Parity results:
1. **Master Company Ref**: Successfully normalized and strip-cleaned company names (e.g. removed embedded newlines like `\n` in `Reliance Industries Ltd`). Face values matched perfectly (e.g. ₹1 for TCS, ₹10 for RELIANCE, ₹5 for INFY, ₹1 for HDFCBANK, ₹10 for ABB).
2. **P&L Metrics**: Matched historical fiscal year sales and net profit figures exactly with original Excel files (excluding invalid TTM items). For instance, in FY24 `TCS` sales read ₹240,893 Crore and profit read ₹46,099 Crore in both database and source files.

---

## What Went Well
- **Parallel URL Checking**: The `DataValidator` handles URL accessibility checks efficiently.
- **SQLite FK Enforcement**: Standardized on transactional SQLite database schema mapping, which will simplify downstream KPI computations in Sprint 2.
- **Pipeline Cleanliness**: Non-annual rows (e.g. TTM) were cleanly separated from annual data arrays without hardcoded scripts.

## Room for Improvement
- **Data Quality Alerts**: Source files contain some missing values (e.g. TVSMOTOR missing face value, several banks missing operating profit/OPM metrics). We relaxed SQLite schema constraints to nullable `REAL` fields to prevent pipeline load failure while tracking these in the validator log.
- **Peer Group Coverage**: Note that only 46 out of 92 companies are currently assigned to peer groups. The peer analytics module in Sprint 3 must handle missing peer group data gracefully.
