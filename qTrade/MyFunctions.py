#!/usr/bin/env python
# coding: utf-8

from datetime import datetime, timedelta, timezone
from sympy import symbols, Eq, solve
from operator import itemgetter
import pandas as pd
import requests
import ast
import os
from os import walk
import json
from qtrade_client.api import QtradeAPI
from numpy import cumsum
import io
import time
import decimal
import sys
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.pyplot import figure
import matplotlib
from matplotlib import gridspec
import matplotlib.ticker as mtick
from mplfinance.original_flavor import candlestick_ohlc
import warnings
warnings.filterwarnings("ignore")
import matplotlib.dates as mdates
import random


def btc_float_round(value):
    rounded_value = round(value, 8)
    return rounded_value


def btc_str2float_round(value):
    rounded_value = round(float(value), 8)
    return rounded_value


def coin_str(value, precision):
    value = str(round(float(value), precision))
    return value


def btc_str(value):
    value = "{:,.8f}".format(value)
    return value


def usd_str(value):
    if '.' in str(value):
        if float(value) < 0:
            value = float(value)*-1
            value = '-'+"${:,.2f}".format(float(value))
        else:
            value = "${:,.2f}".format(float(value))
    else:
        if float(value) < 0:
            value = float(value)*-1
            value = '-'+"${:,}".format(float(value))
        else:
            value = "${:,}".format(float(value))
    return value


def tz_to_timestamp(str_date):
    new_time = datetime.timestamp(datetime.strptime(str_date, '%Y-%m-%dT%H:%M:%S.%fZ'))
    return new_time


def tz_to_str(tz_date, str_format):
    str_time = datetime.strftime(datetime.strptime(tz_date, '%Y-%m-%dT%H:%M:%S.%fZ'), str_format)
    return str_time


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
                    client = QtradeAPI('https://api.qtrade.io', key=credentials['api_key'])
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
                    client = QtradeAPI('https://api.qtrade.io', key=credentials['api_key'])
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


def load_credentials(exchange, bot):
    credentials = load_file(exchange+'_credentials')
    client = QtradeAPI('https://api.qtrade.io', key=credentials['api_key'])
    if bot == True:
        bot = (credentials['bot_token'], credentials['bot_chatID'])
    return client, bot


#Telegram Text Alert
def telegram_sendText(bot_credentials, bot_message):
    bot_token = bot_credentials[0]
    bot_chatID = bot_credentials[1]
    send_text = 'https://api.telegram.org/bot'+bot_token+'/sendMessage?chat_id='+bot_chatID+'&text='+bot_message
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
def list_prompt(initial_dialogue, list_to_view):
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


def sleep_time(step):
    sleep_time = ((datetime.utcnow()+timedelta(minutes=step)).replace(second=0, microsecond=0)-datetime.utcnow()).total_seconds()
    return sleep_time


def dict_to_msg(dict_item):
    dict_msg = ''
    try:
        for x in range(len(dict_item)):
            for k, v in dict_item[x].items():
                dict_msg += k.upper()+': '+str(v)+'\n'
            dict_msg += '\n'
    except KeyError:
        for k, v in dict_item.items():
            dict_msg += k.upper()+': '+str(v)+'\n'
        dict_msg += '\n'
    return dict_msg

