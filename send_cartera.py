import telegram
from telegram import sendTelegram
import json
import pandas as pd
from binance.enums import *
import config_futures
from binance.client import Client
from Binance_futures import *
from datetime import datetime, timedelta
from parametros import *
#recordar que hay que autorizar la api key en las settings para que pueda gestionar margin
client = Client(config_futures.API_KEY, config_futures.API_SECRET)
#defino función para obtener precio


def precio(activo):
    prices = client.futures_symbol_ticker()
    for i in range(len(prices)):
        if activo == prices[i]['symbol']:
            precio = prices[i]['price']
    return precio
    

    
#leo la cartera actual
posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = read_cartera()

msg = 'POSICIÓN: ' + posicion +'\n'
msg += 'ACTIVO: ' + activo +'\n'
msg += 'INV INIC: ' + str(round(float(cant_inic),2)) +' USDT\n'
if activo == 'NINGUNO':
    msg += 'CARTERA ACTUAL: ' + str(round(float(cantidad),1)) +' USDT\n'
else:
    msg += 'CARTERA ACTUAL: ' + str(round(float(cantidad),digits_cant[activo[:-4]])) +' ' + activo[:-4] + '\n'
msg += 'RESTO: ' + str(round(float(resto),1)) +' USDT\n'
msg += 'PRECIO APERTURA: ' + str(round(float(precio_aper),digits[activo[:-4]])) +' USDT\n'
msg += 'STOP LOSS: ' + str(round(float(stop_value),digits[activo[:-4]])) +' USDT\n'
if activo != 'NINGUNO':    
    precio_act = precio(activo)
    msg += 'PRECIO ACTUAL: ' + str(round(float(precio_act),digits[activo[:-4]])) +' USDT\n'
msg += 'TAKE PROFIT: ' + str(round(float(take_profit),digits[activo[:-4]])) +' USDT\n\n'
msg += 'PNL: ' + str(round(float(profit_loss),2)) +'%\n'
#FECHA INICIO BOT
finic = datetime(2022,7,31).date()
now = datetime.utcnow()
date = datetime(now.year,now.month,now.day).date()
delta = float((date - finic).days)
if delta == 0:
    delta = 1

add = 'ANUALIZADO: '+ str(round((pow(1 + (float(profit_loss)/100),365/delta)-1)*100,2))+ "%\n"
msg += add
add = 'FECHA INICIO: ' + str(finic) +'\n\n'
msg += add


balance = client.futures_account_balance()
for dict in balance:
    if dict['asset'] == 'BNB':
        bnb_balance = dict
cant_bnb = round(float(bnb_balance['balance']),4)
precio_bnb = precio('BNBUSDT')
cant_bnb_usd = str(round(float(precio_bnb)*float(cant_bnb),0))

add = 'Cantidad BNB en futures: ' + cant_bnb_usd + ' USD/' +str(round(cant_bnb,2))+' BNB'
msg = msg + add
sendTelegram(msg)





