# customer_manager.py
import requests
import os
from zoho_api import get_access_token

API_BASE_URL = "https://www.zohoapis.in/invoice/v3"
ORG_ID = os.getenv("ZOHO_ORG_ID")

def get_all_customers():
    url = "https://www.zohoapis.in/invoice/v3/contacts"
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "X-com-zoho-invoice-organizationid": ORG_ID
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["contacts"]

import requests

API_BASE_URL = "https://www.zohoapis.in/invoice/v3"


def find_customer(name, city, phone, token):
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}"
    }

    response = requests.get(f"{API_BASE_URL}/contacts", headers=headers)
    contacts = response.json().get("contacts", [])

    name = name.lower()
    city = city.lower()
    phone = phone.strip()

    for contact in contacts:
        contact_name = contact.get("contact_name", "").lower()
        billing_city = contact.get("billing_address", {}).get("city", "").lower()
        contact_phone = contact.get("phone", "").strip()

        # Check in primary fields
        if (name == contact_name and
            (phone == contact_phone or phone in contact_phone)):
            return contact["contact_id"]

        # Also check contact persons if present
        for person in contact.get("contact_persons", []):
            person_phone = person.get("mobile", "").strip()
            if phone == person_phone or phone in person_phone:
                return contact["contact_id"]

    return None



import requests

def create_customer(payload, access_token):
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }

    url = "https://www.zohoapis.in/invoice/v3/contacts"

    response = requests.post(url, headers=headers, json=payload)

    print(f"\n📨 Zoho Create Customer Response: {response.status_code} {response.text}")

    if response.status_code == 201:
        contact_id = response.json()["contact"]["contact_id"]
        print(f"✅ Customer created successfully with ID: {contact_id}")
        return contact_id
    else:
        print("❌ Failed to create customer.")
        return None

# customer_manager.py

def prompt_user_for_customer():
    print("👤 Let's collect customer info\n")

    first_name = input("First name: ")
    last_name = input("Last name: ")
    salutation = input("Salutation (Mr./Ms./Dr./etc.): ")
    address = input("Address: ")
    city = input("City: ")
    state = input("State: ")
    zip_code = input("ZIP Code: ")
    phone = input("Phone number: ")

    place_of_contact = input("Place of Contact (e.g., KA for Karnataka): ") or "KA"

    full_name = f"{salutation} {first_name} {last_name}"

    payload = {
        "contact_name": full_name,
        "contact_type": "customer",
        "currency_id": "2286520000000000064",
        "payment_terms": 0,
        "payment_terms_label": "Paid",
        "payment_terms_id": "2286520000000166102",
        "credit_limit": 0,
        "billing_address": {
            "country": "India",
            "city": city,
            "address": address,
            "state": state,
            "zip": zip_code,
            "phone": phone
        },
        "shipping_address": {
            "country": "India",
            "city": city,
            "address":address,
            "state": state,
            "zip": zip_code,
            "phone": phone
        },
        "contact_persons": [
            {
                "first_name": first_name,
                "last_name": last_name,
                "mobile": phone,
                "phone": phone,
                "email": "",
                "salutation": salutation,
                "is_primary_contact": True
            }
        ],
        "is_taxable": True,
        "language_code": "en",
        "gst_treatment": "consumer",
        "place_of_contact": place_of_contact,
        "customer_sub_type": "individual"
    }

    return payload
