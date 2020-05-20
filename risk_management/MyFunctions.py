#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from datetime import datetime, timedelta, timezone
from sympy import symbols, Eq, solve
from bybit import bybit
from bitmex import bitmex
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
import logging
import decimal
import sys


# In[ ]:


def btc_float_round(value):
    rounded_value = round(value, 8)
    return rounded_value


# In[ ]:


def btc_str2float_round(value):
    rounded_value = round(float(value), 8)
    return rounded_value


# In[ ]:


#Legible format for BTC values
def btc_str(value):
    value = "{:,.8f}".format(value)
    return value


# In[ ]:


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


# In[ ]:


def tz_to_timestamp(str_date):
    new_time = datetime.timestamp(datetime.strptime(str_date, '%Y-%m-%dT%H:%M:%S.%fZ'))
    return new_time


# In[ ]:


def tz_to_str(tz_date, str_format):
    str_time = datetime.strftime(datetime.strptime(tz_date, '%Y-%m-%dT%H:%M:%S.%fZ'), str_format)
    return str_time


# In[ ]:


def find_file(file_type):
    f = []
    if file_type == 'credentials':
        file_path = str(sys.path[0])+'/credentials'
    else:
        file_path = str(sys.path[0])+'/configurations'
    for (dirpath, dirnames, filenames) in walk(file_path):
        f.extend(filenames)
        return f


# In[ ]:


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
        if credentials['api_secret'] == 'TTT':
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
        break
        save_credentials = save_file(str(sys.path[0])+'/credentials/'+credentials_file, credentials)
        credentials_file = [x for x in find_file('credentials') if exchange in x][0]
        credentials = load_file(str(sys.path[0])+'/credentials/'+credentials_file)
    return print('\n'+exchange+' Credentials Verified'), client, (credentials['bot_token'], credentials['bot_chatID'])


# In[ ]:


#Telegram Text Alert
def telegram_sendText(bot_credentials, bot_message):
    bot_token = bot_credentials[0]
    bot_chatID = bot_credentials[1]
    send_text = 'https://api.telegram.org/bot'+bot_token+'/sendMessage?chat_id='+bot_chatID+'&parse_mode=Markdown&text='+bot_message
    response = requests.get(send_text)
    return response.json()


# In[ ]:


#Telegram Image Alert
def telegram_sendImage(bot_credentials, image):
    bot_token = bot_credentials[0]
    bot_chatID = bot_credentials[1]
    url = 'https://api.telegram.org/bot'+bot_token+'/sendPhoto';
    files = {'photo': open(image, 'rb')}
    data = {'chat_id' : bot_chatID}
    r = requests.post(url, files=files, data=data)
    return r


# In[ ]:


def telegram_sendFile(bot_credentials, file):
    bot_token = bot_credentials[0]
    bot_chatID = bot_credentials[1]
    url = 'https://api.telegram.org/bot'+bot_token+'/sendDocument';
    files = {'document': open(file, 'rb')}
    data = {'chat_id' : bot_chatID}
    r = requests.post(url, files=files, data=data)
    return r


# In[ ]:


def float_range(start, stop, step):
    while start < stop:
        yield float(start)
        start += decimal.Decimal(step)


# In[ ]:


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


# In[ ]:


#Read .txt files
def load_file(file):
    temp_list = []
    f = open(file, "r")
    for x in f:
        temp_list.append(x.rstrip('\n'))
    load = [ast.literal_eval(i) for i in temp_list][0]
    f.close()
    return load


# In[ ]:


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


# In[ ]:


#Write to .txt file
def save_file(file, item):
    with open(file, mode="w") as outfile:
        outfile.write(str(item))
    return None


# In[ ]:


#Sort tuples by value by index
def sortTuple(tup, index):
    return(sorted(tup, key = lambda x: x[index], reverse=True))


# In[ ]:


#Remove duplicate values from sorted lists
def sorted_list(list_to_sort):
    return list(dict.fromkeys(list_to_sort))


# In[ ]:


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


# In[ ]:


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


# In[ ]:


def create_directory(directory):
    if os.path.exists(str(sys.path[0])+'/'+directory+'/') == False:
        directory = directory
        path = os.path.join(str(sys.path[0]), directory)
        os.mkdir(path)
    return None


# In[ ]:


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


# In[ ]:


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

