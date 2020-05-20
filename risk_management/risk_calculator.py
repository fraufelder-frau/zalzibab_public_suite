#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from datetime import datetime, timedelta, timezone
from sympy import symbols, Eq, solve
from bybit import bybit
from bitmex import bitmex
from qtrade_client.api import QtradeAPI
import requests
import ast
import os
from os import walk
import json
import warnings
warnings.simplefilter("ignore")
import bravado.exception
import io
import time
import decimal

#Pull Bucketed Trade Data
def bybit_kline_data(client, interval, timestamp):
    params = {"symbol": 'BTCUSD',
          "interval": interval,
          "from": timestamp,
          "limit": "1"}
    pull_data = client.Kline.Kline_get(**params).result()
    return pull_data

def position_size(entry, stop, balance, risk, target, takerFee, makerFee, order_type):
    x = symbols('x')
    if target > entry:
        target_value = (1/target)+((1/target)*takerFee)
        stop_value = (1/stop)+((1/stop)*takerFee)
        if order_type == 'Limit':
            entry_value = (1/entry)-((1/entry)*makerFee)
            eq1 = Eq((x*(entry_value - stop_value)) + (balance*risk/100)) 
        else:
            entry_value = (1/entry)-((1/entry)*takerFee)
            eq1 = Eq((x*(entry_value - stop_value)) + (balance*risk/100))
    elif target < entry:
        target_value = (1/target)-((1/target)*takerFee)
        stop_value = (1/stop)-((1/stop)*takerFee)
        if order_type == 'Limit':
            entry_value = (1/entry)+((1/entry)*makerFee)
            eq1 = Eq((x*(stop_value - entry_value)) - (balance*risk/100))
        else:
            entry_value = (1/entry)+((1/entry)*takerFee)
            eq1 = Eq((x*(stop_value - entry_value)) - (balance*risk/100))
    size = solve(eq1)
    size = [ '%.0f' % elem for elem in size ]
    size = size[0]
    return size, entry_value, stop_value, target_value

def risk_amount_XBT(entry_value, stop_value, size):
    risk_amount = (size*(entry_value - stop_value))
    risk_amount = float(round(risk_amount, 8))
    return risk_amount

def reward_amount_XBT(entry_value, target_value, size):
    reward_amount = (size*(target_value - entry_value))
    reward_amount = float(round(reward_amount, 8))
    return reward_amount

def r_calc(reward_amount, risk_amount):
    r_r = reward_amount/risk_amount
    return r_r

def bybit_new_trade(client, contract, size, entry, target, stop, order_type):
    if order_type == 'Market':
        if target > entry:
            order_side = 'Buy'
            stop_side = 'Sell'
        else:
            order_side = 'Sell'
            stop_side = 'Buy'
        client.Order.Order_newV2(symbol=contract, side=order_side, order_type='Market', qty=size, time_in_force='GoodTillCancelled').result()
        client.Order.Order_newV2(side=stop_side, symbol=contract, order_type='Limit', qty=size, price=target, time_in_force='GoodTillCancelled', reduce_only=True, close_on_trigger=True).result()
    else:
        client.Order.Order_newV2(side=order_side, symbol=contract, order_type='Limit', qty=size, price=entry, time_in_force='GoodTillCancelled').result()
        if target < entry:
            stop_limit_trigger = entry+0.5
        else:
            stop_limit_trigger = entry-0.5
        client.Conditional.Conditional_new(side=stop_side, base_price=round(float(client.Market.Market_symbolInfo(symbol='BTCUSD').result()[0]['result'][0]['mark_price']), 0),  symbol=contract, order_type='Limit', qty=size, time_in_force='ImmediateOrCancel', price=target, stop_px=stop_limit_trigger, close_on_trigger=True).result()
    client.Conditional.Conditional_new(side=stop_side, base_price=round(float(client.Market.Market_symbolInfo(symbol='BTCUSD').result()[0]['result'][0]['mark_price']), 0),  symbol=contract, order_type='Market', qty=size, time_in_force='ImmediateOrCancel', stop_px=stop, close_on_trigger=True).result()
    return None

def bybit_open_positions(client, contract):
    null_orders = ['Deactivated', 'Cancelled', 'Filled']
    resp = client.Positions.Positions_myPositionV2(symbol=contract).result()[0]['result']
    open_orders = [x for x in client.Order.Order_getOrders().result()[0]['result']['data'] if x['order_status'] not in  null_orders]
    bit = {}
    bit['Timestamp'] = tz_to_str(resp['updated_at'], '%m-%d-%Y %H:%M:%S')
    bit['Contract'] = contract
    bit['Side'] = resp['side']
    bit['Size'] = resp['size']
    bit['Entry'] = round(float(resp['entry_price']), 2)
    if bit['Side'] == 'Buy':
        for x in open_orders:
            if x['side'] != bit['Side']:
                if x['order_type'] == 'Market':
                    if float(x['ext_fields']['trigger_price']) > bit['Entry']:
                        bit['Target'] = usd_str(x['ext_fields']['trigger_price'])
                    else:
                        bit['Stop'] = usd_str(x['ext_fields']['trigger_price'])
                else:
                    if float(x['price']) > bit['Entry']:
                        bit['Target'] = usd_str(x['price'])
                    else:
                        bit['Stop'] = usd_str(x['ext_fields']['trigger_price'])
    else:
        for x in open_orders:
            if x['side'] != bit['Side']:
                if float(x['price']) < bit['Entry']:
                    bit['Target'] = usd_str(x['price'])
                else:
                    bit['Stop'] = usd_str(x['ext_fields']['trigger_price'])
    bit['UnrealisedPnL'] = btc_str(resp['unrealised_pnl'])
    bit['Entry'] = usd_str(bit['Entry'])
    return bit

def bybit_close_position(client, contract_to_view):
    orderQty = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']['size']
    side = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']['side']
    if side == 'Buy':
        client.Order.Order_newV2(symbol=contract_to_view, side='Sell', order_type='Market', qty=orderQty, time_in_force='GoodTillCancelled').result()
    elif side == 'Sell':
        client.Order.Order_newV2(symbol=contract_to_view, side='Buy', order_type='Market', qty=orderQty, time_in_force='GoodTillCancelled').result()
    return print(contract_to_view+' Position Closed')

def bybit_amend_order(client, new_stop, new_target, contract_to_view):
    null_orders = ['Deactivated', 'Cancelled', 'Filled']
    resp = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']
    side = resp['side']
    entry = round(float(resp['entry_price']), 2)
    open_orders = [x for x in client.Order.Order_getOrders().result()[0]['result']['data'] if x['order_status'] not in  null_orders]
    if side == 'Buy':
        for x in open_orders:
            if x['side'] != side:
                if x['order_type'] == 'Market':
                    if float(x['ext_fields']['trigger_price']) > entry:
                        close_id = x['order_id']
                    else:
                        stop_id = x['order_id']
                else:
                    if float(x['price']) > entry:
                        close_id = x['order_id']
                    else:
                        stop_id = x['order_id']
    else:
        for x in open_orders:
            if x['side'] != side:
                if x['order_type'] == 'Market':
                    if float(x['ext_fields']['trigger_price']) < entry:
                        close_id = x['order_id']
                    else:
                        stop_id = x['order_id']
                else:
                    if float(x['price']) > entry:
                        close_id = x['order_id']
                    else:
                        stop_id = x['order_id']
    if new_stop != 0:
        client.Conditional.Conditional_replace(symbol=contract_to_view, order_id=stop_id, p_r_trigger_price=new_stop).result()
        print('Stop Amended to '+usd_str(new_stop))
    if new_target != 0:
        client.Order.Order_replace(order_id=close_id, symbol=contract_to_view, p_r_price=new_target).result()
        print('Close Amended to '+usd_str(new_target))
    return None

def bybit_take_profit_order(client, take_profit, new_stop, new_target, contract_to_view):
    resp = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']
    side = resp['side']
    take_profit_size = round(((resp['size']*(int(take_profit)/100))), 0)
    client.Conditional.Conditional_cancelAll(symbol=contract_to_view).result()
    client.Order.Order_cancelAll(symbol=contract_to_view).result()
    if side == 'Buy':
        order_side = 'Sell'
    else:
        order_side = 'Buy'
    client.Order.Order_newV2(side=order_side, symbol=contract_to_view, order_type='Market', qty=take_profit_size, time_in_force='GoodTillCancelled').result()
    time.sleep(1)
    new_size = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']['size']
    if new_target != 0:
        client.Order.Order_newV2(side=order_side, symbol=contract_to_view, order_type='Limit', qty=new_size, price=new_target, time_in_force='GoodTillCancelled', reduce_only=True, close_on_trigger=True).result()
        print('Target for '+contract_to_view+' Set to '+usd_str(new_target))
    if new_stop != 0:
        client.Conditional.Conditional_new(side=order_side, base_price=round(float(client.Market.Market_symbolInfo(symbol='BTCUSD').result()[0]['result'][0]['mark_price']), 0),  symbol=contract_to_view, order_type='Market', qty=new_size, time_in_force='ImmediateOrCancel', stop_px=new_stop, close_on_trigger=True).result()
        print('Stop for '+contract_to_view+' Set to '+usd_str(new_stop))
    return None

def btc_float_round(value):
    rounded_value = round(value, 8)
    return rounded_value

def btc_str2float_round(value):
    rounded_value = round(float(value), 8)
    return rounded_value

#Legible format for BTC values
def btc_str(value):
    value = "{:,.8f}".format(value)
    return value

#Legible format for USD values
def usd_str(value):
    if '.' in str(value):
        if value < 0:
            value = value*-1
            value = '-'+"${:,.2f}".format(value)
        else:
            value = "${:,.2f}".format(value)
    else:
        if value < 0:
            value = value*-1
            value = '-'+"${:,}".format(value)
        else:
            value = "${:,}".format(value)
    return value

def tz_to_timestamp(str_date):
    new_time = datetime.timestamp(datetime.strptime(str_date, '%Y-%m-%dT%H:%M:%S.%fZ'))
    return new_time

def tz_to_str(tz_date, str_format):
    str_time = datetime.strftime(datetime.strptime(tz_date, '%Y-%m-%dT%H:%M:%S.%fZ'), str_format)
    return str_time

def find_file(file_type):
    f = []
    if file_type == 'credentials':
        file_path = str(sys.path[0])+'/credentials'
    else:
        file_path = str(sys.path[0])+'/configurations'
    for (dirpath, dirnames, filenames) in walk(file_path):
        f.extend(filenames)
        return f

def check_credentials(exchange):
    while True:
        credentials_file = [x for x in find_file('credentials') if exchange in x][0]
        credentials = load_file(str(sys.path[0])+'/credentials/'+credentials_file)
        print('\n')
        if credentials['api_key'] == 'XXX':
            print('Please Enter Your '+exchange+' API Key')
            credentials['api_key'] = str(input('> '))
        else:
            print('Change Your '+exchange+' API Key?')
            resp = y_n_prompt()
            if resp == 'Yes':
                print('\n')
                print('Please Enter Your '+exchange+' API Key')
                credentials['api_key'] = str(input('> '))
                print('\n')
                if exchange != 'qTrade':
                    print('Please Enter Your '+exchange+' API Secret')
                    credentials['api_secret'] = str(input('> '))
        if exchange != 'qTrade' and credentials['api_secret'] == 'TTT':
            print('\n')
            print('Please Enter Your '+exchange+' API Secret')
            credentials['api_secret'] = str(input('> '))
        if credentials['bot_token'] == 'YYY' or credentials['bot_chatID'] == 'ZZZ':
            print('\n')
            print('Integrate Telegram Bot?')
            resp = y_n_prompt()
            if resp == 'Yes':
                print('\n')
                print('Please Enter Your Bot Token')
                credentials['bot_token'] = str(input('> '))
                print('\n')
                print('Please Enter Your Telegram Chat ID')
                credentials['bot_chatID'] = str(input('> '))
                if telegram_sendText((credentials['bot_token'], credentials['bot_chatID']), 'Testing')['ok'] == False:
                    print('Invalid Bot Credentials'+'\n')
                    continue
                else:
                    print('\n'+'Confirm Test Message Receipt')
                    resp = y_n_prompt()
                    if resp == 'No':
                        continue
                    else:
                        print('Bot Credentials Verified'+'\n')
        else:
            print('\n')
            print('Change Your Bot?')
            resp = y_n_prompt()
            if resp == 'Yes':
                print('\n')
                print('Please Enter Your Bot Token')
                credentials['bot_token'] = str(input('> '))
                print('\n')
                print('Please Enter Your Telegram Chat ID')
                credentials['bot_chatID'] = str(input('> '))
                if telegram_sendText((credentials['bot_token'], credentials['bot_chatID']), 'Testing')['ok'] == False:
                    print('Invalid Bot Credentials'+'\n')
                    continue
                else:
                    print('\n'+'Confirm Test Message Receipt')
                    resp = y_n_prompt()
                    if resp == 'No':
                        continue
                    else:
                        print('Bot Credentials Verified'+'\n')
        save_credentials = save_file(str(sys.path[0])+'/credentials/'+credentials_file, credentials)
        if exchange == 'Bitmex':
            client = bitmex(test=False,api_key=credentials['api_key'],api_secret=credentials['api_secret'])
            try:
                client.APIKey.APIKey_get().result
            except bravado.exception.HTTPError:
                print('Invalid Credentials'+'\n')
                continue
        elif exchange == 'Bybit':
            client = bybit(test=False,api_key=credentials['api_key'],api_secret=credentials['api_secret'])
            resp = client.APIkey.APIkey_info().result()[0]['ret_msg'];
            if resp == 'invalid api_key':
                print('Invalid Credentials'+'\n')
                continue
        elif exchange == 'qTrade':
            try:
                client = QtradeAPI('https://api.qtrade.io', key=credentials['api_key'])
                client.get("/v1/user/me")
            except:
                print('Invalid Credentials'+'\n')
                continue
        break
        save_credentials = save_file(str(sys.path[0])+'/credentials/'+credentials_file, credentials)
        credentials_file = [x for x in find_file('credentials') if exchange in x][0]
        credentials = load_file(str(sys.path[0])+'/credentials/'+credentials_file)
    return print('\n'+exchange+' Credentials Verified'), client, (credentials['bot_token'], credentials['bot_chatID'])

#Telegram Text Alert
def telegram_sendText(bot_credentials, bot_message):
    bot_token = bot_credentials[0]
    bot_chatID = bot_credentials[1]
    send_text = 'https://api.telegram.org/bot'+bot_token+'/sendMessage?chat_id='+bot_chatID+'&parse_mode=Markdown&text='+bot_message
    response = requests.get(send_text)
    return response.json()

#Telegram Image Alert
def telegram_sendImage(bot_credentials, image):
    bot_token = bot_credentials[0]
    bot_chatID = bot_credentials[1]
    url = 'https://api.telegram.org/bot'+bot_token+'/sendPhoto';
    files = {'photo': open(image, 'rb')}
    data = {'chat_id' : bot_chatID}
    r = requests.post(url, files=files, data=data)
    return r

def telegram_sendFile(bot_credentials, file):
    bot_token = bot_credentials[0]
    bot_chatID = bot_credentials[1]
    url = 'https://api.telegram.org/bot'+bot_token+'/sendDocument';
    files = {'document': open(file, 'rb')}
    data = {'chat_id' : bot_chatID}
    r = requests.post(url, files=files, data=data)
    return r

def float_range(start, stop, step):
    while start < stop:
        yield float(start)
        start += decimal.Decimal(step)

def input_price(client, dialogue, valid_ticks):
    while True:
        print(dialogue)
        price = input('> ')
        print('\n')
        if '.' not in price and price[-1] not in str(valid_ticks) or '.' in price and price[-1] not in str({0, 5}):
            print('Invalid Tick Size'+'\n')
            continue
        else:
            price = float(price)
            break
    return price

#Read .txt files
def load_file(file):
    temp_list = []
    f = open(file, "r")
    for x in f:
        temp_list.append(x.rstrip('\n'))
    load = [ast.literal_eval(i) for i in temp_list][0]
    f.close()
    return load

def y_n_prompt():
    while True:
        y_n_responses = ['Yes', 'No']
        for (x, y) in enumerate(y_n_responses):
            print(str(x)+': '+y)
        response = y_n_responses[int(input('> '))]
        if response not in y_n_responses:
            print('Invalid Selection'+'\n')
            continue
        else:
            break
    return response

#Write to .txt file
def save_file(file, item):
    with open(file, mode="w") as outfile:
        outfile.write(str(item))
    return None

#Sort tuples by value by index
def sortTuple(tup, index):
    return(sorted(tup, key = lambda x: x[index], reverse=True))

#Remove duplicate values from sorted lists
def sorted_list(list_to_sort):
    return list(dict.fromkeys(list_to_sort))

def print_dict(dict_item):
    try:
        for x in range(len(dict_item)):
            for k, v in dict_item[x].items():
                print(str(k)+': '+str(v))
            print('\n')
    except KeyError:
        for k, v in dict_item.items():
            print(str(k)+': '+str(v))
        print('\n')
    return None

#User promp based list element selection by index
def list_user_prompt(initial_dialogue, list_to_view):
    print(initial_dialogue)
    while True:
        try:
            for k, v in enumerate(list_to_view):
                print(str(k)+': '+v)
            resp = list_to_view[int(input('> '))]
        except (IndexError, ValueError):
            print('Selection must be int'+'\n')
            continue
        else:
            print('Selection: '+str(resp))
            break
    return resp

def create_directory(directory):
    if os.path.exists(str(sys.path[0])+'/'+directory+'/') == False:
        directory = directory
        path = os.path.join(str(sys.path[0]), directory)
        os.mkdir(path)
    return None

def sleep_time(timeframe, count, second, minute):
    now = datetime.utcnow()
    if timeframe == 'minute':
        delta = timedelta(minutes=count)
        start_loop = (now + delta).replace(microsecond=0, second=second)
    elif timeframe == 'hour':
        delta = timedelta(hours=count)
        start_loop = (now + delta).replace(microsecond=0, second=second, minute=minute)
    sleep_time = (start_loop - now).total_seconds()
    return sleep_time

def getDuration(start, end, interval = "default"):
    # Returns a duration as specified by variable interval
    # Functions, except totalDuration, returns [quotient, remainder]

    duration = end - start # For build-in functions
    duration_in_s = duration.total_seconds() 

    def years():
        return divmod(duration_in_s, 31536000) # Seconds in a year=31536000.

    def days(seconds = None):
        return divmod(seconds if seconds != None else duration_in_s, 86400) # Seconds in a day = 86400

    def hours(seconds = None):
        return divmod(seconds if seconds != None else duration_in_s, 3600) # Seconds in an hour = 3600

    def minutes(seconds = None):
        return divmod(seconds if seconds != None else duration_in_s, 60) # Seconds in a minute = 60

    def seconds(seconds = None):
        if seconds != None:
            return divmod(seconds, 1)   
        return duration_in_s

    def totalDuration():
        y = years()
        d = days(y[1]) # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])
        
        return "Time between dates: {} years, {} days, {} hours, {} minutes and {} seconds".format(int(y[0]), int(d[0]), int(h[0]), int(m[0]), int(s[0]))

    return {
        'years': int(years()[0]),
        'days': int(days()[0]),
        'hours': int(hours()[0]),
        'minutes': int(minutes()[0]),
        'seconds': int(seconds()),
        'default': totalDuration()
    }[interval]

def bitmex_close_position(client, contract_to_view):
    resp = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]
    if resp['currentQty'] > 0:
        client.Order.Order_new(symbol=contract_to_view, execInst='Close', side='Sell').result()
    else:
        client.Order.Order_new(symbol=contract_to_view, execInst='Close', side='Buy').result()
    client.Order.Order_cancelAll(symbol=contract_to_view).result()
    return print(contract_to_view+' Position Closed')

def bitmex_open_positions(client):
    postions = []
    resp = client.Position.Position_get(filter = json.dumps({'isOpen': True})).result()[0]
    for x in range(len(resp)):
        time.sleep(1)
        current_bitmex = client.Position.Position_get(filter=json.dumps({'symbol': resp[x]['symbol']})).result()[0][0]    
        open_orders = client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true'})).result()[0]
        time.sleep(1)
        if len(client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Limit', 'MarketIfTouched', 'StopLimit', 'LimitIfTouched']})).result()[0]) != 0:
            close_order = client.Order.Order_getOrders(symbol = resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Limit', 'MarketIfTouched', 'StopLimit', 'LimitIfTouched']})).result()[0]
            close_price = usd_str(close_order[0]['price'])
        else:
            close_order = 'No Close Order Set'
            close_price = 'No Close Order Set'
        time.sleep(1)
        if len(client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Stop', 'TrailingStop']})).result()[0]) > 0:
            stop_order = client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Stop', 'TrailingStop']})).result()[0]
            stop_price = usd_str(stop_order[0]['stopPx'])
        else:
            stop_order = 'NO STOP SET!!!'
            stop_price = 'NO STOP SET!!!'
        time.sleep(1)
        mex = {}
        mex['Contract'] = resp[x]['symbol']
        if current_bitmex['currentQty'] < 0:
            mex['Side'] = 'Short'
        elif current_bitmex['currentQty'] > 0:
            mex['Side'] = 'Long'
        else:
            mex['Side'] = 'None'
        if mex['Side'] == 'Short':
            mex['Size'] = current_bitmex['currentQty']*-1
        else:
            mex['Size'] = current_bitmex['currentQty']
        mex['Entry'] = current_bitmex['avgEntryPrice']
        mex['Target'] = close_price
        mex['Stop'] = stop_price
        mex['OpenValue'] = btc_float_round(mex['Size']*((1/mex['Entry'])-(1/mex['Entry'])*0.00075))
        mex['MarketPrice'] = current_bitmex['markPrice']
        mex['MarketValue'] = btc_float_round(mex['Size']*((1/mex['MarketPrice'])-(1/mex['MarketPrice'])*0.00075))
        mex['Entry'] = usd_str(current_bitmex['avgEntryPrice'])
        mex['MarketPrice'] = usd_str(current_bitmex['markPrice'])
        if mex['Side'] == 'Long':
            mex['UnrealisedPnL'] = btc_str(mex['OpenValue'] - mex['MarketValue'])
        else:
            mex['UnrealisedPnL'] = btc_str(mex['MarketValue'] - mex['OpenValue'])
        postions.append(mex)
    return postions

def bitmex_active_contracts(client):
    contracts = requests.get('https://www.bitmex.com/api/v1/instrument/active').json()
    contract_list = [x['symbol'] for x in bitmex_contracts]
    return contract_list

def bitmex_new_trade(client, contract, size, entry, target, stop, order_type):
    if order_type == 'Market':
        client.Order.Order_cancelAll(symbol=contract).result()
        client.Order.Order_new(symbol=contract, orderQty=size, ordType='Market').result()
        client.Order.Order_new(symbol=contract, price=target, execInst='ReduceOnly', orderQty=(size*-1), ordType='Limit').result()
        client.Order.Order_new(symbol=contract, stopPx=stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='Stop').result()
    else:
        client.Order.Order_cancelAll(symbol=contract).result()
        client.Order.Order_new(symbol=contract, orderQty=size, price=entry).result()
        if target < entry:
            stop_limit_trigger = float(float(entry)+0.5)
        else:
            stop_limit_trigger = float(float(entry)-0.5)
        client.Order.Order_new(symbol=contract, stopPx=stop_limit_trigger, price=target, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='StopLimit').result()
        client.Order.Order_new(symbol=contract, stopPx=stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='Stop').result()
    return None

def bitmex_amend_order(client, new_stop, new_target, contract_to_view):
    if len(client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Stop'})).result()[0]) > 0:
        stop = client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Stop'})).result()[0][0]
    else:
        stop = []
    if len(client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'Close'})).result()[0]) > 0:
        close = client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'Close'})).result()[0][0]
    elif len(client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ParticipateDoNotInitiate,ReduceOnly'})).result()[0]) > 0:
        close = client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ParticipateDoNotInitiate,ReduceOnly'})).result()[0][0]
    elif len(client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ReduceOnly'})).result()[0]) > 0:
        close = client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ReduceOnly'})).result()[0][0]
    else:
        close = []
    qty = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]['currentQty']
    orderQty = qty*-1
    if new_stop != 0:
        if len(stop) > 0:
            client.Order.Order_amend(orderID=stop['orderID'], stopPx=new_stop).result()
            print('Stop for '+contract_to_view+' Amended to '+usd_str(new_stop))
        elif len(stop) == 0:
            client.Order.Order_new(symbol=contract_to_view, stopPx=new_stop, execInst=str('LastPrice, ReduceOnly'), orderQty=orderQty, ordType='Stop').result()
            print('Stop for '+contract_to_view+' Set to '+usd_str(new_stop))
    else:
        print('Stop Unchanged')
    if new_target != 0 :
        if len(close) > 0:
            client.Order.Order_amend(orderID=close['orderID'], price=new_target).result()
            print('Target for '+contract_to_view+' Amended to '+usd_str(new_target))
        elif len(close) == 0:
            client.Order.Order_new(symbol=contract_to_view, price=new_target, execInst='ReduceOnly', orderQty=orderQty, ordType='Limit').result()
            print('Target for '+contract_to_view+' Set to '+usd_str(new_target))
    else:
        print('Target Unchanged')
        
        
    return print('\n'+'Updated Positions'), print_dict(open_positions(client))

def bitmex_take_profit_order(client, take_profit, new_stop, new_target, contract_to_view):
    resp = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]
    take_profit_size = round(((resp['currentQty']*(int(take_profit)/100))*-1), 0)
    client.Order.Order_cancelAll(symbol=contract_to_view).result()
    client.Order.Order_new(symbol=contract_to_view, orderQty=take_profit_size, ordType='Market').result()
    new_size = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]['currentQty']
    if new_target != 0:
        client.Order.Order_new(symbol=contract_to_view, price=new_target, execInst='ReduceOnly', orderQty=(new_size*-1), ordType='Limit').result()
        print('Target for '+contract_to_view+' Set to '+usd_str(new_target))
    if new_stop != 0:
        client.Order.Order_new(symbol=contract_to_view, stopPx=new_stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(new_size*-1), ordType='Stop').result()
        print('Stop for '+contract_to_view+' Set to '+usd_str(new_stop))
    return print('\n'+'Updated Positions'), print_dict(open_positions(client))


# In[ ]:


print('Begin Risk Manager')
while True:
    exchanges = ['Bitmex', 'Bybit', 'Exit']
    exchange = list_user_prompt('Choose an Exchange', exchanges)
    if exchange == 'Exit':
        print('Exiting Script')
        break
    verification = check_credentials(exchange)
    client = verification[1]
    bot_credentials = verification[2]
    order_types = ['Market', 'Limit']
    valid_ticks = list(range(10))
    percent_ticks = list(float_range(0, 100, '0.01'))[1:]+[100.00]
    null_orders = ['Deactivated', 'Cancelled', 'Filled']

    if exchange == 'Bitmex':
        contracts = [x['symbol'] for x in client.Instrument.Instrument_getActive().result()[0] if 'XBT' in x['symbol']]
        while True:
            step1_options = ['View/Manage Open Positions', 'Plan New Trade', 'Change Exchange']
            step1 = list_user_prompt('Choose Starting Option', step1_options)
            if step1 == 'Change Exchange':
                break
            elif step1 == 'View/Manage Open Positions':
                mex_positions = bitmex_open_positions(client)
                active_contracts = [x['Contract'] for x in mex_positions]+['Return to Start']
                print('\n'+'Your Bitmex Open Positions'+'\n')
                print_dict(mex_positions)
                step2_options = ['Close Position', 'Amend Orders', 'Take Profit', 'Return to Start']
                step2 = list_user_prompt('Choose an Option', step2_options)
                if step2 != 'Return to Start':
                    contract_to_view = list_user_prompt('Choose a Position to Manage', active_contracts)
                    if contract_to_view == 'Return to Start':
                        print('\n')
                        continue
                    if step2 == 'Close Position':
                        print('\n')
                        bitmex_close_position(client, contract_to_view)
                        continue
                    elif step2 == 'Amend Orders':
                        print('\n')
                        new_stop = input_price(client, 'Enter New Stop Price or 0 to Skip', valid_ticks)
                        new_target = input_price(client, 'Enter New Target Price or 0 to Skip', valid_ticks)
                        bitmex_amend_order(client, new_stop, new_target, contract_to_view)
                        continue
                    elif step2 == 'Take Profit':
                        print('\n')
                        while True:
                            try:
                                take_profit = float(input('Percent of '+contract_to_view+' position to close'+'\n'+'> '))
                            except TypeError:
                                print('Must be a number'+'\n')
                                continue
                            if take_profit == 0:
                                break
                            else:
                                if take_profit not in percent_ticks:
                                    print('Invalid Entry'+'\n')
                                    continue
                                break
                        if take_profit == 0:
                            continue
                        else:
                            new_stop = input_price(client, 'Enter New Stop Price or 0 to Skip', valid_ticks)
                            new_target = input_price(client, 'Enter New Target Price or 0 to Skip', valid_ticks)
                            bitmex_take_profit_order(client, take_profit, new_stop, new_target, contract_to_view)
                            continue

            elif step1 == 'Plan New Trade':
                contract = list_user_prompt('Choose Contract to Trade', contracts)
                order_type = list_user_prompt('Choose Order Type for Entry', order_types)
                stop = input_price(client, 'Enter Stop Price', valid_ticks)
                target = input_price(client, 'Enter Target Price', valid_ticks)
                contract_data = client.Instrument.Instrument_getActive().result()[0] 
                contract_data = next(item for item in contract_data if item["symbol"] == contract)
                bidPrice = float(contract_data['bidPrice'])
                askPrice = float(contract_data['askPrice'])
                makerFee = float(contract_data['makerFee'])
                takerFee = float(contract_data['takerFee'])
                if order_type == 'Limit':
                    entry = input_price(client, 'Enter Entry Price', valid_ticks)
                else:
                    if stop > target:
                        entry = bidPrice
                    else:
                        entry = askPrice
                while True:
                    try:
                        risk = float(input('Account Percent Risk'+'\n'+'> '))
                    except TypeError:
                        print('Must be a number'+'\n')
                        continue
                    if risk == 0:
                        risk = (stop - entry) / entry
                        break
                    else:
                        if risk not in percent_ticks:
                            print('Invalid Entry'+'\n')
                            continue
                    break
                balance = client.User.User_getWalletHistory().result()[0][0]['walletBalance']/100000000
                position_size_1 = bitmex_position_size(entry, stop, balance, risk, target, takerFee, makerFee, order_type)
                size = int(position_size_1[0])
                entry_value = float(position_size_1[1])
                stop_value = float(position_size_1[2])
                target_value = float(position_size_1[3])
                risk_amount = risk_amount_XBT(entry_value, stop_value, size)*-1
                reward_amount = reward_amount_XBT(entry_value, target_value, size)*-1
                r_r = r_calc(reward_amount, risk_amount)
                r_r = format(r_r, '.2f')
                new_trade = {}
                new_trade['Contract'] = contract
                if target < entry:
                    new_trade['Direction'] = 'Short'
                else:
                    new_trade['Direction'] = 'Long'
                new_trade['Risk Percentage'] = str(risk)+'%'
                new_trade['Size'] = size
                new_trade['Entry'] = usd_str(entry)
                new_trade['Stop'] = usd_str(stop)
                new_trade['Target'] = usd_str(target)
                new_trade['BTC Risk'] = btc_str(risk_amount)
                new_trade['BTC Reward'] = btc_str(reward_amount)
                new_trade['R:R'] = r_r
                new_trade['Starting Balance'] = str(btc_str(balance)+', '+usd_str(balance*entry))
                new_trade['Win Balance'] = str(btc_str(balance+reward_amount)+', '+usd_str((balance+reward_amount)*target))
                new_trade['Loss Balance'] = str(btc_str(balance-risk_amount)+', '+usd_str((balance-reward_amount)*stop))
                print_dict(new_trade)
                print('Execute Trade?'+'\n'+'WARNING: ALL EXISTING OPEN POSITIONS AND ORDERS FOR THIS CONTRACT WILL BE CLOSED')
                resp = y_n_prompt()
                if resp == 'No':
                    print('TRADE NOT EXECUTED'+'\n')
                    continue
                else:
                    if len(client.Position.Position_get(filter = json.dumps({'symbol': str(contract)})).result()[0]) != 0:
                        if client.Position.Position_get(filter = json.dumps({'symbol': str(contract)})).result()[0][0]['currentQty'] < 0:
                            client.Order.Order_new(symbol=contract, execInst='Close', side='Buy').result()
                        else:
                            client.Order.Order_new(symbol=contract, execInst='Close', side='Sell').result()
                        bitmex_new_trade(client, contract, size, entry, target, stop, order_type)
                    else:
                        bitmex_new_trade(client, contract, size, entry, target, stop, order_type)
                    print('TRADE EXECUTED')
                    continue

    elif exchange == 'Bybit':
        contract = 'BTCUSD'
        while True:
            step1_options = ['View/Manage Open Positions', 'Plan New Trade', 'Change Exchange']
            step1 = list_user_prompt('Choose Starting Option', step1_options)
            if step1 == 'Change Exchange':
                break
            elif step1 == 'View/Manage Open Positions':
                bybit_position = bybit_open_positions(client, contract)
                print('\n'+'Your Bybit Open Position'+'\n')
                print_dict(bybit_position)
                step2_options = ['Close Position', 'Amend Orders', 'Take Profit', 'Return to Start']
                step2 = list_user_prompt('Choose an Option', step2_options)
                if step2 != 'Return to Start':
                    contract_to_view = list_user_prompt('Choose a Position to Manage', [contract, 'Return to Start'])
                    if contract_to_view == 'Return to Start':
                        print('\n')
                        continue
                    if step2 == 'Close Position':
                        print('\n')
                        bybit_close_position(client, contract_to_view)
                        client.Conditional.Conditional_cancelAll(symbol=contract).result()
                        client.Order.Order_cancelAll(symbol=contract).result()
                        continue
                    elif step2 == 'Amend Orders':
                        print('\n')
                        print_dict(bybit_open_positions(client, contract_to_view))
                        new_stop = input_price(client, 'Enter New Stop Price or 0 to Skip', valid_ticks)
                        new_target = input_price(client, 'Enter New Target Price or 0 to Skip', valid_ticks)
                        bybit_amend_order(client, new_stop, new_target, contract_to_view);
                        print_dict(bybit_open_positions(client, contract_to_view))
                        continue
                    elif step2 == 'Take Profit':
                        print('\n')
                        while True:
                            print_dict(bybit_open_positions(client, contract_to_view))
                            try:
                                take_profit = float(input('Percent of '+contract_to_view+' position to close'+'\n'+'> '))
                            except TypeError:
                                print('Must be a number'+'\n')
                                continue
                            if take_profit == 0:
                                break
                            else:
                                if take_profit not in percent_ticks:
                                    print('Invalid Entry'+'\n')
                                    continue
                                break
                        if take_profit != 0:
                            new_stop = input_price(client, 'Enter New Stop Price or 0 to Skip', valid_ticks)
                            new_target = input_price(client, 'Enter New Target Price or 0 to Skip', valid_ticks)
                            bybit_take_profit_order(client, take_profit, new_stop, new_target, contract_to_view);
                            time.sleep(1)
                            print_dict(bybit_open_positions(client, contract_to_view))
                            continue

            elif step1 == 'Plan New Trade':
                order_type = list_user_prompt('Choose Order Type for Entry', order_types)
                stop = input_price(client, 'Enter Stop Price', valid_ticks)
                target = input_price(client, 'Enter Target Price', valid_ticks)
                contract_data = client.Market.Market_symbolInfo(symbol='BTCUSD').result()[0]['result'][0]
                bidPrice = float(contract_data['bid_price'])
                askPrice = float(contract_data['ask_price'])
                makerFee = [float(x['maker_fee']) for x in client.Symbol.Symbol_get().result()[0]['result'] if x['name'] == 'BTCUSD'][0]
                takerFee = [float(x['taker_fee']) for x in client.Symbol.Symbol_get().result()[0]['result'] if x['name'] == 'BTCUSD'][0]
                if order_type == 'Limit':
                    entry = input_price(client, 'Enter Entry Price', valid_ticks)
                else:
                    if stop > target:
                        entry = bidPrice
                    else:
                        entry = askPrice
                while True:
                    try:
                        risk = float(input('Account Percent Risk'+'\n'+'> '))
                    except TypeError:
                        print('Must be a number'+'\n')
                        continue
                    if risk == 0:
                        risk = (stop - entry) / entry
                        break
                    else:
                        if risk not in percent_ticks:
                            print('Invalid Entry'+'\n')
                            continue
                    break
                balance = client.Wallet.Wallet_getBalance(coin='BTC').result()[0]['result']['BTC']['available_balance']
                position_size_1 = bybit_position_size(entry, stop, balance, risk, target, takerFee, makerFee, order_type)
                size = int(position_size_1[0])
                entry_value = float(position_size_1[1])
                stop_value = float(position_size_1[2])
                target_value = float(position_size_1[3])
                risk_amount = risk_amount_XBT(entry_value, stop_value, size)*-1
                reward_amount = reward_amount_XBT(entry_value, target_value, size)*-1
                r_r = r_calc(reward_amount, risk_amount)
                r_r = format(r_r, '.2f')
                new_trade = {}
                new_trade['Contract'] = contract
                if target < entry:
                    new_trade['Direction'] = 'Short'
                else:
                    new_trade['Direction'] = 'Long'
                new_trade['Risk Percentage'] = str(risk)+'%'
                new_trade['Size'] = size
                new_trade['Entry'] = usd_str(entry)
                new_trade['Stop'] = usd_str(stop)
                new_trade['Target'] = usd_str(target)
                new_trade['BTC Risk'] = btc_str(risk_amount)
                new_trade['BTC Reward'] = btc_str(reward_amount)
                new_trade['R:R'] = r_r
                new_trade['Starting Balance'] = str(btc_str(balance)+', '+usd_str(balance*entry))
                new_trade['Win Balance'] = str(btc_str(balance+reward_amount)+', '+usd_str((balance+reward_amount)*target))
                new_trade['Loss Balance'] = str(btc_str(balance-risk_amount)+', '+usd_str((balance-risk_amount)*stop))
                print_dict(new_trade)
                print('Execute Trade?'+'\n'+'WARNING: ALL EXISTING OPEN POSITIONS AND ORDERS FOR THIS CONTRACT WILL BE CLOSED')
                resp = y_n_prompt()
                if resp == 'No':
                    print('TRADE NOT EXECUTED'+'\n')
                    continue
                else:
                    client.Conditional.Conditional_cancelAll(symbol=contract).result()
                    client.Order.Order_cancelAll(symbol=contract).result()
                    if len(bybit_open_positions(client, contract)) != 0:
                        bybit_close_position(client, contract)
                    bybit_new_trade(client, contract, size, entry, target, stop, order_type)
                    print('TRADE EXECUTED')
                    continue


# In[ ]:




