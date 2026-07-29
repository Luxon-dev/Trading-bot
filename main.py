import base64
import requests
import pandas as pd

# ---------------------------------------------------------
# CONFIGURACIÓN DE CREDENCIALES
# ---------------------------------------------------------
TELEGRAM_TOKEN = "8015499766:AAGQTyV4uTToSBcXq_In14nm5dyc1oPf7FA"
# ID de tu grupo de Telegram (debe incluir el signo menos)
TELEGRAM_CHAT_ID = "-100XXXXXXXXXX" 

# Credenciales de GitHub para actualizar la Landing Page
GITHUB_TOKEN = "ghp_TU_TOKEN_AQUI"          # Pega el token que generaste en el Paso 1
GITHUB_REPO = "tu-usuario/trading-bot"     # Tu usuario/nombre-del-repo (ej: juanperez/trading-bot)
HTML_FILENAME = "index.html"

# ---------------------------------------------------------
# FUNCIONES DE TELEGRAM Y GITHUB
# ---------------------------------------------------------
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def actualizar_github_html(contenido_html):
    """Actualiza o crea el archivo index.html en el repositorio usando la API de GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HTML_FILENAME}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Obtener el SHA actual del archivo si existe
    sha = None
    get_res = requests.get(url, headers=headers)
    if get_res.status_code == 200:
        sha = get_res.json().get("sha")

    # Codificar el contenido HTML en Base64 (requerido por GitHub API)
    encoded_content = base64.b64encode(contenido_html.encode('utf-8')).decode('utf-8')

    payload = {
        "message": "🤖 Auto-update Dashboard Trading",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    put_res = requests.put(url, json=payload, headers=headers)
    if put_res.status_code in [200, 201]:
        print("✅ index.html subido con éxito a GitHub Pages.")
    else:
        print(f"⚠️ Error al actualizar GitHub: {put_res.text}")

def generar_link_compra(symbol):
    if "EUR" in symbol:
        return "https://www.tradingview.com/chart/?symbol=FX:EURUSD"
    else:
        par = symbol.replace("/", "_")
        return f"https://www.binance.com/es/trade/{par}?type=spot"

def obtener_tv_symbol(symbol):
    if "EUR" in symbol: return "FX:EURUSD"
    elif "BTC" in symbol: return "BINANCE:BTCUSDT"
    elif "ETH" in symbol: return "BINANCE:ETHUSDT"
    return "BINANCE:BTCUSDT"

# ---------------------------------------------------------
# CÁLCULOS TÉCNICOS (RSI Y ATR)
# ---------------------------------------------------------
def calcular_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calcular_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

# ---------------------------------------------------------
# OBTENCIÓN DE DATOS DE MERCADO
# ---------------------------------------------------------
def obtener_datos_cripto(symbol, interval="15m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    res = requests.get(url).json()
    df = pd.DataFrame(res, columns=['t', 'open', 'high', 'low', 'close', 'v', 'ct', 'qav', 'nt', 'tbv', 'tqv', 'i'])
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    return df

def obtener_datos_forex_eurusd():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=15m&range=5d"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers).json()
    result = res['chart']['result'][0]
    quote = result['indicators']['quote'][0]
    df = pd.DataFrame({
        'open': quote['open'], 'high': quote['high'],
        'low': quote['low'], 'close': quote['close']
    }).dropna().reset_index(drop=True)
    return df

# ---------------------------------------------------------
# PROCESAMIENTO Y DASHBOARD
# ---------------------------------------------------------
def analizar_y_obtener_card(symbol, df, es_forex=False):
    df['RSI'] = calcular_rsi(df)
    df['ATR'] = calcular_atr(df)
    
    actual = df.iloc[-1]
    precio, rsi, atr = actual['close'], actual['RSI'], actual['ATR']
    
    formato = "{:,.5f}" if es_forex else "{:,.2f}"
    precio_str = formato.format(precio)
    link = generar_link_compra(symbol)
    tv_symbol = obtener_tv_symbol(symbol)
    
    estado_badge = '<span class="badge neutral">NEUTRAL</span>'
    clase_card = "card-neutral"
    sl, tp = "-", "-"
    hay_alerta = False
    
    if rsi <= 30:
        stop_loss, take_profit = precio - (1.5 * atr), precio + (3.0 * atr)
        sl, tp = formato.format(stop_loss), formato.format(take_profit)
        estado_badge, clase_card, hay_alerta = '<span class="badge buy">🚀 COMPRA (LONG)</span>', "card-buy", True
        
        msg = f"🎯 *¡OPORTUNIDAD DE COMPRA EN GRUPO!*\n" \
              f"━━━━━━━━━━━━━━━━━━━━━━━\n" \
              f"📌 *Activo:* `{symbol}`\n" \
              f"📊 *RSI:* `{rsi:.1f}` (Sobreventa)\n\n" \
              f"💵 *ENTRADA:* `{precio_str}`\n" \
              f"🛑 *STOP LOSS:* `{sl}`\n" \
              f"🎯 *TAKE PROFIT:* `{tp}`\n\n" \
              f"📲 [👉 OPERAR EN VIVO]({link})"
        enviar_telegram(msg)

    elif rsi >= 70:
        stop_loss, take_profit = precio + (1.5 * atr), precio - (3.0 * atr)
        sl, tp = formato.format(stop_loss), formato.format(take_profit)
        estado_badge, clase_card, hay_alerta = '<span class="badge sell">⚠️ VENTA (SHORT)</span>', "card-sell", True
        
        msg = f"⚠️ *¡OPORTUNIDAD DE VENTA EN GRUPO!*\n" \
              f"━━━━━━━━━━━━━━━━━━━━━━━\n" \
              f"📌 *Activo:* `{symbol}`\n" \
              f"📊 *RSI:* `{rsi:.1f}` (Sobrecompra)\n\n" \
              f"💵 *ENTRADA:* `{precio_str}`\n" \
              f"🛑 *STOP LOSS:* `{sl}`\n" \
              f"🎯 *TAKE PROFIT:* `{tp}`\n\n" \
              f"📲 [👉 OPERAR EN VIVO]({link})"
        enviar_telegram(msg)

    widget_id = symbol.replace("/", "").replace("=", "")

    card_html = f"""
    <div class="card {clase_card}">
        <div class="card-header">
            <div><h2>{symbol}</h2><span class="sub-symbol">{tv_symbol}</span></div>
            {estado_badge}
        </div>
        <div class="price-box"><span class="label">Precio Actual</span><div class="price">${precio_str}</div></div>
        <div class="metric-row"><span>RSI (14 p):</span><strong class="rsi-val">{rsi:.1f}</strong></div>
        <div class="levels-grid">
            <div class="level-box sl"><span>🛑 Stop Loss</span><strong>{sl}</strong></div>
            <div class="level-box tp"><span>🎯 Take Profit</span><strong>{tp}</strong></div>
        </div>
        <div class="chart-container">
            <iframe src="https://s.tradingview.com/widgetembed/?frameElementId=tv_{widget_id}&symbol={tv_symbol}&interval=15&hidesidetoolbar=1&symboledit=0&saveimage=0&toolbarbg=0f172a&theme=dark&style=1&timezone=Etc%2FUTC" 
                    width="100%" height="200" frameborder="0" allowtransparency="true" scrolling="no"></iframe>
        </div>
        <a href="{link}" target="_blank" class="btn-trade">📲 COMPRAR / OPERAR EN VIVO</a>
    </div>
    """
    return card_html, rsi, hay_alerta

def construir_html_final(cards_html, promedio_rsi, hay_alerta_global):
    if promedio_rsi <= 35: estado_global, color_global = "🟢 MERCADO EN ZONA DE COMPRA GENERAL", "#22c55e"
    elif promedio_rsi >= 65: estado_global, color_global = "🔴 MERCADO EN ZONA DE SOBRECOMPRA GENERAL", "#ef4444"
    else: estado_global, color_global = "🟡 MERCADO EN CONSOLIDACIÓN / NEUTRO", "#eab308"

    sonido_js = "<script>new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3').play();</script>" if hay_alerta_global else ""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>Trading Terminal PRO</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background-color: #0b0f19; color: #f1f5f9; padding: 20px; }}
        header {{ text-align: center; margin-bottom: 25px; }}
        h1 {{ color: #38bdf8; font-size: 26px; font-weight: 800; }}
        p.timestamp {{ color: #64748b; font-size: 13px; margin-top: 4px; }}
        .market-status {{ max-width: 1100px; margin: 0 auto 25px auto; background: #161e2e; border: 1px solid #1e293b; padding: 15px 20px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }}
        .status-title {{ font-size: 14px; color: #94a3b8; font-weight: 600; }}
        .status-pill {{ padding: 6px 14px; border-radius: 30px; font-weight: 700; font-size: 13px; background: {color_global}22; color: {color_global}; border: 1px solid {color_global}; }}
        .container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; max-width: 1100px; margin: 0 auto; }}
        .card {{ background: #161e2e; border-radius: 14px; padding: 20px; border: 1px solid #1e293b; display: flex; flex-direction: column; gap: 12px; }}
        .card-buy {{ border: 2px solid #22c55e; box-shadow: 0 0 15px rgba(34, 197, 94, 0.15); }}
        .card-sell {{ border: 2px solid #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.15); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; }}
        .card-header h2 {{ font-size: 20px; color: #f8fafc; }}
        .sub-symbol {{ font-size: 11px; color: #64748b; text-transform: uppercase; }}
        .price-box {{ background: #0b0f19; padding: 12px; border-radius: 8px; text-align: center; }}
        .price-box .label {{ font-size: 11px; color: #64748b; text-transform: uppercase; }}
        .price {{ font-size: 26px; font-weight: 800; color: #38bdf8; margin-top: 2px; }}
        .metric-row {{ display: flex; justify-content: space-between; background: #0b0f19; padding: 10px 12px; border-radius: 8px; font-size: 13px; color: #94a3b8; }}
        .rsi-val {{ color: #f8fafc; font-size: 14px; }}
        .levels-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .level-box {{ background: #0b0f19; padding: 10px; border-radius: 8px; font-size: 12px; color: #94a3b8; }}
        .level-box span {{ display: block; margin-bottom: 4px; font-size: 11px; }}
        .level-box strong {{ font-size: 14px; color: #f8fafc; }}
        .level-box.sl strong {{ color: #f87171; }}
        .level-box.tp strong {{ color: #4ade80; }}
        .chart-container {{ border-radius: 8px; overflow: hidden; border: 1px solid #1e293b; margin-top: 5px; }}
        .badge {{ padding: 6px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; }}
        .neutral {{ background: #334155; color: #cbd5e1; }}
        .buy {{ background: #22c55e; color: #052e16; }}
        .sell {{ background: #ef4444; color: #ffffff; }}
        .btn-trade {{ display: block; width: 100%; text-align: center; background: #0284c7; color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 13px; margin-top: auto; }}
        .risk-panel {{ max-width: 1100px; margin: 30px auto 0 auto; background: #161e2e; border-radius: 12px; padding: 20px; border: 1px solid #1e293b; }}
        .risk-panel h3 {{ font-size: 16px; margin-bottom: 10px; color: #38bdf8; }}
        .risk-grid {{ display: flex; gap: 15px; flex-wrap: wrap; align-items: center; font-size: 13px; color: #94a3b8; }}
        .risk-grid input {{ background: #0b0f19; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; color: #fff; width: 100px; }}
    </style>
</head>
<body>
    {sonido_js}
    <header>
        <h1>📡 TERMINAL DE TRADING AUTOMÁTICA</h1>
        <p class="timestamp">Estado en vivo (Auto-refresh 60s)</p>
    </header>
    <div class="market-status">
        <span class="status-title">TERMÓMETRO DE MERCADO (RSI PROMEDIO: {promedio_rsi:.1f})</span>
        <span class="status-pill">{estado_global}</span>
    </div>
    <div class="container">
        {''.join(cards_html)}
    </div>
    <div class="risk-panel">
        <h3>🧮 Calculadora de Gestión de Riesgo Rápida</h3>
        <div class="risk-grid">
            <label>Capital a arriesgar (USD): 
                <input type="number" id="riskUsd" value="20" oninput="calcularLote()">
            </label>
            <label>Distancia Stop Loss (%): 
                <input type="number" id="slPercent" value="1.5" step="0.1" oninput="calcularLote()">
            </label>
            <div>
                <span>Tamaño de Posición sugerido: </span>
                <strong id="posResult" style="color:#38bdf8; font-size: 16px;">$1,333 USD</strong>
            </div>
        </div>
    </div>
    <script>
        function calcularLote() {{
            let riesgo = floatVal(document.getElementById('riskUsd').value);
            let sl = floatVal(document.getElementById('slPercent').value);
            if (sl > 0) {{
                let posicion = (riesgo / (sl / 100));
                document.getElementById('posResult').innerText = "$" + posicion.toLocaleString('en-US', {{maximumFractionDigits: 2}}) + " USD";
            }}
        }}
        function floatVal(val) {{ return parseFloat(val) || 0; }}
    </script>
</body>
</html>"""

# ---------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# ---------------------------------------------------------
def ejecutar_bot():
    cards, lista_rsi, hay_alerta_global = [], [], False

    # 1. BTC/USDT
    df_btc = obtener_datos_cripto("BTCUSDT", interval="15m")
    c_html, rsi_b, alt_b = analizar_y_obtener_card("BTC/USDT", df_btc)
    cards.append(c_html); lista_rsi.append(rsi_b)
    if alt_b: hay_alerta_global = True

    # 2. ETH/USDT
    df_eth = obtener_datos_cripto("ETHUSDT", interval="15m")
    c_html, rsi_e, alt_e = analizar_y_obtener_card("ETH/USDT", df_eth)
    cards.append(c_html); lista_rsi.append(rsi_e)
    if alt_e: hay_alerta_global = True

    # 3. EUR/USD
    df_eur = obtener_datos_forex_eurusd()
    c_html, rsi_eu, alt_eu = analizar_y_obtener_card("EUR/USD", df_eur, es_forex=True)
    cards.append(c_html); lista_rsi.append(rsi_eu)
    if alt_eu: hay_alerta_global = True

    promedio_rsi = sum(lista_rsi) / len(lista_rsi) if lista_rsi else 50
    html_final = construir_html_final(cards, promedio_rsi, hay_alerta_global)

    # Actualizar GitHub Pages
    actualizar_github_html(html_final)

if __name__ == "__main__":
    ejecutar_bot()
