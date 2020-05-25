#!/usr/bin/env python
# coding: utf-8

from datetime import datetime, timedelta, timezone
from bitmex import bitmex
import requests
import ast
import os
import json
import warnings
warnings.simplefilter("ignore")
import bravado.exception
import time
import sys
from string import Template
import pytz


def verify_credentials(exchange, bot):
    try:
        credentials = load_file(exchange+'_credentials')
    except FileNotFoundError:
        print('Creating '+exchange+' Credentials File'+'\n')
        while True:
                credentials = {'exchange': exchange,
                               'api_key': str(input('Input Your '+exchange+' API Key'+'\n'+'> '))}
                if exchange != 'qTrade':
                    credentials.update({'api_secret': str(input('Input Your '+exchange+' API Secret'+'\n'+'> '))})
                if exchange == 'Bitmex':
                        client = bitmex(test=False,api_key=credentials['api_key'],
                                        api_secret=credentials['api_secret']);
                        try:
                            print('\n'+'Testing Bitmex Credentials'+'\n')
                            client.User.User_getWalletHistory().result();
                        except bravado.exception.HTTPError:
                            print('Invalid Credentials'+'\n')
                            continue
                        else:
                            print('Bitmex Credentials Verified'+'\n')
                            break
                elif exchange == 'Bybit':
                    client = bybit(test=False,api_key=credentials['api_key'],
                                   api_secret=credentials['api_secret']);
                    resp = client.APIkey.APIkey_info().result()[0]['ret_msg'];
                    if resp == 'invalid api_key':
                        print('Invalid Credentials'+'\n')
                        continue
                    else:
                        print('Bybit Credentials Verified'+'\n')
                        break
                elif exchange == 'qTrade':
                    client = QtradeAPI('https://client.qtrade.io', key=credentials['api_key'])
                    try:
                        client.get("/v1/user/me")
                    except:
                        print('Invalid Credentials'+'\n')
                        continue
                    else:
                        print('qTrade Credentials Verified'+'\n')
                        break
        save_file(exchange+'_credentials', credentials)

    else:
        print('Change Existing '+exchange+' Credentials?')
        resp = y_n_prompt()
        if resp == 'No':
            while True:
                credentials = load_file(exchange+'_credentials')
                if exchange == 'Bitmex':
                    client = bitmex(test=False,api_key=credentials['api_key'],
                                    api_secret=credentials['api_secret']);
                    try:
                        print('\n'+'Testing Bitmex Credentials'+'\n')
                        client.User.User_getWalletHistory().result();
                    except bravado.exception.HTTPError:
                        print('Invalid Credentials'+'\n')
                        credentials = {'exchange': exchange,
                                       'api_key': str(input('Input Your '+exchange+' API Key'+'\n'+'> ')),
                                       'api_secret': str(input('Input Your '+exchange+' API Secret'+'\n'+'> ')),}
                        save_file(exchange+'_credentials', credentials)
                        continue
                    else:
                        print('Bitmex Credentials Verified'+'\n')
                        break
                elif exchange == 'Bybit':
                    client = bybit(test=False,api_key=credentials['api_key'],
                                   api_secret=credentials['api_secret']);
                    resp = client.APIkey.APIkey_info().result()[0]['ret_msg'];
                    if resp == 'invalid api_key':
                        print('Invalid Credentials'+'\n')
                        credentials = {'exchange': exchange,
                                       'api_key': str(input('Input Your '+exchange+' API Key'+'\n'+'> ')),
                                       'api_secret': str(input('Input Your '+exchange+' API Secret'+'\n'+'> ')),}
                        save_file(exchange+'_credentials', credentials)
                        continue
                    else:
                        print('Bybit Credentials Verified'+'\n')
                        break
                elif exchange == 'qTrade':
                    client = QtradeAPI('https://client.qtrade.io', key=credentials['api_key'])
                    try:
                        client.get("/v1/user/me")
                    except:
                        print('Invalid Credentials'+'\n')
                        credentials = {'exchange': exchange,
                                       'api_key': str(input('Input Your '+exchange+' API Key'+'\n'+'> '))}
                        save_file(exchange+'_credentials', credentials)
                        continue
                    else:
                        print('qTrade Credentials Verified'+'\n')
                        break
    while bot:
        credentials = load_file(exchange+'_credentials')
        try:
            credentials['bot_token'] == True
        except KeyError:
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
                    save_file(exchange+'_credentials', credentials)
                    bot = (credentials['bot_token'], credentials['bot_chatID'])
            else:
                print('Test Message Failed. Reenter Bot Credentials'+'\n')
                continue
        else:
            print('Change Existing Bot Credentials?')
            resp = y_n_prompt()
            if resp == 'Yes':
                credentials['bot_token'] = str(input('Input Your Telegram Bot API Key'+'\n'+'> '))
                credentials['bot_chatID'] = str(input('Input Your Telegram User ChatID'+'\n'+'> '))
                test_msg = telegram_sendText((credentials['bot_token'], credentials['bot_chatID']), 'Testing')['ok']
                if test_msg:
                    print('\n'+'Confirm Test Message Receipt')
                    resp = y_n_prompt()
                    if resp == 'No':
                        print('Try Again'+'\n')
                        continue
                    else:
                        print('Bot Credentials Verified'+'\n')
                        save_file(exchange+'_credentials', credentials)
                        bot = (credentials['bot_token'], credentials['bot_chatID'])
                else:
                    print('Test Message Failed. Reenter Bot Credentials'+'\n')
                    continue
            else:
                bot = (credentials['bot_token'], credentials['bot_chatID'])
        break
            
    return client, bot


class DeltaTemplate(Template):
    delimiter = "%"
def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    d["H"], rem = divmod(tdelta.seconds, 3600)
    d["M"], d["S"] = divmod(rem, 60)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


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


#Read .txt files
def load_file(file):
    temp_list = []
    f = open(file, "r")
    for x in f:
        temp_list.append(x.rstrip('\n'))
    load = [ast.literal_eval(i) for i in temp_list][0]
    f.close()
    return load


#Write to .txt file
def save_file(file, item):
    with open(file, mode="w") as outfile:
        outfile.write(str(item))
    return None


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


def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month + 1


def load_credentials(exchange, bot):
    credentials = load_file(exchange+'_credentials')
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


def get_key(val, my_dict): 
    for k, v in my_dict.items(): 
         if val == v: 
            return k 


def load_last_trade(file):
    temp = load_file(file)
    temp = datetime(temp[0], temp[1], temp[2], temp[3], temp[4], temp[5], temp[6])
    return temp


def save_last_trade(file, time):
    temp = save_file(file,'({dt.year},{dt.month},{dt.day},{dt.hour},{dt.minute},{dt.second},{dt.microsecond})'.format(dt = time))
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


exchange = 'Bitmex'
print('Integrate '+exchange+' Telegram Bot?')
use_bot = y_n_prompt()
if use_bot == 'Yes':
    bot = True
else:
    bot = False
print('\n')
check = verify_credentials(exchange, bot)
sleeper = sleep_selection()
while True:
    credentials = load_credentials(exchange, bot)
    client = credentials[0]
    bot_credentials = credentials[1]
    contracts = [x['symbol'] for x in client.Instrument.Instrument_getActive().result()[0] if 'XBT' in x['symbol']]
    balance = btc_str(client.User.User_getWalletHistory().result()[0][0]['walletBalance']/100000000)
    open_symbols = []
    for l in contracts:
        try:
            resp = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': l})).result()[0][0]
        except IndexError:
            break
        else:
            open_symbols.append(resp['symbol'])
            continue
    for symbol in open_symbols:
        last_trade_filled = client.Execution.Execution_get(symbol=symbol, count=1, reverse=True, filter = json.dumps({'ordStatus': 'Filled', 'execType': 'Trade'})).result()[0][0]['timestamp']
        resp = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': symbol})).result()[0][0]
        last_recorded = exchange+'_'+symbol+'_last_recorded'
        if os.path.exists(last_recorded):
            last_trade = load_last_trade(last_recorded)
        else:
            last_trade = last_trade_filled - timedelta(minutes=1)
        if datetime.timestamp(last_trade_filled) > datetime.timestamp(last_trade):
            ###Pull all execution history since last recorded trade
            trade_history = []
            startTime = last_trade
            while datetime.timestamp(last_trade_filled) > datetime.timestamp(startTime):
                temp_data = client.Execution.Execution_get(symbol=symbol, startTime=startTime, count=500, reverse=True, filter = json.dumps({'ordStatus': 'Filled', 'execType': 'Trade'})).result()[0]
                trade_history += temp_data
                startTime = trade_history[0]['timestamp']
                time.sleep(1)
                continue
            trade_history = [x for x in trade_history if datetime.timestamp(x['timestamp']) > datetime.timestamp(last_trade)]
            old_keys = ['side', 'lastQty', 'price', 'ordType', 'homeNotional', 'execComm', 'timestamp']
            new_keys = ['Side', 'Size', 'Price', 'OrderType', 'BTCvalue', 'Fees', 'Timestamp']
            for l in range(len(trade_history)):
                trade_history[l] = {x:y for x,y in trade_history[l].items() if x in old_keys}
                trade_history[l]['execComm'] = btc_str(trade_history[l]['execComm']/100000000)
                trade_history[l]['price'] = usd_str(trade_history[l]['price'])
                trade_history[l]['homeNotional'] = btc_str(trade_history[l]['homeNotional'])
            save_last_trade(last_recorded, trade_history[0]['timestamp'])
            for l in range(len(trade_history)):
                for x in range(len(old_keys)):
                    trade_history[l][new_keys[x]] = trade_history[l].pop(old_keys[x])
                trade_history[l]['Timestamp'] = datetime.strftime(trade_history[l]['Timestamp'], '%m-%d-%Y %H:%M:%S')
            ###Get Updated Position Data
            temp = {'Exchange': exchange,
                    'Balance': balance,
                   'Timestamp': datetime.strftime(datetime.utcnow(), '%m-%d-%Y %H:%M:%S')
                   }
            if resp['currentQty'] < 0:
                temp['Side'] = 'Sell'
            elif resp['currentQty'] > 0:
                temp['Side'] = 'Buy'
            if temp['Side'] == 'Short':
                temp['Size'] = resp['currentQty']*-1
            else:
                temp['Size'] = resp['currentQty']
            temp['Entry'] = usd_str(resp['avgEntryPrice'])
            temp['MarketPrice'] = usd_str(resp['markPrice'])
            temp['UnrealisedPnL'] = btc_str(resp['unrealisedPnl']/100000000)
            temp['LastFilled'] = datetime.strftime(last_trade_filled, '%m-%d-%Y %H:%M:%S')
            temp['TimeSinceLastTrade'] = strfdelta(datetime.utcnow().replace(tzinfo=pytz.timezone('UTC'))-last_trade_filled, '%H Hrs, %M Mins, %S Secs')
            if bot:
                msg = 'Last Executed '+symbol+' Orders'+'\n'+'\n'
                msg += dict_to_msg(trade_history);
                if len(msg) <= 4096:
                    telegram_sendText(bot_credentials, msg);
                else:
                    telegram_sendText(bot_credentials, 'Msg Too Long')
                msg = 'Current '+symbol+' Position'+'\n'+'\n'
                msg += dict_to_msg(temp)
                if len(msg) <= 4096:
                    telegram_sendText(bot_credentials, msg);
                else:
                    telegram_sendText(bot_credentials, 'Msg Too Long')
    time.sleep(sleep_time(sleeper))
    continue

