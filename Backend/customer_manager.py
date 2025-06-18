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
    url = f"{API_BASE_URL}/contacts"
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        # Including ORGANIZATION_ID for robustness, as many Zoho endpoints require it
        "X-com-zoho-invoice-organizationid": ORG_ID
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        contacts = response.json().get("contacts", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching contacts from Zoho: {e}")
        return None

    normalized_name = name.lower().strip()
    normalized_city = city.lower().strip()
    normalized_phone = phone.strip()

    # --- Scenario 1: Phone-only lookup (when name and city are empty) ---
    # This is the primary case for the initial phone number prompt.
    if not normalized_name and not normalized_city and normalized_phone:
        for contact in contacts:
            contact_phone_main = contact.get("phone", "").strip()
            contact_mobile_main = contact.get("mobile", "").strip() # Check main mobile field

            # Check primary contact's phone or mobile number
            if (normalized_phone == contact_phone_main or normalized_phone in contact_phone_main or
                normalized_phone == contact_mobile_main or normalized_phone in contact_mobile_main):
                return contact["contact_id"]

            # Check contact persons' phone or mobile numbers
            for person in contact.get("contact_persons", []):
                person_phone = person.get("phone", "").strip()
                person_mobile = person.get("mobile", "").strip()
                if (normalized_phone == person_phone or normalized_phone in person_phone or
                    normalized_phone == person_mobile or normalized_phone in person_mobile):
                    return contact["contact_id"]
        return None # No match found when only phone was provided

    # --- Scenario 2: Detailed lookup (when name and/or city are provided) ---
    # This part will execute when the user is providing full details for creation or re-validation.
    for contact in contacts:
        contact_name = contact.get("contact_name", "").lower().strip()
        billing_city = contact.get("billing_address", {}).get("city", "").lower().strip()
        contact_phone_main = contact.get("phone", "").strip()
        contact_mobile_main = contact.get("mobile", "").strip()

        # Evaluate matches for the main contact fields
        name_match = (not normalized_name) or (normalized_name == contact_name)
        city_match = (not normalized_city) or (normalized_city == billing_city)
        phone_match = (not normalized_phone) or \
                      (normalized_phone == contact_phone_main) or \
                      (normalized_phone in contact_phone_main) or \
                      (normalized_phone == contact_mobile_main) or \
                      (normalized_phone in contact_mobile_main)

        # Combine checks for main contact (all provided criteria must match)
        if name_match and city_match and phone_match:
             return contact["contact_id"]

        # Check contact persons if main contact doesn't match fully
        for person in contact.get("contact_persons", []):
            person_first_name = person.get("first_name", "").lower().strip()
            person_last_name = person.get("last_name", "").lower().strip()
            person_full_name = f"{person_first_name} {person_last_name}".strip()
            person_phone = person.get("phone", "").strip()
            person_mobile = person.get("mobile", "").strip()

            # For contact persons, match either their full name or their phone/mobile
            person_name_match = (not normalized_name) or \
                                (normalized_name == person_full_name) or \
                                (normalized_name == person_first_name) or \
                                (normalized_name == person_last_name)

            person_phone_match = (not normalized_phone) or \
                                 (normalized_phone == person_phone) or \
                                 (normalized_phone in person_phone) or \
                                 (normalized_phone == person_mobile) or \
                                 (normalized_phone in person_mobile)

            # Combine checks for contact person (City is typically at contact level)
            # A contact person match, combined with city match on the parent contact, is sufficient.
            if person_name_match and person_phone_match and (not normalized_city or normalized_city == billing_city):
                return contact["contact_id"]

    return None # No match found

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
