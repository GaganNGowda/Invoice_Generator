# ai/ai_mcp_plugin.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Backend.customer_manager import find_customer, create_customer
from Backend.invoice_manager import create_invoice
from Backend.item_manager import get_items
from langchain_community.llms import Ollama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Setup your LLM (Ollama + LLaMA 3)
llm = Ollama(model="llama3.2")

# Define how the AI should interpret user intent
template = """
You are an assistant that helps manage customers and create invoices.
Extract the following fields from user input:
- Customer name
- City
- Phone number (if mentioned)
- Item name
- Quantity

Respond ONLY in this JSON format:
{{
    "name": "...",
    "city": "...",
    "phone": "...",
    "item": "...",
    "quantity": "..."
}}

User input: {user_input}
"""

prompt = PromptTemplate(input_variables=["user_input"], template=template)
chain = LLMChain(llm=llm, prompt=prompt)


def ai_generate_invoice(user_input, access_token):
    print("🤖 Thinking...")

    # Step 1: Extract data using LLM
    extracted = chain.run(user_input)
    print("🧠 Extracted Data:\n", extracted)

    try:
        data = eval(extracted)  # ⚠️ For safer parsing, use `json.loads()` if needed
        name = data["name"]
        city = data["city"]
        phone = data["phone"]
        item_name = data["item"]
        quantity_str = data.get("quantity", "")
        quantity = int(quantity_str) if quantity_str.isdigit() else None

        # Step 2: Find or create customer
        contact_id = find_customer(name, city, phone, access_token)
        if not contact_id:
            print("🆕 Customer not found, creating new one...")
            customer_payload = {
                "contact_name": name,
                "billing_address": {"city": city},
                "phone": phone
            }
            contact_id = create_customer(customer_payload, access_token)

        # Step 3: Fetch items and match
        items = get_items(access_token)
        selected_item = next((item for item in items if item_name.lower() in item["name"].lower()), None)

        if not selected_item:
            print("❌ Item not found.")
            return

        # Step 4: Create invoice
        invoice_id = create_invoice(contact_id, selected_item["item_id"], quantity, access_token)
        print(f"✅ Invoice created: ID = {invoice_id}")

    except Exception as e:
        print("🚨 Error processing input:", str(e))
