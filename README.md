# Lead Enrichment Pipeline

Pulls company records from HubSpot, enriches them with firmographic data from People Data Labs (PDL), deduplicates by domain, writes enriched properties back to HubSpot, and saves the full dataset as JSON for downstream ML scoring. The HubSpot pull and write-back are fully functional. PDL enrichment is fully implemented but requires a valid API key to return results.

## Tech Stack

- **Language:** Python
- **Libraries:** requests, python-dotenv
- **APIs:** HubSpot CRM v3 (companies), People Data Labs Company Enrichment v5

## How It Fits Into the GTM System

This pipeline sits between the CRM data connector (which pulls raw records) and the ML lead scoring model. It adds firmographic fields — employee count, revenue range, industry vertical, tech stack — that the scoring model uses as input features. Enrichment is what makes ML scoring meaningful — without employee count, revenue range, and tech stack, the lead scoring model is working with incomplete signals.

## Key Design Decisions

**I built the full PDL integration even without a funded key.** The enrichment function makes live calls to PDL's company enrichment endpoint with proper auth, error handling, and write-back to HubSpot. Without a valid key, companies get marked `enrichment_status: failed` and the pipeline moves on. The HubSpot pull and write-back logic run independently of PDL. That's deliberate. Someone could drop in a funded key and the pipeline would enrich 204 real companies immediately. No code changes required.

**HubSpot is the source of truth. PDL fills gaps.** When HubSpot and PDL both have a value for a field (company size, industry, revenue), HubSpot wins. The logic is simple: if HubSpot has a value, keep it. If HubSpot has null, write PDL's value. This prevents a third-party API from overwriting rep-maintained CRM data. Reps trust what they see in HubSpot, so PDL has to supplement rather than replace.

**Deduplication happens before write-back, not during fetch.** I pull the full enrichment batch first, deduplicate against HubSpot records, then write back. If enrichment fails mid-batch, no partial write. The alternative (write as you go) is faster but leaves the CRM in an inconsistent state if the job crashes. I'd rather re-run the whole pipeline than clean up half-written data.

## Architecture Overview

The pipeline runs as a single sequential pass through seven steps:

- **`fetch_all_records()`** — Pulls all company records from HubSpot with automatic pagination. Requests specific properties (domain, name, employee_count, etc.) to limit payload size.
- **`enrich_company(domain)`** — Calls PDL's company enrichment endpoint using the company domain. Extracts firmographic fields from the response and returns a standardized dict. Returns None on 404 (company not found).
- **`merge_company_data(hubspot_record, pdl_data)`** — Combines HubSpot and PDL data into a single record. PDL fills empty fields only. Sets `enrichment_status` to "enriched" or "failed" and stamps `enrichment_date`.
- **`deduplicate_companies(enriched_results)`** — Groups records by domain, scores each by count of non-null values, keeps the most complete record per domain.
- **`write_to_hubspot(company_id, enriched_fields, headers)`** — PATCHes each company record back to HubSpot. Handles 429 rate limits with a single 60-second retry. Sleeps 0.1s between calls.
- **`save_to_json(data, filename)`** — Writes the final deduplicated dataset to JSON for the ML scoring pipeline.
- **`run_pipeline()`** — Orchestrates all steps in sequence. Wraps enrichment calls in try/except so a single failure logs and continues rather than crashing the run.

## Sample Output

```json
{
  "name": "Baptist Health",
  "domain": "baptisthealth.com",
  "hs_object_id": "12345678",
  "employee_count": 5200,
  "estimated_revenue_range": "$500M-$1B",
  "industry_vertical": "healthcare",
  "linkedin_url": "https://linkedin.com/company/baptist-health",
  "tech_stack": "Cerner,Epic,Salesforce",
  "enrichment_status": "enriched",
  "enrichment_date": "2026-04-08"
}
```

When PDL enrichment fails (no valid key or company not found):

```json
{
  "name": "Baptist Health",
  "domain": "baptisthealth.com",
  "hs_object_id": "12345678",
  "employee_count": null,
  "estimated_revenue_range": null,
  "industry_vertical": null,
  "enrichment_status": "failed"
}
```

## How to Run

**1. Install dependencies:**

```bash
pip install -r requirements.txt
```

**2. Create a `.env` file:**

```
HUBSPOT_API_KEY=pat-na1-your-token-here
PDL_API_KEY=your-pdl-key-here
```

Your HubSpot Private App needs `crm.objects.companies.read` and `crm.objects.companies.write` scopes.

**3. Run the pipeline:**

```bash
python enrichment_pipeline.py
```

Output is saved to `dedup_enrich_hubspot_companies.json`.

## Limitations

PDL enrichment requires a valid PDL API key. The enrichment pipeline is fully implemented — `enrich_company()` makes live API calls to PDL's company enrichment endpoint and writes results back to HubSpot. Without a valid key, enrichment calls return 401 and companies are marked `enrichment_status: failed`. The HubSpot data pull and write-back logic runs independently of PDL.

## Documentation

For the enriched lead data contract (field definitions, types, and sources), see [enriched_lead_contract.md](enriched_lead_contract.md).

For a comparison of this pipeline vs. Clay as an enrichment tool, see [clay_comparison.md](clay_comparison.md).

## Planned Extensions

- Add retry logic with exponential backoff for sustained rate limits (current 429 handling only retries once)
- Filter write-back fields to avoid overwriting unintended HubSpot properties
- Implement contact-to-company mapping by domain (Step 5 is outlined but not built)
- Add support for additional enrichment providers as fallback when PDL returns no match
- Add incremental enrichment mode that skips companies already marked as enriched
