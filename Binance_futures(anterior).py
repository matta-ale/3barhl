import logging
logging.basicConfig(filename="log.txt", level=logging.DEBUG,
                    format="%(asctime)s %(message)s", filemode="a")
logging.basicConfig()
from binance.enums import *
import config_futures
from binance.client import Client
import math
import datetime
import time
from telegram import sendTelegram
import telegram
import pandas as pd


client = Client(config_futures.API_KEY, config_futures.API_SECRET)


def aper_to_excel(fecha_aper,tipo_trade,activo,precio_aper, precio_aper_target,cant_aper,resto):
    dfTrades = pd.read_excel('Trades.xlsx')
    try:
        index = dfTrades.index[-1] + 1
        dfTrades.loc[index,'Nro trade'] = round(dfTrades["Nro trade"].iloc[-1] + 1)
    except:
        index = 0
        dfTrades.loc[index,'Nro trade'] = 1
    dfTrades.loc[index,'Fecha apertura'] = fecha_aper #viene de la lógica del df
    dfTrades.loc[index,'Tipo trade'] = tipo_trade
    dfTrades.loc[index,'Activo'] = activo
    dfTrades.loc[index,'Precio apertura'] = round(float(precio_aper),4)
    dfTrades.loc[index,'Precio aper target'] = round(float(precio_aper_target),4)
    if tipo_trade == 'LONG':    
        dfTrades.loc[index,'Slippage aper %'] = (-1)*round((float(precio_aper)/float(precio_aper_target)-1)*100,3) 
    else:
        dfTrades.loc[index,'Slippage aper %'] = round((float(precio_aper)/float(precio_aper_target)-1)*100,3)
    dfTrades.loc[index,'Cantidad apertura'] = round(float(cant_aper),4)
    dfTrades.loc[index,'USDT apertura'] = round(float(precio_aper)*float(cant_aper),2)
    dfTrades.loc[index,'Resto USDT'] = round(float(resto),4)
    dfTrades.loc[index,'Comisión apertura'] = 0.0002*float(precio_aper)*float(cant_aper)
    dfTrades.set_index('Nro trade', inplace = True)
    dfTrades.to_excel('Trades.xlsx')
    return

def cierre_to_excel(cant_inic,fecha_cierre,precio_cierre,precio_cierre_target,cant_cierre,motivo):
    dfTrades = pd.read_excel('Trades.xlsx')
    index = dfTrades.index[-1]
    precio_aper = dfTrades.loc[index,'Precio apertura']
    cant_aper = dfTrades.loc[index,'Cantidad apertura']
    resto = dfTrades.loc[index,'Resto USDT']
    comi_aper = dfTrades.loc[index,'Comisión apertura']
    tipo_trade = dfTrades.loc[index,'Tipo trade']
    dfTrades.loc[index,'Fecha cierre'] = fecha_cierre #viene de la lógica del df
    dfTrades.loc[index,'Precio cierre'] = round(float(precio_cierre),4)
    dfTrades.loc[index,'Precio cierre target'] = round(float(precio_cierre_target),4)
    dfTrades.loc[index,'Comisión cierre'] = 0.0002*float(precio_cierre)*float(cant_aper)
    if tipo_trade == 'SHORT':    
        dfTrades.loc[index,'Slippage cierre %'] = (-1)*round((float(precio_cierre)/float(precio_cierre_target)-1)*100,3)    
    else:
        dfTrades.loc[index,'Slippage cierre %'] = round((float(precio_cierre)/float(precio_cierre_target)-1)*100,3)
    dfTrades.loc[index,'Cantidad cierre'] = round(float(cant_cierre),4)
    dfTrades.loc[index,'Motivo cierre'] = motivo
    dfTrades.loc[index,'Total USDT'] = dfTrades.loc[index,'Cantidad cierre'] + float(resto)
    dfTrades.loc[index,'Resultado acum %'] = (dfTrades.loc[index,'Total USDT']/cant_inic -1)*100
    dfTrades.loc[index,'Resultado USDT'] = dfTrades.loc[index,'Total USDT'] - (dfTrades.loc[index,'USDT apertura'] + float(resto))
    dfTrades.loc[index,'Resultado %'] = (dfTrades.loc[index,'Total USDT']/((dfTrades.loc[index,'Cantidad apertura']*dfTrades.loc[index,'Precio apertura'])*0.9998 + resto)-1)*100
    if dfTrades.loc[index,'Resultado %'] >= 0:
        dfTrades.loc[index,'WIN/LOSS'] = 'WIN'
    else:
        dfTrades.loc[index,'WIN/LOSS'] = 'LOSS'
    dfTrades.set_index('Nro trade', inplace = True)
    dfTrades.to_excel('Trades.xlsx')
    return

def read_cartera():

    import json         # import the json library
    with open("cartera.json", "r") as f:      # read the json file
        variables = json.load(f)
    
    posicion = variables["posicion"]
    activo = variables["activo"]
    cant_inic = variables["cant_inic"]    # To get the value currently stored
    cantidad = variables['cantidad']
    resto = variables['resto']
    profit_loss = variables['profit_loss']
    precio_aper = variables['precio_aper']
    stop_value = variables['stop_value']
    take_profit = variables['take_profit']

    return  posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit

def modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit): #,cant_inic, resto, profit_loss, precio_apertura, stop_value):

    import json         # import the json library
    with open("cartera.json", "r") as f:      # write the json file
        variables = json.load(f)
        variables["activo"] = activo
        variables["cant_inic"] = cant_inic    # To get the value currently stored
        variables['posicion'] = posicion
        variables['cantidad'] = cantidad
        variables['resto'] = resto
        variables['profit_loss'] = profit_loss
        variables['precio_aper'] = precio_aper
        variables['stop_value'] = stop_value
        variables['take_profit'] = take_profit
    with open("cartera.json", "w") as f:      # write the json file  
        variables = json.dump(variables,f)
    return posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit



def precio(activo):
    prices = client.futures_symbol_ticker()
    for i in range(len(prices)):
        if activo == prices[i]['symbol']:
            precio = prices[i]['price']
    return precio

#función para truncar decimales, de manera de ajustar a la cantidad múltiplo mínima de ETHUSDT PERPETUAL, que es 0.01
def truncate(number, digits) -> float:
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper

def open_long(precio_input,activo,cantidad,digits): #compra en futuros   
    client.futures_change_leverage(symbol=activo, contractType = 'PERPETUAL', leverage=1)
    cant_ajust = truncate(cantidad/float(precio_input),digits)
    cant_cripto_aper = cant_ajust
    startTime = time.time()
    trade = ''
    order_list = []
    qtty_order = 0
    qtty_usdt = 0
    qtty = 0
    while trade != 'COMPLETED':    
        estado = 'EXPIRED'
        while estado == 'EXPIRED':
            startTime = time.time()
            precio_actual = precio(activo)
            long_order_ol = client.futures_create_order(symbol=activo,contractType = 'PERPETUAL', side = 'BUY', type = 'LIMIT',price = precio_actual, quantity = cant_ajust,timeInForce = 'GTX') #acá lo pongo quoteOrderQty porque le digo los BTC que tengo (supongo que compro ETHBTC)       
            orderId = long_order_ol['orderId']
            logging.debug('OrderId1: ' + str(orderId))
            while True:
                try:
                    time.sleep(0.1)
                    long_order_ol = client.futures_get_order(symbol = activo, orderId = orderId)
                except:
                    logging.debug('Esperando order status')
                    continue
                break
            estado = long_order_ol['status']
            logging.debug('Estado1: ' + str(estado))
            time.sleep(0.2)
        delta = 0
        while (estado == 'NEW' and delta <= 10):
            while True:
                try:
                    time.sleep(0.1)
                    long_order_ol = client.futures_get_order(symbol = activo, orderId = orderId)
                except:
                    logging.debug('Esperando order status')
                    continue
                break
            estado = long_order_ol['status']
            delta = time.time() - startTime
        logging.debug('Estado2: ' + str(estado))
        if estado == 'NEW':
            try:
                canceled_order_ol = client.futures_cancel_order(symbol = activo, orderId = orderId)
                logging.debug(canceled_order_ol)
            except:
                logging.debug('no se pudo cancelar orden (en NEW)')
            time.sleep(1)
            exec_qtty = float(canceled_order_ol['executedQty'])
            cant_ajust -= exec_qtty  #se le resta a la cantidad por las dudas que suceda que al cancelar de "NEW" a "CANCELED", en el medio se pase a partially filled
            logging.debug(exec_qtty)
            long_order_ol = client.futures_get_order(symbol = activo, orderId = orderId)
            estado = long_order_ol['status']
            logging.debug(estado)
            qtty = 0
            avg_price = 0
        if estado == 'PARTIALLY_FILLED':
            while estado == 'PARTIALLY_FILLED':
                time.sleep(10) #cambié de 5 a 10 segundos
                update_order_ol = client.futures_get_order(symbol = activo, orderId = orderId)
                estado = update_order_ol['status']
                logging.debug(estado)
                if estado == 'PARTIALLY_FILLED':
                    try:
                        canceled_order_ol = client.futures_cancel_order(symbol = activo, orderId = orderId)
                        logging.debug(canceled_order_ol)
                    except:
                        logging.debug('no se pudo cancelar orden (en partially filled)') #puse esto antes para que pare de fillear pedazos y luego sí calcule las qtty
                    time.sleep(1) #agrego esto para darle tiempo a binance para actualizar el estado
                    canceled_order_ol = client.futures_get_order(symbol = activo, orderId = orderId)
                    qtty_open_order = float(canceled_order_ol['cumQuote'])  #*(1-0.0002) aquí no lo sacamos para que no altere el valor cripto
                    avg_price_order = float(canceled_order_ol['avgPrice'])
                    exec_qtty = float(canceled_order_ol['executedQty'])
                    cant_ajust -= exec_qtty
                    logging.debug(cant_ajust)
                    logging.debug(exec_qtty)
                    order_list.append(orderId)
                    time.sleep(1)
                update_order_ol = client.futures_get_order(symbol = activo, orderId = orderId)
                estado = update_order_ol['status']
                logging.debug(estado)   
        
        if estado == 'FILLED':                                  
            while True:
                try:
                    time.sleep(0.1)
                    long_order_ol = client.futures_get_order(symbol = activo, orderId = orderId)
                except:
                    logging.debug('Esperando order status')
                    continue
                break
            order_list.append(orderId)
            trade = 'COMPLETED'
        
    order_list = list(dict.fromkeys(order_list))
    for i in order_list:
        update_order_ol = client.futures_get_order(symbol = activo, orderId = i)
        logging.debug(update_order_ol)
        while update_order_ol['status'] == 'NEW':
            sendTelegram('ORDER FILLED PASO A NEW')
            time.sleep(5)
            update_order_ol = client.futures_get_order(symbol = activo, orderId = i)
            logging.debug(update_order_ol) 
        qtty_usdt_order = float(update_order_ol['cumQuote'])
        qtty_usdt+= qtty_usdt_order
        qtty_order = float(update_order_ol['executedQty']) 
        qtty += qtty_order
    avg_price = float(qtty_usdt)/float(cant_cripto_aper)    
    return update_order_ol, qtty, avg_price

def close_long(activo,cantidad,precio_aper,precio_actual): #cierro long en futuros
    cant_cripto_aper = cantidad
    cant_aper = float(cantidad)*float(precio_aper)
    client.futures_change_leverage(symbol=activo, contractType = 'PERPETUAL', leverage=1)
    estado = 'EXPIRED'
    delta = 0
    qtty_close = 0
    order_list = []
    while estado != 'FILLED':
        while estado == 'PARTIALLY_FILLED':
            time.sleep(10) #cambié de 5 a 10 segundos
            update_order_cl = client.futures_get_order(symbol = activo, orderId = orderId)
            estado = update_order_cl['status']
            if estado == 'PARTIALLY_FILLED':
                try:
                    canceled_order_cl = client.futures_cancel_order(symbol = activo, orderId = orderId)
                    logging.debug(canceled_order_cl)
                except:
                    logging.debug('no se pudo cancelar orden (en partially filled)') #puse esto antes para que pare de fillear pedazos y luego sí calcule las qtty
                time.sleep(1) #agrego esto para darle tiempo a binance para actualizar el estado
                canceled_order_cl = client.futures_get_order(symbol = activo, orderId = orderId)
                qtty_close_order = float(canceled_order_cl['cumQuote'])  #*(1-0.0002) aquí no lo sacamos para que no altere el valor cripto
                avg_price_order = float(canceled_order_cl['avgPrice'])
                exec_qtty = float(canceled_order_cl['executedQty'])
                cantidad -= exec_qtty
                logging.debug(qtty_close)
                order_list.append(orderId)
                time.sleep(1)
            update_order_cl = client.futures_get_order(symbol = activo, orderId = orderId)
            estado = update_order_cl['status']
            logging.debug(estado)  #esto es nuevo
        if estado != 'FILLED': #esto es nuevo           
            precio_actual = precio(activo)
            startTime = time.time()    
            close_long_output = client.futures_create_order(symbol=activo,contractType = 'PERPETUAL', side = 'SELL', type = 'LIMIT',price= precio_actual, quantity = cantidad,timeInForce = 'GTX',reduceOnly = False) #acá lo pongo quoteOrderQty porque le digo los BTC que tengo (supongo que compro ETHBTC)
            orderId = close_long_output['orderId']      #acá no hay un try, nunca pasó que la data no haya llegado a tiempo como en los update?  
            while True:
                try:
                    time.sleep(0.1)
                    update_order_cl = client.futures_get_order(symbol = activo, orderId = orderId)
                except:
                    logging.debug('Esperando order status')
                    continue
                break
            estado = update_order_cl['status']
            logging.debug(estado)
            while estado == 'NEW':
                delta = time.time() - startTime 
                if delta > 10: #mayor a 10 segundos, si pasaron 10 segs me voy a cancelar la orden
                    try:
                        canceled_order_cl = client.futures_cancel_order(symbol = activo, orderId = orderId)
                        logging.debug(canceled_order_cl)
                    except:
                        logging.debug('no se pudo cancelar orden (en delta > 10)')
                    
                    while True:
                        try:
                            time.sleep(0.1)
                            canceled_order_cl = client.futures_get_order(symbol = activo, orderId = orderId)
                        except:
                            logging.debug('Esperando order status')
                            continue
                        break
                    exec_qtty = float(canceled_order_cl['executedQty'])
                    cantidad -= exec_qtty  #se le resta a la cantidad por las dudas que suceda que al cancelar de "NEW" a "CANCELED", en el medio se pase a partially filled
                    logging.debug(exec_qtty)
                    estado = canceled_order_cl['status']
                    logging.debug(estado)
                    
                else:
                    update_order_cl = client.futures_get_order(symbol = activo, orderId = orderId)
                    estado = update_order_cl['status'] 
                    logging.debug(estado)
                    time.sleep(1)             # le voy diciendo que cada un segundo chequee el estado de la órden...                                  
            time.sleep(0.5)
        order_list.append(orderId)
        logging.debug(orderId)
        logging.debug(order_list)
    qtty_close = 0
    order_list = list(dict.fromkeys(order_list))
    for i in order_list:
        update_order_cl = client.futures_get_order(symbol = activo, orderId = i)
        logging.debug(update_order_cl)
        while update_order_cl['status'] == 'NEW':
            sendTelegram('ORDER FILLED PASO A NEW')
            time.sleep(5)
            update_order_cl = client.futures_get_order(symbol = activo, orderId = i)
            logging.debug(update_order_cl) 
        qtty_close_order = float(update_order_cl['cumQuote'])
        qtty_close+= qtty_close_order
    avg_price = float(qtty_close)/float(cant_cripto_aper)
    qtty_close = qtty_close*(1-0.0002)
    return update_order_cl, qtty_close, avg_price

def open_short(precio_input,activo,cantidad,digits): #short en futuros   
    client.futures_change_leverage(symbol=activo, contractType = 'PERPETUAL', leverage=1)
    cant_ajust = truncate(cantidad/float(precio_input),digits)
    cant_cripto_aper = cant_ajust
    startTime = time.time()
    trade = ''
    order_list = []
    qtty_order = 0
    qtty_usdt = 0
    qtty = 0
    while trade != 'COMPLETED':    
        estado = 'EXPIRED'
        while estado == 'EXPIRED':
            startTime = time.time()
            precio_actual = precio(activo)
            short_order_os = client.futures_create_order(symbol=activo,contractType = 'PERPETUAL', side = 'SELL', type = 'LIMIT',price = precio_actual, quantity = cant_ajust,timeInForce = 'GTX') #acá lo pongo quoteOrderQty porque le digo los BTC que tengo (supongo que compro ETHBTC)       
            orderId = short_order_os['orderId']
            logging.debug('OrderId1: ' + str(orderId))
            while True:
                try:
                    time.sleep(0.1)
                    short_order_os = client.futures_get_order(symbol = activo, orderId = orderId)
                except:
                    logging.debug('Esperando order status')
                    continue
                break
            estado = short_order_os['status']
            logging.debug('Estado1: ' + str(estado))
            time.sleep(0.2)
        delta = 0
        while (estado == 'NEW' and delta <= 10):
            while True:
                try:
                    time.sleep(0.1)
                    short_order_os = client.futures_get_order(symbol = activo, orderId = orderId)
                except:
                    logging.debug('Esperando order status')
                    continue
                break
            estado = short_order_os['status']
            delta = time.time() - startTime
        logging.debug('Estado2: ' + str(estado))
        if estado == 'NEW':
            try:
                canceled_order_os = client.futures_cancel_order(symbol = activo, orderId = orderId)
                logging.debug(canceled_order_os)
            except:
                logging.debug('no se pudo cancelar orden (en NEW)')
            time.sleep(1)
            exec_qtty = float(canceled_order_os['executedQty'])
            cant_ajust -= exec_qtty  #se le resta a la cantidad por las dudas que suceda que al cancelar de "NEW" a "CANCELED", en el medio se pase a partially filled
            logging.debug(exec_qtty)
            short_order_os = client.futures_get_order(symbol = activo, orderId = orderId)
            estado = short_order_os['status']
            logging.debug(estado)
            qtty = 0
            avg_price = 0
        if estado == 'PARTIALLY_FILLED':
            while estado == 'PARTIALLY_FILLED':
                time.sleep(10) #cambié de 5 a 10 segundos
                short_order_os = client.futures_get_order(symbol = activo, orderId = orderId)
                estado = short_order_os['status']
                logging.debug(estado)
                if estado == 'PARTIALLY_FILLED':
                    try:
                        canceled_order_os = client.futures_cancel_order(symbol = activo, orderId = orderId)
                        logging.debug(canceled_order_os)
                    except:
                        logging.debug('no se pudo cancelar orden (en partially filled)') #puse esto antes para que pare de fillear pedazos y luego sí calcule las qtty
                    time.sleep(1) #agrego esto para darle tiempo a binance para actualizar el estado
                    canceled_order_os = client.futures_get_order(symbol = activo, orderId = orderId)
                    qtty_open_order = float(canceled_order_os['cumQuote'])  #*(1-0.0002) aquí no lo sacamos para que no altere el valor cripto
                    avg_price_order = float(canceled_order_os['avgPrice'])
                    exec_qtty = float(canceled_order_os['executedQty'])
                    cant_ajust -= exec_qtty
                    logging.debug(cant_ajust)
                    logging.debug(exec_qtty)
                    order_list.append(orderId)
                    time.sleep(1)
                update_order_os = client.futures_get_order(symbol = activo, orderId = orderId)
                estado = update_order_os['status']
                logging.debug(estado)   
        
        if estado == 'FILLED':                                  
            while True:
                try:
                    time.sleep(0.1)
                    short_order_os = client.futures_get_order(symbol = activo, orderId = orderId)
                except:
                    logging.debug('Esperando order status')
                    continue
                break
            order_list.append(orderId)
            trade = 'COMPLETED'
        
    order_list = list(dict.fromkeys(order_list))
    for i in order_list:
        update_order_os = client.futures_get_order(symbol = activo, orderId = i)
        logging.debug(update_order_os)
        while update_order_os['status'] == 'NEW':
            sendTelegram('ORDER FILLED PASO A NEW')
            time.sleep(5)
            update_order_os = client.futures_get_order(symbol = activo, orderId = i)
            logging.debug(update_order_os)  
        qtty_usdt_order = float(update_order_os['cumQuote'])
        qtty_usdt+= qtty_usdt_order
        qtty_order = float(update_order_os['executedQty']) 
        qtty += qtty_order
    avg_price = float(qtty_usdt)/float(cant_cripto_aper)    
    return update_order_os, qtty, avg_price

def close_short(activo,cantidad,precio_aper,precio_actual): #cierro short en futuros
    cant_cripto_aper = cantidad
    cant_aper = float(cantidad)*float(precio_aper)
    client.futures_change_leverage(symbol=activo, contractType = 'PERPETUAL', leverage=1)
    estado = 'EXPIRED'
    delta = 0
    qtty_close = 0
    order_list = []
    while estado != 'FILLED':
        while estado == 'PARTIALLY_FILLED':
            time.sleep(10) #cambié de 5 a 10 segundos
            update_order_cs = client.futures_get_order(symbol = activo, orderId = orderId)
            estado = update_order_cs['status']
            if estado == 'PARTIALLY_FILLED':
                try:
                    canceled_order_cs = client.futures_cancel_order(symbol = activo, orderId = orderId) #puse esto antes para que pare de fillear pedazos y luego sí calcule las qtty
                except:
                    logging.debug('no se pudo cancelar orden (en partially filled)')
                time.sleep(1) #agrego esto para darle tiempo a binance para actualizar el estado
                canceled_order_cs = client.futures_get_order(symbol = activo, orderId = orderId)
                qtty_close_order = float(canceled_order_cs['cumQuote'])  #*(1-0.0002) aquí no lo sacamos para que no altere el valor cripto
                avg_price_order = float(canceled_order_cs['avgPrice'])
                exec_qtty = float(canceled_order_cs['executedQty'])
                cantidad -= exec_qtty
                logging.debug(qtty_close)
                order_list.append(orderId)
                time.sleep(1)
            update_order_cs = client.futures_get_order(symbol = activo, orderId = orderId)
            estado = update_order_cs['status']
            logging.debug(estado)  #esto es nuevo
        if estado != 'FILLED':
            precio_actual = precio(activo)
            startTime = time.time()
            close_short_output = client.futures_create_order(symbol=activo,contractType = 'PERPETUAL', side = 'BUY', type = 'LIMIT',price= precio_actual, quantity = cantidad,timeInForce = 'GTX',reduceOnly = False) #acá lo pongo quoteOrderQty porque le digo los BTC que tengo (supongo que compro ETHBTC)
            orderId = close_short_output['orderId']        
            while True:
                try:
                    time.sleep(0.1)
                    update_order_cs = client.futures_get_order(symbol = activo, orderId = orderId)
                except:
                    logging.debug('Esperando order status')
                    continue
                break
            estado = update_order_cs['status']
            logging.debug(estado)
            while estado == 'NEW':
                delta = time.time()- startTime   
                if delta > 10: #mayor a 10 segundos
                    try:
                        canceled_order_cs = client.futures_cancel_order(symbol = activo, orderId = orderId)
                        logging.debug(canceled_order_cs)
                    except:
                        logging.debug('no se pudo cancelar orden (en delta > 10)')
                    while True:
                        try:
                            time.sleep(0.1)
                            canceled_order_cs = client.futures_get_order(symbol = activo, orderId = orderId)
                        except:
                            logging.debug('Esperando order status')
                            continue
                        break
                    exec_qtty = float(canceled_order_cs['executedQty'])
                    cantidad -= exec_qtty  #se le resta a la cantidad por las dudas que suceda que al cancelar de "NEW" a "CANCELED", en el medio se pase a partially filled
                    logging.debug(exec_qtty)
                    estado = canceled_order_cs['status']
                    logging.debug(estado)
                else:
                    update_order_cs = client.futures_get_order(symbol = activo, orderId = orderId)
                    estado = update_order_cs['status']
                    logging.debug(estado)
                    time.sleep(1)
            time.sleep(0.5)                                               
        
        order_list.append(orderId)
        logging.debug(orderId)
        logging.debug(order_list)
    qtty_close = 0
    order_list = list(dict.fromkeys(order_list))
    for i in order_list:
        update_order_cs = client.futures_get_order(symbol = activo, orderId = i)
        logging.debug(update_order_cs)
        while update_order_cs['status'] == 'NEW':
            sendTelegram('ORDER FILLED PASO A NEW')
            time.sleep(5)
            update_order_cs = client.futures_get_order(symbol = activo, orderId = i)
            logging.debug(update_order_cs) 
        qtty_close_order = float(update_order_cs['cumQuote'])
        qtty_close+= qtty_close_order
    avg_price = float(qtty_close)/float(cant_cripto_aper)
    qtty_close = float(cant_aper) +(float(cant_aper) - float(qtty_close))-float(qtty_close)*0.0002
    return update_order_cs, qtty_close, avg_price

def balance():
    balance_total = client.futures_account_balance()[1]['balance']
    balance_transferible = client.futures_account_balance()[1]['withdrawAvailable']
    return balance_total, balance_transferible

def position(activo):
    
    position = client.futures_position_information()
    for i in range(len(position)):
        if activo == position[i]['symbol']:
            pos_activo = position[i]
    #para los short hay que multiplicar x -1 el resultado
    if float(pos_activo['positionAmt']) >= 0:
        profit_loss = 100*float(pos_activo['unRealizedProfit'])/(float(pos_activo['entryPrice'])*float(pos_activo['positionAmt']))
    else:
        profit_loss = -100*float(pos_activo['unRealizedProfit'])/(float(pos_activo['entryPrice'])*float(pos_activo['positionAmt']))
    profit_loss = round(profit_loss,2)
    profit_loss_abs = str(round(float(pos_activo['unRealizedProfit']),2))+' USDT'
    return profit_loss_abs, profit_loss
    