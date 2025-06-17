import json
from llm.local_llm import ask_llm
from tools.customer_tool import handle_customer
from tools.invoice_tool import handle_invoice

def run_ai_agent(user_input: str):
    prompt = open("llm/prompt_template.txt").read() + f"\n\nUser: {user_input}"
    structured = json.loads(ask_llm(prompt))

    if structured["action"] == "create_invoice":
        customer_id = handle_customer(structured["customer"])
        invoice_id = handle_invoice(customer_id, structured["items"], structured["custom_fields"])
        return invoice_id

    return "❌ Action not supported yet."
