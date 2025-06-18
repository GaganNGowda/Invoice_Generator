from fastapi import APIRouter
from zoho_api import get_access_token
from item_manager import get_items
from invoice_manager import create_invoice
from download_invoice_pdf import download_invoice_pdf

router = APIRouter()

@router.get("/items")
def fetch_items():
    access_token = get_access_token()
    return get_items(access_token)

@router.post("/create")
def generate_invoice(payload: dict):
    access_token = get_access_token()
    contact_id = payload["contact_id"]
    selected_items = payload["items"]  # [{"item_id": "...", "quantity": 2}]
    city_cf = payload.get("city")
    code_cf = payload.get("code")
    vehicle_cf = payload.get("vehicle")

    invoice_id = create_invoice(contact_id, selected_items, access_token, city_cf, code_cf, vehicle_cf)
    if not invoice_id:
        return {"status": "error", "message": "Invoice creation failed"}

    download_invoice_pdf(invoice_id, access_token)
    return {"status": "success", "invoice_id": invoice_id}
