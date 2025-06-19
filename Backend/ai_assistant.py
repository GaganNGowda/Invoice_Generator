# ai_assistant.py
# Updated imports for Pydantic v2 compatibility and newer LangChain Ollama client
from pydantic import BaseModel, Field, conint, ValidationError # Import ValidationError
from typing import List, Optional, Dict
import json # For parsing JSON strings

# For newer LangChain versions, Ollama client is in langchain-ollama package
# You might need to install: pip install -U langchain-ollama
from langchain_ollama import OllamaLLM # New import for Ollama LLM

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate


# --- Ollama LLM Initialization ---
# Initialize LLM instances once at the module level.
# This avoids re-initializing the LLM for every API call, improving performance.
llm_model_name = "llama3.2" # Define your desired Ollama model name here
llm_invoice_generator = None
llm_contact_extractor = None

try:
    # Attempt to initialize the Ollama LLM.
    # Set temperature to 0 for more deterministic and factual output, good for extraction tasks.
    llm_invoice_generator = OllamaLLM(model=llm_model_name, temperature=0.0)
    llm_contact_extractor = OllamaLLM(model=llm_model_name, temperature=0.0)
    print(f"DEBUG: Ollama LLM '{llm_model_name}' initialized successfully for invoice and contact extraction.")
except Exception as e:
    # Log an error if LLM initialization fails. This is crucial for debugging startup issues.
    print(f"ERROR: Failed to initialize Ollama LLM: {e}. "
          f"Make sure Ollama server is running and model '{llm_model_name}' is available via `ollama run {llm_model_name}`.")
    # In a production application, you might want to:
    # 1. Raise a critical error and stop the application if LLM is mandatory.
    # 2. Implement a retry mechanism.
    # 3. Use a fallback mechanism (e.g., return default responses or switch to rule-based logic).


# --- Pydantic Models for Structured Output ---
# These models define the schema for the JSON output we expect from the LLM.

# Model for individual items within an invoice
class InvoiceItem(BaseModel):
    item_name: str = Field(description="Name of the item")
    quantity: conint(gt=0) = Field(description="Quantity of the item, must be greater than zero")

# Model for the overall invoice data structure
class InvoiceData(BaseModel):
    customer_name: Optional[str] = Field(None, description="Full name of the customer")
    customer_phone: Optional[str] = Field(None, description="Phone number of the customer")
    items: List[InvoiceItem] = Field(description="List of items on the invoice")
    city_cf: Optional[str] = Field(None, description="City custom field for the invoice")
    code_cf: Optional[str] = Field(None, description="Total items code custom field for the invoice")
    vehicle_cf: Optional[str] = Field(None, description="Vehicle number custom field for the invoice")

# Model for extracting general contact information
class ContactInfo(BaseModel):
    name: Optional[str] = Field(None, description="Full name of the person or entity")
    phone_number: Optional[str] = Field(None, description="Phone number, including country code if available. Digits only.")
    address: Optional[str] = Field(None, description="Street address, building name, and other location details")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State name or abbreviation")
    pincode: Optional[str] = Field(None, description="Postal or ZIP code, digits only")
    country: Optional[str] = Field(None, description="Country name, default to India if not specified")


# --- LLM Invocation Functions ---

def generate_invoice_from_text(text: str) -> Optional[InvoiceData]:
    """
    Uses the LLM to extract comprehensive invoice details from a given text input.
    The LLM is prompted to produce a JSON object conforming to the InvoiceData schema.

    Args:
        text: The raw text from which to extract invoice details (e.g., OCR output).

    Returns:
        An instance of InvoiceData if successful, otherwise None.
    """
    if llm_invoice_generator is None:
        print("ERROR: LLM for invoice generation is not initialized. Cannot process request.")
        return None

    # We will get raw text from LLM, then parse it manually for robust error handling.
    # JsonOutputParser is good for generating format instructions, but direct parsing gives more control.
    temp_parser = JsonOutputParser(pydantic_object=InvoiceData) # Used just to get format instructions

    prompt = PromptTemplate(
        template="""You are an expert at extracting invoice details from text.
        Extract the following information and format it as a JSON object.
        DO NOT include any markdown code blocks (e.g., ```json). Just output the raw JSON.
        If a field is not found, omit it or set it to null/empty as per the schema.
        Ensure all quantities are positive integers.
        For items, 'item_name' and 'quantity' are required.

        {format_instructions}

        Information:
        {text_input}

        Extracted Invoice Data:
        """,
        input_variables=["text_input"],
        partial_variables={"format_instructions": temp_parser.get_format_instructions()},
    )

    chain = prompt | llm_invoice_generator # Chain produces raw text output from LLM

    try:
        # Invoke the chain to get the raw text response from the LLM
        llm_response_text = chain.invoke({"text_input": text})
        print(f"\n--- DEBUG (Invoice Extraction): Raw LLM Response ---\n{llm_response_text}\n--- END RAW LLM Response ---\n")

        # --- Explicitly parse JSON string and validate with Pydantic v2 ---
        # 1. Parse the JSON string into a Python dictionary
        parsed_dict = json.loads(llm_response_text)
        
        # 2. Validate the dictionary against the Pydantic model
        #    This will raise a ValidationError if the structure/types don't match.
        structured_invoice = InvoiceData.model_validate(parsed_dict)

        print(f"\n--- DEBUG (Invoice Extraction): Successfully Parsed Invoice Data ---\n{structured_invoice.dict()}\n--- END Parsed Invoice Data ---\n")
        return structured_invoice
    except json.JSONDecodeError as e:
        print(f"ERROR (Invoice Extraction): LLM did not return valid JSON: {e}")
        print(f"The LLM's raw response was:\n{llm_response_text}")
        return None
    except ValidationError as e:
        print(f"ERROR (Invoice Extraction): LLM output did not conform to InvoiceData schema: {e}")
        print(f"The LLM's raw response was:\n{llm_response_text}")
        return None
    except Exception as e:
        print(f"ERROR (Invoice Extraction): An unexpected error occurred during invoice data parsing: {e}")
        print(f"The LLM's raw response was:\n{llm_response_text}")
        return None


def extract_contact_info_from_text(text: str) -> Optional[ContactInfo]:
    """
    Uses the LLM to extract specific contact information (name, phone, address, city, state, pincode, country)
    from a given text input.
    The LLM is prompted to produce a JSON object conforming to the ContactInfo schema.

    Args:
        text: The raw text from which to extract contact details (e.g., OCR output, chat message).

    Returns:
        An instance of ContactInfo if successful, otherwise None.
    """
    if llm_contact_extractor is None:
        print("ERROR: LLM for contact extraction is not initialized. Cannot process request.")
        return None

    # JsonOutputParser is used primarily to generate format instructions for the LLM
    temp_parser = JsonOutputParser(pydantic_object=ContactInfo)

    prompt = PromptTemplate(
        template="""You are an expert at extracting contact details from any given text.
        Your goal is to identify the primary individual's or entity's full name,
        their phone number, street address, city, state, and pincode.
        
        Prioritize extracting the name of the main recipient or party the document is addressed to.

        Examples:
        Input: "To, John Doe, 123 Main St, New York, NY 10001. Phone: (555) 123-4567"
        Output: {{"name": "John Doe", "phone_number": "5551234567", "address": "123 Main St", "city": "New York", "state": "NY", "pincode": "10001", "country": "United States"}}

        Input: "Received from: Acme Corp, 456 Business Ave, Bengaluru, Karnataka 560002. Contact: +91 9876543210"
        Output: {{"name": "Acme Corp", "phone_number": "919876543210", "address": "456 Business Ave", "city": "Bengaluru", "state": "Karnataka", "pincode": "560002", "country": "India"}}

        Input: "Customer Name: K P Srinivas, Address: NO 115, 3RD MAIN 4TH CROSS, HANUMANTHA NAGAR, Bangalore, Karnataka 560019, Mobile: 9886581525"
        Output: {{"name": "K P Srinivas", "phone_number": "9886581525", "address": "NO 115, 3RD MAIN 4TH CROSS, HANUMANTHA NAGAR", "city": "Bangalore", "state": "Karnataka", "pincode": "560019", "country": "India"}}

        Input: "Regarding Gagan's order. Call 7778889990. Delivery to House #5, Gandhi Road, Chennai, TN 600001"
        Output: {{"name": "Gagan", "phone_number": "7778889990", "address": "House #5, Gandhi Road", "city": "Chennai", "state": "TN", "pincode": "600001", "country": "India"}}
        
        Input: "Invoice for Mr. Vinod Kumar. Flat 10, MG Apartments, Pune, Maharashtra - 411001. Phone: 9000111222"
        Output: {{"name": "Vinod Kumar", "phone_number": "9000111222", "address": "Flat 10, MG Apartments", "city": "Pune", "state": "Maharashtra", "pincode": "411001", "country": "India"}}

        Rules:
        - The 'name' should be the full name of the primary person or company.
        - If the text contains "To," or "S/O", interpret the name following it as the primary name.
        - Phone_number and pincode must contain ONLY digits. Remove any spaces, dashes, or parentheses.
        - If a field is not found or cannot be confidently extracted, set its value to null.
        - Default country to 'India' if not explicitly mentioned.
        - Your response MUST be a raw JSON object. DO NOT include any markdown code blocks (e.g., ```json) or extra text before or after the JSON.

        {format_instructions}

        Information:
        {text_input}

        Extracted Contact Info:
        """,
        input_variables=["text_input"],
        partial_variables={"format_instructions": temp_parser.get_format_instructions()},
    )

    chain = prompt | llm_contact_extractor # Chain produces raw text output from LLM

    try:
        # Invoke the chain to get the raw text response from the LLM
        llm_response_text = chain.invoke({"text_input": text})
        print(f"\n--- DEBUG (Contact Extraction): Raw LLM Response ---\n{llm_response_text}\n--- END RAW LLM Response ---\n")

        # --- Explicitly parse JSON string and validate with Pydantic v2 ---
        # 1. Parse the JSON string into a Python dictionary
        parsed_dict = json.loads(llm_response_text)
        
        # 2. Validate the dictionary against the Pydantic model
        structured_contact_info = ContactInfo.model_validate(parsed_dict)

        print(f"\n--- DEBUG (Contact Extraction): Successfully Parsed Contact Info ---\n{structured_contact_info.dict()}\n--- END Parsed Contact Info ---\n")
        return structured_contact_info
    except json.JSONDecodeError as e:
        print(f"ERROR (Contact Extraction): LLM did not return valid JSON: {e}")
        print(f"The LLM's raw response was:\n{llm_response_text}")
        return None
    except ValidationError as e:
        print(f"ERROR (Contact Extraction): LLM output did not conform to ContactInfo schema: {e}")
        print(f"The LLM's raw response was:\n{llm_response_text}")
        return None
    except Exception as e:
        print(f"ERROR (Contact Extraction): An unexpected error occurred during contact data parsing: {e}")
        print(f"The LLM's raw response was:\n{llm_response_text}")
        return None
