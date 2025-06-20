# invoice_manager.py
import requests
import os
import json

# Ensure get_access_token and any other shared Zoho API utils are available
# from zoho_api import get_access_token # Assuming it's imported or defined here

# Placeholder for get_access_token if it's not managed in zoho_api.py
# In your actual project, ensure get_access_token is correctly imported or defined.
# For example:
# def get_access_token():
#    # Your existing logic to get Zoho access token
#    return "YOUR_ZOHO_ACCESS_TOKEN"

def create_invoice(customer_id: str, selected_items: list, access_token: str, city_cf: str, code_cf: str, vehicle_cf: str, final_total_amount: float = None):
    """
    Creates an invoice in Zoho Invoice.

    Args:
        customer_id: The Zoho customer ID.
        selected_items: A list of dictionaries, each with 'item_id', 'quantity', and 'rate'.
                        Example: [{'item_id': '...', 'quantity': 2, 'rate': 100.50}]
        access_token: Zoho API access token.
        city_cf: Value for the 'City' custom field. (Note: This is still passed but won't be used in payload if custom_fields removed)
        code_cf: Value for the 'Code' custom field. (Note: This is still passed but won't be used in payload if custom_fields removed)
        vehicle_cf: Value for the 'Vehicle No' custom field. (Note: This is still passed but won't be used in payload if custom_fields removed)
        final_total_amount: The final total amount to set for the invoice. Used to ensure
                            the invoice total matches the adjusted amount if applicable.

    Returns:
        The invoice ID if successful, None otherwise.
    """
    zoho_api_base_url = os.getenv('API_BASE_URL', 'https://www.zohoapis.in/invoice/v3')
    zoho_org_id = os.getenv("ZOHO_ORG_ID")

    invoice_url = f"{zoho_api_base_url}/invoices"

    line_items_payload = []
    for item in selected_items:
        line_item = {
            "item_id": item['item_id'],
            "quantity": item['quantity'],
            "rate": item['rate'] # <--- CRITICAL: Use the rate from selected_items (which contains the adjusted rate)
        }
        line_items_payload.append(line_item)

    payload = {
        "customer_id": customer_id,
        "line_items": line_items_payload,
        # Removed custom_fields section as per error: "A custom field with the label City doesnot exist."
        # If you later create these custom fields in Zoho, you can re-add this section
        # with the exact labels from your Zoho account.
        "custom_fields": [
            {"customfield_id": "2286520000000029794", "value": city_cf},
            {"customfield_id": "2286520000000131080","value": code_cf},
            {"customfield_id": "2286520000000136037", "value": vehicle_cf}
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-com-zoho-invoice-organizationid": zoho_org_id,
        "Content-Type": "application/json"
    }

    print(f"DEBUG: Creating invoice with payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(invoice_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        invoice_data = response.json()
        print(f"DEBUG: Zoho Invoice creation response: {json.dumps(invoice_data, indent=2)}")

        if invoice_data and invoice_data.get('code') == 0: # Zoho API success code
            return invoice_data['invoice']['invoice_id']
        else:
            print(f"ERROR: Zoho Invoice creation failed: {invoice_data.get('message', 'Unknown error')}")
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response text: {http_err.response.text}")
        return None
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
        return None
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected request error occurred: {req_err}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during invoice creation: {e}")
        return None

# --- Placeholder for get_items if not in item_manager.py or zoho_api.py ---
# Ensure this function correctly fetches items with their rates
def get_items(access_token):
    zoho_api_base_url = os.getenv('API_BASE_URL', 'https://www.zohoapis.in/invoice/v3')
    zoho_org_id = os.getenv("ZOHO_ORG_ID")
    items_url = f"{zoho_api_base_url}/items"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-com-zoho-invoice-organizationid": zoho_org_id
    }
    try:
        response = requests.get(items_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('items', [])
    except Exception as e:
        print(f"ERROR: Failed to fetch items from Zoho: {e}")
        return []

