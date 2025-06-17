import requests
from config import API_BASE_URL, ORGANIZATION_ID

# Fetch items list from Zoho Invoice
def get_items(access_token):
    url = f"{API_BASE_URL}/items"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-com-zoho-invoice-organizationid": ORGANIZATION_ID
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        items = response.json().get("items", [])
        return items
    else:
        print("❌ Failed to fetch items:", response.text)
        return []

# Ask user to select items to include in invoice
def prompt_user_for_items(items):
    print("\n📦 Available Items:")
    for i, item in enumerate(items):
        print(f"  {i+1}. {item['name']} (Rate: {item['rate']})")

    selected_items = []
    while True:
        choice = input("Enter item number to add (or press Enter to finish): ")
        if not choice:
            break
        try:
            index = int(choice) - 1
            if 0 <= index < len(items):
                quantity = int(input(f"Enter quantity for {items[index]['name']}: "))
                selected_items.append({
                    "item_id": items[index]["item_id"],
                    "name": items[index]["name"],
                    "rate": items[index]["rate"],
                    "quantity": quantity
                })
            else:
                print("❌ Invalid item number.")
        except ValueError:
            print("❌ Please enter a valid number.")
    return selected_items
