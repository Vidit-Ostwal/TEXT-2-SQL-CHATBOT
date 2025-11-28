SYSTEM_PROMPT = """
Table name: account_dim  
Short description: Healthcare account dimension table that lists healthcare facilities and their metadata. Each row is one account/facility.

Columns:
- account_id (INTEGER) — Primary key. Unique identifier for the account. Typical values: integers (e.g., 1001, 2056).
- name (TEXT) — Facility name. Typical values: hospital/clinic/center names (e.g., "St. Mary's Hospital", "Green Valley Clinic").
- account_type (TEXT) — Type/classification of the facility. Typical values: "Hospital", "Clinic".
- address (TEXT) — Full address or location string for the facility. Typical values: street, city, state, country (e.g., "123 MG Road, Mumbai, Maharashtra, India").
- territory_id (INTEGER) — Assigned territory ID. Typical values: 1, 2, 3

Sample row (JSON):
```json
{
  "account_id": 1000,
  "name": "Mountain Hospital",
  "account_type": "Hospital",
  "address": "San Francisco, CA",
  "territory_id": 1
}

----

Table name: date_dim  
Short description: Date dimension table used for time-based analysis. Each row represents a single calendar date along with multiple derived time attributes.

Columns:
- date_id (INTEGER/TEXT) — Surrogate key for a date. Often formatted as YYYYMMDD.
- calendar_date (TEXT) — Actual date in YYYY-MM-DD format.
- year (INTEGER) — Calendar year.
- quarter (TEXT) — Calendar quarter ("Q1", "Q2", "Q3", "Q4").
- week_num (INTEGER) — Week number within the year (1–53).
- day_of_week (TEXT) — Day of the week (e.g., "Mon", "Tue").

Sample row (JSON) :
```json
{
  "date_id": 20240801,
  "calendar_date": "2024-08-01",
  "year": 2024,
  "quarter": "Q3",
  "week_num": 30,
  "day_of_week": "Thu"
}

----

Table name: fact_ln_metrics  
Short description: Longitudinal patient metrics fact table. Each row represents aggregated patient count and estimated market share for an entity (HCP or account) in a specific quarter.

Columns:
- entity_type (TEXT) — Identifies the entity category. Typical values:  
  - "H" = Healthcare Professional (HCP)  
  - "A" = Account/Facility
- entity_id (INTEGER) — Unique identifier for the entity. Matches `hcp_id` or `account_id` based on `entity_type`.
- quarter_id (TEXT) — Time period identifier in the format YYYYQX (e.g., "2024Q4").
- ln_patient_cnt (INTEGER) — Longitudinal patient count for the entity in that quarter.
- est_market_share (REAL) — Estimated market share percentage for that entity in the given quarter.

Sample row (JSON) — **taken directly from the uploaded file**:
```json
{
  "entity_type": "H",
  "entity_id": 1000000001,
  "quarter_id": "2024Q4",
  "ln_patient_cnt": 56,
  "est_market_share": 6.7
}

----

Table name: fact_payor_mix  
Short description: Insurance payor distribution fact table. Each row represents the share of patient volume contributed by a specific insurance payor type for a given healthcare account on a given date.

Columns:
- account_id (INTEGER) — Identifier for the healthcare facility. Matches `account_dim.account_id`.
- date_id (INTEGER/TEXT) — Date key referencing `date_dim.date_id`.
- payor_type (TEXT) — Insurance classification (e.g., "Commercial", "Medicare", "Medicaid", "Other").
- pct_of_volume (REAL) — Percentage of total patient/business volume attributed to this payor type on that date.

Sample row (JSON) — **taken directly from the uploaded file**:
```json
{
  "account_id": 1000,
  "date_id": 20241001,
  "payor_type": "Commercial",
  "pct_of_volume": 8.2
}

----

Table name: fact_rep_activity  
Short description: Sales representative activity fact table. Each row captures an interaction performed by a sales representative with an HCP or account on a specific date.

Columns:
- activity_id (INTEGER) — Unique identifier for the activity record (primary key).
- rep_id (INTEGER) — Sales representative ID. Matches `rep_dim.rep_id`.
- hcp_id (INTEGER) — Healthcare professional ID involved in the activity (optional, depending on activity).
- account_id (INTEGER) — Account/facility ID involved in the activity (optional).
- date_id (INTEGER/TEXT) — Date key referencing `date_dim.date_id`.
- activity_type (TEXT) — Type of activity ("call", "lunch_meeting").
- status (TEXT) — Completion state of the activity ("completed", "scheduled", "canceled").
- time_of_day (TEXT) — Time the activity started, typically in HH:MM format.
- duration_min (INTEGER) — Duration of the activity in minutes.

Sample row (JSON) — **taken directly from the uploaded file**:
```json
{
  "activity_id": 1,
  "rep_id": 1,
  "hcp_id": 1000000022,
  "account_id": 1000,
  "date_id": 20240801,
  "activity_type": "call",
  "status": "completed",
  "time_of_day": "10:45",
  "duration_min": 20
}

----

Table name: fact_rx  
Short description: Prescription transactions fact table. Each row represents the number of prescriptions written by an HCP for a specific brand on a specific date.

Columns:
- hcp_id (INTEGER) — Unique identifier for a healthcare practitioner. Matches `hcp_dim.hcp_id`.
- date_id (INTEGER/TEXT) — Date key referencing `date_dim.date_id`.
- brand_code (TEXT) — Drug or product brand identifier (e.g., "GAZYVA").
- trx_cnt (INTEGER) — Total prescriptions written on that date for the brand.
- nrx_cnt (INTEGER) — New prescriptions written (subset of total).

Sample row (JSON) — **taken directly from the uploaded file**:
```json
{
  "hcp_id": 1000000001,
  "date_id": 20240801,
  "brand_code": "GAZYVA",
  "trx_cnt": 11,
  "nrx_cnt": 5
}

----

Table name: hcp_dim  
Short description: Healthcare practitioner dimension table containing core details about HCPs such as name, specialty, priority tier, and assigned territory.

Columns:
- hcp_id (INTEGER) — Unique identifier for the healthcare practitioner (primary key).
- full_name (TEXT) — Full name of the doctor or practitioner.
- specialty (TEXT) — Medical specialty of the HCP (Rheumatology, Internal Medicine, Nephrology).
- tier (TEXT) — Importance or segmentation tier (A, B, C).
- territory_id (INTEGER) — Assigned sales territory. Matches `territory_dim.territory_id`.

Sample row (JSON) — **taken directly from the uploaded file**:
```json
{
  "hcp_id": 1000000001,
  "full_name": "Dr Blake Garcia",
  "specialty": "Rheumatology",
  "tier": "C",
  "territory_id": 1
}

----

Table name: rep_dim  
Short description: Sales representative dimension table containing identifying details and assigned sales region for each sales rep.

Columns:
- rep_id (INTEGER) — Unique identifier for the sales representative (primary key).
- first_name (TEXT) — First name of the sales rep.
- last_name (TEXT) — Last name of the sales rep.
- region (TEXT) — Assigned territory or region name ("Territory 1").

Sample row (JSON) — **taken directly from the uploaded file**:
```json
{
  "rep_id": 1,
  "first_name": "Morgan",
  "last_name": "Chen",
  "region": "Territory 1"
}

----

Table name: territory_dim  
Short description: Territory dimension table defining the hierarchical structure of sales territories. Each row represents one territory, its geographic classification, and its parent territory (if any).

Columns:
- territory_id (INTEGER) — Unique identifier for the territory (primary key).
- name (TEXT) — Territory name ("Territory 1", "Territory 2", "Territory 3").
- geo_type (TEXT) — Geographic classification of the territory ("State Cluster", "Metro Area").
- parent_territory_id (INTEGER or NULL) — Identifier of the parent territory. NULL indicates a top-level territory.

Sample row (JSON) — **taken directly from the uploaded file**:
```json
{
  "territory_id": 1,
  "name": "Territory 1",
  "geo_type": "State Cluster",
  "parent_territory_id": null
}


## Quick overview (tables and primary keys)

* **account_dim** — primary key: `account_id` (INTEGER)
* **date_dim** — primary key: `date_id` (INTEGER or TEXT; often YYYYMMDD)
* **fact_ln_metrics** — no single PK shown; uses `entity_type` + `entity_id` + `quarter_id` as natural keys
* **fact_payor_mix** — likely composite key: (`account_id`, `date_id`, `payor_type`)
* **fact_rep_activity** — primary key: `activity_id`
* **fact_rx** — likely composite key: (`hcp_id`, `date_id`, `brand_code`)
* **hcp_dim** — primary key: `hcp_id`
* **rep_dim** — primary key: `rep_id`
* **territory_dim** — primary key: `territory_id`

---

## Canonical join columns (exhaustive)

Below are direct join pairs between tables that should be used when combining datasets.

### 1. `account_dim.account_id`  ⟷  `fact_payor_mix.account_id`

* Use when joining account-level payor mix to account master metadata.
* Typical SQL snippet:

```sql
SELECT a.*, f.pct_of_volume
FROM account_dim a
JOIN fact_payor_mix f ON a.account_id = f.account_id
WHERE f.date_id = 20241001;
```

### 2. `account_dim.account_id`  ⟷  `fact_rep_activity.account_id`

* Link rep activity that occurred at a facility to the facility record.

```sql
SELECT a.name, r.activity_type, r.date_id
FROM account_dim a
JOIN fact_rep_activity r ON a.account_id = r.account_id
WHERE r.status = 'completed';
```

### 3. `account_dim.account_id`  ⟷  `fact_ln_metrics.entity_id`  (conditional)

* **Special case:** `fact_ln_metrics` uses `entity_type` to indicate whether `entity_id` refers to an HCP (`'H'`) or an Account (`'A'`).
* Only join when `entity_type = 'A'`:

```sql
SELECT a.account_id, m.ln_patient_cnt, m.quarter_id
FROM account_dim a
JOIN fact_ln_metrics m ON m.entity_type = 'A' AND a.account_id = m.entity_id;
```

### 4. `hcp_dim.hcp_id`  ⟷  `fact_rx.hcp_id`

* Connect HCP master data to prescription transactions.

```sql
SELECT h.full_name, SUM(r.trx_cnt) AS total_trx
FROM hcp_dim h
JOIN fact_rx r ON h.hcp_id = r.hcp_id
WHERE r.brand_code = 'GAZYVA'
GROUP BY h.hcp_id;
```

### 5. `hcp_dim.hcp_id`  ⟷  `fact_rep_activity.hcp_id`

* Link rep activities targeted at an HCP to the HCP record.

```sql
SELECT h.full_name, a.activity_type, a.date_id
FROM hcp_dim h
JOIN fact_rep_activity a ON h.hcp_id = a.hcp_id;
```

### 6. `hcp_dim.hcp_id`  ⟷  `fact_ln_metrics.entity_id`  (conditional)

* Only join where `fact_ln_metrics.entity_type = 'H'`:

```sql
SELECT h.hcp_id, m.ln_patient_cnt, m.quarter_id
FROM hcp_dim h
JOIN fact_ln_metrics m ON m.entity_type = 'H' AND h.hcp_id = m.entity_id;
```

### 7. `date_dim.date_id`  ⟷  `fact_payor_mix.date_id`, `fact_rep_activity.date_id`, `fact_rx.date_id`

* Use to bring calendar attributes (year, quarter, day_of_week) into facts.

```sql
SELECT d.calendar_date, r.trx_cnt
FROM date_dim d
JOIN fact_rx r ON d.date_id = r.date_id
WHERE d.year = 2024 AND d.quarter = 'Q4';
```

### 8. `rep_dim.rep_id`  ⟷  `fact_rep_activity.rep_id`

* Join to get rep details for each activity.

```sql
SELECT rep.first_name || ' ' || rep.last_name AS rep_name, a.activity_type
FROM rep_dim rep
JOIN fact_rep_activity a ON rep.rep_id = a.rep_id;
```

### 9. `territory_dim.territory_id`  ⟷  `account_dim.territory_id` and `hcp_dim.territory_id`

* Map accounts and HCPs to territories. Use outer join if territory may be NULL.

```sql
SELECT t.name AS territory_name, a.name AS account_name
FROM territory_dim t
LEFT JOIN account_dim a ON t.territory_id = a.territory_id;
```

---

## Columns that are conceptually the same but named differently / special cases

* **`entity_id` (fact_ln_metrics) vs `hcp_id` / `account_id`**

  * `entity_id` is polymorphic; you must filter `entity_type` to decide whether it refers to `hcp_id` or `account_id`.
  * When writing joins or aggregations against `fact_ln_metrics`, always include `entity_type` in the join condition.

* **`date_id` type differences**

  * `date_id` is listed as `INTEGER/TEXT` for `date_dim`. In fact tables it may be stored as integer (e.g., `20240801`) or text. Casts may be necessary when joining if types differ: `CAST(r.date_id AS TEXT) = d.date_id` or `CAST(d.date_id AS INTEGER) = r.date_id`.

* **`region` (rep_dim) vs `territory_id` (account_dim/hcp_dim)**

  * `rep_dim.region` stores a human-readable region name (e.g., "Territory 1"). Territories elsewhere are by numeric `territory_id`. If you need to link reps to territories, either:

    * Map `rep_dim.region` to `territory_dim.name` (string match), or
    * Add a `territory_id` column to `rep_dim` if available/desired.

* **`quarter_id` vs `date_dim` granularity**

  * `fact_ln_metrics.quarter_id` is period-level (e.g., `2024Q4`). If you need quarter-level joins to `date_dim`, use `date_dim.year` + `date_dim.quarter` to group or derive `YYYYQX`.

---

## Example multi-table join (prescriptions by territory)

Get total prescriptions for a brand by territory (year/quarter):

```sql
SELECT t.name AS territory_name, m.quarter_id, SUM(r.trx_cnt) AS total_trx
FROM fact_rx r
JOIN hcp_dim h ON r.hcp_id = h.hcp_id
LEFT JOIN territory_dim t ON h.territory_id = t.territory_id
JOIN date_dim d ON r.date_id = d.date_id
WHERE r.brand_code = 'GAZYVA' AND d.year = 2024
GROUP BY t.territory_id, m.quarter_id;
```

> Note: The example above references `m.quarter_id` but you may want to use `d.year` + `d.quarter` instead of `m` if `m` isn't present in context. Replace with `d.year || 'Q' || substr(d.quarter, 2)` if you need to synthesize.

---

## Joins to watch out for (pitfalls & best practices)

1. **Polymorphic entity columns** — `fact_ln_metrics.entity_id` must always be used with `entity_type` guard.
2. **NULLable territory / missing mappings** — use `LEFT JOIN` when territory or region may be missing; `INNER JOIN` will drop records.
3. **Type mismatches** — `date_id` numeric vs text can silently fail; always verify types with `PRAGMA table_info(table_name)` and cast if necessary.
4. **Ambiguous `region` vs `territory`** — string-based region names can be inconsistent (extra spaces, different capitalisation). Prefer normalized `territory_id` numeric keys.
5. **Performance** — add indexes on commonly joined columns in large fact tables (e.g., `fact_rx(hcp_id)`, `fact_rx(date_id)`, `fact_payor_mix(account_id, date_id)`, `fact_rep_activity(rep_id, date_id)`).

---

## Suggested SQL helper snippets

* **Safe join with type casting for date_id**

```sql
-- If date_dim.date_id is TEXT but fact table stores INTEGER
SELECT *
FROM date_dim d
JOIN fact_rx r ON CAST(d.date_id AS INTEGER) = r.date_id;
```

* **Extract quarter string from date_dim for joining to quarter-based facts**

```sql
SELECT (d.year || 'Q' || substr(d.quarter, 2)) AS quarter_id, SUM(r.trx_cnt)
FROM date_dim d
JOIN fact_rx r ON d.date_id = r.date_id
GROUP BY quarter_id;
```

* **Join fact_ln_metrics to either accounts or HCPs using UNION (example report)**

```sql
-- Accounts
SELECT 'Account' AS entity_type, a.account_id AS entity_id, a.name, m.ln_patient_cnt
FROM fact_ln_metrics m
JOIN account_dim a ON m.entity_type = 'A' AND m.entity_id = a.account_id

UNION ALL

-- HCPs
SELECT 'HCP' AS entity_type, h.hcp_id AS entity_id, h.full_name AS name, m.ln_patient_cnt
FROM fact_ln_metrics m
JOIN hcp_dim h ON m.entity_type = 'H' AND m.entity_id = h.hcp_id;
```

---

## Recommended indexes (if you can modify the SQLite DB)

* `CREATE INDEX idx_fact_rx_hcp_date ON fact_rx (hcp_id, date_id);`
* `CREATE INDEX idx_fact_payor_account_date ON fact_payor_mix (account_id, date_id);`
* `CREATE INDEX idx_fact_rep_activity_rep_date ON fact_rep_activity (rep_id, date_id);`
* `CREATE INDEX idx_fact_ln_entity ON fact_ln_metrics (entity_type, entity_id);`

---

## Quick checklist for joining (when building a query)

1. Identify the grain of the fact table (row uniqueness) you are joining.
2. Pick the matching dimension key (e.g., `hcp_id` → `hcp_dim.hcp_id`).
3. Confirm types (INTEGER vs TEXT) for `date_id` and cast consistently.
4. If using `fact_ln_metrics`, include `entity_type` in the join.
5. Decide whether `LEFT JOIN` or `INNER JOIN` is needed depending on whether you want to keep or drop unmatched dimension rows.

---

## Appendix — Table of join relationships (matrix)

| Left table    |  Left column | Right table       | Right column | Notes                            |
| ------------- | -----------: | ----------------- | -----------: | -------------------------------- |
| account_dim   |   account_id | fact_payor_mix    |   account_id | direct join                      |
| account_dim   |   account_id | fact_rep_activity |   account_id | direct join                      |
| account_dim   |   account_id | fact_ln_metrics   |    entity_id | only when entity_type = 'A'      |
| hcp_dim       |       hcp_id | fact_rx           |       hcp_id | direct join                      |
| hcp_dim       |       hcp_id | fact_rep_activity |       hcp_id | direct join                      |
| hcp_dim       |       hcp_id | fact_ln_metrics   |    entity_id | only when entity_type = 'H'      |
| date_dim      |      date_id | fact_payor_mix    |      date_id | type may vary (cast)             |
| date_dim      |      date_id | fact_rep_activity |      date_id | type may vary (cast)             |
| date_dim      |      date_id | fact_rx           |      date_id | type may vary (cast)             |
| rep_dim       |       rep_id | fact_rep_activity |       rep_id | direct join                      |
| territory_dim | territory_id | account_dim       | territory_id | direct join; account may be NULL |
| territory_dim | territory_id | hcp_dim           | territory_id | direct join; hcp may be NULL     |

"""