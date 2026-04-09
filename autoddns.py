import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv


def load_settings():
    env_path = os.path.join(os.path.dirname(__file__), "credentials.env")
    if os.path.isfile(env_path):
        load_dotenv(dotenv_path=env_path, override=False)

    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip() or os.getenv("CLOUDFLARE_API", "").strip()
    api_key = os.getenv("CLOUDFLARE_API_KEY", "").strip()
    api_email = os.getenv("CLOUDFLARE_EMAIL", "").strip()
    record_name = os.getenv("RECORD_TO_EDIT", "").strip()
    zone_name = os.getenv("ZONE_NAME", "").strip()
    ip_check_url = os.getenv("IP_CHECK_URL", "https://api.ipify.org").strip()
    ttl_value = os.getenv("TTL", "1").strip()
    proxy_value = os.getenv("PROXY", "true").strip().lower()
    interval_value = os.getenv("CHECK_INTERVAL", "300").strip()

    if api_key and api_email:
        auth = {"type": "key", "key": api_key, "email": api_email}
        print(f"[DEBUG] Auth: API Key mode (email: {api_email})")
    elif api_token:
        auth = {"type": "token", "value": api_token}
        token_preview = f"...{api_token[-10:]}" if len(api_token) > 10 else "token_short"
        print(f"[DEBUG] Auth: Token mode (token: {token_preview}, length: {len(api_token)})")
    else:
        print("[DEBUG] No credentials found")
        raise SystemExit(
            "Errore: manca CLOUDFLARE_API_TOKEN/CLOUDFLARE_API oppure CLOUDFLARE_API_KEY e CLOUDFLARE_EMAIL"
        )

    if not record_name:
        raise SystemExit("Errore: manca RECORD_TO_EDIT")

    if not zone_name:
        zone_name = derive_zone_name(record_name)

    try:
        ttl = int(ttl_value)
    except ValueError:
        raise SystemExit("Errore: TTL deve essere un numero intero")

    try:
        check_interval = int(interval_value)
    except ValueError:
        raise SystemExit("Errore: CHECK_INTERVAL deve essere un numero intero")

    proxy = proxy_value not in {"0", "false", "no", "off"}

    return auth, record_name, zone_name, ttl, proxy, ip_check_url, check_interval


def derive_zone_name(record_name):
    parts = record_name.split(".")
    if len(parts) < 2:
        raise SystemExit("Errore: RECORD_TO_EDIT non è un dominio valido")
    return ".".join(parts[-2:])


def validate_ipv4(ip):
    if not re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", ip):
        return False
    return all(0 <= int(part) <= 255 for part in ip.split("."))


def fetch_public_ipv4(ip_check_url):
    request = Request(ip_check_url, headers={"User-Agent": "autoDDNS/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            ip = response.read().decode("utf-8").strip()
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"Errore nel rilevamento dell'IP pubblico: {exc}")

    if not validate_ipv4(ip):
        raise SystemExit(f"IP non valido ricevuto da {ip_check_url}: '{ip}'")

    return ip


def cf_request(method, path, auth, payload=None, params=None):
    base_url = "https://api.cloudflare.com/client/v4"
    url = base_url + path
    if params:
        url = f"{url}?{urlencode(params)}"

    data = None
    headers = {"Content-Type": "application/json"}
    if auth["type"] == "token":
        headers["Authorization"] = f"Bearer {auth['value']}"
        print(f"[DEBUG] Sending request with Bearer token auth")
    else:
        headers["X-Auth-Key"] = auth["key"]
        headers["X-Auth-Email"] = auth["email"]
        print(f"[DEBUG] Sending request with Key/Email auth ({auth['email']})")

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)
    except HTTPError as exc:
        message = exc.read().decode("utf-8") if exc.fp is not None else str(exc)
        raise SystemExit(f"Cloudflare API error {exc.code}: {message}")
    except URLError as exc:
        raise SystemExit(f"Cloudflare API connection error: {exc}")

    if not result.get("success", False):
        errors = result.get("errors", [])
        print(f"[DEBUG] Full response: {result}")
        raise SystemExit(f"Cloudflare API failure: {errors}")

    return result.get("result")


def get_zone_id(auth, zone_name):
    zones = cf_request("GET", "/zones", auth, params={"name": zone_name, "status": "active"})
    if not zones:
        raise SystemExit(f"Impossibile trovare la zona Cloudflare: {zone_name}")
    return zones[0]["id"]


def get_dns_record(auth, zone_id, record_name):
    records = cf_request(
        "GET",
        f"/zones/{zone_id}/dns_records",
        auth,
        params={"type": "A", "name": record_name},
    )
    return records[0] if records else None


def create_dns_record(auth, zone_id, record_name, ip_address, ttl, proxied):
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip_address,
        "ttl": ttl,
        "proxied": proxied,
    }
    record = cf_request("POST", f"/zones/{zone_id}/dns_records", auth, payload=payload)
    print(f"Creato record A {record_name} -> {ip_address} (proxy={'ON' if proxied else 'OFF'})")
    return record


def update_dns_record(auth, zone_id, record_id, record_name, ip_address, ttl, proxied):
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip_address,
        "ttl": ttl,
        "proxied": proxied,
    }
    record = cf_request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", auth, payload=payload)
    print(f"Aggiornato record A {record_name} -> {ip_address} (proxy={'ON' if proxied else 'OFF'})")
    return record


def main():
    auth, record_name, zone_name, ttl, proxied, ip_check_url, check_interval = load_settings()
    print(f"[DEBUG] Cloudflare auth mode: {auth['type']}")
    print(f"[DEBUG] Zone: {zone_name}, Record: {record_name}")
    zone_id = get_zone_id(auth, zone_name)

    try:
        while True:
            public_ip = fetch_public_ipv4(ip_check_url)
            print(f"IP pubblico rilevato: {public_ip}")

            current_record = get_dns_record(auth, zone_id, record_name)

            if current_record is None:
                create_dns_record(auth, zone_id, record_name, public_ip, ttl, proxied)
            else:
                current_ip = current_record.get("content")
                current_proxied = current_record.get("proxied", False)
                current_ttl = current_record.get("ttl")

                if current_ip == public_ip and current_proxied == proxied and current_ttl == ttl:
                    print("Il record è già aggiornato. Nessuna modifica necessaria.")
                else:
                    update_dns_record(
                        auth,
                        zone_id,
                        current_record["id"],
                        record_name,
                        public_ip,
                        ttl,
                        proxied,
                    )

            print(f"Prossimo controllo tra {check_interval} secondi...\n")
            time.sleep(check_interval)
    except KeyboardInterrupt:
        print("Interrotto dall'utente. Uscita.")


if __name__ == "__main__":
    main()
