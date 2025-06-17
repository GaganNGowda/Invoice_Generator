from dotenv import load_dotenv
import os

# 🟢 Load variables from .env
load_dotenv()

# 🔑 Access your secrets
client_id = os.getenv("ZOHO_CLIENT_ID")
client_secret = os.getenv("ZOHO_CLIENT_SECRET")
refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
