from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import math
import threading
import time

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
BASE_URL = "https://api.binance.com"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "WyckoffCryptoRadar/1.0"})
CACHE = {}
CACHE_LOCK = threading.Lock()
CACHE_TTL = 45


def cached(key, ttl=CACHE_TTL):
    with CACHE_LOCK:
        item = CACHE.get(key)
        if item and time.time() - item[0] < ttl:
            return item[1]
    return None


def put_cache(key, value):
    with CACHE_LOCK:
        CACHE[key] = (time.time(), value)


def binance_get(path, params=None, timeout=12):
    response = SESSION.get(BASE_URL + path, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_universe():
    key = "universe"
    old = cached(key, 300)
    if old is not None:
        return old
    exchange = binance_get("/api/v3/exchangeInfo")
    tickers = binance_get("/api/v3/ticker/24hr")
    ticker_map = {t["symbol"]: t for t in tickers}
    symbols = []
    for item in exchange.get("symbols", []):
        symbol = item.get("symbol", "")
        if item.get("status") != "TRADING" or item.get("quoteAsset") != "USDT":
            continue
        # Use only spot-enabled symbols; Binance has changed this field over time.
        if item.get("isSpotTradingAllowed") is False:
            continue
        ticker = ticker_map.get(symbol)
        if not ticker:
            continue
        try:
            quote_volume = float(ticker.get("quoteVolume", 0))
            last_price = float(ticker.get("lastPrice", 0))
            change = float(ticker.get("priceChangePercent", 0))
        except (TypeError, ValueError):
            continue
        if quote_volume <= 0 or last_price <= 0:
            continue
        # Avoid common leveraged-token suffixes to reduce noisy scan results.
        base = item.get("baseAsset", "")
        if base.endswith(("UP", "DOWN", "BULL", "BEAR")):
            continue
        symbols.append({
            "symbol": symbol,
            "base": base,
            "quoteVolume": quote_volume,
            "lastPrice": last_price,
            "change24h": change,
        })
    symbols.sort(key=lambda x: x["quoteVolume"], reverse=True)
    result = symbols[:100]
    put_cache(key, result)
    return result


def safe_float(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def get_klines(symbol, interval="1h", limit=100):
    key = f"klines:{symbol}:{interval}:{limit}"
    old = cached(key, 35)
    if old is not None:
        return old
    raw = binance_get("/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    rows = []
    for k in raw:
        rows.append({
            "time": int(k[0]),
            "open": safe_float(k[1]),
            "high": safe_float(k[2]),
            "low": safe_float(k[3]),
            "close": safe_float(k[4]),
            "volume": safe_float(k[5]),
            "closeTime": int(k[6]),
            "quoteVolume": safe_float(k[7]),
        })
    put_cache(key, rows)
    return rows


def mean(values):
    return sum(values) / len(values) if values else 0.0


def analyze_symbol(item, interval="1h"):
    candles = get_klines(item["symbol"], interval=interval, limit=100)
    if len(candles) < 55:
        raise ValueError("Not enough candles")
    # Exclude the current, still-forming candle from structural calculations.
    c = candles[:-1]
    last = c[-1]
    recent = c[-24:]
    prior = c[-48:-24]
    wider = c[-48:]
    price = last["close"]
    recent_high = max(x["high"] for x in recent)
    recent_low = min(x["low"] for x in recent)
    prior_high = max(x["high"] for x in prior)
    prior_low = min(x["low"] for x in prior)
    volume_base = mean([x["volume"] for x in c[-21:-1]])
    vol_ratio = last["volume"] / volume_base if volume_base else 1.0
    close_location = (last["close"] - last["low"]) / max(last["high"] - last["low"], 1e-12)
    range_pct = (recent_high - recent_low) / max(price, 1e-12) * 100
    prior_mid = (prior_high + prior_low) / 2
    trend_pct = (price / max(c[-25]["close"], 1e-12) - 1) * 100

    # Rule-based pattern heuristics, not authoritative Wyckoff labeling.
    spring = last["low"] < prior_low * 0.997 and last["close"] > prior_low and close_location > 0.55
    sos = last["close"] > prior_high and vol_ratio >= 1.15 and close_location > 0.60
    lps = price > prior_mid and trend_pct > 0 and vol_ratio < 1.15 and last["low"] > prior_low * 0.99
    utad = last["high"] > prior_high * 1.003 and last["close"] < prior_high and close_location < 0.45
    sow = last["close"] < prior_low and vol_ratio >= 1.15 and close_location < 0.40
    range_bound = abs(trend_pct) < 7 and range_pct < 12
    declining = trend_pct < -5
    rising = trend_pct > 5

    score = 35
    tags = []
    if spring:
        score += 25
        tags.append("Spring tiềm năng")
    if sos:
        score += 30
        tags.append("SOS")
    if lps:
        score += 15
        tags.append("LPS tiềm năng")
    if utad:
        score -= 20
        tags.append("UTAD tiềm năng")
    if sow:
        score -= 30
        tags.append("SOW")
    if range_bound:
        score += 10
        tags.append("Đi ngang")
    if vol_ratio >= 1.5:
        score += 5 if last["close"] >= last["open"] else -5
    score = max(0, min(100, int(round(score))))

    if sow or (utad and declining):
        phase = "Phân phối / suy yếu"
        bias = "Cẩn trọng"
    elif sos:
        phase = "Sức mạnh (SOS)"
        bias = "Theo dõi xác nhận"
    elif spring:
        phase = "Spring tiềm năng"
        bias = "Chờ xác nhận"
    elif lps:
        phase = "LPS tiềm năng"
        bias = "Theo dõi hỗ trợ"
    elif range_bound and declining:
        phase = "Có thể tích lũy"
        bias = "Chưa xác nhận"
    elif range_bound and rising:
        phase = "Đi ngang sau tăng"
        bias = "Theo dõi"
    elif range_bound:
        phase = "Vùng đi ngang"
        bias = "Chờ tín hiệu"
    elif declining:
        phase = "Xu hướng giảm"
        bias = "Tránh bắt đáy vội"
    elif rising:
        phase = "Xu hướng tăng"
        bias = "Theo dõi pullback"
    else:
        phase = "Chưa rõ cấu trúc"
        bias = "Chờ thêm dữ liệu"

    # Levels are reference areas, not personalized trading instructions.
    support = recent_low
    resistance = recent_high
    invalidation = recent_low * 0.99
    target = price + (price - invalidation) * 2 if price > invalidation else None

    return {
        **item,
        "price": price,
        "change24h": item["change24h"],
        "quoteVolume": item["quoteVolume"],
        "interval": interval,
        "phase": phase,
        "bias": bias,
        "score": score,
        "tags": tags or ["Chưa có mẫu hình rõ"],
        "volumeRatio": round(vol_ratio, 2),
        "trendPct": round(trend_pct, 2),
        "rangePct": round(range_pct, 2),
        "support": support,
        "resistance": resistance,
        "invalidation": invalidation,
        "target2R": target,
        "lastCandleTime": last["time"],
        "candles": candles,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "Wyckoff Crypto Radar", "time": datetime.now(timezone.utc).isoformat()})


@app.route("/api/scan")
def scan():
    interval = request.args.get("interval", "1h")
    if interval not in ("15m", "1h", "4h", "1d"):
        return jsonify({"error": "Khung thời gian không hợp lệ"}), 400
    try:
        universe = get_universe()
    except requests.RequestException as exc:
        return jsonify({"error": f"Không lấy được danh sách Binance: {exc}"}), 502
    results, errors = [], []
    # Moderate concurrency to avoid overloading public endpoints.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(analyze_symbol, item, interval): item for item in universe}
        for future in as_completed(futures):
            item = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append({"symbol": item["symbol"], "error": str(exc)})
    results.sort(key=lambda x: (x["score"], x["quoteVolume"]), reverse=True)
    return jsonify({
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "interval": interval,
        "count": len(results),
        "requested": len(universe),
        "errors": len(errors),
        "results": results,
        "errorSymbols": [e["symbol"] for e in errors[:12]],
        "notice": "Điểm Wyckoff là heuristic dựa trên OHLCV, cần kiểm tra biểu đồ thủ công; không phải xác suất thắng."
    })


@app.route("/api/chart/<symbol>")
def chart(symbol):
    symbol = symbol.upper()
    interval = request.args.get("interval", "1h")
    if interval not in ("15m", "1h", "4h", "1d"):
        return jsonify({"error": "Khung thời gian không hợp lệ"}), 400
    try:
        universe_symbols = {x["symbol"] for x in get_universe()}
        if symbol not in universe_symbols:
            return jsonify({"error": "Cặp không nằm trong Top 100 Spot USDT hiện tại"}), 404
        candles = get_klines(symbol, interval, 100)
        return jsonify({"symbol": symbol, "interval": interval, "candles": candles})
    except requests.RequestException as exc:
        return jsonify({"error": f"Binance API lỗi: {exc}"}), 502


@app.errorhandler(500)
def server_error(_error):
    return jsonify({"error": "Lỗi máy chủ nội bộ. Hãy kiểm tra cửa sổ terminal."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
