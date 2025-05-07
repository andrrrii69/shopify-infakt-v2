import os
import logging
from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

INFAKT_TOKEN = os.getenv("INFAKT_API_TOKEN")
if not INFAKT_TOKEN:
    raise RuntimeError("Brakuje zmiennej środowiskowej INFAKT_API_TOKEN")

INFAKT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Api-Key": INFAKT_TOKEN,
}

@app.post("/shopify")
async def shopify_webhook(req: Request):
    order = await req.json()
    order_no = order.get("order_number")
    email = order.get("email")
    logging.info(f"✅ Otrzymano zamówienie #{order_no} od {email}")

    # Utworzenie klienta w Infakt
    client_payload = {
        "client": {
            "email": email,
            "name": order.get("billing_address", {}).get("name", ""),
            "company": ""
        }
    }
    try:
        resp = httpx.post("https://api.infakt.pl/v3/clients.json", headers=INFAKT_HEADERS, json=client_payload)
        resp.raise_for_status()
        client_id = resp.json().get("client", {}).get("id")
        logging.info(f"✅ Utworzono klienta ID {client_id}")
    except httpx.HTTPStatusError as e:
        logging.error(f"❌ Błąd tworzenia klienta: {e.response.status_code} {e.response.text}")
        raise HTTPException(status_code=500, detail="Błąd tworzenia klienta")

    # Utworzenie faktury
    invoice_payload = {
        "invoice": {
            "client_id": client_id,
            "currency": order.get("currency", "PLN"),
            "issue_date": order.get("created_at", "").split("T")[0],
            "invoice_items": [
                {
                    "name": item.get("title"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("price")
                } for item in order.get("line_items", [])
            ]
        }
    }
    try:
        resp = httpx.post("https://api.infakt.pl/v3/invoices.json", headers=INFAKT_HEADERS, json=invoice_payload)
        resp.raise_for_status()
        invoice_id = resp.json().get("invoice", {}).get("id")
        logging.info(f"✅ Utworzono fakturę ID {invoice_id}")
    except httpx.HTTPStatusError as e:
        logging.error(f"❌ Błąd tworzenia faktury: {e.response.status_code} {e.response.text}")
        raise HTTPException(status_code=500, detail="Błąd tworzenia faktury")

    return {"status": "ok"}