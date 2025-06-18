# main.py
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from io import BytesIO
import shutil
import os
import requests

# Import manager functions
from customer_manager import find_customer, create_customer
from item_manager import get_items
from invoice_manager import create_invoice
from zoho_api import get_access_token

# Import routers
from routes import customer, invoice

app = FastAPI()

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
app.include_router(customer.router, prefix="/customer", tags=["Customer"])
app.include_router(invoice.router, prefix="/invoice", tags=["Invoice"])

# --- Global Conversation State ---
conversation_states = {}


# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}


# --- Endpoint to serve PDF to frontend ---
@app.get("/download-invoice-pdf/{invoice_id}")
async def download_invoice_pdf_frontend(invoice_id: str):
    try:
        access_token = get_access_token()

        zoho_api_base_url = os.getenv('API_BASE_URL', 'https://www.zohoapis.in/invoice/v3')
        zoho_org_id = os.getenv("ZOHO_ORG_ID")

        url = f"{zoho_api_base_url}/invoices/print?invoice_ids={invoice_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-com-zoho-invoice-organizationid": zoho_org_id,
            "Accept": "application/pdf"
        }

        print(f"DEBUG: Attempting to fetch PDF from Zoho URL: {url}")
        print(
            f"DEBUG: Headers (excluding full token): {{'Authorization': 'Bearer ...', 'X-com-zoho-invoice-organizationid': '{zoho_org_id}'}}")

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        pdf_content = BytesIO(response.content)

        return StreamingResponse(
            pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_id}.pdf"}
        )
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error fetching PDF from Zoho: {e.response.status_code} - {e.response.text}"
        print(f"ERROR: {error_message}")
        return {"status": "error", "message": error_message}
    except requests.exceptions.RequestException as e:
        error_message = f"Network/Request Error fetching PDF from Zoho: {e}"
        print(f"ERROR: {error_message}")
        return {"status": "error", "message": error_message}
    except Exception as e:
        error_message = f"An unexpected error occurred during PDF streaming: {e}"
        print(f"ERROR: {error_message}")
        return {"status": "error", "message": f"An unexpected error occurred on server: {e}"}


# --- AI/NLP Process Endpoint (Central Conversational Logic) ---
@app.post("/process")
async def process(input_data: dict):
    user_message = input_data.get("text")
    session_id = input_data.get("session_id", "default_session")

    if not user_message:
        return {"status": "error", "message": "No text provided", "action": "error"}

    response_from_nlp = await process_user_input(user_message, session_id)
    return response_from_nlp


# --- Core Conversational Logic Function ---
async def process_user_input(text: str, session_id: str):
    text_lower = text.lower().strip()
    current_state = conversation_states.get(session_id, {})
    current_customer_data = current_state.get('customer_data', {})
    current_invoice_data = current_state.get('invoice_data', {})
    current_status = current_state.get('status')
    next_field_to_ask = current_state.get('next_field')
    invoice_sub_status = current_state.get('invoice_collection_sub_status')

    # --- Handle reset command first ---
    if text_lower == "reset_conversation_command":
        if session_id in conversation_states:
            del conversation_states[session_id]
        return {"action": "reset_success", "status": "info", "message": "Chat has been reset. How can I help you now?"}

    # --- Handle active customer collection flow ---
    if current_status == 'collecting_customer_info':
        if next_field_to_ask == 'phone_lookup':
            phone_number_for_lookup = text.strip()
            if not phone_number_for_lookup.isdigit() and not phone_number_for_lookup.replace('+', '').replace(' ',
                                                                                                              '').isdigit():
                return {"action": "ask_question", "status": "error",
                        "message": "Invalid phone number format. Please enter a valid phone number (digits only, or with '+' and spaces).",
                        "context": current_state}

            try:
                access_token = get_access_token()
                found_contact_id = find_customer(name="", city="", phone=phone_number_for_lookup, token=access_token)

                if found_contact_id:
                    if current_state.get('return_flow') == 'collecting_invoice_info':
                        current_invoice_data['customer_id'] = found_contact_id
                        current_invoice_data['selected_items'] = current_invoice_data.get('selected_items', [])
                        current_state['status'] = 'collecting_invoice_info'
                        current_state['next_field'] = 'items'
                        current_state['invoice_collection_sub_status'] = 'asking_item_number'
                        current_state['customer_data'] = {}
                        del current_state['return_flow']
                        del current_state['return_phone']

                        conversation_states[session_id] = current_state

                        all_items = get_items(access_token)
                        current_state['all_available_items'] = all_items
                        if all_items:
                            # FIX START for SyntaxError
                            items_display_list = [
                                f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                                for i, item in enumerate(all_items)
                            ]
                            # FIX END
                            items_display_message = "\n".join(items_display_list)
                            return {"action": "ask_question", "status": "info",
                                    "message": f"✅ Customer found! Using ID {found_contact_id} for invoice. Now, please select an item by number:\n{items_display_message}",
                                    "context": current_state}
                        else:
                            return {"action": "ask_question", "status": "warning",
                                    "message": f"✅ Customer found! Using ID {found_contact_id} for invoice. No items found in your Zoho account. What is the item ID?",
                                    "context": current_state}
                    else:
                        del conversation_states[session_id]
                        return {"action": "customer_exists", "status": "info",
                                "message": f"✅ Customer found! Contact ID: {found_contact_id}. How can I help you now?",
                                "contact_id": found_contact_id}
                else:
                    current_customer_data['phone'] = phone_number_for_lookup
                    current_state['next_field'] = 'first_name'
                    conversation_states[session_id] = current_state
                    return {"action": "ask_question", "status": "info",
                            "message": "❌ Customer not found with that phone number. Let's create a new one. What is their first name?",
                            "context": current_state}
            except Exception as e:
                del conversation_states[session_id]
                return {"action": "customer_lookup_error", "status": "error",
                        "message": f"An error occurred during customer lookup: {e}. Please try again.",
                        "context": current_state}

        elif next_field_to_ask == 'first_name':
            current_customer_data['first_name'] = text
            current_state['next_field'] = 'last_name'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is the customer's last name?",
                    "context": current_state}
        elif next_field_to_ask == 'last_name':
            current_customer_data['last_name'] = text
            current_state['next_field'] = 'salutation'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is their salutation (Mr./Ms./Dr.)?",
                    "context": current_state}
        elif next_field_to_ask == 'salutation':
            current_customer_data['salutation'] = text
            current_state['next_field'] = 'address'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is their street address?",
                    "context": current_state}
        elif next_field_to_ask == 'address':
            current_customer_data['address'] = text
            current_state['next_field'] = 'city'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "Which city do they live in?",
                    "context": current_state}
        elif next_field_to_ask == 'city':
            current_customer_data['city'] = text
            current_state['next_field'] = 'state'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is their state?",
                    "context": current_state}
        elif next_field_to_ask == 'state':
            current_customer_data['state'] = text
            current_state['next_field'] = 'zip_code'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is their ZIP Code?",
                    "context": current_state}
        elif next_field_to_ask == 'zip_code':
            current_customer_data['zip_code'] = text
            current_state['next_field'] = 'phone'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is their phone number?",
                    "context": current_state}
        elif next_field_to_ask == 'phone':
            if 'phone' not in current_customer_data or (text.strip() and (
                    not current_customer_data['phone'] or current_customer_data['phone'] != text.strip())):
                current_customer_data['phone'] = text.strip()

            if not current_customer_data.get('phone', '').strip().isdigit():
                return {"action": "ask_question", "status": "error",
                        "message": "Invalid phone number. Please enter a valid phone number (digits only).",
                        "context": current_state}

            current_state['next_field'] = 'place_of_contact'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info",
                    "message": "Finally, what is their Place of Contact (e.g., KA for Karnataka)? (Press Enter for default: KA)",
                    "context": current_state}
        elif next_field_to_ask == 'place_of_contact':
            current_customer_data['place_of_contact'] = text if text else "KA"

            full_name = f"{current_customer_data.get('salutation', '')} {current_customer_data.get('first_name', '')} {current_customer_data['last_name']}".strip()

            customer_payload = {
                "contact_name": full_name,
                "contact_type": "customer",
                "currency_id": "2286520000000000064",
                "payment_terms": 0,
                "payment_terms_label": "Paid",
                "payment_terms_id": "2286520000000166102",
                "credit_limit": 0,
                "billing_address": {
                    "country": "India",
                    "city": current_customer_data['city'],
                    "address": current_customer_data['address'],
                    "state": current_customer_data['state'],
                    "zip": current_customer_data['zip_code'],
                    "phone": current_customer_data['phone']
                },
                "shipping_address": {
                    "country": "India",
                    "city": current_customer_data['city'],
                    "address": current_customer_data['address'],
                    "state": current_customer_data['state'],
                    "zip": current_customer_data['zip_code'],
                    "phone": current_customer_data['phone']
                },
                "contact_persons": [
                    {
                        "first_name": current_customer_data['first_name'],
                        "last_name": current_customer_data['last_name'],
                        "mobile": current_customer_data['phone'],
                        "phone": current_customer_data['phone'],
                        "email": "",
                        "salutation": current_customer_data.get('salutation', ''),
                        "is_primary_contact": True
                    }
                ],
                "is_taxable": True,
                "language_code": "en",
                "gst_treatment": "consumer",
                "place_of_contact": current_customer_data['place_of_contact'],
                "customer_sub_type": "individual"
            }

            try:
                access_token = get_access_token()
                re_check_contact_id = find_customer(full_name, current_customer_data['city'],
                                                    current_customer_data['phone'], token=access_token)
                if re_check_contact_id:
                    if current_state.get('return_flow') == 'collecting_invoice_info':
                        current_invoice_data['customer_id'] = re_check_contact_id
                        current_invoice_data['selected_items'] = current_invoice_data.get('selected_items', [])
                        current_state['status'] = 'collecting_invoice_info'
                        current_state['next_field'] = 'items'
                        current_state['invoice_collection_sub_status'] = 'asking_item_number'
                        del current_state['customer_data']
                        del current_state['return_flow']
                        del current_state['return_phone']

                        conversation_states[session_id] = current_state
                        all_items = get_items(access_token)
                        current_state['all_available_items'] = all_items
                        if all_items:
                            # FIX START
                            items_display_list = [
                                f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                                for i, item in enumerate(all_items)
                            ]
                            # FIX END
                            items_display_message = "\n".join(items_display_list)
                            return {"action": "ask_question", "status": "info",
                                    "message": f"✅ Customer found! Using ID {re_check_contact_id} for invoice. Now, please select an item by number:\n{items_display_message}",
                                    "context": current_state}
                        else:
                            return {"action": "ask_question", "status": "warning",
                                    "message": f"✅ Customer found! Using ID {re_check_contact_id} for invoice. No items found in your Zoho account. What is the item ID?",
                                    "context": current_state}
                    else:
                        del conversation_states[session_id]
                        return {"action": "customer_exists", "status": "info",
                                "message": f"✅ Customer already exists with contact ID: {re_check_contact_id}",
                                "contact_id": re_check_contact_id}

                contact_id = create_customer(customer_payload, access_token)
                if contact_id:
                    if current_state.get('return_flow') == 'collecting_invoice_info':
                        current_invoice_data['customer_id'] = contact_id
                        current_invoice_data['selected_items'] = current_invoice_data.get('selected_items', [])
                        current_state['status'] = 'collecting_invoice_info'
                        current_state['next_field'] = 'items'
                        current_state['invoice_collection_sub_status'] = 'asking_item_number'
                        del current_state['customer_data']
                        del current_state['return_flow']
                        del current_state['return_phone']

                        conversation_states[session_id] = current_state
                        all_items = get_items(access_token)
                        current_state['all_available_items'] = all_items
                        if all_items:
                            # FIX START
                            items_display_list = [
                                f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                                for i, item in enumerate(all_items)
                            ]
                            # FIX END
                            items_display_message = "\n".join(items_display_list)
                            return {"action": "ask_question", "status": "info",
                                    "message": f"✅ New customer created with ID {contact_id}. Using this for invoice. Now, please select an item by number:\n{items_display_message}",
                                    "context": current_state}
                        else:
                            return {"action": "ask_question", "status": "warning",
                                    "message": f"✅ New customer created with ID {contact_id}. Using this for invoice. No items found in your Zoho account. What is the item ID?",
                                    "context": current_state}
                    else:
                        del conversation_states[session_id]
                        return {"action": "customer_created", "status": "success",
                                "message": f"✅ New customer created with contact ID: {contact_id}",
                                "contact_id": contact_id}
                else:
                    del conversation_states[session_id]
                    return {"action": "customer_creation_failed", "status": "error",
                            "message": "❌ Failed to create customer."}
            except Exception as e:
                del conversation_states[session_id]
                return {"action": "customer_creation_error", "status": "error",
                        "message": f"An error occurred during customer creation/lookup: {e}"}

        return {"action": "general_response", "status": "error",
                "message": "I'm still collecting customer details, but I didn't understand that. Please provide the specific information requested."}

    # --- Handle active invoice collection flow ---
    if current_status == 'collecting_invoice_info':
        if next_field_to_ask == 'customer_phone_for_invoice':
            phone_number_for_invoice = text.strip()
            if not phone_number_for_invoice.isdigit() and not phone_number_for_invoice.replace('+', '').replace(' ',
                                                                                                                '').isdigit():
                return {"action": "ask_question", "status": "error",
                        "message": "Invalid phone number format. Please enter a valid phone number for the customer (digits only, or with '+' and spaces).",
                        "context": current_state}

            try:
                access_token = get_access_token()
                found_contact_id = find_customer(name="", city="", phone=phone_number_for_invoice, token=access_token)

                if found_contact_id:
                    current_invoice_data['customer_id'] = found_contact_id
                    current_invoice_data['selected_items'] = current_invoice_data.get('selected_items', [])
                    current_state['next_field'] = 'items'
                    current_state['invoice_collection_sub_status'] = 'asking_item_number'

                    conversation_states[session_id] = current_state

                    all_items = get_items(access_token)
                    current_state['all_available_items'] = all_items

                    if all_items:
                        # FIX START
                        items_display_list = [
                            f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                            for i, item in enumerate(all_items)
                        ]
                        # FIX END
                        items_display_message = "\n".join(items_display_list)
                        return {"action": "ask_question", "status": "info",
                                "message": f"✅ Customer found! Using ID {found_contact_id} for invoice. Now, please select an item by number:\n{items_display_message}",
                                "context": current_state}
                    else:
                        return {"action": "ask_question", "status": "warning",
                                "message": f"✅ Customer found! Using ID {found_contact_id} for invoice. No items found in your Zoho account. What is the item ID?",
                                "context": current_state}
                else:
                    current_state['status'] = 'collecting_customer_info'
                    current_state['next_field'] = 'first_name'
                    current_state['customer_data'] = {'phone': phone_number_for_invoice}
                    current_state['return_flow'] = 'collecting_invoice_info'
                    current_state['return_phone'] = phone_number_for_invoice

                    conversation_states[session_id] = current_state
                    return {"action": "ask_question", "status": "info",
                            "message": "❌ Customer not found with that phone number. Let's create a new customer first. What is their first name?",
                            "context": current_state}
            except Exception as e:
                del conversation_states[session_id]
                return {"action": "customer_lookup_error", "status": "error",
                        "message": f"An error occurred during customer lookup for invoice: {e}. Please try again.",
                        "context": current_state}

        elif next_field_to_ask == 'items':
            if invoice_sub_status == 'asking_item_number':
                try:
                    item_index = int(text.strip()) - 1
                    all_available_items = current_state.get('all_available_items', [])
                    if 0 <= item_index < len(all_available_items):
                        selected_item = all_available_items[item_index]
                        current_state['current_item_id'] = selected_item['item_id']
                        current_state['current_item_name'] = selected_item['name']
                        current_state['invoice_collection_sub_status'] = 'asking_item_quantity'
                        conversation_states[session_id] = current_state
                        return {"action": "ask_question", "status": "info",
                                "message": f"How many '{selected_item['name']}' do you need?",
                                "context": current_state}
                    else:
                        return {"action": "ask_question", "status": "error",
                                "message": "Invalid item number. Please select an item from the list by its number.",
                                "context": current_state}
                except ValueError:
                    return {"action": "ask_question", "status": "error",
                            "message": "Please enter a valid number for the item selection.",
                            "context": current_state}

            elif invoice_sub_status == 'asking_item_quantity':
                try:
                    quantity = int(text.strip())
                    if quantity <= 0:
                        raise ValueError("Quantity must be positive.")

                    item_id = current_state['current_item_id']
                    item_name = current_state['current_item_name']

                    current_invoice_data['selected_items'].append({
                        "item_id": item_id,
                        "quantity": quantity
                    })

                    current_state['invoice_collection_sub_status'] = 'ask_more_items'
                    conversation_states[session_id] = current_state
                    return {"action": "ask_question", "status": "info",
                            "message": f"Added {quantity} x '{item_name}'. Do you want to add another item? (yes/no or y/n)",
                            "context": current_state}
                except ValueError:
                    return {"action": "ask_question", "status": "error",
                            "message": "Invalid quantity. Please enter a whole number greater than zero.",
                            "context": current_state}

            elif invoice_sub_status == 'ask_more_items':
                if text_lower in ['yes', 'y']:
                    current_state['invoice_collection_sub_status'] = 'asking_item_number'
                    conversation_states[session_id] = current_state
                    items_display_list = []
                    all_available_items = current_state.get('all_available_items', [])
                    for i, item in enumerate(all_available_items):
                        # FIX START
                        items_display_list.append(
                            f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                        )
                        # FIX END
                    items_display_message = "\n".join(items_display_list)
                    return {"action": "ask_question", "status": "info",
                            "message": f"Okay, select next item by number:\n{items_display_message}",
                            "context": current_state}
                elif text_lower in ['no', 'n']:
                    current_state['next_field'] = 'city_cf'
                    current_state['invoice_collection_sub_status'] = None
                    conversation_states[session_id] = current_state
                    return {"action": "ask_question", "status": "info",
                            "message": "What is the city for the custom field?", "context": current_state}
                else:
                    return {"action": "ask_question", "status": "error",
                            "message": "Please respond with 'yes' or 'no' (y/n). Do you want to add another item?",
                            "context": current_state}

            else:  # Fallback for unexpected sub-status during items collection
                return {"action": "general_response", "status": "error",
                        "message": "I'm in the middle of item collection, but something went wrong. Please try restarting invoice creation or specify the item number."}

        elif next_field_to_ask == 'city_cf':
            current_invoice_data['city_cf'] = text.strip()
            current_state['next_field'] = 'code_cf'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info",
                    "message": "What is the total items code for the custom field?", "context": current_state}

        elif next_field_to_ask == 'code_cf':
            current_invoice_data['code_cf'] = text.strip()
            current_state['next_field'] = 'vehicle_cf'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info",
                    "message": "What is the vehicle number for the custom field? (Optional, press Enter to skip)",
                    "context": current_state}

        elif next_field_to_ask == 'vehicle_cf':
            current_invoice_data['vehicle_cf'] = text.strip() if text.strip() else ''

            try:
                access_token = get_access_token()
                invoice_id = create_invoice(
                    current_invoice_data['customer_id'],
                    current_invoice_data['selected_items'],
                    access_token,
                    current_invoice_data.get('city_cf', ''),
                    current_invoice_data.get('code_cf', ''),
                    current_invoice_data.get('vehicle_cf', '')
                )
                if invoice_id:
                    # Return PDF download URL to frontend
                    backend_base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
                    pdf_download_url = f"{backend_base_url}/download-invoice-pdf/{invoice_id}"
                    del conversation_states[session_id]
                    return {"action": "invoice_created", "status": "success",
                            "message": f"✅ Invoice created successfully with ID: {invoice_id}.",
                            "invoice_id": invoice_id,
                            "pdf_url": pdf_download_url}
                else:
                    del conversation_states[session_id]
                    return {"action": "invoice_creation_failed", "status": "error",
                            "message": "❌ Failed to create invoice."}
            except Exception as e:
                del conversation_states[session_id]
                return {"action": "invoice_creation_error", "status": "error",
                        "message": f"An error occurred during invoice creation: {e}"}

        return {"action": "general_response", "status": "error",
                "message": "I'm still collecting invoice details, but I didn't understand that. Please try restarting the invoice creation."}

    # --- Handle initial intents if no active conversation flow ---
    if "show items" in text_lower or "list items" in text_lower or "what items" in text_lower:
        try:
            access_token = get_access_token()
            items = get_items(access_token)
            if items:
                items_display = "\n".join(
                    [f"- {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                     for item in items])
                return {"action": "list_items", "status": "success",
                        "message": f"Here are your items:\n{items_display}", "data": items}
            else:
                return {"action": "list_items", "status": "info",
                        "message": "No items found in your Zoho Invoice account."}
        except Exception as e:
            return {"action": "list_items", "status": "error", "message": f"Failed to fetch items: {e}"}

    if "create customer" in text_lower:
        conversation_states[session_id] = {
            'status': 'collecting_customer_info',
            'next_field': 'phone_lookup',
            'customer_data': {}
        }
        return {"action": "ask_question", "status": "info",
                "message": "Okay, let's find or create a customer. What is their phone number?",
                "context": conversation_states[session_id]}

    if "create invoice" in text_lower:
        conversation_states[session_id] = {
            'status': 'collecting_invoice_info',
            'next_field': 'customer_phone_for_invoice',
            'invoice_data': {'selected_items': []}
        }
        return {"action": "ask_question", "status": "info",
                "message": "Okay, let's create an invoice. What is the customer's phone number?",
                "context": conversation_states[session_id]}

    # Default response if no specific intent is matched
    return {"action": "general_response", "status": "info",
            "message": f"You said: '{text}'. I'm still learning to understand complex requests. How else can I help with invoices?"}


# --- File Upload Endpoint (unchanged) ---
@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    try:
        upload_dir = "uploaded_files"
        os.makedirs(upload_dir, exist_ok=True)
        file_location = os.path.join(upload_dir, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "message": f"File '{file.filename}' uploaded successfully!",
                "action": "file_uploaded", "file_path": file_location}
    except Exception as e:
        return {"status": "error", "message": f"Failed to upload file: {e}", "action": "error"}


# The `main()` function is a standalone script and should not interfere with FastAPI.
def main():
    pass


if __name__ == "__main__":
    main()