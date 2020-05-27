#!/usr/bin/env python
# coding: utf-8

from datetime import datetime, timedelta, timezone
from bitmex import bitmex
from bybit import bybit
from qtrade_client.api import QtradeAPI
import requests
import ast
import os
import json
import warnings
warnings.simplefilter("ignore")
import bravado.exception
rate_limit = bravado.exception.HTTPTooManyRequests
import time
import sys
import pytz
from json import JSONEncoder


def generate_credentials(exchange, bot):
    while True:
        try:
            master_credentials = json_read('credentials')
        except FileNotFoundError:
            print('Creating Credentials File'+'\n')
            credentials = exchange_credentials(exchange)
            json_write('credentials', credentials)
            credentials = json_read('credentials')[exchange]
            break
        else:
            try:
                credentials = master_credentials[exchange]
            except KeyError:
                print('Creating '+exchange+' Credentials'+'\n')
                master_credentials.update(exchange_credentials(exchange))
                json_write('credentials', master_credentials)
                credentials = master_credentials[exchange]
                break
            else:
                print(exchange+' Credentials Detected'+'\n'+'Change Current Credentials?'+'\n')
                resp = y_n_prompt()
                if resp == 'No':
                    break
                else:
                    credentials = exchange_credentials(exchange)
                    master_credentials[exchange]['api_key'] = credentials[exchange]['api_key']
                    if exchange != 'qTrade':
                        master_credentials[exchange]['api_secret'] = credentials[exchange]['api_secret']
                    json_write('credentials', master_credentials)
                    credentials = json_read('credentials')[exchange]
                    break
    if bot:
        print('\n')
        while True:
            try:
                bot_credentials = (credentials['bot_token'], credentials['bot_chatID'])
            except KeyError:
                print('Creating New '+exchange+' Telegram Bot Credentials'+'\n')
                credentials = create_tg_bot(credentials)
                master_credentials = json_read('credentials')
                master_credentials[exchange].update(credentials)
                json_write('credentials', master_credentials)
                credentials = json_read('credentials')[exchange]
                break
            else:
                print('Bot Credentials Detected'+'\n'+'Change Current Bot?'+'\n')
                resp = y_n_prompt()
                if resp == 'No':
                    break
                else:
                    credentials = create_tg_bot(credentials)
                    master_credentials = json_read('credentials')
                    master_credentials[exchange].update(credentials)
                    json_write('credentials', master_credentials)
                    credentials = json_read('credentials')[exchange]
                    break
    
    return credentials


def create_tg_bot(credentials):
    while True:
        credentials.update({'bot_token': str(input('Input Your Telegram Bot API Key'+'\n'+'> ')),
                            'bot_chatID': str(input('Input Your Telegram User ChatID'+'\n'+'> ')),})
        test_msg = telegram_sendText((credentials['bot_token'], credentials['bot_chatID']), 'Testing')['ok']
        if test_msg:
            print('\n'+'Confirm Test Message Receipt')
            resp = y_n_prompt()
            if resp == 'No':
                print('Try Again'+'\n')
                continue
            else:
                print('Bot Credentials Verified'+'\n')
                break
        else:
            print('Test Message Failed. Reenter Bot Credentials'+'\n')
            continue
    return credentials


def exchange_credentials(exchange):
    if exchange == 'qTrade':
        while True:
            credentials = {exchange: {'api_key': str(input('Input Your qTrade API Key'+'\n'+'> '))}}
            client = QtradeAPI('https://api.qtrade.io', key=credentials[exchange]['api_key'])
            try:
                client.get("/v1/user/me")
            except:
                print('Invalid Credentials'+'\n')
                continue
            else:
                print('qTrade Credentials Verified'+'\n')
                break
    elif exchange == 'Bybit':
        while True:
            credentials = {exchange: {'api_key': str(input('Input Your Bybit API Key'+'\n'+'> ')),
                                      'api_secret': str(input('Input Your Bybit API Secret'+'\n'+'> '))}}
            client = bybit(test=False,api_key=credentials[exchange]['api_key'],
                           api_secret=credentials[exchange]['api_secret'])
            resp = client.APIkey.APIkey_info().result()[0]['ret_msg'];
            if resp == 'invalid api_key':
                print('Invalid Credentials'+'\n')
                continue
            else:
                print('Bybit Credentials Verified'+'\n')
                break
    elif exchange == 'Bitmex':
        while True:
            credentials = {exchange: {'api_key': str(input('Input Your Bitmex API Key'+'\n'+'> ')),
                                      'api_secret': str(input('Input Your Bitmex API Secret'+'\n'+'> '))}}
            client = bitmex(test=False,api_key=credentials[exchange]['api_key'],
                            api_secret=credentials[exchange]['api_secret']);
            try:
                print('\n'+'Testing Bitmex Credentials'+'\n')
                client.User.User_getWalletHistory().result();
            except bravado.exception.HTTPError:
                print('Invalid Credentials'+'\n')
                continue
            else:
                print('Bitmex Credentials Verified'+'\n')
                break
    return credentials


def usd_str(value):
    if '.' in str(value):
        if float(value) < 0:
            value = float(value)*-1
            value = '-'+"${0:,.2f}".format(float(value))
        else:
            value = "${0:,.2f}".format(float(value))
    else:
        if float(value) < 0:
            value = float(value)*-1
            value = '-'+"${0:,}".format(float(value))
        else:
            value = "${0:,}".format(float(value))
    return value

def btc_str(value):
    value = "{0:,.8f}".format(float(value))
    return value

def pct_str(value):
    value = "{0:,.2f}%".format(float(value))
    return value

def btc_round(value):
    rounded_value = round(float(value), 8)
    return float(rounded_value)


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


#User promp based list element selection by index
def list_prompt(initial_dialogue, list_to_view):
    while True:
        try:
            print(initial_dialogue)
            for k, v in enumerate(list_to_view):
                print(str(k)+': '+v)
            resp = list_to_view[int(input('> '))]
        except (IndexError, ValueError):
            print('Selection out of range of acceptable responses'+'\n')
            continue
        else:
            print('Selection: '+str(resp)+'\n')
            break
    return resp


#Telegram Text Alert
def telegram_sendText(bot_credentials, bot_message):
    bot_token = bot_credentials[0]
    bot_chatID = bot_credentials[1]
    send_text = 'https://api.telegram.org/bot'+bot_token+'/sendMessage?chat_id='+bot_chatID+'&text='+bot_message
    response = requests.get(send_text)
    return response.json()


def dict_to_msg(dict_item):
    dict_msg = ''
    try:
        for x in range(len(dict_item)):
            for k, v in dict_item[x].items():
                dict_msg += k+': '+str(v)+'\n'
            dict_msg += '\n'
    except KeyError:
        for k, v in dict_item.items():
            dict_msg += k+': '+str(v)+'\n'
        dict_msg += '\n'
    return dict_msg


def sleep_time(sleeper):
    timeframe = sleeper[0]
    count = sleeper[1]
    now = datetime.utcnow()
    if timeframe == 'Seconds':
        delta = timedelta(seconds=count)
        start_loop = (now + delta).replace(microsecond=0)
    elif timeframe == 'Minutes':
        delta = timedelta(minutes=count)
        start_loop = (now + delta).replace(microsecond=0, second=0)
    elif timeframe == 'Hours':
        delta = timedelta(hours=count)
        start_loop = (now + delta).replace(microsecond=0, second=0, minute=0)
    sleep_time = (start_loop - now).total_seconds()
    return sleep_time


def load_credentials(exchange, bot):
    credentials = json_read('credentials')[exchange]
    if exchange == 'Bitmex':
        client = bitmex(test=False,api_key=credentials['api_key'],api_secret=credentials['api_secret']) 
    elif exchange == 'Bybit':
        client = bybit(test=False,api_key=credentials['api_key'],api_secret=credentials['api_secret'])
    elif exchange == 'qTrade':
        client = QtradeAPI('https://client.qtrade.io', key=credentials['api_key'])
    if bot == True:
        bot = (credentials['bot_token'], credentials['bot_chatID'])
    return client, bot


def list_to_dict(list_item):
    temp = {}
    for x,y in enumerate(list_item):
        temp[(x+1)] = y
    return temp


def comparative_prompt(initial_dialogue, comp_list, resp_format):
    while True:
        try:
            print(initial_dialogue)
            resp = resp_format.__class__(input('> '))
        except ValueError:
            print('Selection must be '+resp_format.__class__.__name__+'\n')
            continue
        else:
            if resp not in comp_list:
                print('Selection Invalid'+'\n'+'Available Responses: '+str(comp_list)+'\n')
                continue
            else:
                print('Selection: {}'.format(resp))
                break
    return resp_format.__class__(resp)


def sleep_selection():
    keys = ['Hours', 'Minutes', 'Seconds']
    values = [list(range(1,24)), list(range(3,60)), list(range(1,60))]
    timeframe_dict = dict(zip(keys, values))
    timeframe = list_prompt('Choose Sleep Timeframe', keys)
    count = comparative_prompt('Number of {} to Sleep'.format(timeframe), timeframe_dict[timeframe], 1)
    return timeframe, count


def DecodeDateTime(empDict):
    if '+00:00' in empDict['LastFilled']:
        empDict['LastFilled'] = datetime.strptime(empDict['LastFilled'][:-6], '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=pytz.timezone('UTC'))
    else:
        empDict['LastFilled'] = datetime.strptime(empDict['LastFilled'], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=pytz.timezone('UTC'))
    return empDict


def json_write(file, item):
    with open(file, mode="w") as outfile:
        json.dump(item, outfile)
    return None


class DateTimeEncoder(JSONEncoder):
    #Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime, datetime)):
            return obj.isoformat()


def json_read(file):
    with open(file, 'r') as fp:
        data = json.load(fp)
    return data


"""
Initial startup query string
Generate/read/save credentials
Set sleep timer for script loop
"""
exchange = 'Bitmex'
print('Integrate '+exchange+' Telegram Bot?')
use_bot = y_n_prompt()
if use_bot == 'Yes':
    bot = True
else:
    bot = False
print('\n')
credentials_check = generate_credentials(exchange, bot);
sleeper = sleep_selection()


while True:
    credentials = load_credentials(exchange, bot);
    client = credentials[0]
    bot_credentials = credentials[1]
    balance = client.User.User_getWalletHistory().result()[0][0]['walletBalance']/100000000
    contract_data = {}
    contracts = [x['symbol'] for x in client.Instrument.Instrument_getActive().result()[0]]
    for x in contracts:
        contract_data[x] = {'Contract': x}
        try:
            contract_data[x].update({'LastFilled':  datetime.strftime((client.Execution.Execution_get(symbol=x, count=1, reverse=True, filter = json.dumps({'ordStatus': 'Filled', 'execType': 'Trade'})).result()[0][0]['timestamp']), '%Y-%m-%d %H:%M:%S.%f')})
        except rate_limit:
            time.sleep(5)
            continue
        except IndexError:
            contract_data[x].update({'LastFilled': None})
    contract_data = {k:v for k,v in contract_data.items() if v['LastFilled'] is not None}

    if os.path.exists('bitmex_contract_data'):
        master_data = eval(json_read('bitmex_contract_data'))
        for x in list(master_data.keys()):
            master_data[x] = DecodeDateTime(master_data[x])
        for x in list(contract_data.keys()):
            contract_data[x] = DecodeDateTime(contract_data[x])
        temp_list1 = list(master_data.values())
        temp_list2 = list(contract_data.items())
        contract_data = {x:y for x,y in temp_list2 if y not in temp_list1}

    else:
        for x in list(contract_data.keys()):
            contract_data[x] = DecodeDateTime(contract_data[x])
        master_data = contract_data

    for symbol in list(contract_data.keys()):

        last_recorded = contract_data[symbol]['LastFilled']-timedelta(minutes=1)
        startTime = last_recorded
        last_filled = contract_data[symbol]['LastFilled']

        trade_history = []
        loops = 0
        while last_filled > startTime:
            try:
                temp_data = client.Execution.Execution_get(symbol=symbol, startTime=startTime, count=500, reverse=True, filter = json.dumps({'ordStatus': 'Filled', 'execType': 'Trade'})).result()[0]
                trade_history += temp_data
                startTime = trade_history[0]['timestamp']
            except rate_limit:
                time.sleep(5)
                continue
        trade_history = [x for x in trade_history if x['timestamp'] > last_recorded]

        old_keys = ['side', 'lastQty', 'price', 'ordType', 'execComm', 'timestamp']
        new_keys = ['Side', 'Size', 'Price', 'OrderType', 'Fees', 'Timestamp']
        if 'USD' in symbol or 'XBT' in symbol:
            old_keys.append('homeNotional')
            new_keys.append(symbol[:3]+'value')
        else:
            old_keys.append('foreignNotional')
            new_keys.append('BTCvalue')

        for l in range(len(trade_history)):
            trade_history[l] = {x:y for x,y in trade_history[l].items() if x in old_keys}
            trade_history[l]['execComm'] = btc_str(trade_history[l]['execComm']/100000000)
            trade_history[l]['timestamp'] = datetime.strftime(trade_history[l]['timestamp'], '%m-%d-%Y %H:%M:%S')
            if 'USD' in symbol or 'XBT' in symbol: 
                trade_history[l]['price'] = usd_str(trade_history[l]['price'])
            else:
                trade_history[l]['price'] = btc_str(trade_history[l]['price'])
            if 'USD' in symbol or 'XBT' in symbol:
                trade_history[l]['homeNotional'] = btc_str(trade_history[l]['homeNotional'])
            else:
                trade_history[l]['foreignNotional'] = btc_str(trade_history[l]['foreignNotional'])
        for l in range(len(trade_history)):
            for x in range(len(old_keys)):
                trade_history[l][new_keys[x]] = trade_history[l].pop(old_keys[x])
                
        if bot:
            msg = 'Last Executed '+symbol+' Orders'+'\n'+'\n'
            msg += dict_to_msg(trade_history);
        while True:
            try:
                resp = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': symbol})).result()[0][0]
            except rate_limit:
                time.sleep(5)
                continue
            except IndexError:
                if bot:
                    msg += ('All '+symbol+' Positions Closed')
                    if len(msg) <= 4096:
                        telegram_sendText(bot_credentials, msg);
                    else:
                        telegram_sendText(bot_credentials, 'Msg Too Long')
                break
            else:
                if len(msg) <= 4096:
                    telegram_sendText(bot_credentials, msg);
                else:
                    telegram_sendText(bot_credentials, 'Msg Too Long')
                temp = {'Exchange': exchange,
                        'Balance': balance,
                       'Timestamp': datetime.strftime(datetime.utcnow(), '%m-%d-%Y %H:%M:%S'),
                        'Symbol': symbol
                       }
                if resp['currentQty'] < 0:
                    temp['Side'] = 'Short'
                elif resp['currentQty'] > 0:
                    temp['Side'] = 'Long'
                temp['Size'] = resp['currentQty']
                if 'USD' in symbol:
                    temp['Entry'] = usd_str(resp['avgEntryPrice'])
                    temp['MarketPrice'] = usd_str(resp['markPrice'])
                else:
                    temp['Entry'] = btc_str(resp['avgEntryPrice'])
                    temp['MarketPrice'] = btc_str(resp['markPrice'])
                temp['UnrealisedPnL'] = btc_str(resp['unrealisedPnl']/100000000)
                                
                msg = 'Current '+symbol+' Position'+'\n'+'\n'
                msg += dict_to_msg(temp)
                if len(msg) <= 4096:
                    telegram_sendText(bot_credentials, msg);
                else:
                    telegram_sendText(bot_credentials, 'Msg Too Long')
                break
    for symbol in (contract_data.keys()):
        master_data[symbol] = contract_data[symbol]
    json_write('bitmex_contract_data', json.dumps(master_data, cls=DateTimeEncoder))
    time.sleep(sleep_time(sleeper))        

