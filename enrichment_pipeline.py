import os
import json
import requests
from dotenv import load_dotenv
import datetime
import time


load_dotenv()
PDL_API_KEY = os.getenv("PDL_API_KEY")
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")

if not HUBSPOT_API_KEY:
    raise ValueError("Missing HUBSPOT_API_KEY in .env file")

headers = {
    "Authorization": f"Bearer {HUBSPOT_API_KEY}",
    "Content-Type": "application/json"
}


def fetch_all_records(object_type, headers, properties=None):
    """
    Fetch all records of a given type from HubSpot using pagination.
    """
    base_url = f"https://api.hubapi.com/crm/v3/objects/{object_type}"
    all_records = []
    next_token = None
    page_number = 1

    while True:
        if next_token:
            url = f"{base_url}?after={next_token}"
        else:
            url = base_url

        try:
            property_string = ",".join(properties) if properties else None
            params = {"properties": property_string}

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 401:
                raise ValueError("Invalid API credentials - check your API key")

            if response.status_code == 429:
                print(f"Rate limited on {object_type}. Stopping pagination.")
                break

            if response.status_code != 200:
                print(f"API error {response.status_code} for {object_type}")
                break

            data = response.json()

        except requests.exceptions.Timeout:
            print(f"Timeout on {object_type} page {page_number}")
            break
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching {object_type}: {e}")
            break
        except ValueError as e:
            print(f"JSON parsing error for {object_type}: {e}")
            break

        results = data.get("results", [])

        if not results:
            print(f"No results found for {object_type} page {page_number}")
            break

        all_records.extend(results)
        print(f"Fetching {object_type} - Page {page_number}: Got {len(results)} records. Total: {len(all_records)}")

        paging = data.get("paging", {})
        next_info = paging.get("next", {})

        if next_info and "after" in next_info:
            next_token = next_info["after"]
            page_number += 1
        else:
            break

    return all_records


def save_to_json(data, filename):
    """
    Save data to JSON file with error handling.
    """
    try:
        with open(filename, 'w') as file:
            json.dump(data, file, indent=2)
    except OSError as e:
        print(f"Failed to save {filename}: {e}")
        print("Check disk space and file permissions")
        return
    except TypeError as e:
        print(f"Data serialization error: {e}")
        print("Data contains non-JSON-serializable types")
        return

    print(f"Saved {len(data)} records to {filename}")


# enrichment_pipeline.py

# STEP 1: Load companies from HubSpot
# - Pull all companies via API
# - Store as list of dictionaries

def load_hubspot_companies():
    return fetch_all_records("companies", headers, properties = ['domain', 'name', 'hs_object_id', 'employee_count', 'estimated_revenue_range',
    'industry_vertical', 'linkedin_url', 'tech_stack'] )


# STEP 2: Enrich each company via PDL
# - Call PDL Company Enrichment API with domain
# - Return firmographic fields
# - Handle API errors and missing records


def enrich_company(domain):
   
    params = {
    "website": domain,
    "api_key": PDL_API_KEY
}
    url = "https://api.peopledatalabs.com/v5/company/enrich"
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"Enriched company: {domain}")
     
        tech_stack = ",".join(data.get('tech_stack'))if data.get('tech_stack') else None

        company_enrich_data = {'name': data.get('name'),
        'domain': domain,
        'estimated_revenue_range': data.get('estimated_revenue_range'),
        'employee_count': data.get('employee_count'),
        'industry_vertical': data.get('industry_vertical'),
        'linkedin_url': data.get('linkedin_url'),
        'tech_stack': tech_stack}
       
        return company_enrich_data

    elif response.status_code == 401:
        raise ValueError("Invalid API key")
    
    elif response.status_code == 404: return None

    else:
        raise ValueError(f"Unexpected status code: {response.status_code}")
        


# STEP 3: Merge HubSpot data with PDL data
# - Combine into one enriched record per company
# - Handle fields that exist in one source but not the other

def merge_company_data(hubspot_record, pdl_data):
    if pdl_data is None:
        hubspot_record["enrichment_status"] = "failed"
        return hubspot_record
    
    for field, value in pdl_data.items():
        if hubspot_record.get(field) is None:
            hubspot_record[field] = pdl_data[field]
            
    
    hubspot_record["enrichment_status"] = "enriched"
    hubspot_record["enrichment_date"] = datetime.date.today().isoformat()
    return hubspot_record
                #modify enrichment status and date fields

                


def run_pipeline():
    # call load_hubspot_companies
    hubspot_companies = load_hubspot_companies()
    # create empty list for enriched results
    enriched_results = []
    # loop through companies
    for record in hubspot_companies: 
         # get domain
        domain = record.get('domain')
        # guard clause for missing domain
        if not domain:
            continue
       
        # call enrich_company
        try:
            enriched_data = enrich_company(domain)
        except requests.exceptions.RequestException as e:
            print(f"Network error enriching {domain}: {e}")
            enriched_data = None
        except ValueError as e:
            print(f"API error enriching {domain}: {e}")
            enriched_data = None

        # call merge_company_data
        merged_data = merge_company_data(record, enriched_data)
        # append to enriched results list
        enriched_results.append(merged_data)

    deduplicated_enriched = deduplicate_companies(enriched_results)
    for record in deduplicated_enriched:
       
        write_to_hubspot(record.get('hubspot_object_id'), record, headers)
        time.sleep(0.1)

    save_to_json(deduplicated_enriched, 'dedup_enrich_hubspot_companies.json')
    
    return deduplicated_enriched

    # return enriched results    
    


# STEP 4: Deduplicate
# - Identify duplicate companies by domain
# - Keep most complete record


def deduplicate_companies(enriched_results):
    best_record_per_domain = {}
    for record in enriched_results:
        domain = record.get('domain')
        if not domain:
            continue
        if domain not in best_record_per_domain:
            best_record_per_domain[domain] = record
        else:
            new_score = len([v for v in record.values() if v is not None])
            existing_score = len([v for v in best_record_per_domain[domain].values() if v is not None])
            if new_score > existing_score:
                best_record_per_domain[domain] = record
    
    return list(best_record_per_domain.values())



# STEP 5: Map contacts to companies
# - Pull contacts from HubSpot
# - Match to enriched companies by domain or company name
# - Flag unmatched contacts

# STEP 6: Write enriched properties back to HubSpot
# - PATCH request per company
# - Rate limit between calls
# - Log results

def write_to_hubspot(company_id, enriched_fields, headers):
    url = f"https://api.hubapi.com/crm/v3/objects/companies/{company_id}"
    body = {"properties": enriched_fields}
    response = requests.patch(url, headers=headers, json=body)
    
    if response.status_code == 200:
        print(f'Successfully patched {company_id}')
        # success
    elif response.status_code == 404:
        print(f'404 error on {company_id}, moving on')
        # log and move on
    elif response.status_code == 429:
        # sleep and retry once
        time.sleep(60)
        response = requests.patch(url, headers=headers, json=body)
        print(f'Second 429 error')
    else:
        print(f"Unexpected error {response.status_code} for {company_id}")
        # log unexpected error




# STEP 7: Save full enriched dataset to JSON
# - For use in ML lead scoring pipeline


if __name__ == "__main__":
    run_pipeline()
