from fastapi import APIRouter
from zoho_api import get_access_token
from customer_manager import find_customer, create_customer

router = APIRouter()


@router.post("/find_or_create")
def find_or_create_customer(customer_payload: dict):
    access_token = get_access_token()
    name = customer_payload["contact_name"]
    city = customer_payload["billing_address"]["city"]
    phone = customer_payload["billing_address"]["phone"]

    contact_id = find_customer(name, city, phone, access_token)
    if not contact_id:
        contact_id = create_customer(customer_payload, access_token)
        return {"status": "created", "contact_id": contact_id}

    return {"status": "exists", "contact_id": contact_id}
