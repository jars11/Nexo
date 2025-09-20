# Agregar a un txt debug cada vez que se haga una orden, con el precio antes de realizar la orden y el precio actual de la orden
import requests
import time
import json
from typing import List, Dict
from dotenv import load_dotenv
from urllib.parse import urlsplit
import os
import threading
import sys
import hmac
import hashlib
import base64
import datetime

# Cargar variables de entorno desde .env
load_dotenv()
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
API_URL = 'https://pro-api.nexo.io'

def get_headers():
    nonce = str(int(time.time() * 1000))  # milisegundos
    secret_bytes = API_SECRET.encode("utf-8")
    msg_bytes = nonce.encode("utf-8")
    signature = hmac.new(secret_bytes, msg_bytes, hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature).decode()
    return {
        "X-API-KEY": API_KEY,
        "X-NONCE": nonce,
        "X-SIGNATURE": signature_b64
    }

def get_trading_taker_fee_percent():
    url = f"{API_URL}/api/v1/feeTier"
    r = requests.get(url, headers=get_headers())
    return r.json()['tradingTakerFeePercent']

comision = get_trading_taker_fee_percent()

class Perfil:
    def __init__(self):
        self.nombre = ""
        self.stablecoin = ""
        self.coins = []
        self.next_movement = []
        self.amount_COIN = []
        self.amount_STABLECOIN = []
        self.money_to_invest = []
        self.add_stablecoins = []
        self.last_buy_value = []
        self.max_sell_value = []
        self.actual_sell_value = []
        self.fluctuation_tolerance = []
        self.base_profit_per_move = []
        self.base_profit_per_move_percentage = []

def get_metadata_order(pairs=None):
    url = f"{API_URL}/api/v1/spot/metadata/order"
    r = requests.get(url, headers=get_headers(), params={"pairs": pairs})
    return r.json()

def precision_moneda(coin, stablecoin="USDT"):
    url = f"{API_URL}/api/v1/spot/metadata/order"
    r = requests.get(url, headers=get_headers(), params={"pairs": [coin + "/" + stablecoin], "pageSize": 1})
    try:
        return r.json()["orderMetadata"]["content"][0]["amountPrecision"]
    except (IndexError, KeyError):
        print(f"No se encontró la precisión de la moneda: {coin}/{stablecoin}")
        return None

def get_last_order_price(pair):
    url = f"{API_URL}/api/v1/orders"
    params = {
        "pairs": [pair],
        "pageSize": 1,  # Tamaño de página reducido para mejorar tiempo de respuesta
        "pageNum": 0
    }
    r = requests.get(url, headers=get_headers(), params=params)
    order = r.json()["orders"][0]
    if order["executedQuantity"] < order["quantity"]:   # la orden aún no se ejecuta por completo
        time.sleep(1)   # esperar un segundo antes de volver a intentar
        return get_last_order_price(pair)
    return order["exchangeRate"]

def get_trades_history(pairs=None, startDate=None, endDate=None, pageSize=None, pageNum=None):
    url = f"{API_URL}/api/v1/trades"
    params = {
        "pairs": pairs,
        "startDate": startDate,
        "endDate": endDate,
        "pageSize": pageSize,
        "pageNum": pageNum
    }
    r = requests.get(url, headers=get_headers(), params=params)
    return r.json()

# def get_order_info(order_id):
#     url = f"{API_URL}/api/v1/orderDetails"
#     params = {"id": order_id}
#     r = requests.get(url, headers=get_headers(), params=params)
#     return r.json()

def get_account_balances():
    url = f"{API_URL}/api/v2/accountSummary"
    r = requests.get(url, headers=get_headers())
    return r.json()

def get_price_quote(pair, side, amount=1):
    url = f"{API_URL}/api/v1/quote"
    params = {
        "pair": pair,
        "amount": str(amount),
        "side": side
    }
    headers = get_headers()
    r = requests.get(url, headers=headers, params=params)
    return r.json()['price'] if side == "sell" else 1/r.json()['price'] # Si es compra, devolver el inverso del precio, porque lo da siempre en dolares

def place_market_order(pair, side, quantity):
    url = f"{API_URL}/api/v1/orders"
    order = {
        "pair": pair,
        "side": side,
        "type": "market",
        "quantity": str(quantity)
    }
    r = requests.post(url, headers=get_headers(), json=order)
    return r.json()

def actualizar_archivo_txt(perfiles, filename="Profiles Nexo Pro.txt"):
    text = ""
    for i, perfil in enumerate(perfiles, 1):
        text += f"Profile {i}: {perfil.nombre}\n"
        text += f"Stablecoin: {perfil.stablecoin}\n"
        text += "Coins: " + ", ".join(perfil.coins) + "\n"
        text += "Next movement: " + ", ".join(perfil.next_movement) + "\n"
        text += "Amount coins: " + ", ".join(str(x) for x in perfil.amount_COIN) + "\n"
        text += "Amount stablecoin: " + ", ".join(str(x) for x in perfil.amount_STABLECOIN) + "\n"
        text += "Add stablecoin: " + ", ".join(str(x) for x in perfil.add_stablecoins) + "\n"
        text += "Last buy value: " + ", ".join(str(x) for x in perfil.last_buy_value) + "\n"
        text += "Max sell value: " + ", ".join(str(x) for x in perfil.max_sell_value) + "\n"
        text += "Fluctuation tolerance: " + ", ".join(f"{x}%" for x in perfil.fluctuation_tolerance) + "\n"
        text += "Base profit per move: "
        for j in range(len(perfil.base_profit_per_move)):
            if perfil.base_profit_per_move[j]:
                text += f"{perfil.base_profit_per_move[j]} usd"
            else:
                text += f"{perfil.base_profit_per_move_percentage[j]}%"
            if j < len(perfil.base_profit_per_move) - 1:
                text += ", "
        if i < len(perfiles):
            text += "\n\n"
    with open(filename, "w") as f:
        f.write(text)

stop_flag = False

def wait_for_keypress():
    global stop_flag
    input("Presiona ENTER para salir...\n")
    stop_flag = True

    
def main():
    global stop_flag
    perfiles: List[Perfil] = []
    with open("Profiles Nexo Pro.txt", "r") as f:
        text = f.read().split("\n\n")
        for profile_text in text:
            lines = profile_text.strip().split("\n")
            perfil = Perfil()
            perfil.nombre = lines[0].split(": ")[1]
            perfil.stablecoin = lines[1].split(": ")[1]
            perfil.coins = lines[2].split(": ")[1].split(", ")
            perfil.next_movement = lines[3].split(": ")[1].split(", ")
            perfil.amount_COIN = list(map(float, lines[4].split(": ")[1].split(", ")))
            perfil.amount_STABLECOIN = list(map(float, lines[5].split(": ")[1].split(", ")))
            perfil.add_stablecoins = list(map(float, lines[6].split(": ")[1].split(", ")))
            perfil.last_buy_value = list(map(float, lines[7].split(": ")[1].split(", ")))
            perfil.max_sell_value = list(map(float, lines[8].split(": ")[1].split(", ")))
            perfil.fluctuation_tolerance = [float(x.replace("%", "")) for x in lines[9].split(": ")[1].split(", ")]
            base_profit = lines[10].split(": ")[1].split(", ")
            for bp in base_profit:
                if bp.endswith("%"):
                    perfil.base_profit_per_move.append(0)
                    perfil.base_profit_per_move_percentage.append(float(bp.replace("%", "")))
                else:
                    perfil.base_profit_per_move.append(float(bp.replace(" usd", "")))
                    perfil.base_profit_per_move_percentage.append(0)
            perfiles.append(perfil)

    listener = threading.Thread(target=wait_for_keypress, daemon=True)
    listener.start()

    while not stop_flag:
        for perfil in perfiles:
            for idx, coin in enumerate(perfil.coins):
                pair = f"{coin}/{perfil.stablecoin}"
                
                qty = perfil.amount_STABLECOIN[idx]*perfil.actual_sell_value[idx] if perfil.next_movement[idx] == "buy" else perfil.amount_COIN[idx] # Siempre la cantidad es en crypto, por eso si side es buy, hay que pasar de stablecoin a crypto multiplicando por actual_sell_value
                qty = round(qty, precision_moneda(coin))

                if len(perfil.money_to_invest) <= idx:
                    perfil.money_to_invest.append(qty if perfil.next_movement[idx] == "sell" else qty/perfil.actual_sell_value[idx])
                else:
                    perfil.money_to_invest[idx] = qty if perfil.next_movement[idx] == "sell" else qty/perfil.actual_sell_value[idx]

                try:
                    price = get_price_quote(pair, perfil.next_movement[idx])
                except Exception as e:
                    print(f"Error obteniendo precio de {pair}: {e}")
                    continue

                if len(perfil.actual_sell_value) <= idx:
                    perfil.actual_sell_value.append(price)
                else:
                    perfil.actual_sell_value[idx] = price

                if perfil.actual_sell_value[idx] > perfil.max_sell_value[idx]:
                    perfil.max_sell_value[idx] = perfil.actual_sell_value[idx]

                se_supera_tolerancia = perfil.max_sell_value[idx] - perfil.actual_sell_value[idx] > (perfil.fluctuation_tolerance[idx]/100)*perfil.max_sell_value[idx]
                if perfil.base_profit_per_move[idx]:
                    se_alcanza_ganancia_base = perfil.actual_sell_value[idx] * perfil.money_to_invest[idx] >= perfil.last_buy_value[idx] * perfil.money_to_invest[idx] + perfil.base_profit_per_move[idx]
                    se_alcanza_porcentaje_ganancia_base = False
                else:
                    se_alcanza_ganancia_base = False
                    se_alcanza_porcentaje_ganancia_base = perfil.actual_sell_value[idx] >= perfil.last_buy_value[idx] * (1 + perfil.base_profit_per_move_percentage[idx]/100)

                if se_supera_tolerancia and (se_alcanza_ganancia_base or se_alcanza_porcentaje_ganancia_base):
                    try:
                        place_market_order(pair, perfil.next_movement[idx], qty)
                        print(f"Orden ejecutada para perfil '{perfil.nombre}' en par '{pair}'.")
                        print(f"last_buy_value: {perfil.last_buy_value[idx]}")
                        print(f"max_sell_value: {perfil.max_sell_value[idx]}")
                        print(f"estimated_sell_value: {perfil.actual_sell_value[idx]}")
                        print(f"fluctuation: {(perfil.max_sell_value[idx] - perfil.actual_sell_value[idx]) / perfil.max_sell_value[idx] * 100}%")
                        if perfil.next_movement[idx] == "buy":
                            perfil.amount_COIN[idx] += qty * (1 - comision) #Antiguamente qty/actual_sell_value * (1 - comision), pero qty ya está en crypto
                            perfil.amount_STABLECOIN[idx] -= qty/perfil.actual_sell_value[idx]
                            perfil.next_movement[idx] = "sell"
                        else:
                            perfil.amount_STABLECOIN[idx] += qty * perfil.actual_sell_value[idx] * (1 - comision) + perfil.add_stablecoins[idx]
                            perfil.add_stablecoins[idx] = 0
                            perfil.amount_COIN[idx] -= qty
                            perfil.next_movement[idx] = "buy"
                        last_order_price = get_last_order_price(pair)
                        print(f"actual_sell_value: {last_order_price if perfil.next_movement[idx] == 'buy' else 1/last_order_price}")
                        perfil.last_buy_value[idx] = last_order_price if perfil.next_movement[idx] == "sell" else 1/last_order_price
                        perfil.max_sell_value[idx] = 0
                        actualizar_archivo_txt(perfiles)
                        print(f"Perfil {perfil.nombre} actualizado y guardado.")
                        print("-" * 40)

                    except Exception as e:
                        print(f"Error ejecutando orden: {e}")
            if stop_flag:
                break
        time.sleep(5)

if __name__ == "__main__":
    main()