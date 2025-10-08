# 🐙 Octopus Energy Price Alert Bot

A simple Python bot that monitors **electricity and gas prices** on [Octopus Energy Italia](https://octopusenergy.it/le-nostre-tariffe) and sends you **Telegram notifications** when prices drop below your current rates.

It can be run locally or automatically on a schedule using **GitHub Actions**.

## Features
- Scrapes current **electricity** (€/kWh) and **gas** (€/Smc) tariff prices from the Octopus Energy Italy website  
- Sends separate Telegram alerts when electricity or gas prices drop below your targets  
- Prevents duplicate notifications (via a small local `state.json`)  
- Works with GitHub Actions for hourly automatic checks  

## Setup Instructions

### Create a Telegram Bot
1. Open Telegram and chat with [**@BotFather**](https://t.me/BotFather)
2. Send the command `/newbot` and follow the prompts  
3. Copy your new **bot token** — it’ll look like `123456:ABC-xyz...`

### Get your Telegram Chat ID
1. Send any message to your bot on Telegram  
2. Run this in your terminal (replace `<YOUR_TOKEN>`):

   ```bash
   curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
   ```

3. Copy the `message.chat.id` value from the JSON — that’s your CHAT_ID

## Local Usage

### Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Create a `.env` file

```bash
TELEGRAM_TOKEN=123456:ABC-xyz
TELEGRAM_CHAT_ID=123456789

# Electricity price monitoring
TARGET_ELECTRICITY_PRICE=0.110    # €/kWh — your current electricity rate
ELECTRICITY_TARIFF_URL=https://octopusenergy.it/le-nostre-tariffe

# Gas price monitoring
TARGET_GAS_PRICE=0.850    # €/Smc — your current gas rate
GAS_TARIFF_URL=https://octopusenergy.it/le-nostre-tariffe
```

Alternatively, export them as environment variables:

```bash
export TELEGRAM_TOKEN=...
export TELEGRAM_CHAT_ID=...
export TARGET_ELECTRICITY_PRICE=0.11
export TARGET_GAS_PRICE=0.85
```

### Run the bot manually

```bash
python octopus_price_bot.py
```

If the script finds a price below your target, you’ll get a Telegram notification.

## Deploy with GitHub Actions

1. Push this repository to GitHub
2. Go to **Settings → Secrets and variables → Actions → New repository secret**
3. Add the following secrets:

  | Secret Name                | Description                           |
  | -------------------------- | ------------------------------------- |
  | `TELEGRAM_TOKEN`           | Your Telegram bot token               |
  | `TELEGRAM_CHAT_ID`         | Your Telegram chat ID                 |
  | `TARGET_ELECTRICITY_PRICE` | Your current electricity price in €/kWh |
  | `ELECTRICITY_TARIFF_URL`   | URL of the electricity tariffs page   |
  | `TARGET_GAS_PRICE`         | Your current gas price in €/Smc      |
  | `GAS_TARIFF_URL`           | URL of the gas tariffs page           |

4. The repo includes a preconfigured workflow:
   `.github/workflows/price-check.yml`
   It runs **hourly** and sends a Telegram alert when prices drop.

   You can also trigger it manually from the Actions tab.

## How It Works

1. **Electricity Price Check:**
   - Scrapes the electricity tariff page
   - Parses the €/kWh value using regex and compares it to your `TARGET_ELECTRICITY_PRICE`
   - Sends a Telegram message if the electricity price drops below your target

2. **Gas Price Check:**
   - Scrapes the gas tariff page
   - Parses the €/Smc value using regex and compares it to your `TARGET_GAS_PRICE`
   - Sends a Telegram message if the gas price drops below your target

3. **State Management:**
   - Saves state in `state.json` to avoid duplicate alerts for both electricity and gas
   - Each energy type has separate notification tracking

## Troubleshooting

### 403 Forbidden when scraping

> The website may block simple HTTP requests.
> Try running from a different network or switch to Playwright (real browser mode).
> If you want, you can extend the script with a headless Playwright snippet.

### No Telegram messages

> Double-check that:
> 1. "The bot is started (you sent it a message)"
> 2. "You used the correct `chat_id`"
> 3. "Your token is valid"

### GitHub Actions not triggering

> Make sure the workflow file is committed to:
> ```bash
> .github/workflows/price-check.yml
> ```

## Example Telegram Messages

**Electricity Price Alert:**
```bash
Price Alert! Octopus current electricity price is 0.1067 €/kWh — below your target 0.1100 €/kWh.
https://octopusenergy.it/le-nostre-tariffe
```

**Gas Price Alert:**
```bash
Price Alert! Octopus current gas price is 0.8234 €/Smc — below your target 0.8500 €/Smc.
https://octopusenergy.it/le-nostre-tariffe
```
