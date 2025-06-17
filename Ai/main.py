from ai_mcp_plugin import ai_generate_invoice
from zoho_api import get_access_token

access_token = get_access_token()

while True:
    query = input("\n💬 Ask me to create invoice or find customer:\n> ")
    if query.lower() in ["exit", "quit"]:
        break
    ai_generate_invoice(query, access_token)
