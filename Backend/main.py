from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from io import BytesIO
import shutil
import os
import requests
import json # Ensure json is imported if used elsewhere for logging/debug

# Import manager functions
from customer_manager import find_customer, create_customer
from item_manager import get_items
from invoice_manager import create_invoice
from zoho_api import get_access_token

# Import routers
from routes import customer, invoice
from i18n_utils import t # Import the translation utility

# Define GST rate globally for easy adjustment
GST_RATE = 0.18 # 18% GST (18%)
PRECISION = 2 # Decimal places for calculations

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
    return {"message": t("backend_running", language="en")} # Use English for root, or determine based on header if needed


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
    context = input_data.get("context", {})

    if not user_message:
        return {"status": "error", "message": t("no_text_provided", language=context.get("language", "kn")), "action": "error"}

    response_from_nlp = await process_user_input(user_message, session_id, context)
    return response_from_nlp


# --- Core Conversational Logic Function ---
async def process_user_input(text: str, session_id: str, incoming_context: dict):
    # Set the language from incoming context, default to Kannada ('kn')
    language = incoming_context.get("language", "kn")
    
    current_state = conversation_states.get(session_id, {})
    current_state.update(incoming_context)
    current_state['language'] = language # Store language in current state

    text_lower = text.lower().strip()
    
    current_customer_data = current_state.get('customer_data', {})
    current_invoice_data = current_state.get('invoice_data', {})
    current_status = current_state.get('status')
    next_field_to_ask = current_state.get('next_field')
    invoice_sub_status = current_state.get('invoice_collection_sub_status')
    
    # Store current_state back into global conversation_states
    conversation_states[session_id] = current_state


    # --- Handle reset command first ---
    if text_lower == "reset_conversation_command":
        if session_id in conversation_states:
            del conversation_states[session_id]
        return {"action": "reset_success", "status": "info", 
                "message": t("reset_success", language=language), "context": current_state}

    # --- Handle active customer collection flow (Unchanged from previous simplified version) ---
    if current_status == 'collecting_customer_info':
        if next_field_to_ask == 'phone_lookup':
            phone_number_for_lookup = text.strip()
            if not phone_number_for_lookup.isdigit() and not phone_number_for_lookup.replace('+', '').replace(' ',
                                                                                                              '').isdigit():
                return {"action": "ask_question", "status": "error",
                        "message": t("invalid_phone_format", language=language),
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
                        current_state['customer_data'] = {} # Reset customer data after successful lookup/creation
                        current_state.pop('return_flow', None) # Clean up return flow state
                        current_state.pop('return_phone', None)
                        
                        all_items = get_items(access_token)
                        current_state['all_available_items'] = all_items # Store available items in state
                        if all_items:
                            items_display_list = [
                                f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                                for i, item in enumerate(all_items)
                            ]
                            items_display_message = "\n".join(items_display_list)
                            return {"action": "ask_question", "status": "info",
                                    "message": t("customer_found_for_invoice", language=language, contact_id=found_contact_id, items_display_message=items_display_message),
                                    "context": current_state}
                        else:
                            return {"action": "ask_question", "status": "warning",
                                    "message": t("customer_found_for_invoice_no_items", language=language, contact_id=found_contact_id),
                                    "context": current_state}
                    else:
                        del conversation_states[session_id] # Customer found, end customer creation flow
                        return {"action": "customer_exists", "status": "info",
                                "message": t("customer_exists", language=language, contact_id=found_contact_id),
                                "contact_id": found_contact_id}
                else: # Customer not found, proceed to create new customer
                    current_customer_data['phone'] = phone_number_for_lookup
                    current_state['next_field'] = 'first_name'
                    return {"action": "ask_question", "status": "info",
                            "message": t("customer_not_found_create", language=language),
                            "context": current_state}
            except Exception as e:
                del conversation_states[session_id]
                return {"action": "customer_lookup_error", "status": "error",
                        "message": t("customer_lookup_error", language=language, error_message=str(e)),
                        "context": current_state}

        elif next_field_to_ask == 'first_name':
            current_customer_data['first_name'] = text
            current_state['next_field'] = 'last_name'
            return {"action": "ask_question", "status": "info", "message": t("ask_last_name", language=language),
                    "context": current_state}
        elif next_field_to_ask == 'last_name':
            current_customer_data['last_name'] = text
            current_state['next_field'] = 'salutation'
            return {"action": "ask_question", "status": "info", "message": t("ask_salutation", language=language),
                    "context": current_state}
        elif next_field_to_ask == 'salutation':
            current_customer_data['salutation'] = text
            current_state['next_field'] = 'address'
            return {"action": "ask_question", "status": "info", "message": t("ask_address", language=language),
                    "context": current_state}
        elif next_field_to_ask == 'address':
            current_customer_data['address'] = text
            current_state['next_field'] = 'city'
            return {"action": "ask_question", "status": "info", "message": t("ask_city", language=language),
                    "context": current_state}
        elif next_field_to_ask == 'city':
            current_customer_data['city'] = text
            current_state['next_field'] = 'state'
            return {"action": "ask_question", "status": "info", "message": t("ask_state", language=language),
                    "context": current_state}
        elif next_field_to_ask == 'state':
            current_customer_data['state'] = text
            current_state['next_field'] = 'zip_code'
            return {"action": "ask_question", "status": "info", "message": t("ask_zip_code", language=language),
                    "context": current_state}
        elif next_field_to_ask == 'zip_code':
            current_customer_data['zip_code'] = text
            current_state['next_field'] = 'phone'
            return {"action": "ask_question", "status": "info", "message": t("ask_phone", language=language),
                    "context": current_state}
        elif next_field_to_ask == 'phone':
            if 'phone' not in current_customer_data or (text.strip() and (
                    not current_customer_data['phone'] or current_customer_data['phone'] != text.strip())):
                current_customer_data['phone'] = text.strip()

            if not current_customer_data.get('phone', '').strip().isdigit():
                return {"action": "ask_question", "status": "error",
                        "message": t("invalid_phone_number", language=language),
                        "context": current_state}

            current_state['next_field'] = 'place_of_contact'
            return {"action": "ask_question", "status": "info",
                    "message": t("ask_place_of_contact", language=language),
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
                        current_state.pop('customer_data', None)
                        current_state.pop('return_flow', None)
                        current_state.pop('return_phone', None)
                        
                        all_items = get_items(access_token)
                        current_state['all_available_items'] = all_items
                        if all_items:
                            items_display_list = [
                                f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                                for i, item in enumerate(all_items)
                            ]
                            items_display_message = "\n".join(items_display_list)
                            return {"action": "ask_question", "status": "info",
                                    "message": t("customer_found_for_invoice", language=language, contact_id=re_check_contact_id, items_display_message=items_display_message),
                                    "context": current_state}
                        else:
                            return {"action": "ask_question", "status": "warning",
                                    "message": t("customer_found_for_invoice_no_items", language=language, contact_id=re_check_contact_id),
                                    "context": current_state}
                    else:
                        del conversation_states[session_id]
                        return {"action": "customer_exists", "status": "info",
                                "message": t("customer_exists", language=language, contact_id=re_check_contact_id),
                                "contact_id": re_check_contact_id}
                else:
                    contact_id = create_customer(customer_payload, access_token)
                    if contact_id:
                        if current_state.get('return_flow') == 'collecting_invoice_info':
                            current_invoice_data['customer_id'] = contact_id
                            current_invoice_data['selected_items'] = current_invoice_data.get('selected_items', [])
                            current_state['status'] = 'collecting_invoice_info'
                            current_state['next_field'] = 'items'
                            current_state['invoice_collection_sub_status'] = 'asking_item_number'
                            current_state.pop('customer_data', None)
                            current_state.pop('return_flow', None)
                            current_state.pop('return_phone', None)
                            
                            all_items = get_items(access_token)
                            current_state['all_available_items'] = all_items
                            if all_items:
                                items_display_list = [
                                    f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                                    for i, item in enumerate(all_items)
                                ]
                                items_display_message = "\n".join(items_display_list)
                                return {"action": "ask_question", "status": "info",
                                        "message": t("customer_found_for_invoice", language=language, contact_id=contact_id, items_display_message=items_display_message),
                                        "context": current_state}
                            else:
                                return {"action": "ask_question", "status": "warning",
                                        "message": t("customer_found_for_invoice_no_items", language=language, contact_id=contact_id),
                                        "context": current_state}
                        else:
                            del conversation_states[session_id]
                            return {"action": "customer_created", "status": "success",
                                    "message": t("customer_created", language=language, contact_id=contact_id),
                                    "contact_id": contact_id}
                    else:
                        del conversation_states[session_id]
                        return {"action": "customer_creation_failed", "status": "error",
                            "message": t("customer_creation_failed", language=language)}
            except Exception as e:
                del conversation_states[session_id]
                return {"action": "customer_creation_error", "status": "error",
                        "message": t("customer_creation_error", language=language, error_message=str(e))}

        return {"action": "general_response", "status": "error",
                "message": t("collecting_customer_details_fallback", language=language, next_field=next_field_to_ask),
                "context": current_state}

    # --- Handle active invoice collection flow ---
    if current_status == 'collecting_invoice_info':
        if next_field_to_ask == 'customer_phone_for_invoice':
            phone_number_for_invoice = text.strip()
            if not phone_number_for_invoice.isdigit() and not phone_number_for_invoice.replace('+', '').replace(' ',
                                                                                                                '').isdigit():
                return {"action": "ask_question", "status": "error",
                        "message": t("invalid_phone_format", language=language),
                        "context": current_state}

            try:
                access_token = get_access_token()
                found_contact_id = find_customer(name="", city="", phone=phone_number_for_invoice, token=access_token)

                if found_contact_id:
                    current_invoice_data['customer_id'] = found_contact_id
                    current_invoice_data['selected_items'] = current_invoice_data.get('selected_items', [])
                    current_state['next_field'] = 'items'
                    current_state['invoice_collection_sub_status'] = 'asking_item_number'

                    all_items = get_items(access_token)
                    current_state['all_available_items'] = all_items

                    if all_items:
                        items_display_list = [
                            f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                            for i, item in enumerate(all_items)
                        ]
                        items_display_message = "\n".join(items_display_list)
                        return {"action": "ask_question", "status": "info",
                                "message": t("customer_found_for_invoice", language=language, contact_id=found_contact_id, items_display_message=items_display_message),
                                "context": current_state}
                    else:
                        return {"action": "ask_question", "status": "warning",
                                "message": t("customer_found_for_invoice_no_items", language=language, contact_id=found_contact_id),
                                "context": current_state}
                else:
                    current_state['status'] = 'collecting_customer_info'
                    current_state['next_field'] = 'first_name'
                    current_state['customer_data'] = {'phone': phone_number_for_invoice}
                    current_state['return_flow'] = 'collecting_invoice_info'
                    current_state['return_phone'] = phone_number_for_invoice

                    return {"action": "ask_question", "status": "info",
                            "message": t("customer_not_found_create", language=language),
                            "context": current_state}
            except Exception as e:
                del conversation_states[session_id]
                return {"action": "customer_lookup_error", "status": "error",
                        "message": t("customer_lookup_error", language=language, error_message=str(e)),
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
                        current_state['current_item_rate'] = selected_item['rate'] # Store item's rate
                        current_state['invoice_collection_sub_status'] = 'asking_item_quantity'
                        return {"action": "ask_question", "status": "info",
                                "message": t("ask_quantity", language=language, item_name=selected_item['name']),
                                "context": current_state}
                    else:
                        return {"action": "ask_question", "status": "error",
                                "message": t("invalid_item_number", language=language),
                                "context": current_state}
                except ValueError:
                    return {"action": "ask_question", "status": "error",
                            "message": t("enter_valid_number", language=language),
                            "context": current_state}

            elif invoice_sub_status == 'asking_item_quantity':
                try:
                    quantity = int(text.strip())
                    if quantity <= 0:
                        raise ValueError("Quantity must be positive.")

                    item_id = current_state['current_item_id']
                    item_name = current_state['current_item_name']
                    item_rate = current_state['current_item_rate'] # Retrieve item rate

                    current_invoice_data['selected_items'].append({
                        "item_id": item_id,
                        "quantity": quantity,
                        "rate": item_rate # Store rate with the selected item
                    })

                    current_state['invoice_collection_sub_status'] = 'ask_more_items'
                    return {"action": "ask_question", "status": "info",
                            "message": t("item_added_ask_more", language=language, quantity=quantity, item_name=item_name),
                            "context": current_state}
                except ValueError:
                    return {"action": "ask_question", "status": "error",
                            "message": t("invalid_quantity", language=language),
                            "context": current_state}

            elif invoice_sub_status == 'ask_more_items':
                if text_lower in ['yes', 'y', t("yes", language=language).lower(), t("y", language=language).lower()]: # Added translation check
                    current_state['invoice_collection_sub_status'] = 'asking_item_number'
                    items_display_list = []
                    all_available_items = current_state.get('all_available_items', [])
                    for i, item in enumerate(all_available_items):
                        items_display_list.append(
                            f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                        )
                    items_display_message = "\n".join(items_display_list)
                    return {"action": "ask_question", "status": "info",
                            "message": t("ask_more_items_prompt", language=language, items_display_message=items_display_message),
                            "context": current_state}
                elif text_lower in ['no', 'n', t("no", language=language).lower(), t("n", language=language).lower()]: # Added translation check
                    # After adding all items, ask for the total amount
                    current_state['next_field'] = 'total_amount'
                    current_state['invoice_collection_sub_status'] = None # Reset sub_status

                    # Calculate the current subtotal and total with GST
                    calculated_subtotal = sum(item['quantity'] * item['rate'] for item in current_invoice_data['selected_items'])
                    calculated_gst_amount = round(calculated_subtotal * GST_RATE, PRECISION)
                    calculated_total_with_gst = round(calculated_subtotal + calculated_gst_amount, PRECISION)
                    
                    current_state['calculated_subtotal'] = calculated_subtotal
                    current_state['calculated_gst_amount'] = calculated_gst_amount
                    current_state['calculated_total_with_gst'] = calculated_total_with_gst

                    return {"action": "ask_question", "status": "info",
                            "message": t("ask_total_amount", language=language, 
                                        calculated_subtotal=calculated_subtotal, 
                                        gst_rate_percent=GST_RATE*100, 
                                        calculated_gst_amount=calculated_gst_amount, 
                                        calculated_total_with_gst=calculated_total_with_gst),
                            "context": current_state}
                else:
                    return {"action": "ask_question", "status": "error",
                            "message": t("yes_no_prompt", language=language),
                            "context": current_state}

            else:  # Fallback for unexpected sub-status during items collection
                return {"action": "general_response", "status": "error",
                        "message": t("item_collection_error", language=language),
                        "context": current_state}
        
        # --- NEW LOGIC: Handle Total Amount Input and DIRECT Adjustment ---
        elif next_field_to_ask == 'total_amount':
            try:
                provided_total = float(text.strip())
                if provided_total <= 0:
                    raise ValueError("Total amount must be positive.")
                
                calculated_total_with_gst = current_state.get('calculated_total_with_gst', 0.0)
                
                difference = round(provided_total - calculated_total_with_gst, PRECISION)

                if abs(difference) < 0.01: # Use a small epsilon for floating point comparison
                    # Amounts match, proceed to custom fields
                    current_invoice_data['final_total_override'] = provided_total # Store the final total for invoice_manager
                    current_state['next_field'] = 'city_cf'
                    # Clear calculation-related state
                    current_state.pop('calculated_subtotal', None)
                    current_state.pop('calculated_gst_amount', None)
                    current_state.pop('calculated_total_with_gst', None)
                    current_state.pop('provided_total_amount', None)
                    
                    return {"action": "ask_question", "status": "info",
                            "message": t("total_amount_matches_proceed_custom_fields", language=language),
                            "context": current_state}
                else:
                    # Amounts do not match, DIRECTLY ADJUST prices (skip confirmation)
                    provided_total_amount_from_state = current_state.get('provided_total_amount') # This would be provided_total from current turn
                    calculated_subtotal_from_items = current_state.get('calculated_subtotal') # Base subtotal from current items

                    # Use provided_total (current input) for adjustment, not provided_total_amount_from_state
                    # provided_total = text.strip() # Already converted to float at top of this block

                    if provided_total is None or calculated_subtotal_from_items is None: # Use current provided_total here
                        return {"action": "general_response", "status": "error",
                                "message": t("adjustment_error_missing_data", language=language),
                                "context": current_state}

                    # Calculate the desired subtotal needed to reach 'provided_total' after GST
                    # This is the base amount that, when GST is added, results in provided_total
                    desired_subtotal_from_provided_total = round(provided_total / (1 + GST_RATE), PRECISION + 4) # Use higher precision for intermediate calculation
                    
                    adjusted_items = []
                    if calculated_subtotal_from_items == 0:
                        # If original subtotal is zero, and user provides a total,
                        # we cannot proportionately adjust rates. We must apply the total as a final override.
                        print(f"WARNING: Calculated subtotal is zero, cannot adjust item rates proportionately. Final invoice total will be forced to {provided_total:.2f}.")
                        current_invoice_data['final_total_override'] = provided_total # Store the provided total
                        current_state['next_field'] = 'city_cf'
                        # Clear calculation-related state
                        current_state.pop('calculated_subtotal', None)
                        current_state.pop('calculated_gst_amount', None)
                        current_state.pop('calculated_total_with_gst', None)
                        current_state.pop('provided_total_amount', None) # Clear it
                        
                        return {"action": "ask_question", "status": "info",
                                "message": t("calculated_subtotal_zero_adjust_total", language=language, provided_total=provided_total),
                                "context": current_state}
                    
                    # Calculate the scaling factor for item rates based on desired subtotal
                    scaling_factor = desired_subtotal_from_provided_total / calculated_subtotal_from_items

                    adjusted_items_for_zoho = []
                    for item in current_invoice_data['selected_items']:
                        original_rate = item['rate']
                        adjusted_rate = round(original_rate * scaling_factor, PRECISION + 2) # Apply scaling, higher precision for sending to Zoho
                        adjusted_items_for_zoho.append({
                            "item_id": item['item_id'],
                            "quantity": item['quantity'],
                            "rate": adjusted_rate # Update rate to adjusted rate
                        })
                    
                    current_invoice_data['selected_items'] = adjusted_items_for_zoho # Update selected_items with adjusted rates
                    current_invoice_data['final_total_override'] = provided_total # Store the provided total for invoice_manager to use as the final total
                    
                    current_state['next_field'] = 'city_cf'
                    # Clear all calculation/adjustment related state
                    current_state.pop('calculated_subtotal', None)
                    current_state.pop('calculated_gst_amount', None)
                    current_state.pop('calculated_total_with_gst', None)
                    current_state.pop('provided_total_amount', None) # Clear it

                    return {"action": "ask_question", "status": "info",
                            "message": t("item_prices_adjusted_proceed_custom_fields", language=language, provided_total=provided_total),
                            "context": current_state}

            except ValueError:
                return {"action": "ask_question", "status": "error",
                        "message": t("invalid_total_amount", language=language),
                        "context": current_state}
        
        # --- REMOVED THE 'adjust_prices_confirmation' BLOCK AS PER USER REQUEST ---
        # elif next_field_to_ask == 'adjust_prices_confirmation':
        #    ... (this entire block is removed) ...

        elif next_field_to_ask == 'city_cf':
            current_invoice_data['city_cf'] = text.strip()
            current_state['next_field'] = 'code_cf'
            return {"action": "ask_question", "status": "info",
                    "message": t("ask_code_cf", language=language), "context": current_state}

        elif next_field_to_ask == 'code_cf':
            current_invoice_data['code_cf'] = text.strip()
            current_state['next_field'] = 'vehicle_cf'
            return {"action": "ask_question", "status": "info",
                    "message": t("ask_vehicle_cf", language=language),
                    "context": current_state}

        elif next_field_to_ask == 'vehicle_cf':
            current_invoice_data['vehicle_cf'] = text.strip() if text.strip() else ''

            try:
                access_token = get_access_token()
                
                # Retrieve the total amount to send to Zoho's create_invoice
                final_total_for_zoho = current_invoice_data.get('final_total_override')
                
                invoice_id = create_invoice(
                    current_invoice_data['customer_id'],
                    current_invoice_data['selected_items'], # This now contains adjusted rates if applicable
                    access_token,
                    current_invoice_data.get('city_cf', ''),
                    current_invoice_data.get('code_cf', ''),
                    current_invoice_data.get('vehicle_cf', ''),
                    final_total_amount=final_total_for_zoho # Pass the final desired total to invoice_manager
                )
                if invoice_id:
                    backend_base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
                    pdf_download_url = f"{backend_base_url}/download-invoice-pdf/{invoice_id}"
                    del conversation_states[session_id] # Clear session on completion
                    return {"action": "invoice_created", "status": "success",
                            "message": t("invoice_created", language=language, invoice_id=invoice_id),
                            "invoice_id": invoice_id,
                            "pdf_url": pdf_download_url}
                else:
                    del conversation_states[session_id]
                    return {"action": "invoice_creation_failed", "status": "error",
                            "message": t("invoice_creation_failed", language=language)}
            except Exception as e:
                del conversation_states[session_id]
                return {"action": "invoice_creation_error", "status": "error",
                        "message": t("invoice_creation_error", language=language, error_message=str(e))}

        # Fallback for invoice info collection
        return {"action": "general_response", "status": "error",
                "message": t("collecting_customer_details_fallback", language=language, next_field=next_field_to_ask), # Reusing for invoice flow as well
                "context": current_state}

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
                        "message": t("list_items_success", language=language, items_display=items_display), "data": items}
            else:
                return {"action": "list_items", "status": "info",
                        "message": t("no_items_found", language=language)}
        except Exception as e:
            return {"action": "list_items", "status": "error", "message": t("failed_to_fetch_items", language=language, error_message=str(e))}

    if "create customer" in text_lower:
        conversation_states[session_id] = {
            'status': 'collecting_customer_info',
            'next_field': 'phone_lookup',
            'customer_data': {},
            'language': language # Ensure language is carried forward
        }
        return {"action": "ask_question", "status": "info",
                "message": t("create_customer_prompt", language=language),
                "context": conversation_states[session_id]}

    if "create invoice" in text_lower:
        print(f"DEBUG: Matched 'create invoice' intent.")
        conversation_states[session_id] = {
            'status': 'collecting_invoice_info',
            'next_field': 'customer_phone_for_invoice',
            'invoice_data': {'selected_items': []},
            'language': language # This should ensure 'kn' is saved
        }
        print(f"DEBUG: Updated state for 'create invoice': {conversation_states[session_id]}")
        print(f"DEBUG: Calling t('create_invoice_prompt', language={language})")
        return {"action": "ask_question", "status": "info",
                "message": t("create_invoice_prompt", language=language), # THIS is the line to confirm
                "context": conversation_states[session_id]}


# --- File Upload Endpoint (unchanged) ---
# main.py

# ... (other imports and code) ...

# --- File Upload Endpoint (unchanged from functional perspective, but syntax fixed) ---
@app.post("/upload-document")
async def upload_document(request: Request, file: UploadFile = File(...)): # Moved request before file
    language = "kn" # Default language for file upload, can be extracted from headers if available
    if request.headers.get("accept-language"):
        # This is a very basic way to get language from headers, you might need a more robust parsing
        # For simplicity, let's just take the first part of the header
        header_lang = request.headers.get("accept-language").split(',')[0].strip().lower()
        if header_lang in ["en", "kn"]:
            language = header_lang

    try:
        upload_dir = "uploaded_files"
        os.makedirs(upload_dir, exist_ok=True)
        file_location = os.path.join(upload_dir, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "message": t("file_uploaded_success", language=language, file_name=file.filename),
                "action": "file_uploaded", "file_path": file_location}
    except Exception as e:
        return {"status": "error", "message": t("failed_to_upload_file", language=language, error_message=str(e)), "action": "error"}



# The `main()` function is a standalone script and should not interfere with FastAPI.
def main():
    pass


if __name__ == "__main__":
    main()