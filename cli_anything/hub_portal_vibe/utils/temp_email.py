"""Temp email via mail.tm for OTP capture."""
import time
import re
import requests


class MailTM:
    BASE = "https://api.mail.tm"

    def __init__(self):
        self.email = None
        self.password = None
        self.token = None
        self.account_id = None

    def create_account(self, custom_user=None):
        domains = requests.get(f"{self.BASE}/domains").json()
        domain = domains["hydra:member"][0]["domain"]
        user = custom_user or f"test{int(time.time())}{id(self) % 10000}"
        self.email = f"{user}@{domain}"
        self.password = f"Pass{int(time.time())}!"
        for attempt in range(3):
            r = requests.post(f"{self.BASE}/accounts", json={
                "address": self.email, "password": self.password
            })
            if r.ok:
                self.account_id = r.json()["id"]
                self._authenticate()
                return self.email
            if r.status_code == 429:
                wait = (attempt + 1) * 10
                print(f"[mail.tm] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
        raise RuntimeError("mail.tm rate limit after 3 retries")

    def _authenticate(self):
        r = requests.post(f"{self.BASE}/token", json={
            "address": self.email, "password": self.password
        })
        r.raise_for_status()
        self.token = r.json()["token"]

    def wait_for_otp(self, timeout=120, interval=3, subject_filter="token"):
        start = time.time()
        while time.time() - start < timeout:
            try:
                msgs = requests.get(f"{self.BASE}/messages", headers={
                    "Authorization": f"Bearer {self.token}"
                }).json().get("hydra:member", [])
                for msg in msgs:
                    if subject_filter and subject_filter.lower() not in msg.get("subject", "").lower():
                        continue
                    full = requests.get(f"{self.BASE}/messages/{msg['id']}", headers={
                        "Authorization": f"Bearer {self.token}"
                    }).json()
                    body = full.get("text", "") or full.get("html", "")
                    match = re.search(r"\b(\d{6})\b", body)
                    if match:
                        return match.group(1)
            except Exception as e:
                print(f"[mail.tm] Polling error: {e}")
            elapsed = int(time.time() - start)
            print(f"[mail.tm] Polling... ({elapsed}s/{timeout}s)")
            time.sleep(interval)
        raise TimeoutError(f"No OTP received in {timeout}s")

    def delete_account(self):
        if self.account_id and self.token:
            try:
                requests.delete(f"{self.BASE}/accounts/{self.account_id}",
                    headers={"Authorization": f"Bearer {self.token}"})
            except Exception:
                pass
