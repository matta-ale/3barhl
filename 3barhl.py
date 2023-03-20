import logging
logging.basicConfig(filename="log.txt", level=logging.DEBUG,
                    format="%(asctime)s %(message)s", filemode="w")
#logging.debug("Logging test...")
#logging.info("The program is working as expected")
#logging.warning("The program may not function properly")
#logging.error("The program encountered an error")
#logging.critical("The program crashed")

from telegram import sendTelegram
from datetime import datetime
import pandas as pd
import json, pprint
import config_futures
import websocket
import time
from Binance_futures import *
from parametros import *
import runpy
import sys
import os
import pandas_ta as ta
#defino la función que me devuelve el indicador (le agregué return data abajo)
def add_tdfi_indicator(data, tdfi_p, tdfi_s):
    limit_up = 0.05
    limit_down = -0.05
    mma = ta.ema(data.Close, tdfi_p)
    smma = ta.ema(mma, tdfi_p)
    impetmma = ta.mom(mma,1)
    impetsmma = ta.mom(smma,1)
    divma = abs(mma - smma) / 0.01
    averimpet = ((impetmma+impetsmma)/2)/ (2*0.01)
    tdfRaw = (divma * (averimpet**3)).fillna(0)
    tdfAbsRaw = abs(tdfRaw)
    
    cand = tdfAbsRaw.rolling(3*tdfi_p-1).max()
    ratio = (tdfRaw / cand).fillna(0)

    #smoothing:
    alpha = 0.45*(tdfi_s-1) / (0.45*(tdfi_s-1)+2)
    e0 = [0]*len(data)
    e1 = [0]*len(data)
    e2 = [0]*len(data)
    smooth = [0]*len(data)
    tdf = [0]*len(data)
    tdf_trend = ['']*len(data)
    
    for x in range(1,len(data)):
        e0[x] = (1-alpha)*ratio[x] + alpha*e0[x-1]
        e1[x] = (1-alpha)*(ratio[x]-e0[x])+alpha*e1[x-1]
        e2[x] = ((1-alpha)**2)*(e0[x]+e1[x]-smooth[x-1])+((alpha**2)*e2[x-1])
        smooth[x] = e2[x] + smooth[x-1]

        tdf[x] = max(min(smooth[x],1),-1)
        if tdf[x] > limit_up:
            tdf_trend[x] = 'LONG'
        elif tdf[x] < limit_down:
            tdf_trend[x] = 'SHORT'

    data['tdfi'] = tdf
    data['tdfi_trend'] = tdf_trend
    return data
       

dfDict = {}  #creo el diccionario de dataFrames, acá se almacenan los df de cada ticker
#bajo los datos para armar los df de cada symbol
for token1 in tickers:
    ticker = token1 + token2
    #candles = client.futures_historical_klines_generator(ticker, timeframe[interval],fecha_aux,fecha_hasta)
    candles = client.futures_continous_klines(pair = ticker,contractType ='PERPETUAL', interval =timeframe[interval],limit = cant_rows_df)
    data = pd.DataFrame(candles, columns = ['timestamp', 'Open','High','Low','Close','Volume','Col1','Col2','Col3','Col4','Col5','Col6'])
    data = data.drop(['Col1','Col2','Col3','Col4','Col5','Col6'],axis =1)
    data['timestamp']=data['timestamp']/1000
    data['timestamp'] = [datetime.datetime.fromtimestamp(x) for x in data['timestamp']]
    data = data.set_index('timestamp')
    data['Open'] = data['Open'].astype(float)
    data['High'] = data['High'].astype(float)
    data['Low'] = data['Low'].astype(float)
    data['Close'] = data['Close'].astype(float)
    data['Volume'] = data['Volume'].astype(float)
    
    data['mm_high'] = data['High'].rolling(mm).mean()
    data['mm_low'] = data['Low'].rolling(mm).mean()
    
    data['mm_slow'] = data['Close'].rolling(slow_mm).mean()
    data['mm_fast'] = data['Close'].rolling(fast_mm).mean()
    data['trend'] = data['mm_fast'].gt(data['mm_slow']).mul(1)
    #data = data.dropna()

    dfDict[token1] = data 



#creo el string del websocket para todos los tickers
socket = "wss://fstream.binance.com/stream?streams="
for ticker in tickers:   #los tickers vienen de parametros.py
    socket += ticker.lower() + 'usdt@kline_' + interval + '/'

print('arrancando')
def on_open(ws):
    sendTelegram('connection opened')

def on_close(ws, close_status_code, close_msg):
    sendTelegram('closed connection')

def on_message(ws,message):
    #print('received message')
    posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = read_cartera()
    #print('Posicion: ' + str(posicion))
    json_message = json.loads(message)
    candle = json_message['data']['k']
    ticker = candle['s']
    is_candle_closed = candle['x']
    open = float(candle['o'])
    high = float(candle['h'])
    low = float(candle['l'])
    close = float(candle['c'])
    volume = float(candle['v'])
    timestamp = datetime.datetime.fromtimestamp((candle['t'])/1000)
    #actualizo df
    data = dfDict[ticker[:-4]]
    data.loc[timestamp,'Open'] = open
    data.loc[timestamp,'High'] = high
    data.loc[timestamp,'Low'] = low
    data.loc[timestamp,'Close'] = close
    data.loc[timestamp,'Volume'] = volume
    data['mm_high'] = data['High'].rolling(mm).mean()
    data['mm_low'] = data['Low'].rolling(mm).mean()
    data['mm_slow'] = data['Close'].rolling(slow_mm).mean()
    data['mm_fast'] = data['Close'].rolling(fast_mm).mean()
    data['trend'] = data['mm_fast'].gt(data['mm_slow']).mul(1)
    #agrego indicador 
    data = add_tdfi_indicator(data, tdfi_p, tdfi_s)
    dfDict[ticker[:-4]] = data
    
    
    if posicion == 'COMPRADO' and activo == ticker:
        if data.loc[timestamp,'Close'] <= stop_value:
            motivo = 'STOP LOSS'
            precio_cierre_target = data.loc[timestamp,'Close']
            close_long_order, qtty_close, avg_price = close_long(activo,cantidad,precio_aper,precio_cierre_target)
            sendTelegram('CERRAR LONG DE ' + activo +' POR ' + motivo)
            posicion = 'LIQUIDO'
            activo = 'NINGUNO'
            resultado = ((float(qtty_close) + float(resto))/(float(precio_aper)*float(cantidad)*0.9998 + float(resto)) -1)*100
            cantidad = float(qtty_close) + float(resto) #la comisión ya se calcula en Binance_futures
            sendTelegram('P/L OPERACIÓN: ' + str(round(float(resultado),2)) + '%')
            profit_loss = (float(cantidad)/float(cant_inic)-1)*100
            precio_aper = 0
            stop_value = 0
            take_profit = 0
            resto = 0
            precio_cierre = float(avg_price)
            posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit)
            time_close = datetime.datetime.fromtimestamp(float(close_long_order['updateTime'])/1000).strftime('%Y/%m/%d %H:%M:%S')
            cierre_to_excel(cant_inic,time_close,precio_cierre,precio_cierre_target,qtty_close,motivo)
            runpy.run_path('send_cartera.py')
        elif data.loc[timestamp,'Close'] >= take_profit:
            motivo = 'TAKE PROFIT'
            precio_cierre_target = data.loc[timestamp,'Close']
            close_long_order, qtty_close, avg_price = close_long(activo,cantidad,precio_aper,precio_cierre_target)
            sendTelegram('CERRAR LONG DE ' + activo +' POR ' + motivo)
            posicion = 'LIQUIDO'
            activo = 'NINGUNO'
            resultado = ((float(qtty_close) + float(resto))/(float(precio_aper)*float(cantidad)*0.9998 + float(resto)) -1)*100
            cantidad = float(qtty_close) + float(resto) #la comisión ya se calcula en Binance_futures
            sendTelegram('P/L OPERACIÓN: ' + str(round(float(resultado),2)) + '%')
            profit_loss = (float(cantidad)/float(cant_inic)-1)*100
            precio_aper = 0
            stop_value = 0
            take_profit = 0
            resto = 0
            precio_cierre = float(avg_price)
            posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit)
            time_close = datetime.datetime.fromtimestamp(float(close_long_order['updateTime'])/1000).strftime('%Y/%m/%d %H:%M:%S')
            cierre_to_excel(cant_inic,time_close,precio_cierre,precio_cierre_target,qtty_close,motivo)
            runpy.run_path('send_cartera.py')
        elif data.loc[timestamp,'Close'] >= data.loc[timestamp,'mm_high']:
            motivo = 'CONDICIÓN DE SALIDA'
            precio_cierre_target = data.loc[timestamp,'Close']
            close_long_order, qtty_close, avg_price = close_long(activo,cantidad,precio_aper,precio_cierre_target)
            sendTelegram('CERRAR LONG DE ' + activo +' POR ' + motivo)
            posicion = 'LIQUIDO'
            activo = 'NINGUNO'
            resultado = ((float(qtty_close) + float(resto))/(float(precio_aper)*float(cantidad)*0.9998 + float(resto)) -1)*100
            cantidad = float(qtty_close) + float(resto) #la comisión ya se calcula en Binance_futures
            sendTelegram('P/L OPERACIÓN: ' + str(round(float(resultado),2)) + '%')
            profit_loss = (float(cantidad)/float(cant_inic)-1)*100
            precio_aper = 0
            stop_value = 0
            take_profit = 0
            resto = 0
            precio_cierre = float(avg_price)
            posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit)
            time_close = datetime.datetime.fromtimestamp(float(close_long_order['updateTime'])/1000).strftime('%Y/%m/%d %H:%M:%S')
            cierre_to_excel(cant_inic,time_close,precio_cierre,precio_cierre_target,qtty_close,motivo)
            runpy.run_path('send_cartera.py')
    
    elif posicion == 'VENDIDO' and activo == ticker:
        if data.loc[timestamp,'Close'] >= stop_value:
            motivo = 'STOP LOSS'
            precio_cierre_target = data.loc[timestamp,'Close']
            close_short_order, qtty_close, avg_price = close_short(activo,cantidad,precio_aper,precio_cierre_target)
            sendTelegram('CERRAR SHORT DE ' + activo +' POR ' + motivo)
            posicion = 'LIQUIDO'
            activo = 'NINGUNO'
            resultado = ((float(qtty_close) + float(resto))/(float(precio_aper)*float(cantidad)*0.9998 + float(resto)) -1)*100
            cantidad = float(qtty_close) + float(resto) #la comisión ya se calcula en Binance_futures
            sendTelegram('P/L OPERACIÓN: ' + str(round(float(resultado),2)) + '%')
            profit_loss = profit_loss = (float(cantidad)/float(cant_inic)-1)*100
            precio_aper = 0
            stop_value = 0
            take_profit = 0
            resto = 0
            precio_cierre = float(avg_price)
            posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit)
            time_close = datetime.datetime.fromtimestamp(float(close_short_order['updateTime'])/1000).strftime('%Y/%m/%d %H:%M:%S')
            cierre_to_excel(cant_inic,time_close,precio_cierre,precio_cierre_target,qtty_close,motivo)
            runpy.run_path('send_cartera.py')
        elif data.loc[timestamp,'Close'] <= take_profit:
            motivo = 'TAKE PROFIT'
            precio_cierre_target = data.loc[timestamp,'Close']
            close_short_order, qtty_close, avg_price = close_short(activo,cantidad,precio_aper,precio_cierre_target)
            sendTelegram('CERRAR SHORT DE ' + activo +' POR ' + motivo)
            posicion = 'LIQUIDO'
            activo = 'NINGUNO'
            resultado = ((float(qtty_close) + float(resto))/(float(precio_aper)*float(cantidad)*0.9998 + float(resto)) -1)*100
            cantidad = float(qtty_close) + float(resto) #la comisión ya se calcula en Binance_futures
            sendTelegram('P/L OPERACIÓN: ' + str(round(float(resultado),2)) + '%')
            profit_loss = profit_loss = (float(cantidad)/float(cant_inic)-1)*100
            precio_aper = 0
            stop_value = 0
            take_profit = 0
            resto = 0
            precio_cierre = float(avg_price)
            posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit)
            time_close = datetime.datetime.fromtimestamp(float(close_short_order['updateTime'])/1000).strftime('%Y/%m/%d %H:%M:%S')
            cierre_to_excel(cant_inic,time_close,precio_cierre,precio_cierre_target,qtty_close,motivo)
            runpy.run_path('send_cartera.py')
        elif data.loc[timestamp,'Close'] <= data.loc[timestamp,'mm_low']:
            motivo = 'CONDICIÓN DE SALIDA'
            precio_cierre_target = data.loc[timestamp,'Close']
            close_short_order, qtty_close, avg_price = close_short(activo,cantidad,precio_aper,precio_cierre_target)
            sendTelegram('CERRAR SHORT DE ' + activo +' POR ' + motivo)
            posicion = 'LIQUIDO'
            activo = 'NINGUNO'
            resultado = ((float(qtty_close) + float(resto))/(float(precio_aper)*float(cantidad)*0.9998 + float(resto)) -1)*100
            cantidad = float(qtty_close) + float(resto) #la comisión ya se calcula en Binance_futures
            sendTelegram('P/L OPERACIÓN: ' + str(round(float(resultado),2)) + '%')
            profit_loss = profit_loss = (float(cantidad)/float(cant_inic)-1)*100
            precio_aper = 0
            stop_value = 0
            take_profit = 0
            resto = 0
            precio_cierre = float(avg_price)
            posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit)
            time_close = datetime.datetime.fromtimestamp(float(close_short_order['updateTime'])/1000).strftime('%Y/%m/%d %H:%M:%S')
            cierre_to_excel(cant_inic,time_close,precio_cierre,precio_cierre_target,qtty_close,motivo)
            runpy.run_path('send_cartera.py')
    
    if is_candle_closed == True:
        
            
        if posicion == 'LIQUIDO':
            if  data.loc[timestamp,'trend'] == 1 and data.loc[timestamp,'Close'] <= data.loc[timestamp,'mm_low'] and data.loc[timestamp,'tdfi_trend'] == 'LONG':
                activo = ticker
                precio_aper_target = data.loc[timestamp,'Close']
                long_order, qtty, avg_price = open_long(precio_aper_target,activo,float(cantidad)*0.9998,digits_cant[activo[:-4]])
                sendTelegram('ABRIR LONG DE '+ ticker +' @ '+str(round(float(precio_aper_target),digits[activo[:-4]])))
                if long_order['status'] == 'FILLED':
                    posicion = 'COMPRADO'
                    precio_aper = float(avg_price)
                    stop_value = precio_aper*(1-float(sl[ticker[:-4]]))
                    take_profit = precio_aper*(1+float(tp[ticker[:-4]]))
                    resto = float(cantidad)*0.9998 - float(qtty)*precio_aper
                    msg = 'OPERADO LONG DE ' +str(round(float(cantidad),2)) + ' USDT de ' + str(activo)+'\nCant Operado: ' +str(round(float(qtty),digits_cant[activo[:-4]]))+' '+str(activo[:-4])+'\nPrecio Operado: '+str(round(float(precio_aper),digits[activo[:-4]]))+' USDT\nStop Loss: '+str(round(float(stop_value),digits[activo[:-4]]))+' USDT\nTake_Profit: '+str(round(float(take_profit),digits[activo[:-4]]))
                    sendTelegram(msg)
                    cantidad = float(qtty)
                    posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit)
                    time_aper = datetime.datetime.fromtimestamp(float(long_order['updateTime'])/1000).strftime('%Y/%m/%d %H:%M:%S')
                    aper_to_excel(time_aper,'LONG',activo,precio_aper,precio_aper_target,cantidad,resto)
                else:
                    sendTelegram('NO SE PUDO ABRIR LONG DE '+ ticker)
                

            elif  data.loc[timestamp,'trend'] == 0 and data.loc[timestamp,'Close'] >= data.loc[timestamp,'mm_high'] and data.loc[timestamp,'tdfi_trend'] == 'SHORT':
                activo = ticker
                precio_aper_target = data.loc[timestamp,'Close']
                short_order, qtty, avg_price = open_short(precio_aper_target,activo,float(cantidad)*0.9998,digits_cant[activo[:-4]])
                if short_order['status'] == 'FILLED':
                    sendTelegram('ABRIR SHORT DE '+ ticker +' @ '+str(round(float(precio_aper_target),digits[activo[:-4]])))
                    posicion = 'VENDIDO'
                    precio_aper = float(avg_price)
                    stop_value = precio_aper*(1+float(sl[ticker[:-4]]))
                    take_profit = precio_aper*(1-float(tp[ticker[:-4]]))
                    resto = float(cantidad)*0.9998 - float(qtty)*precio_aper
                    msg = 'OPERADO SHORT DE ' +str(round(float(cantidad),2)) + ' USDT de ' + str(activo)+'\nCant Operado: ' +str(round(float(qtty),digits_cant[activo[:-4]]))+' '+str(activo[:-4])+'\nPrecio Operado: '+str(round(float(precio_aper),digits[activo[:-4]]))+' USDT\nStop Loss: '+str(round(float(stop_value),digits[activo[:-4]]))+' USDT\nTake_Profit: '+str(round(float(take_profit),digits[activo[:-4]]))
                    sendTelegram(msg)
                    cantidad = float(qtty)
                    posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit = modify_cartera(posicion, activo, cant_inic, cantidad, resto, profit_loss, precio_aper, stop_value, take_profit)
                    time_aper = datetime.datetime.fromtimestamp(float(short_order['updateTime'])/1000).strftime('%Y/%m/%d %H:%M:%S')
                    aper_to_excel(time_aper,'SHORT',activo,precio_aper,precio_aper_target,cantidad,resto)
                else:
                    sendTelegram('NO SE PUDO ABRIR SHORT DE '+ ticker)
                

        if ticker[:-4] == tickers[0]:
            runpy.run_path('send_cartera.py')

        
    if len(dfDict[ticker[:-4]]) > cant_rows_df:
        dfDict[ticker[:-4]].drop(index=dfDict[ticker[:-4]].index[0],axis=0,inplace=True)
            
while True:       
    try:
        ws = websocket.WebSocketApp(socket, on_open=on_open,on_close=on_close,on_message=on_message)
        ws.run_forever() 
    except Exception as e:
        logging.debug("Websocket connection Error  : {0}".format(e))                    
        logging.debug("Reconnecting websocket  after 5 sec")
        time.sleep(5)
