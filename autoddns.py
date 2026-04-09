import json
import os
import re
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def load_settings():
    env_path = os.path.join(os.path.dirname(__file__), "credentials.env")
    if os.path.isfile(env_path):
        load_dotenv(dotenv_path=env_path, override=False)

    api_token = os.getenv("CLOUDFLARE_API", "").strip()
    record_name = os.getenv("RECORD_TO_EDIT", "").strip()
    zone_name = os.getenv("ZONE_NAME", "").strip()
    ip_check_url = os.getenv("IP_CHECK_URL", "https://api.ipify.org").strip()
    ttl_value = os.getenv("TTL", "1").strip()
    proxy_value = os.getenv("PROXY", "true").strip().lower()
    interval_value = os.getenv("CHECK_INTERVAL", "300").strip()

    if not api_token:
        raise SystemExit("Errore: manca CLOUDFLARE_API in credentials.env")

    if not record_name:
        raise SystemExit("Errore: manca RECORD_TO_EDIT in credentials.env")

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

    return api_token, record_name, zone_name, ttl, proxy, ip_check_url, check_interval


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


def cf_request(method, path, api_token, payload=None, params=None):
    base_url = "https://api.cloudflare.com/client/v4"
    url = base_url + path
    if params:
        url = f"{url}?{urlencode(params)}"

    data = None
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

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
        raise SystemExit(f"Cloudflare API failure: {errors}")

    return result.get("result")


def get_zone_id(api_token, zone_name):
    zones = cf_request("GET", "/zones", api_token, params={"name": zone_name, "status": "active"})
    if not zones:
        raise SystemExit(f"Impossibile trovare la zona Cloudflare: {zone_name}")
    return zones[0]["id"]


def get_dns_record(api_token, zone_id, record_name):
    records = cf_request(
        "GET",
        f"/zones/{zone_id}/dns_records",
        api_token,
        params={"type": "A", "name": record_name},
    )
    return records[0] if records else None


def create_dns_record(api_token, zone_id, record_name, ip_address, ttl, proxied):
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip_address,
        "ttl": ttl,
        "proxied": proxied,
    }
    record = cf_request("POST", f"/zones/{zone_id}/dns_records", api_token, payload=payload)
    log(f"Creato record A {record_name} -> {ip_address} (proxy={'ON' if proxied else 'OFF'})")
    return record
    return record


def update_dns_record(api_token, zone_id, record_id, record_name, ip_address, ttl, proxied):
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip_address,
        "ttl": ttl,
        "proxied": proxied,
    }
    record = cf_request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", api_token, payload=payload)
    log(f"Aggiornato record A {record_name} -> {ip_address} (proxy={'ON' if proxied else 'OFF'})")
    return record
    return record


def main():
    api_token, record_name, zone_name, ttl, proxied, ip_check_url, check_interval = load_settings()
    zone_id = get_zone_id(api_token, zone_name)

    try:
        while True:
            public_ip = fetch_public_ipv4(ip_check_url)
            log(f"IP pubblico rilevato: {public_ip}")

            current_record = get_dns_record(api_token, zone_id, record_name)

            if current_record is None:
                create_dns_record(api_token, zone_id, record_name, public_ip, ttl, proxied)
            else:
                current_ip = current_record.get("content")
                current_proxied = current_record.get("proxied", False)
                current_ttl = current_record.get("ttl")

                if current_ip == public_ip and current_proxied == proxied and current_ttl == ttl:
                    log("Il record è già aggiornato. Nessuna modifica necessaria.")
                else:
                    update_dns_record(
                        api_token,
                        zone_id,
                        current_record["id"],
                        record_name,
                        public_ip,
                        ttl,
                        proxied,
                    )

            log(f"Prossimo controllo tra {check_interval} secondi...")
            time.sleep(check_interval)
    except KeyboardInterrupt:
        log("Interrotto dall'utente. Uscita.")


if __name__ == "__main__":
    main()
