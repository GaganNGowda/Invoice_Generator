import requests
from config import API_BASE_URL, ORGANIZATION_ID

def create_invoice(contact_id, items, access_token, city_cf, code_cf, vehicle_cf):
    url = f"{API_BASE_URL}/invoices"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-com-zoho-invoice-organizationid": ORGANIZATION_ID,
        "Content-Type": "application/json"
    }

    line_items = [
        {
            "item_id": item["item_id"],
            "quantity": item["quantity"]
        }
        for item in items
    ]

    payload = {
        "customer_id": contact_id,
        "line_items": line_items,
        "custom_fields": [
            {
                "value": city_cf,
                "customfield_id": "2286520000000029794"
            },
            {
                "value": code_cf,
                "customfield_id": "2286520000000131080"
            },
            {
                "value": vehicle_cf or '',
                "customfield_id": "2286520000000136037"
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        invoice = response.json()["invoice"]
        print(f"✅ Invoice created successfully with ID: {invoice['invoice_id']}")
        return invoice["invoice_id"]
    else:
        print("❌ Failed to create invoice:", response.text)
        return None
