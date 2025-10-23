#!/usr/bin/env python3
# octopus_price_bot.py
import os, re, json, time, logging
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Electricity price monitoring
TARGET_ELECTRICITY_PRICE = float(os.getenv("TARGET_ELECTRICITY_PRICE", "0.11"))
ELECTRICITY_TARIFF_URL = "https://octopusenergy.it/le-nostre-tariffe"

# Gas price monitoring
TARGET_GAS_PRICE = float(os.getenv("TARGET_GAS_PRICE", "0.85"))
GAS_TARIFF_URL = "https://octopusenergy.it/le-nostre-tariffe"

STATE_FILE = Path("state.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "last_electricity_price": None,
        "last_gas_price": None,
        "electricity_notified": False,
        "gas_notified": False,
    }


def save_state(s):
    STATE_FILE.write_text(json.dumps(s))


def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    r = requests.post(url, data=payload, timeout=15)
    logging.info("Telegram status: %s", r.status_code)
    return r.ok


def extract_price_from_text(text, price_type="electricity"):
    # find first occurrence of a number followed by €/kWh (electricity) or €/Smc (gas)
    # supports "0,1067 €/kWh" or "€0.1067/kWh" or "0.1067<!-- -->€/kWh"
    # supports "0,8567 €/Smc" or "€0.8567/Smc" or "0.8567<!-- -->€/Smc"

    if price_type == "gas":
        # Gas price patterns (€/Smc)
        patterns = [
            r"(\d+[.,]\d+)(?:\s*<!--[^>]*-->)?\s*€\s*/?\s*s?mc",  # N <!-- -->€/Smc
            r"€\s*(\d+[.,]\d+)(?:\s*<!--[^>]*-->)?\s*/?\s*s?mc",  # €N <!-- -->/Smc
            r"(\d+[.,]\d+)(?:\s*<!--[^>]*-->)?\s*€/smc",  # N <!-- -->€/Smc
            r"(\d+[.,]\d+)(?:\s*<!--[^>]*-->)?\s*€/mc",  # fallback
            r"(\d+[.,]\d+)\s*€\s*/?\s*s?mc",  # N €/Smc (original)
            r"€\s*(\d+[.,]\d+)\s*/?\s*s?mc",  # €N /Smc (original)
            r"(\d+[.,]\d+)\s*€/smc",  # N €/Smc (original)
            r"(\d+[.,]\d+)\s*€/mc",  # fallback (original)
        ]
    else:
        # Electricity price patterns (€/kWh)
        patterns = [
            r"(\d+[.,]\d+)(?:\s*<!--[^>]*-->)?\s*€\s*/?\s*k? ?wh",  # N <!-- -->€/kWh
            r"€\s*(\d+[.,]\d+)(?:\s*<!--[^>]*-->)?\s*/?\s*k? ?wh",  # €N <!-- -->/kWh
            r"(\d+[.,]\d+)(?:\s*<!--[^>]*-->)?\s*€/kWh",  # N <!-- -->€/kWh
            r"(\d+[.,]\d+)(?:\s*<!--[^>]*-->)?\s*€/kW",  # fallback
            r"(\d+[.,]\d+)\s*€\s*/?\s*k? ?wh",  # N €/kWh (original)
            r"€\s*(\d+[.,]\d+)\s*/?\s*k? ?wh",  # €N /kWh (original)
            r"(\d+[.,]\d+)\s*€/kWh",  # N €/kWh (original)
            r"(\d+[.,]\d+)\s*€/kW",  # fallback (original)
        ]

    lower = text.lower()
    for p in patterns:
        m = re.search(p, lower)
        if m:
            num = m.group(1).replace(",", ".")
            try:
                return float(num)
            except:
                continue
    # fallback: any €/ number
    m = re.search(r"(\d+[.,]\d+)\s*€", lower)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def fetch_price_by_scraping(url, price_type="electricity"):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PriceBot/1.0; +https://example.org/bot)"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 403:
            logging.warning("Got 403 from target page; scraping might be blocked.")
            return None
        r.raise_for_status()
        html = r.text
        # quick text search + regex
        price = extract_price_from_text(html, price_type)
        if price:
            return price
        # try parsing visible text nodes
        soup = BeautifulSoup(html, "html.parser")
        visible_text = " ".join([t.get_text(" ", strip=True) for t in soup.find_all()])
        return extract_price_from_text(visible_text, price_type)
    except Exception as e:
        logging.error("Scraping failed for %s: %s", price_type, e)
        return None


def check_price(price_type, tariff_url, target_price, state):
    """Check price for either electricity or gas and send alert if needed"""

    # Scrape the tariff URL
    logging.info("Scraping %s for %s", tariff_url, price_type)
    price = fetch_price_by_scraping(tariff_url, price_type)

    # Check if price was found
    if price is None:
        logging.error("Could not determine %s price. Skipping.", price_type)
        return state

    unit = "€/kWh" if price_type == "electricity" else "€/Smc"
    logging.info("Current %s price discovered: %.6f %s", price_type, price, unit)

    # Update state with current price
    if price_type == "electricity":
        state["last_electricity_price"] = price
        notified_key = "electricity_notified"
    else:
        state["last_gas_price"] = price
        notified_key = "gas_notified"

    logging.info("Target %s price: %.4f %s", price_type, target_price, unit)

    if price < target_price and not state.get(notified_key, False):
        msg = f"Price Alert! Octopus current {price_type} price is {price:.4f} {unit} — below your target {target_price:.4f} {unit}. ({datetime.utcnow().isoformat()} UTC)\n{tariff_url}"
        ok = send_telegram_message(msg)
        if ok:
            state[notified_key] = True
    elif price >= target_price and state.get(notified_key, False):
        # price has gone back up — reset notification lock so we can alert later
        state[notified_key] = False
        logging.info(
            "%s price has gone back up, resetting notification lock",
            price_type.capitalize(),
        )

    return state


def main():
    state = load_state()

    # Check electricity price
    logging.info("=== Checking Electricity Price ===")
    state = check_price(
        "electricity", ELECTRICITY_TARIFF_URL, TARGET_ELECTRICITY_PRICE, state
    )

    # Check gas price
    logging.info("=== Checking Gas Price ===")
    state = check_price("gas", GAS_TARIFF_URL, TARGET_GAS_PRICE, state)

    # Save updated state
    save_state(state)


if __name__ == "__main__":
    main()
