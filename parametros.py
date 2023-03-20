from binance.client import Client
tickers = ['AVAX','ETH','SOL','ADA']
digits = {'NIN': 0,'SOL': 3,'AVAX': 3,'ADA': 4,'BTC': 0,'ETH': 0}
digits_cant = {'NIN': 0,'SOL': 0,'AVAX': 0, 'ADA': 0,'BTC': 3,'ETH': 3}
interval = '30m'
token2 = 'USDT'
timeframe = {'1m' :  Client.KLINE_INTERVAL_1MINUTE, '3m' : Client.KLINE_INTERVAL_3MINUTE,'5m' : Client.KLINE_INTERVAL_5MINUTE,'15m' : Client.KLINE_INTERVAL_15MINUTE,'30m' : Client.KLINE_INTERVAL_30MINUTE,'1h' : Client.KLINE_INTERVAL_1HOUR,'2h' : Client.KLINE_INTERVAL_2HOUR,'4h' : Client.KLINE_INTERVAL_4HOUR,'6h' : Client.KLINE_INTERVAL_6HOUR,'8h' : Client.KLINE_INTERVAL_8HOUR,'12h' : Client.KLINE_INTERVAL_12HOUR,'1d' : Client.KLINE_INTERVAL_1DAY}
minutes = {'1m' : 1, '3m' : 3,'5m' : 5,'15m' : 15,'30m' : 30,'1h' : 60,'2h' : 120,'4h' : 240,'6h' : 360,'8h' : 480,'12h' : 720,'1d' : 1440}
mm = 3 #cantidad de velas de la media movil para las bandas de low y high que se usan para entrar y salir al trade
slow_mm = 20
fast_mm = 2
tdfi_p = 20
tdfi_s = 6
cant_rows_df = 200 #cantidad de filas de los df que usamos 
sl = {'SOL': 0.03, 'AVAX': 0.03,'ETH' : 0.03, 'BTC' : 0.03, 'ADA': 0.03}
tp = {'SOL': 0.01,'AVAX': 0.01,'ETH' : 0.01,'BTC' : 0.01, 'ADA': 0.01}
