# zoho_api.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load from .env file


def get_access_token():
    load_dotenv()

    access_token_url = "https://accounts.zoho.in/oauth/v2/token"
    response = requests.post(access_token_url, data={
        'refresh_token': os.getenv("ZOHO_REFRESH_TOKEN"),
        'client_id': os.getenv("ZOHO_CLIENT_ID"),
        'client_secret': os.getenv("ZOHO_CLIENT_SECRET"),
        'grant_type': 'refresh_token'
    })

    print("Zoho Token Response:", response.status_code, response.text)  # 👀 inspect this

    return response.json()["access_token"]
