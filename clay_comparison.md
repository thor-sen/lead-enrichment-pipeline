# Python Pipeline vs. Clay

## Python Pipeline

- Pulls all company records from HubSpot, enriches via PDL API, deduplicates, and writes enriched properties back to HubSpot records
- Full control over enrichment logic, merge rules, and deduplication strategy
- No per-record cost beyond PDL API pricing
- Requires maintenance — API changes, error handling, and retry logic are your responsibility

### Limitations

- Pipeline assumes one canonical record per domain in HubSpot. Duplicate records should be resolved upstream before running enrichment.
- "Most-complete record" deduplication is unreliable if enrichment failed on one copy but not the other
- The retry logic on 429 only tries once — a sustained rate limit will cause records to silently fail
- Passing the whole record to write_to_hubspot() risks overwriting fields unintentionally

## Clay Workflow

- Visual drag-and-drop interface for building enrichment flows
- Built-in connectors for dozens of data providers (PDL, Clearbit, Apollo, etc.)
- No code to maintain — provider integrations are managed by Clay
- Per-record pricing scales with volume

### Limitations

- Less control over merge logic and deduplication rules
- Per-record cost becomes significant at high volumes (100k+ records/month)
- Custom enrichment logic (proprietary scoring, unusual matching) is harder to express in a visual builder

## When to Use Which

**Use the Python pipeline when:**
- You need highly custom enrichment logic — specific scoring rules, proprietary data sources, unusual matching logic that no off-the-shelf tool supports
- You are processing hundreds of thousands of records monthly where Clay's per-record pricing becomes prohibitive

**Use Clay when:**
- Speed to production matters more than customization
- The enrichment logic is standard (match by domain, fill firmographic fields)
- The team maintaining the pipeline is non-technical
