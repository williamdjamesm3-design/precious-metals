#!/usr/bin/env python3
"""抓取贵金属实时价格，写入 data.json"""
import json
import os
import ssl
import urllib.request

SYMBOLS = {
    "xauUsd": "XAUUSD",
    "xagUsd": "XAGUSD",
    "xptUsd": "XPTUSD",
    "xpdUsd": "XPDUSD",
    "usdCny": "USDCNY",
}

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def fetch_one(symbol):
    url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&e=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            raw = resp.read().decode()
            # Stooq malformed JSON fix
            raw = raw.replace('"volume":}', '"volume":null}')
            data = json.loads(raw)
            item = data["symbols"][0]
            close = float(item["close"])
            open_p = float(item["open"])
            return {
                "price": close,
                "open": open_p,
                "high": float(item["high"]),
                "low": float(item["low"]),
                "change": close - open_p,
                "changePct": round((close - open_p) / open_p * 100, 2) if open_p else 0,
                "time": f"{item['date']} {item['time']}",
            }
    except Exception as e:
        print(f"  Failed {symbol}: {e}")
        return None


def main():
    print("Fetching precious metal prices...")

    # Load existing data as fallback
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE) as f:
                existing = json.load(f)
        except Exception:
            pass

    result = {}
    for key, symbol in SYMBOLS.items():
        print(f"  {symbol}...", end=" ")
        data = fetch_one(symbol)
        if data:
            result[key] = data
            print(f"¥{data['price']:.2f}" if "Cny" in key else f"${data['price']:.2f}")
        else:
            print("FAILED")
            # Keep existing data if available
            if key in existing:
                result[key] = existing[key]

    # Calculate CNY prices from USD
    rate = result.get("usdCny", {}).get("price", 7.1)
    for metal in ["xau", "xag", "xpt", "xpd"]:
        usd_key = f"{metal}Usd"
        cny_key = f"{metal}Cny"
        if usd_key in result:
            usd = result[usd_key]
            cny_per_gram = (usd["price"] * rate) / 31.1035
            result[cny_key] = {
                "price": round(cny_per_gram, 2),
                "change": round((usd["change"] * rate) / 31.1035, 2),
                "changePct": usd["changePct"],
                "time": usd["time"],
            }

    # Jewelry & buyback estimates (based on gold CNY)
    if "xauCny" in result:
        spot = result["xauCny"]["price"]
        result["jewelryPrice"] = round(spot * 1.12, 2)
        result["buybackPrice"] = round(spot * 0.97, 2)

    result["updatedAt"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Done. Updated at {result['updatedAt']}")


if __name__ == "__main__":
    main()
