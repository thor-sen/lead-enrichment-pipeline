# Enriched Lead Data Contract
## Version: 1.0
## Date: 3.2.2026

## Enrichment Properties (written by lead-enrichment-pipeline)
| Property | Type | Source | Required |
|----------|------|--------|----------|
| employee_count | Number | PDL | Yes |
| estimated_revenue_range | Text | PDL | Yes |
| industry_vertical | Text | PDL | Yes |
| linkedin_url | Text | PDL | No |
| tech_stack | Text | PDL | No |
| enrichment_status | Text | Pipeline | Yes |
| enrichment_date | Date | Pipeline | Yes |

## Scoring Properties (written by gtm-intelligence-dashboard)
| Property | Type | Source | Required |
|----------|------|--------|----------|
| firmographic_score | Number | ML Lead Scoring | Yes |
| engagement_score | Number | HubSpot activity | Yes |
| pain_signal_score | Number | Pain Signal Detection | Yes |
| composite_score | Number | gtm-intelligence-dashboard | Yes |
| pain_signal_flag | Checkbox | Pain Signal Detection | Yes |
| pain_signal_type | Text | Pain Signal Detection | No |
| score_date | Date | gtm-intelligence-dashboard | Yes |
| priority_tier | Text | gtm-intelligence-dashboard | Yes |

## Composite Score Formula
composite_score = (firmographic_score * 0.50) + (engagement_score * 0.25) + (pain_signal_score * 0.25)

## Score Behavior
- Cold prospect (no HubSpot activity): max score = 75 (firmographic + pain signal only)
- Active outreach prospect: max score = 100 (all three components)
- Engagement score = 0 for companies with no HubSpot activity (neutral, not negative)

## Priority Tiers
- Tier 1: composite_score >= 75
- Tier 2: composite_score >= 50
- Tier 3: composite_score < 50

##Values for enrichment status are 
- "enriched"
- "failed"

## Limitations
- Pipeline assumes one canonical record per domain in HubSpot. Duplicate HubSpot records should be resolved upstream before running enrichment.
- Most-complete isn't reliable if enrichment failed as rule for record deduplication