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
        try:
            client = QtradeAPI('https://api.qtrade.io', key=credentials['api_key'])
            client.get("/v1/user/me")
        except:
            print('Invalid Credentials'+'\n')
            continue
        break
        save_credentials = save_file(str(sys.path[0])+'/credentials/'+credentials_file, credentials)
    return print('\n'+exchange+' Credentials Verified')


def load_credentials(exchange, my_token, myID):
    credentials_file = [x for x in find_file('credentials') if exchange in x][0]
    credentials = load_file(str(sys.path[0])+'/credentials/'+credentials_file)
    client = QtradeAPI('https://api.qtrade.io', key=credentials['api_key'])
    if credentials['bot_token'] == 'YYY':
        my_token = None
    else:
        my_token = credentials['bot_token']
    if credentials['bot_chatID'] == 'ZZZ':
        myID = None
    else:
        myID = credentials['bot_chatID']
    return client, (my_token, myID)


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


def sleep_time(count):
    time_to_sleep = count - datetime.utcnow().minute % count
    sleep_time = time_to_sleep*60
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

