import requests
from config import API_BASE_URL, ORGANIZATION_ID

def download_invoice_pdf(invoice_id, access_token, save_path="invoice.pdf"):
    url = f"{API_BASE_URL}/invoices/print?invoice_ids={invoice_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-com-zoho-invoice-organizationid": ORGANIZATION_ID,
        "Accept": "application/pdf"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Invoice PDF downloaded and saved as {save_path}")
        return save_path
    else:
        print("❌ Failed to download invoice PDF:", response.status_code, response.text)
        return None
