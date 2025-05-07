import os
import logging
from fastapi import FastAPI, Request, HTTPException
import requests

app = FastAPI()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# Pobranie tokenu Infakt z zmiennych środowiskowych
token = os.getenv("INFAKT_API_TOKEN")
if not token:
    raise RuntimeError("Brakuje zmiennej środowiskowej INFAKT_API_TOKEN")

# Nagłówki do autoryzacji w API Infakt
INFAKT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    # Infakt wymaga nagłówka Api-Key zamiast Authorization
    "Api-Key": token
}
BASE_URL = "https://api.infakt.pl/v3"

@app.post("/shopify")
async def shopify_webhook(req: Request):
    order = await req.json()
    order_no = order.get("order_number")
    email = order.get("email")
    logging.info(f"✅ Otrzymano zamówienie #{order_no} od {email}")

    # Tworzenie klienta w Infakt
    client_payload = {
        "client": {
            "email": email
            # w razie potrzeby dodaj inne pola (np. nazwa, adres)
        }
    }
    resp_client = requests.post(
        f"{BASE_URL}/clients.json",
        json=client_payload,
        headers=INFAKT_HEADERS
    )
    if resp_client.status_code != 201:
        logging.error(f"❌ Błąd tworzenia klienta: {resp_client.status_code} {resp_client.text}")
        raise HTTPException(
            status_code=500,
            detail=f"Błąd tworzenia klienta: {resp_client.text}"
        )
    client_id = resp_client.json().get("client", {}).get("id")
    logging.info(f"✅ Utworzono klienta w Infakt: {client_id}")

    # Tworzenie faktury w Infakt
    invoice_payload = {
        "invoice": {
            "client_id": client_id,
            "number": str(order_no),
            # pozycje faktury: uzupełnij według linii zamówienia
            "positions": []
        }
    }
    resp_invoice = requests.post(
        f"{BASE_URL}/invoices.json",
        json=invoice_payload,
        headers=INFAKT_HEADERS
    )
    if resp_invoice.status_code not in (200, 201):
        logging.error(f"❌ Błąd tworzenia faktury: {resp_invoice.status_code} {resp_invoice.text}")
        raise HTTPException(
            status_code=500,
            detail=f"Błąd tworzenia faktury: {resp_invoice.text}"
        )
    invoice_id = resp_invoice.json().get("invoice", {}).get("id")
    logging.info(f"✅ Utworzono fakturę w Infakt: {invoice_id}")

    return {"status": "ok"}