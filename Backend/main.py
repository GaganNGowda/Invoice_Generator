from zoho_api import get_access_token
from customer_manager import find_customer, create_customer, prompt_user_for_customer
from item_manager import get_items, prompt_user_for_items
from invoice_manager import create_invoice
from download_invoice_pdf import  download_invoice_pdf

def main():
    # Step 1: Get customer input
    customer_payload = prompt_user_for_customer()
    name = customer_payload["contact_name"]
    city = customer_payload["billing_address"]["city"]
    phone = customer_payload["billing_address"]["phone"]

    # Step 2: Get access token
    access_token = get_access_token()

    # Step 3: Try to find existing customer
    contact_id = find_customer(name, city, phone, access_token)
    if contact_id:
        print(f"✅ Customer already exists with contact ID: {contact_id}")
    else:
        print("❌ Customer not found. Proceeding to create a new customer...")
        contact_id = create_customer(customer_payload, access_token)
        print(f"✅ New customer created with contact ID: {contact_id}")

    # Step 4: Get available items
    items = get_items(access_token)
    if not items:
        print("❌ No items available to select.")
        return

    # Step 5: Let user pick items and quantity
    selected_items = prompt_user_for_items(items)
    if not selected_items:
        print("❌ No items selected. Exiting.")
        return

    # Step 6: Ask for custom fields
    city_cf = input("🌍 Enter city (for custom field): ")
    code_cf = input("🔢 Enter total items (for custom field): ")
    vehicle_cf = input("🚚 Enter vehicle number (for custom field): ")

    # Step 7: Create invoice with selected items and custom fields
    invoice_id = create_invoice(contact_id, selected_items, access_token, city_cf, code_cf, vehicle_cf)
    if invoice_id:
        download_invoice_pdf(invoice_id, access_token)

if __name__ == "__main__":
    main()
