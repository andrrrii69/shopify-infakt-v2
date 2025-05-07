import os
import logging
from fastapi import FastAPI, Request, HTTPException
import requests

app = FastAPI()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

INFAKT_TOKEN = os.getenv("INFAKT_API_TOKEN")
if not INFAKT_TOKEN:
    raise RuntimeError("Brakuje zmiennej środowiskowej INFAKT_API_TOKEN")

INFAKT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {INFAKT_TOKEN}",
}

@app.post("/shopify")
async def shopify_webhook(req: Request):
    order = await req.json()
    order_no = order.get("order_number")
    email = order.get("email")
    logging.info(f"✅ Otrzymano zamówienie #{order_no} od {email}")

    # 1) Twórz klienta
    client_payload = {
        "client": {
            "name": order["billing_address"]["name"],
            "email": email,
            "addresses": [{
                "street": order["billing_address"]["address1"],
                "zip": order["billing_address"]["zip"],
                "city": order["billing_address"]["city"],
                "country": order["billing_address"]["country_code"],
            }]
        }
    }
    r = requests.post(
        "https://api.infakt.pl/v3/clients.json",
        json=client_payload,
        headers=INFAKT_HEADERS,
        timeout=10
    )
    if not r.ok:
        logging.error(f"❌ Błąd tworzenia klienta: {r.status_code} {r.text}")
        raise HTTPException(500, "Nie udało się utworzyć klienta w Infakcie")
    client_id = r.json()["client"]["id"]
    logging.info(f"🆔 Utworzono klienta id={client_id}")

    # 2) Twórz fakturę
    lines = []
    for li in order.get("line_items", []):
        lines.append({
            "name": li["title"],
            "quantity": li["quantity"],
            "price_net": li["price"],
            "tax": 0
        })
    invoice_payload = {
        "invoice": {
            "kind": "income",
            "client_id": client_id,
            "issue_date": order["created_at"][:10],
            "lines": lines
        }
    }
    r = requests.post(
        "https://api.infakt.pl/v3/invoices.json",
        json=invoice_payload,
        headers=INFAKT_HEADERS,
        timeout=10
    )
    if not r.ok:
        logging.error(f"❌ Błąd tworzenia faktury: {r.status_code} {r.text}")
        raise HTTPException(500, "Nie udało się wystawić faktury w Infakcie")
    inv = r.json()["invoice"]
    logging.info(f"✅ Wystawiono fakturę id={inv['id']} nr={inv['full_number']}")

    return {"status": "ok"}
