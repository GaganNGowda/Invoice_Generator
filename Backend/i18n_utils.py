# i18n_utils.py

TRANSLATIONS = {
    "en": {
        "reset_success": "Chat has been reset. How can I help you now?",
        "invalid_phone_format": "Invalid phone number format. Please enter a valid phone number (digits only, or with '+' and spaces).",
        "customer_not_found_create": "❌ Customer not found with that phone number. Let's create a new one. What is their first name?",
        "customer_found_for_invoice": "✅ Customer found! Using ID {contact_id} for invoice. Now, please select an item by number:\n{items_display_message}",
        "customer_found_for_invoice_no_items": "✅ Customer found! Using ID {contact_id} for invoice. No items found in your Zoho account. What is the item ID?",
        "customer_lookup_error": "An error occurred during customer lookup: {error_message}. Please try again.",
        "customer_exists": "✅ Customer found! Contact ID: {contact_id}. How can I help you now?",
        "ask_first_name": "What is their first name?",
        "ask_last_name": "What is the customer's last name?",
        "ask_salutation": "What is their salutation (Mr./Ms./Dr.)?",
        "ask_address": "What is their street address?",
        "ask_city": "Which city do they live in?",
        "ask_state": "What is their state?",
        "ask_zip_code": "What is their ZIP Code?",
        "ask_phone": "What is their phone number?",
        "invalid_phone_number": "Invalid phone number. Please enter a valid phone number (digits only).",
        "ask_place_of_contact": "Finally, what is their Place of Contact (e.g., KA for Karnataka)? (Press Enter for default: KA)",
        "customer_created": "✅ New customer created with contact ID: {contact_id}",
        "customer_creation_failed": "❌ Failed to create customer.",
        "customer_creation_error": "An error occurred during customer creation/lookup: {error_message}",
        "collecting_customer_details_fallback": "I'm still collecting customer details. Please provide the customer's {next_field}.",
        "invalid_item_number": "Invalid item number. Please select an item from the list by its number.",
        "enter_valid_number": "Please enter a valid number for the item selection.",
        "ask_quantity": "How many '{item_name}' do you need?",
        "item_added_ask_more": "Added {quantity} x '{item_name}'. Do you want to add another item? (yes/no or y/n)",
        "invalid_quantity": "Invalid quantity. Please enter a whole number greater than zero.",
        "ask_more_items_prompt": "Okay, select next item by number:\n{items_display_message}",
        "yes_no_prompt": "Please respond with 'yes' or 'no' (y/n). Do you want to add another item?",
        "item_collection_error": "I'm in the middle of item collection, but something went wrong. Please try restarting invoice creation or specify the item number.",
        "ask_total_amount": "Okay, I have recorded your items. The calculated subtotal is {calculated_subtotal:.2f}, GST ({gst_rate_percent}%) is {calculated_gst_amount:.2f}, making the calculated total: **{calculated_total_with_gst:.2f}**. What is the final total amount you expect for this invoice?",
        "invalid_total_amount": "Invalid total amount. Please enter a valid number.",
        "total_amount_matches_proceed_custom_fields": "Total amount matches! Proceeding with invoice creation. What is the city for the custom field?",
        "calculated_subtotal_zero_adjust_total": "Calculated subtotal was zero. Cannot adjust individual item prices proportionately. Using provided total **{provided_total:.2f}** for the invoice. What is the city for the custom field?",
        "item_prices_adjusted_proceed_custom_fields": "Item prices have been adjusted to match the total **{provided_total:.2f}**. Proceeding to custom fields. What is the city for the custom field?",
        "adjustment_error_missing_data": "Error in adjustment logic (missing initial total or subtotal). Please try re-entering the total amount.",
        "ask_city_cf": "What is the city for the custom field?",
        "ask_code_cf": "What is the total items code for the custom field?",
        "ask_vehicle_cf": "What is the vehicle number for the custom field? (Optional, press Enter to skip)",
        "invoice_created": "✅ Invoice created successfully with ID: {invoice_id}.",
        "invoice_creation_failed": "❌ Failed to create invoice.",
        "invoice_creation_error": "An error occurred during invoice creation: {error_message}",
        "list_items_success": "Here are your items:\n{items_display}",
        "no_items_found": "No items found in your Zoho Invoice account.",
        "failed_to_fetch_items": "Failed to fetch items: {error_message}",
        "create_customer_prompt": "Okay, let's find or create a customer. What is their phone number?",
        "create_invoice_prompt": "Okay, let's create an invoice. What is the customer's phone number?",
        "general_fallback_message": "You said: '{text}'. I'm still learning to understand complex requests. How else can I help with invoices?",
        "no_text_provided": "No text provided",
        "file_uploaded_success": "File '{file_name}' uploaded successfully!",
        "failed_to_upload_file": "Failed to upload file: {error_message}",
        "backend_running": "Backend is running!"
    },
    "kn": {
        "reset_success": "ಚಾಟ್ ಅನ್ನು ಮರುಹೊಂದಿಸಲಾಗಿದೆ. ಈಗ ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
        "invalid_phone_format": "ಅಮಾನ್ಯ ಫೋನ್ ಸಂಖ್ಯೆ ಸ್ವರೂಪ. ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ಫೋನ್ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ (ಅಂಕೆಗಳು ಮಾತ್ರ, ಅಥವಾ '+' ಮತ್ತು ಸ್ಥಳಗಳೊಂದಿಗೆ).",
        "customer_not_found_create": "❌ ಆ ಫೋನ್ ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಗ್ರಾಹಕರು ಕಂಡುಬಂದಿಲ್ಲ. ಹೊಸದನ್ನು ರಚಿಸೋಣ. ಅವರ ಮೊದಲ ಹೆಸರು ಏನು?",
        "customer_found_for_invoice": "✅ ಗ್ರಾಹಕರು ಸಿಕ್ಕಿದ್ದಾರೆ! ಇನ್‌ವಾಯ್ಸ್‌ಗಾಗಿ ID {contact_id} ಅನ್ನು ಬಳಸಲಾಗುತ್ತಿದೆ. ಈಗ, ದಯವಿಟ್ಟು ಸಂಖ್ಯೆಯ ಮೂಲಕ ಐಟಂ ಅನ್ನು ಆಯ್ಕೆಮಾಡಿ:\n{items_display_message}",
        "customer_found_for_invoice_no_items": "✅ ಗ್ರಾಹಕರು ಸಿಕ್ಕಿದ್ದಾರೆ! ಇನ್‌ವಾಯ್ಸ್‌ಗಾಗಿ ID {contact_id} ಅನ್ನು ಬಳಸಲಾಗುತ್ತಿದೆ. ನಿಮ್ಮ Zoho ಖಾತೆಯಲ್ಲಿ ಯಾವುದೇ ಐಟಂಗಳು ಕಂಡುಬಂದಿಲ್ಲ. ಐಟಂ ID ಏನು?",
        "customer_lookup_error": "ಗ್ರಾಹಕರ ಹುಡುಕಾಟದ ಸಮಯದಲ್ಲಿ ದೋಷ ಸಂಭವಿಸಿದೆ: {error_message}. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        "customer_exists": "✅ ಗ್ರಾಹಕರು ಸಿಕ್ಕಿದ್ದಾರೆ! ಸಂಪರ್ಕ ID: {contact_id}. ಈಗ ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
        "ask_first_name": "ಅವರ ಮೊದಲ ಹೆಸರು ಏನು?",
        "ask_last_name": "ಗ್ರಾಹಕರ ಕೊನೆಯ ಹೆಸರು ಏನು?",
        "ask_salutation": "ಅವರ ಗೌರವ  (Mr./Ms./Dr.) ಏನು?",
        "ask_address": "ಅವರ ರಸ್ತೆ ವಿಳಾಸ ಏನು?",
        "ask_city": "ಅವರು ಯಾವ ನಗರದಲ್ಲಿ ವಾಸಿಸುತ್ತಿದ್ದಾರೆ?",
        "ask_state": "ಅವರ ರಾಜ್ಯ ಯಾವುದು?",
        "ask_zip_code": "ಅವರ ಪಿನ್ ಕೋಡ್ ಏನು?",
        "ask_phone": "ಅವರ ಫೋನ್ ಸಂಖ್ಯೆ ಏನು?",
        "invalid_phone_number": "ಅಮಾನ್ಯ ಫೋನ್ ಸಂಖ್ಯೆ. ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ಫೋನ್ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ (ಅಂಕೆಗಳು ಮಾತ್ರ).",
        "ask_place_of_contact": "ಕೊನೆಯದಾಗಿ, ಅವರ ಸಂಪರ್ಕದ ಸ್ಥಳ ಯಾವುದು (ಉದಾ. ಕರ್ನಾಟಕಕ್ಕೆ KA)? (ಡಿಫಾಲ್ಟ್‌ಗಾಗಿ Enter ಒತ್ತಿ: KA)",
        "customer_created": "✅ ಹೊಸ ಗ್ರಾಹಕರು ಸಂಪರ್ಕ ID ಯೊಂದಿಗೆ ರಚಿಸಲಾಗಿದೆ: {contact_id}",
        "customer_creation_failed": "❌ ಗ್ರಾಹಕರನ್ನು ರಚಿಸಲು ವಿಫಲವಾಗಿದೆ.",
        "customer_creation_error": "ಗ್ರಾಹಕರ ರಚನೆ/ಹುಡುಕಾಟದ ಸಮಯದಲ್ಲಿ ದೋಷ ಸಂಭವಿಸಿದೆ: {error_message}",
        "collecting_customer_details_fallback": "ನಾನು ಇನ್ನೂ ಗ್ರಾಹಕರ ವಿವರಗಳನ್ನು ಸಂಗ್ರಹಿಸುತ್ತಿದ್ದೇನೆ. ದಯವಿಟ್ಟು ಗ್ರಾಹಕರ {next_field} ಅನ್ನು ಒದಗಿಸಿ.",
        "invalid_item_number": "ಅಮಾನ್ಯ ಐಟಂ ಸಂಖ್ಯೆ. ದಯವಿಟ್ಟು ಪಟ್ಟಿಯಿಂದ ಅದರ ಸಂಖ್ಯೆಯ ಮೂಲಕ ಐಟಂ ಅನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
        "enter_valid_number": "ದಯವಿಟ್ಟು ಐಟಂ ಆಯ್ಕೆಗೆ ಮಾನ್ಯವಾದ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ.",
        "ask_quantity": "'{item_name}' ಎಷ್ಟು ಬೇಕು?",
        "item_added_ask_more": "{quantity} x '{item_name}' ಸೇರಿಸಲಾಗಿದೆ. ನೀವು ಇನ್ನೊಂದು ಐಟಂ ಅನ್ನು ಸೇರಿಸಲು ಬಯಸುವಿರಾ? (ಹೌದು/ಇಲ್ಲ ಅಥವಾ y/n)",
        "invalid_quantity": "ಅಮಾನ್ಯ ಪ್ರಮಾಣ. ದಯವಿಟ್ಟು ಸೊನ್ನೆಗಿಂತ ಹೆಚ್ಚಿನ ಪೂರ್ಣ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ.",
        "ask_more_items_prompt": "ಸರಿ, ಮುಂದಿನ ಐಟಂ ಅನ್ನು ಸಂಖ್ಯೆಯ ಮೂಲಕ ಆಯ್ಕೆಮಾಡಿ:\n{items_display_message}",
        "yes_no_prompt": "'ಹೌದು' ಅಥವಾ 'ಇಲ್ಲ' (ಹ/ಇ) ಎಂದು ಪ್ರತಿಕ್ರಿಯಿಸಿ. ನೀವು ಇನ್ನೊಂದು ಐಟಂ ಅನ್ನು ಸೇರಿಸಲು ಬಯಸುವಿರಾ?",
        "item_collection_error": "ನಾನು ಐಟಂ ಸಂಗ್ರಹದ ಮಧ್ಯೆ ಇದ್ದೇನೆ, ಆದರೆ ಏನೋ ತಪ್ಪಾಗಿದೆ. ದಯವಿಟ್ಟು ಇನ್‌ವಾಯ್ಸ್ ರಚನೆಯನ್ನು ಮರುಪ್ರಾರಂಭಿಸಲು ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಐಟಂ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ.",
        "ask_total_amount": "ಸರಿ, ನಾನು ನಿಮ್ಮ ಐಟಂಗಳನ್ನು ದಾಖಲಿಸಿದ್ದೇನೆ. ಲೆಕ್ಕ ಹಾಕಿದ ಉಪಮೊತ್ತ {calculated_subtotal:.2f}, GST ({gst_rate_percent}%) {calculated_gst_amount:.2f}, ಒಟ್ಟು ಲೆಕ್ಕ ಹಾಕಿದ ಮೊತ್ತ: **{calculated_total_with_gst:.2f}**. ಈ ಇನ್‌ವಾಯ್ಸ್‌ಗಾಗಿ ನೀವು ನಿರೀಕ್ಷಿಸುವ ಅಂತಿಮ ಒಟ್ಟು ಮೊತ್ತ ಎಷ್ಟು?",
        "invalid_total_amount": "ಅಮಾನ್ಯ ಒಟ್ಟು ಮೊತ್ತ. ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ.",
        "total_amount_matches_proceed_custom_fields": "ಒಟ್ಟು ಮೊತ್ತವು ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ! ಇನ್‌ವಾಯ್ಸ್ ರಚನೆಯೊಂದಿಗೆ ಮುಂದುವರಿಯಲಾಗುತ್ತಿದೆ. ಕಸ್ಟಮ್ ಫೀಲ್ಡ್‌ಗಾಗಿ ನಗರ ಯಾವುದು?",
        "calculated_subtotal_zero_adjust_total": "ಲೆಕ್ಕ ಹಾಕಿದ ಉಪಮೊತ್ತ ಶೂನ್ಯವಾಗಿತ್ತು. ಪ್ರತ್ಯೇಕ ಐಟಂ ಬೆಲೆಗಳನ್ನು ಅನುಪಾತದಲ್ಲಿ ಹೊಂದಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ಇನ್‌ವಾಯ್ಸ್‌ಗಾಗಿ ಒದಗಿಸಿದ ಒಟ್ಟು **{provided_total:.2f}** ಅನ್ನು ಬಳಸಲಾಗುತ್ತಿದೆ. ಕಸ್ಟಮ್ ಫೀಲ್ಡ್‌ಗಾಗಿ ನಗರ ಯಾವುದು?",
        "item_prices_adjusted_proceed_custom_fields": "ಐಟಂ ಬೆಲೆಗಳನ್ನು ಒಟ್ಟು **{provided_total:.2f}** ಗೆ ಹೊಂದಿಸಲಾಗಿದೆ. ಮುಂದುವರಿಯಲಾಗುತ್ತಿದೆ. ಕಸ್ಟಮ್ ಫೀಲ್ಡ್‌ಗಾಗಿ ನಗರ ಯಾವುದು?",
        "adjustment_error_missing_data": "ಹೊಂದಾಣಿಕೆ ತರ್ಕದಲ್ಲಿ ದೋಷ (ಆರಂಭಿಕ ಒಟ್ಟು ಅಥವಾ ಉಪಮೊತ್ತ ಕಾಣೆಯಾಗಿದೆ). ದಯವಿಟ್ಟು ಒಟ್ಟು ಮೊತ್ತವನ್ನು ಮರು ನಮೂದಿಸಲು ಪ್ರಯತ್ನಿಸಿ.",
        "ask_city_cf": "ಯಾವ ಜಿಲ್ಲೆ/ನಗರ?", 
        "ask_code_cf": "✅ ಒಟ್ಟು ಐಟಂಗಳು ಎಷ್ಟು??",
        "ask_vehicle_cf": "ವಾಹನ ಸಂಖ್ಯೆ ಏನು? (ಐಚ್ಛಿಕ, ಬಿಟ್ಟುಬಿಡಲು 0 ಒತ್ತಿ)",
        "invoice_created": "✅ ಇನ್‌ವಾಯ್ಸ್ ಯಶಸ್ವಿಯಾಗಿ ರಚಿಸಲಾಗಿದೆ ID: {invoice_id}.",
        "invoice_creation_failed": "❌ ಇನ್‌ವಾಯ್ಸ್ ರಚಿಸಲು ವಿಫಲವಾಗಿದೆ.",
        "invoice_creation_error": "ಇನ್‌ವಾಯ್ಸ್ ರಚನೆಯ ಸಮಯದಲ್ಲಿ ದೋಷ ಸಂಭವಿಸಿದೆ: {error_message}",
        "list_items_success": "ನಿಮ್ಮ ಐಟಂಗಳು ಇಲ್ಲಿವೆ:\n{items_display}",
        "no_items_found": "ನಿಮ್ಮ Zoho Invoice ಖಾತೆಯಲ್ಲಿ ಯಾವುದೇ ಐಟಂಗಳು ಕಂಡುಬಂದಿಲ್ಲ.",
        "failed_to_fetch_items": "ಐಟಂಗಳನ್ನು ಪಡೆಯಲು ವಿಫಲವಾಗಿದೆ: {error_message}",
        "create_customer_prompt": "ಸರಿ, ಗ್ರಾಹಕರನ್ನು ಹುಡುಕೋಣ ಅಥವಾ ರಚಿಸೋಣ. ಅವರ ಫೋನ್ ಸಂಖ್ಯೆ ಏನು?",
        "create_invoice_prompt": "ಸರಿ, ಇನ್‌ವಾಯ್ಸ್ ರಚಿಸೋಣ. ಗ್ರಾಹಕರ ಫೋನ್ ಸಂಖ್ಯೆ ಏನು?",
        "general_fallback_message": "ನೀವು ಹೇಳಿದಿರಿ: '{text}'. ಸಂಕೀರ್ಣ ವಿನಂತಿಗಳನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ನಾನು ಇನ್ನೂ ಕಲಿಯುತ್ತಿದ್ದೇನೆ. ಇನ್‌ವಾಯ್ಸ್‌ಗಳೊಂದಿಗೆ ನಾನು ಇನ್ನೇನು ಸಹಾಯ ಮಾಡಬಹುದು?",
        "no_text_provided": "ಯಾವುದೇ ಪಠ್ಯವನ್ನು ಒದಗಿಸಲಾಗಿಲ್ಲ",
        "file_uploaded_success": "ಫೈಲ್ '{file_name}' ಯಶಸ್ವಿಯಾಗಿ ಅಪ್‌ಲೋಡ್ ಆಗಿದೆ!",
        "failed_to_upload_file": "ಫೈಲ್ ಅಪ್‌ಲೋಡ್ ಮಾಡಲು ವಿಫಲವಾಗಿದೆ: {error_message}",
        "backend_running": "ಬ್ಯಾಕೆಂಡ್ ಚಾಲನೆಯಲ್ಲಿದೆ!"
    }
}

def t(key: str, language: str = "en", **kwargs) -> str:
    """
    Translates a given key into the specified language.
    If the key is not found in the specified language, it falls back to English.
    Supports f-string style formatting for placeholders.
    """
    lang_translations = TRANSLATIONS.get(language, TRANSLATIONS["en"]) # Fallback to English
    message = lang_translations.get(key, TRANSLATIONS["en"].get(key, f"Translation missing for '{key}'"))
    
    try:
        return message.format(**kwargs)
    except KeyError as e:
        print(f"WARNING: Placeholder {e} missing for translation key '{key}' in language '{language}'. Raw message: '{message}'")
        return message # Return raw message if placeholder is missing
    except AttributeError:
        # If message is not a string (e.g., None), just return it as is
        return message