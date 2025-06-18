# ai_assistant.py
from langchain_community.llms import Ollama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, conint
from typing import List, Optional, Dict
import json # Import json for pretty printing

# Define your Pydantic models (can be in a separate models.py and imported)
class InvoiceItem(BaseModel):
    item_name: str = Field(description="Name of the item")
    quantity: conint(gt=0) = Field(description="Quantity of the item, must be greater than zero")

class InvoiceData(BaseModel):
    customer_name: str = Field(description="Full name of the customer")
    customer_phone: Optional[str] = Field(None, description="Phone number of the customer, if available")
    items: List[InvoiceItem] = Field(description="List of items on the invoice")
    city_cf: Optional[str] = Field(None, description="City custom field for the invoice")
    code_cf: Optional[str] = Field(None, description="Total items code custom field for the invoice")
    vehicle_cf: Optional[str] = Field(None, description="Vehicle number custom field for the invoice")

# Initialize LLM once (make sure this is not re-initialized on every call in your actual setup)
# For the purpose of this example, we'll keep it here, but in a FastAPI app,
# you might want to initialize it during app startup or as a dependency.
llm_invoice_generator = None
try:
    llm_invoice_generator = Ollama(model="llama3.2")
    print("DEBUG: Ollama LLM initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize Ollama LLM: {e}. Make sure Ollama server is running and model 'llama3.2' is available.")


def generate_invoice_from_text(text: str) -> Optional[InvoiceData]:
    if llm_invoice_generator is None:
        print("ERROR: LLM not initialized. Cannot generate invoice.")
        return None

    parser = JsonOutputParser(pydantic_object=InvoiceData)

    prompt = PromptTemplate(
        template="""You are an expert at extracting invoice details from text.
        Extract the following information and format it as a JSON object.
        If a field is not found, omit it or set it to null/empty as per the schema.
        Ensure all quantities are positive integers.

        {format_instructions}

        Information:
        {text_input}

        Extracted Invoice Data:
        """,
        input_variables=["text_input"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm_invoice_generator

    try:
        # Step 1: Get raw LLM response
        llm_response_text = chain.invoke({"text_input": text})
        print(f"\n--- DEBUG: Raw LLM Response (before parsing) ---\n{llm_response_text}\n--- END RAW LLM Response ---\n")

        # Step 2: Try to parse the response
        structured_invoice = parser.parse(llm_response_text)
        print(f"\n--- DEBUG: Successfully Parsed Invoice Data ---\n{structured_invoice.dict()}\n--- END Parsed Invoice Data ---\n")
        return structured_invoice
    except Exception as e:
        print(f"ERROR: Failed to parse LLM response into InvoiceData: {e}")
        print(f"The LLM's raw response was:\n{llm_response_text}") # Repeat raw response for convenience
        return None