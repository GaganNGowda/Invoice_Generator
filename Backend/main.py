from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from io import BytesIO
import shutil
import os
import requests
import json

# Import OCR utility for unified image and PDF text extraction
from ocr_utils import extract_text_from_document

# Import AI assistant functions and Pydantic models for structured data
from ai_assistant import generate_invoice_from_text, InvoiceData, extract_contact_info_from_text, ContactInfo

# Import manager functions for interacting with Zoho
from customer_manager import find_customer, create_customer
from item_manager import get_items
from invoice_manager import create_invoice
from zoho_api import get_access_token

# Import API routers for modularity
from routes import customer, invoice

# NEW: Import for pincode matching
from pincode_matcher import find_nearest_pincode

# Initialize FastAPI application
app = FastAPI()

# Enable CORS for frontend communication (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WARNING: Use specific frontend origins in production (e.g., ["http://localhost:3000", "https://yourfrontend.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Consolidated Root Endpoint ---
@app.get("/")
def read_root():
    return {"message": "Backend for Invoice Assistant is running!"}

# --- OCR Endpoint (Unified for Images and PDFs) ---
@app.post("/process-ocr")
async def process_ocr(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        content_type = file.content_type

        if not content_type:
            raise ValueError("Could not determine content type of the uploaded file.")

        extracted_text = extract_text_from_document(contents, content_type)
        return {"text": extracted_text, "status": "success", "message": "Text extracted successfully."}
    except Exception as e:
        print(f"OCR Processing Error: {e}")
        return {"status": "error", "message": f"OCR processing failed: {e}"}

# --- AI-driven Invoice Generation Endpoint ---
@app.post("/generate-invoice")
async def generate_invoice(text: str = Form(...)):
    result = generate_invoice_from_text(text)
    return {"invoice": result}

app.include_router(customer.router, prefix="/customer", tags=["Customer"])
app.include_router(invoice.router, prefix="/invoice", tags=["Invoice"])

# --- Global Conversation State Management ---
conversation_states = {}

# --- Helper function to reset a specific conversation session's state ---
def reset_session_state(session_id: str):
    if session_id in conversation_states:
        del conversation_states[session_id]
        print(f"DEBUG: Session '{session_id}' state reset.")

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
    context_from_frontend = input_data.get("context", {})

    if not user_message:
        return {"status": "error", "message": "No text provided", "action": "error"}

    response_from_nlp = await process_user_input(user_message, session_id, context_from_frontend)
    return response_from_nlp


# --- Core Conversational Logic Function ---
async def process_user_input(text: str, session_id: str, incoming_context: dict):
    text_lower = text.lower().strip()
    
    current_state = conversation_states.get(session_id, {})
    current_state.update(incoming_context) # Merge incoming context (from FE) with BE state
    
    current_customer_data = current_state.get('customer_data', {})
    current_invoice_data = current_state.get('invoice_data', {})
    current_status = current_state.get('status')
    next_field_to_ask = current_state.get('next_field')
    invoice_sub_status = current_state.get('invoice_collection_sub_status')

    # --- 1. Handle Reset Command ---
    if text_lower == "reset_conversation_command":
        reset_session_state(session_id)
        return {"action": "reset_success", "status": "info", "message": "Chat has been reset. How can I help you now?"}

    # --- 2. Attempt Initial LLM Contact Info Extraction ---
    # This block attempts to extract general contact info from unstructured text (e.g., OCR output).
    extracted_contact_info: Optional[ContactInfo] = None
    # Heuristic: Only try extraction if not already in a specific flow and text is somewhat long/looks like info.
    if not current_status and len(text) > 20 and not any(cmd in text_lower for cmd in ["show items", "list items", "what items", "create customer", "create invoice"]):
        print(f"DEBUG: Attempting initial contact info extraction from general input: '{text[:50]}...'")
        extracted_contact_info = extract_contact_info_from_text(text)
        if extracted_contact_info:
            print(f"DEBUG: Successfully extracted contact info: {extracted_contact_info.dict()}")
            current_state['extracted_contact_info'] = extracted_contact_info.dict()
            conversation_states[session_id] = current_state # Update state with extracted info

            message = "I've extracted some contact details from your input. Do you want to create a new customer or an invoice using this information?"
            details = []
            if extracted_contact_info.name: details.append(f"Name: {extracted_contact_info.name}")
            if extracted_contact_info.phone_number: details.append(f"Phone: {extracted_contact_info.phone_number}")
            if extracted_contact_info.address: details.append(f"Address: {extracted_contact_info.address}")
            if extracted_contact_info.pincode: details.append(f"Pincode: {extracted_contact_info.pincode}")
            if details:
                message += f"\n\nExtracted: " + ", ".join(details)
            
            return {"action": "ask_question", "status": "info",
                    "message": message,
                    "context": current_state} # Return updated state

    # --- 3. Handle Active Customer Collection Flow (RESTRUCTURED LOGIC) ---
    if current_status == 'collecting_customer_info':
        llm_extracted_contact_info = None
        if 'extracted_contact_info' in current_state:
            llm_extracted_contact_info = ContactInfo(**current_state['extracted_contact_info'])

        # Prioritize pre-filling from LLM extracted data for the current 'next_field_to_ask'
        # If a field is pre-filled, update customer_data and advance next_field, then return the next question.
        # This prevents falling through to the general "didn't understand" if the original 'text' was not the direct answer.

        if next_field_to_ask == 'phone_lookup':
            if llm_extracted_contact_info and llm_extracted_contact_info.phone_number:
                current_customer_data['phone'] = llm_extracted_contact_info.phone_number
                print(f"DEBUG: Pre-filled phone_lookup with LLM extracted phone: {llm_extracted_contact_info.phone_number}")
                current_state['next_field'] = 'first_name' # Advance state
                conversation_states[session_id] = current_state
                # Immediately return to process this pre-fill
                return await process_user_input(llm_extracted_contact_info.phone_number, session_id, current_state)
            else: # If not pre-filled by LLM, expect user to provide it now
                phone_number_for_lookup = text.strip()
                if not phone_number_for_lookup.isdigit() and not phone_number_for_lookup.replace('+', '').replace(' ', '').isdigit():
                    return {"action": "ask_question", "status": "error",
                            "message": "Invalid phone number format. Please enter a valid phone number (digits only, or with '+' and spaces).",
                            "context": current_state}
                current_customer_data['phone'] = phone_number_for_lookup # Store valid input
                current_state['next_field'] = 'first_name' # Advance state
                conversation_states[session_id] = current_state
                # Now try to find customer or ask for first name
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
                            current_state.pop('customer_data', None)
                            current_state.pop('return_flow', None)
                            current_state.pop('return_phone', None)
                            current_state.pop('extracted_contact_info', None)
                            conversation_states[session_id] = current_state
                            all_items = get_items(access_token)
                            current_state['all_available_items'] = all_items
                            if all_items:
                                items_display_list = [f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})" for i, item in enumerate(all_items)]
                                items_display_message = "\n".join(items_display_list)
                                return {"action": "ask_question", "status": "info",
                                        "message": f"✅ Customer found! Using ID {found_contact_id} for invoice. Now, please select an item by number:\n{items_display_message}",
                                        "context": current_state}
                            else:
                                return {"action": "ask_question", "status": "warning",
                                        "message": f"✅ Customer found! Using ID {found_contact_id} for invoice. No items found in your Zoho account. What is the item ID?",
                                        "context": current_state}
                        else:
                            reset_session_state(session_id)
                            return {"action": "customer_exists", "status": "info",
                                    "message": f"✅ Customer found! Contact ID: {found_contact_id}. How can I help you now?",
                                    "contact_id": found_contact_id}
                    else:
                        return {"action": "ask_question", "status": "info",
                                "message": "❌ Customer not found with that phone number. Let's create a new one. What is their first name?",
                                "context": current_state}
                except Exception as e:
                    reset_session_state(session_id)
                    return {"action": "customer_lookup_error", "status": "error",
                            "message": f"An error occurred during customer lookup: {e}. Please try again.",
                            "context": current_state}

        elif next_field_to_ask == 'first_name':
            if llm_extracted_contact_info and llm_extracted_contact_info.name:
                first_name_llm = llm_extracted_contact_info.name.split(' ')[0]
                if first_name_llm:
                    current_customer_data['first_name'] = first_name_llm
                    print(f"DEBUG: Pre-filled first_name with LLM extracted name: {first_name_llm}")
                    current_state['next_field'] = 'last_name' # Advance state
                    conversation_states[session_id] = current_state
                    return {"action": "ask_question", "status": "info", "message": "What is the customer's last name?", "context": current_state}
            # If not pre-filled by LLM, use user's input
            current_customer_data['first_name'] = text
            current_state['next_field'] = 'last_name'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is the customer's last name?",
                    "context": current_state}

        elif next_field_to_ask == 'last_name':
            if llm_extracted_contact_info and len(llm_extracted_contact_info.name.split(' ')) > 1:
                last_name_llm = " ".join(llm_extracted_contact_info.name.split(' ')[1:])
                current_customer_data['last_name'] = last_name_llm
                print(f"DEBUG: Pre-filled last_name with LLM extracted name: {last_name_llm}")
                current_state['next_field'] = 'salutation' # Advance state
                conversation_states[session_id] = current_state
                return {"action": "ask_question", "status": "info", "message": "What is their salutation (Mr./Ms./Dr.)?", "context": current_state}
            # If not pre-filled by LLM, use user's input
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
            if llm_extracted_contact_info and llm_extracted_contact_info.address:
                current_customer_data['address'] = llm_extracted_contact_info.address
                print(f"DEBUG: Pre-filled address with LLM extracted address: {llm_extracted_contact_info.address}")
                current_state['next_field'] = 'city' # Advance state
                conversation_states[session_id] = current_state
                return {"action": "ask_question", "status": "info", "message": "Which city do they live in?", "context": current_state}
            # If not pre-filled by LLM, use user's input
            current_customer_data['address'] = text
            current_state['next_field'] = 'city'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "Which city do they live in?",
                    "context": current_state}

        elif next_field_to_ask == 'city':
            if llm_extracted_contact_info and llm_extracted_contact_info.city:
                current_customer_data['city'] = llm_extracted_contact_info.city
                print(f"DEBUG: Pre-filled city with LLM extracted city: {llm_extracted_contact_info.city}")
                current_state['next_field'] = 'state' # Advance state
                conversation_states[session_id] = current_state
                return {"action": "ask_question", "status": "info", "message": "What is their state?", "context": current_state}
            # If not pre-filled by LLM, use user's input
            current_customer_data['city'] = text
            current_state['next_field'] = 'state'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is their state?",
                    "context": current_state}

        elif next_field_to_ask == 'state':
            if llm_extracted_contact_info and llm_extracted_contact_info.state:
                current_customer_data['state'] = llm_extracted_contact_info.state
                print(f"DEBUG: Pre-filled state with LLM extracted state: {llm_extracted_contact_info.state}")
                current_state['next_field'] = 'zip_code' # Advance state
                conversation_states[session_id] = current_state
                return {"action": "ask_question", "status": "info", "message": "What is their ZIP Code?", "context": current_state}
            # If not pre-filled by LLM, use user's input
            current_customer_data['state'] = text
            current_state['next_field'] = 'zip_code'
            conversation_states[session_id] = current_state
            return {"action": "ask_question", "status": "info", "message": "What is their ZIP Code?",
                    "context": current_state}

        elif next_field_to_ask == 'zip_code':
            target_pincode_str = text.strip() # This is the user's input or LLM pre-fill

            # Attempt to find the nearest pincode from CSV
            nearest_csv_pincode = find_nearest_pincode(target_pincode_str, 'branch_list 2.csv')

            if nearest_csv_pincode:
                current_customer_data['zip_code'] = nearest_csv_pincode
                current_state['next_field'] = 'phone' # Advance state
                conversation_states[session_id] = current_state
                return {"action": "ask_question", "status": "info",
                        "message": f"Found a nearest matching pincode: **{nearest_csv_pincode}**. Using this for the customer. What is their phone number?",
                        "context": current_state}
            else: # If no nearest match found in CSV
                # Basic validation for 6-digit number if no CSV match
                if not (target_pincode_str.isdigit() and len(target_pincode_str) == 6):
                    return {"action": "ask_question", "status": "error",
                            "message": "Invalid ZIP Code. Please enter a 6-digit number. (No close match found in our branches)",
                            "context": current_state}
                current_customer_data['zip_code'] = target_pincode_str
                current_state['next_field'] = 'phone'
                conversation_states[session_id] = current_state
                return {"action": "ask_question", "status": "info", "message": "What is their phone number?",
                        "context": current_state}

        elif next_field_to_ask == 'phone':
            if llm_extracted_contact_info and llm_extracted_contact_info.phone_number:
                phone_num_llm = llm_extracted_contact_info.phone_number
                # Clean LLM extracted phone number to be digits only for validation
                phone_num_llm = ''.join(filter(str.isdigit, phone_num_llm))
                if phone_num_llm: # Only pre-fill if LLM actually provided digits
                    current_customer_data['phone'] = phone_num_llm
                    print(f"DEBUG: Pre-filled phone with LLM extracted phone: {phone_num_llm}")
                    current_state['next_field'] = 'place_of_contact' # Advance state
                    conversation_states[session_id] = current_state
                    return {"action": "ask_question", "status": "info", "message": "Finally, what is their Place of Contact (e.g., KA for Karnataka)? (Press Enter for default: KA)", "context": current_state}
            # If not pre-filled by LLM, use user's input
            current_phone_input = text.strip()
            if 'phone' not in current_customer_data or (current_phone_input and (
                    not current_customer_data['phone'] or current_customer_data['phone'] != current_phone_input)):
                current_customer_data['phone'] = current_phone_input

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
                    "city": current_customer_data.get('city', ''),
                    "address": current_customer_data.get('address', ''),
                    "state": current_customer_data.get('state', ''),
                    "zip": current_customer_data.get('zip_code', ''),
                    "phone": current_customer_data.get('phone', '')
                },
                "shipping_address": {
                    "country": "India",
                    "city": current_customer_data.get('city', ''),
                    "address": current_customer_data.get('address', ''),
                    "state": current_customer_data.get('state', ''),
                    "zip": current_customer_data.get('zip_code', ''),
                    "phone": current_customer_data.get('phone', '')
                },
                "contact_persons": [
                    {
                        "first_name": current_customer_data.get('first_name', ''),
                        "last_name": current_customer_data.get('last_name', ''),
                        "mobile": current_customer_data.get('phone', ''),
                        "phone": current_customer_data.get('phone', ''),
                        "email": "",
                        "salutation": current_customer_data.get('salutation', ''),
                        "is_primary_contact": True
                    }
                ],
                "is_taxable": True,
                "language_code": "en",
                "gst_treatment": "consumer",
                "place_of_contact": current_customer_data.get('place_of_contact', ''),
                "customer_sub_type": "individual"
            }

            try:
                access_token = get_access_token()
                re_check_contact_id = find_customer(full_name, current_customer_data.get('city', ''),
                                                    current_customer_data.get('phone', ''), token=access_token)
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
                        current_state.pop('extracted_contact_info', None)
                        conversation_states[session_id] = current_state
                        all_items = get_items(access_token)
                        current_state['all_available_items'] = all_items
                        if all_items:
                            items_display_list = [f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})" for i, item in enumerate(all_items)]
                            items_display_message = "\n".join(items_display_list)
                            return {"action": "ask_question", "status": "info",
                                    "message": f"✅ Customer found! Using ID {re_check_contact_id} for invoice. Now, please select an item by number:\n{items_display_message}",
                                    "context": current_state}
                        else:
                            return {"action": "ask_question", "status": "warning",
                                    "message": f"✅ Customer found! Using ID {re_check_contact_id} for invoice. No items found in your Zoho account. What is the item ID?",
                                    "context": current_state}
                    else:
                        reset_session_state(session_id)
                        return {"action": "customer_exists", "status": "info",
                                "message": f"✅ Customer found! Contact ID: {re_check_contact_id}. How can I help you now?",
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
                            current_state.pop('extracted_contact_info', None)
                            conversation_states[session_id] = current_state
                            all_items = get_items(access_token)
                            current_state['all_available_items'] = all_items
                            if all_items:
                                items_display_list = [f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})" for i, item in enumerate(all_items)]
                                items_display_message = "\n".join(items_display_list)
                                return {"action": "ask_question", "status": "info",
                                        "message": f"✅ New customer created with ID {contact_id}. Using this for invoice. Now, please select an item by number:\n{items_display_message}",
                                        "context": current_state}
                            else:
                                return {"action": "ask_question", "status": "warning",
                                        "message": f"✅ New customer created with ID {contact_id}. Using this for invoice. No items found in your Zoho account. What is the item ID?",
                                        "context": current_state}
                        else:
                            reset_session_state(session_id)
                            return {"action": "customer_created", "status": "success",
                                    "message": f"✅ New customer created with contact ID: {contact_id}",
                                    "contact_id": contact_id}
                    else:
                        reset_session_state(session_id)
                        return {"action": "customer_creation_failed", "status": "error",
                                "message": "❌ Failed to create customer."}
            except Exception as e:
                reset_session_state(session_id)
                return {"action": "customer_creation_error", "status": "error",
                        "message": f"An error occurred during customer creation/lookup: {e}",
                        "context": current_state}

        # Fallback if in customer collection but current input doesn't match expected field
        return {"action": "general_response", "status": "error",
                "message": f"I'm still collecting customer details, specifically the '{next_field_to_ask}'. Please provide that information.",
                "context": current_state}

    # --- 4. Handle Active Invoice Collection Flow (RESTRUCTURED LOGIC) ---
    if current_status == 'collecting_invoice_info':
        llm_extracted_contact_info = None
        if 'extracted_contact_info' in current_state:
            llm_extracted_contact_info = ContactInfo(**current_state['extracted_contact_info'])

        if next_field_to_ask == 'customer_phone_for_invoice':
            if llm_extracted_contact_info and llm_extracted_contact_info.phone_number:
                phone_number_for_invoice = llm_extracted_contact_info.phone_number
                print(f"DEBUG: Pre-filling customer_phone_for_invoice with LLM extracted phone: {phone_number_for_invoice}")
                current_invoice_data['customer_phone_for_invoice'] = phone_number_for_invoice # Store it in invoice_data
                current_state['next_field'] = 'items' # Advance state
                conversation_states[session_id] = current_state
                # Immediately return to process this pre-fill
                return await process_user_input(phone_number_for_invoice, session_id, current_state)
            else: # If not pre-filled by LLM, expect user to provide it now
                phone_number_for_invoice = text.strip()
                if not phone_number_for_invoice.isdigit() and not phone_number_for_invoice.replace('+', '').replace(' ', '').isdigit():
                    return {"action": "ask_question", "status": "error",
                            "message": "Invalid phone number format. Please enter a valid phone number for the customer (digits only, or with '+' and spaces).",
                            "context": current_state}
                current_invoice_data['customer_phone_for_invoice'] = phone_number_for_invoice # Store valid input
                current_state['next_field'] = 'items' # Advance state
                conversation_states[session_id] = current_state
                # Now try to find customer or ask for first name (will transition to customer flow if not found)
                try:
                    access_token = get_access_token()
                    found_contact_id = find_customer(name="", city="", phone=phone_number_for_invoice, token=access_token)

                    if found_contact_id:
                        current_invoice_data['customer_id'] = found_contact_id
                        current_invoice_data['selected_items'] = current_invoice_data.get('selected_items', [])
                        current_state['next_field'] = 'items'
                        current_state['invoice_collection_sub_status'] = 'asking_item_number'
                        current_state.pop('extracted_contact_info', None)
                        conversation_states[session_id] = current_state
                        all_items = get_items(access_token)
                        current_state['all_available_items'] = all_items
                        if all_items:
                            items_display_list = [f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})" for i, item in enumerate(all_items)]
                            items_display_message = "\n".join(items_display_list)
                            return {"action": "ask_question", "status": "info",
                                    "message": f"✅ Customer found! Using ID {found_contact_id} for invoice. Now, please select an item by number:\n{items_display_message}",
                                    "context": current_state}
                        else:
                            return {"action": "ask_question", "status": "warning",
                                    "message": f"✅ Customer found! Using ID {found_contact_id} for invoice. No items found in your Zoho account. What is the item ID?",
                                    "context": current_state}
                    else:
                        current_state['status'] = 'collecting_customer_info' # Transition to customer creation
                        current_state['next_field'] = 'first_name'
                        current_state['customer_data'] = {'phone': phone_number_for_invoice}
                        current_state['return_flow'] = 'collecting_invoice_info'
                        current_state['return_phone'] = phone_number_for_invoice
                        conversation_states[session_id] = current_state
                        return {"action": "ask_question", "status": "info",
                                "message": "❌ Customer not found with that phone number. Let's create a new customer first. What is their first name?",
                                "context": current_state}
                except Exception as e:
                    reset_session_state(session_id)
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
                        items_display_list.append(
                            f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})"
                        )
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

            else:
                return {"action": "general_response", "status": "error",
                        "message": "I'm in the middle of item collection, but something went wrong. Please try restarting invoice creation or specify the item number.",
                        "context": current_state}

        elif next_field_to_ask == 'city_cf':
            if llm_extracted_contact_info and llm_extracted_contact_info.city:
                current_invoice_data['city_cf'] = llm_extracted_contact_info.city
                print(f"DEBUG: Pre-filled city_cf with LLM extracted city: {llm_extracted_contact_info.city}")
                current_state['next_field'] = 'code_cf' # Advance state
                conversation_states[session_id] = current_state
                return {"action": "ask_question", "status": "info", "message": "What is the total items code for the custom field?", "context": current_state}
            # If not pre-filled by LLM, use user's input
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
                    current_invoice_data.get('customer_id', ''),
                    current_invoice_data.get('selected_items', []),
                    access_token,
                    current_invoice_data.get('city_cf', ''),
                    current_invoice_data.get('code_cf', ''),
                    current_invoice_data.get('vehicle_cf', '')
                )
                if invoice_id:
                    backend_base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
                    pdf_download_url = f"{backend_base_url}/download-invoice-pdf/{invoice_id}"
                    reset_session_state(session_id)
                    return {"action": "invoice_created", "status": "success",
                            "message": f"✅ Invoice created successfully with ID: {invoice_id}.",
                            "invoice_id": invoice_id,
                            "pdf_url": pdf_download_url}
                else:
                    reset_session_state(session_id)
                    return {"action": "invoice_creation_failed", "status": "error",
                            "message": "❌ Failed to create invoice."}
            except Exception as e:
                reset_session_state(session_id)
                return {"action": "invoice_creation_error", "status": "error",
                        "message": f"An error occurred during invoice creation: {e}",
                        "context": current_state}

        # Fallback if in invoice collection but current input doesn't match expected field
        return {"action": "general_response", "status": "error",
                "message": f"I'm still collecting invoice details. Please provide the '{next_field_to_ask}'.",
                "context": current_state}

    # --- 5. Handle Initial Explicit Commands ---
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
        reset_session_state(session_id) # Ensure a clean start for customer creation
        conversation_states[session_id] = {
            'status': 'collecting_customer_info',
            'next_field': 'phone_lookup', # Default start point
            'customer_data': {}
        }
        # If LLM previously extracted contact info, try to pre-populate and advance flow
        if 'extracted_contact_info' in current_state:
            llm_extracted_contact_info = ContactInfo(**current_state['extracted_contact_info'])
            # Use a dummy text that will trigger the internal processing of phone_lookup
            # This is important because the 'text' variable holds the *original* user input (e.g., "create customer")
            # so we use a dummy value to trigger the pre-filling logic without causing validation errors on the original text.
            initial_prefill_text = llm_extracted_contact_info.phone_number or "prefill" # Use actual phone or a dummy

            # Call process_user_input recursively to immediately process the pre-filled steps
            # This ensures the conversation flows automatically through known data.
            return await process_user_input(initial_prefill_text, session_id, current_state)
        else:
            return {"action": "ask_question", "status": "info",
                    "message": "Okay, let's find or create a customer. What is their phone number?",
                    "context": conversation_states[session_id]}

    if "create invoice" in text_lower:
        reset_session_state(session_id)
        conversation_states[session_id] = {
            'status': 'collecting_invoice_info',
            'next_field': 'customer_phone_for_invoice',
            'invoice_data': {'selected_items': []}
        }
        # If LLM previously extracted contact info, try to pre-populate and advance flow
        if 'extracted_contact_info' in current_state:
            llm_extracted_contact_info = ContactInfo(**current_state['extracted_contact_info'])
            initial_prefill_text = llm_extracted_contact_info.phone_number or "prefill" # Use actual phone or a dummy
            return await process_user_input(initial_prefill_text, session_id, current_state)
        else:
            return {"action": "ask_question", "status": "info",
                    "message": "Okay, let's create an invoice. What is the customer's phone number?",
                    "context": conversation_states[session_id]}

    # --- 6. Attempt LLM-based Full Invoice Extraction (Fallback for complex inputs) ---
    print(f"DEBUG: Attempting LLM-based full invoice extraction for: '{text}'")
    structured_invoice_data: Optional[InvoiceData] = generate_invoice_from_text(text)

    if structured_invoice_data:
        print(f"DEBUG: LLM successfully extracted full invoice data: {structured_invoice_data.dict()}")
        try:
            access_token = get_access_token()

            customer_id_from_llm = None
            if structured_invoice_data.customer_phone:
                customer_id_from_llm = find_customer(name="", city="", phone=structured_invoice_data.customer_phone, token=access_token)
            if not customer_id_from_llm and structured_invoice_data.customer_name:
                customer_id_from_llm = find_customer(name=structured_invoice_data.customer_name, city="", phone="", token=access_token)

            if not customer_id_from_llm:
                reset_session_state(session_id)
                current_state = {
                    'status': 'collecting_customer_info',
                    'next_field': 'first_name',
                    'customer_data': {'phone': structured_invoice_data.customer_phone or '',
                                      'first_name': structured_invoice_data.customer_name.split(' ')[0] if structured_invoice_data.customer_name else ''},
                    'return_flow': 'collecting_invoice_info',
                    'return_invoice_data': structured_invoice_data.dict()
                }
                conversation_states[session_id] = current_state
                # Try to pre-fill customer creation based on extracted invoice data
                return await process_user_input("prefill", session_id, current_state) # Use a dummy text to trigger processing
            
            line_items_for_invoice = []
            all_available_items = get_items(access_token)
            for item_from_llm in structured_invoice_data.items:
                found_zoho_item = next(
                    (zi for zi in all_available_items if zi.get('name', '').lower() == item_from_llm.item_name.lower()),
                    None
                )
                if found_zoho_item:
                    line_items_for_invoice.append({
                        "item_id": found_zoho_item['item_id'],
                        "quantity": item_from_llm.quantity
                    })
                else:
                    print(f"WARNING: Item '{item_from_llm.item_name}' from LLM not found in Zoho. Initiating manual item selection.")
                    reset_session_state(session_id)
                    current_invoice_data['customer_id'] = customer_id_from_llm
                    current_invoice_data['selected_items'] = []
                    current_state = {
                        'status': 'collecting_invoice_info',
                        'next_field': 'items',
                        'invoice_collection_sub_status': 'asking_item_number',
                        'all_available_items': all_available_items,
                        'invoice_data': current_invoice_data
                    }
                    conversation_states[session_id] = current_state
                    items_display_list = [f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})" for i, item in enumerate(all_available_items)]
                    items_display_message = "\n".join(items_display_list)
                    return {"action": "ask_question", "status": "warning",
                            "message": f"I extracted some invoice details, but some items weren't found in your Zoho account. Let's create the invoice step-by-step. Customer found! Now, please select an item by number:\n{items_display_message}",
                            "context": current_state}

            if not line_items_for_invoice:
                reset_session_state(session_id)
                current_invoice_data['customer_id'] = customer_id_from_llm
                current_invoice_data['selected_items'] = []
                current_state = {
                    'status': 'collecting_invoice_info',
                    'next_field': 'items',
                    'invoice_collection_sub_status': 'asking_item_number',
                    'all_available_items': all_available_items,
                    'invoice_data': current_invoice_data
                }
                conversation_states[session_id] = current_state
                items_display_list = [f"{i + 1}. {item.get('name', 'N/A')} (ID: {item.get('item_id', 'N/A')}, Rate: {item.get('rate', 'N/A')})" for i, item in enumerate(all_available_items)]
                items_display_message = "\n".join(items_display_list)
                return {"action": "ask_question", "status": "warning",
                        "message": f"I extracted some invoice details, but no valid items were identified. Let's create the invoice step-by-step. Customer found! Now, please select an item by number:\n{items_display_message}",
                        "context": current_state}

            invoice_id = create_invoice(
                current_customer_data.get('customer_id', customer_id_from_llm), # Use customer_id from current_customer_data (if updated by sub-flow) or LLM
                line_items_for_invoice,
                access_token,
                structured_invoice_data.city_cf or '',
                structured_invoice_data.code_cf or '',
                structured_invoice_data.vehicle_cf or ''
            )
            if invoice_id:
                backend_base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
                pdf_download_url = f"{backend_base_url}/download-invoice-pdf/{invoice_id}"
                reset_session_state(session_id)
                return {"action": "invoice_created", "status": "success",
                        "message": f"✅ Invoice created successfully from extracted text with ID: {invoice_id}.",
                        "invoice_id": invoice_id,
                        "pdf_url": pdf_download_url}
            else:
                reset_session_state(session_id)
                return {"action": "invoice_creation_failed", "status": "error",
                        "message": "❌ Failed to create invoice after LLM extraction. Missing info or Zoho API issue."}

        except Exception as e:
            print(f"ERROR: Error during invoice creation after LLM extraction: {e}")
            reset_session_state(session_id)
            conversation_states[session_id] = {
                'status': 'collecting_invoice_info',
                'next_field': 'customer_phone_for_invoice',
                'invoice_data': {'selected_items': []}
            }
            return {"action": "ask_question", "status": "error",
                    "message": f"I had trouble processing the extracted invoice data: {e}. Let's try creating the invoice step-by-step. What is the customer's phone number?",
                    "context": conversation_states[session_id]}

    # --- 7. Default Response (Initiate Guided Flow if nothing else matched) ---
    reset_session_state(session_id)
    conversation_states[session_id] = {
        'status': 'collecting_invoice_info',
        'next_field': 'customer_phone_for_invoice',
        'invoice_data': {'selected_items': []}
    }
    return {"action": "ask_question", "status": "info",
            "message": "I couldn't fully understand your request, but I can help you create an invoice. What is the customer's phone number?",
            "context": conversation_states[session_id]}


# --- File Upload Endpoint (General Purpose) ---
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


# The `main()` function is a standalone script and should not interfere with FastAPI's
# lifecycle. FastAPI applications are typically run using `uvicorn`.
def main():
    pass

if __name__ == "__main__":
    main()

