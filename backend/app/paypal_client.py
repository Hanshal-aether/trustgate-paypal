"""
Thin client for the PayPal REST API (Sandbox by default).

Endpoints used (all from PayPal's Subscriptions and Webhooks docs):
  POST /v1/oauth2/token                          sign in with client id + secret
  POST /v1/catalogs/products                     create the product we sell
  POST /v1/billing/plans                         a plan with a TRIAL cycle then a REGULAR cycle
  POST /v1/billing/subscriptions                 start a subscription, returns an "approve" link for the buyer
  GET  /v1/billing/subscriptions/{id}            read status and the payer after approval
  POST /v1/billing/subscriptions/{id}/cancel     cancel (TrustGate uses this on repeat-trial abuse)
  POST /v1/notifications/verify-webhook-signature
"""
import os
import time
import uuid

import httpx


class PayPalError(Exception):
    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


class PayPalClient:
    def __init__(self, client_id, client_secret, base_url="https://api-m.sandbox.paypal.com", transport=None):
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""
        self.base_url = base_url
        self.http = httpx.Client(base_url=base_url, timeout=20.0, transport=transport)
        self._token = None
        self._expires = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def mode(self) -> str:
        return "sandbox" if "sandbox" in self.base_url else "live"

    def _access_token(self) -> str:
        if self._token and time.time() < self._expires - 30:
            return self._token
        r = self.http.post("/v1/oauth2/token", auth=(self.client_id, self.client_secret),
                           data={"grant_type": "client_credentials"}, headers={"Accept": "application/json"})
        if r.status_code != 200:
            raise PayPalError("PayPal sign-in failed. Check PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET.", r.status_code, r.text)
        data = r.json()
        self._token = data["access_token"]
        self._expires = time.time() + int(data.get("expires_in", 300))
        return self._token

    def _request(self, method, path, body=None, idempotent=False):
        headers = {"Authorization": f"Bearer {self._access_token()}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if idempotent:
            headers["PayPal-Request-Id"] = str(uuid.uuid4())
        r = self.http.request(method, path, json=body, headers=headers)
        if r.status_code >= 400:
            raise PayPalError(f"PayPal {method} {path} failed ({r.status_code})", r.status_code, r.text)
        return r.json() if r.content else {}

    def create_product(self, name: str) -> str:
        body = {"name": name, "description": "Demo SaaS subscription protected by TrustGate", "type": "SERVICE", "category": "SOFTWARE"}
        return self._request("POST", "/v1/catalogs/products", body, True)["id"]

    def create_plan(self, product_id: str, name: str, trial_days: int = 7, price: str = "9.99", currency: str = "USD") -> str:
        body = {
            "product_id": product_id,
            "name": name,
            "description": f"{trial_days}-day free trial, then {price} {currency} per month",
            "status": "ACTIVE",
            "billing_cycles": [
                {"frequency": {"interval_unit": "DAY", "interval_count": trial_days}, "tenure_type": "TRIAL", "sequence": 1, "total_cycles": 1,
                 "pricing_scheme": {"fixed_price": {"value": "0", "currency_code": currency}}},
                {"frequency": {"interval_unit": "MONTH", "interval_count": 1}, "tenure_type": "REGULAR", "sequence": 2, "total_cycles": 0,
                 "pricing_scheme": {"fixed_price": {"value": price, "currency_code": currency}}},
            ],
            "payment_preferences": {"auto_bill_outstanding": True, "setup_fee": {"value": "0", "currency_code": currency},
                                    "setup_fee_failure_action": "CONTINUE", "payment_failure_threshold": 3},
        }
        return self._request("POST", "/v1/billing/plans", body, True)["id"]

    def create_subscription(self, plan_id: str, return_url: str, cancel_url: str, custom_id: str) -> dict:
        body = {
            "plan_id": plan_id,
            "custom_id": custom_id,
            "application_context": {"brand_name": "CloudNotes (TrustGate demo)", "locale": "en-US", "shipping_preference": "NO_SHIPPING",
                                    "user_action": "SUBSCRIBE_NOW", "return_url": return_url, "cancel_url": cancel_url},
        }
        data = self._request("POST", "/v1/billing/subscriptions", body, True)
        approve = next((l.get("href") for l in data.get("links", []) if l.get("rel") == "approve"), None)
        if not approve:
            raise PayPalError("PayPal did not return an approval link.", 200, str(data))
        return {"id": data["id"], "approve_url": approve, "status": data.get("status")}

    def get_subscription(self, subscription_id: str) -> dict:
        return self._request("GET", f"/v1/billing/subscriptions/{subscription_id}")

    def cancel_subscription(self, subscription_id: str, reason: str) -> None:
        self._request("POST", f"/v1/billing/subscriptions/{subscription_id}/cancel", {"reason": reason[:128]})

    def verify_webhook(self, headers: dict, event: dict, webhook_id: str) -> bool:
        h = {k.lower(): v for k, v in headers.items()}
        body = {"auth_algo": h.get("paypal-auth-algo"), "cert_url": h.get("paypal-cert-url"), "transmission_id": h.get("paypal-transmission-id"),
                "transmission_sig": h.get("paypal-transmission-sig"), "transmission_time": h.get("paypal-transmission-time"),
                "webhook_id": webhook_id, "webhook_event": event}
        return self._request("POST", "/v1/notifications/verify-webhook-signature", body).get("verification_status") == "SUCCESS"


def from_env() -> PayPalClient:
    return PayPalClient(os.getenv("PAYPAL_CLIENT_ID", ""), os.getenv("PAYPAL_CLIENT_SECRET", ""),
                        os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com"))
