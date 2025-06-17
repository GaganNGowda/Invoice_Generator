from Backend.customer_manager import find_customer, create_customer
from zoho_api import get_access_token

def handle_customer(data):
    access_token = get_access_token()
    contact_id = find_customer(data["name"], data["city"], data["phone"], access_token)
    if not contact_id:
        customer_payload = {
            # map input to payload structure
        }
        contact_id = create_customer(customer_payload, access_token)
    return contact_id
