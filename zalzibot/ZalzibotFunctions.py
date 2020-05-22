#!/usr/bin/env python
# coding: utf-8

import requests
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import numpy as np
import time
from matplotlib.pyplot import figure
import matplotlib
from matplotlib import gridspec
import matplotlib.ticker as mtick
import os
from os import walk
import sys
import ast


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


def find_file(file_type):
    f = []
    if file_type == 'credentials':
        file_path = str(sys.path[0])+'/credentials'
    else:
        file_path = str(sys.path[0])+'/configurations'
    for (dirpath, dirnames, filenames) in walk(file_path):
        f.extend(filenames)
        return f


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


def create_directory(directory):
    if os.path.exists(str(sys.path[0])+'/'+directory+'/') == False:
        directory = directory
        path = os.path.join(str(sys.path[0]), directory)
        os.mkdir(path)
    return None


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


def tg_bot_credentials():
    while True:
        credentials_file = [x for x in find_file('credentials')][0]
        credentials = load_file(str(sys.path[0])+'/credentials/'+credentials_file)
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
        credentials_file = [x for x in find_file('credentials')][0]
        credentials = load_file(str(sys.path[0])+'/credentials/'+credentials_file)
        return (credentials['bot_token'], credentials['bot_chatID'])


def new_xbt_data(file, bitmex_contracts, date):
    xbt_data = [x for x in bitmex_contracts if x['symbol'] == 'XBTUSD'][0]
    xbt = {}
    xbt['time'] = date
    xbt['price'] = xbt_data['lastPrice']
    xbt['openInterest'] = xbt_data['openInterest']
    xbt['openValue'] = xbt_data['openValue']/100000000
    xbt['24hrVolume'] = xbt_data['foreignNotional24h']
    xbt['funding'] = '{:,.4f}%'.format(round(xbt_data['fundingRate']*100, 4))
    xbt['predictedfunding'] = round(xbt_data['indicativeFundingRate']*100, 4)
    with open(file, mode="w") as outfile:
        outfile.write(str(xbt))
    return xbt


def dict_formatting(dict_item):
    dict_item['price'] = usd_str(dict_item['price'])
    dict_item['openInterest'] = usd_str(dict_item['openInterest'])
    dict_item['openValue'] = btc_str(dict_item['openValue'])
    dict_item['24hrVolume'] = usd_str(dict_item['24hrVolume'])
    dict_item['predictedfunding'] = '{:,.4f}%'.format(dict_item['predictedfunding'])
    return dict_item


def open_value(contracts, filenames, date, chart_directory):
    open_value_list = [(x['symbol'], round(x['openValue']/100000000, 2)) for x in contracts if 'XBT' not in x['symbol'] and 'USD' not in x['symbol']]

    if len(open_value_list) > 7:
        short_open_value_list = []
        long_open_value_list = []
        for x in range(len(open_value_list)):
            if open_value_list[x][1] == open_value_list[0][1]:
                short_open_value_list.append((open_value_list[x][0], open_value_list[x][1]))
            else:
                long_open_value_list.append((open_value_list[x][0], open_value_list[x][1]))
        all_short_open_value = []
        for x in range(len(short_open_value_list)):
            all_short_open_value.append(short_open_value_list[x][1])
        total_short_open_value = sum(all_short_open_value)

        all_long_open_value = []
        for x in range(len(long_open_value_list)):
            all_long_open_value.append(long_open_value_list[x][1])
        total_long_open_value = sum(all_long_open_value)
        short_open_value_list = sortTuple(short_open_value_list, 1)
        long_open_value_list = sortTuple(long_open_value_list, 1)

        labels, ys = zip(*short_open_value_list)
        xs = np.arange(len(labels)) 
        width = 0.8
        y = list(ys)

        fig = plt.figure(figsize=(18,10))                                                               
        ax = fig.gca()  #get current axes
        ax.barh(xs, ys, width, align='center')
        ax.set_yticks(xs)
        ax.set_yticklabels(labels)
        ax.set_axisbelow(True)
        plt.grid(b=None, which='major', axis='both')
        plt.ylabel('Contract', fontdict={'fontsize': 32})
        plt.title(str(short_open_value_list[0][0])[3:]+' Open Value for '+date+'\n'+'Total Open Value = '+str(total_short_open_value)+' BTC', fontdict={'fontsize': 32})
        plt.xlabel('BTC Open Value', fontdict={'fontsize': 32})
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(14)
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(14)
        for i, v in enumerate(y):
            ax.text(v, i, '{:,.2f}'.format(v), color='black', fontweight='bold')
        plt.tight_layout(True)
        plt.savefig(chart_directory+'short_open_value.png',bbox_inches='tight',dpi=100)
        plt.clf();

        labels, ys = zip(*long_open_value_list)
        xs = np.arange(len(labels)) 
        width = 0.8
        y = list(ys)

        fig = plt.figure(figsize=(18,10))                                                               
        ax = fig.gca()  #get current axes
        ax.barh(xs, ys, width, align='center')
        ax.set_yticks(xs)
        ax.set_yticklabels(labels)
        ax.set_axisbelow(True)
        plt.grid(b=None, which='major', axis='both')
        plt.ylabel('Contract', fontdict={'fontsize': 32})
        plt.title(str(long_open_value_list[0][0])[3:]+' Open Value for '+date+'\n'+'Total Open Value = '+str(total_long_open_value)+' BTC', fontdict={'fontsize': 32})
        plt.xlabel('BTC Open Value', fontdict={'fontsize': 32})
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(14)
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(14)
        for i, v in enumerate(y):
            ax.text(v, i, '{:,.2f}'.format(v), color='black', fontweight='bold')
        plt.tight_layout(True)
        plt.savefig(chart_directory+'long_open_value.png',bbox_inches='tight',dpi=100)
        plt.clf();

        filenames.append(chart_directory+'short_open_value.png')
        filenames.append(chart_directory+'long_open_value.png')

    else:
        all_open_value_list = []
        for x in range(len(open_value_list)):
            all_open_value_list.append(open_value_list[x][1])
        total_open_value = round(sum(all_open_value_list), 2)
        open_value_list = sortTuple(open_value_list, 1)

        labels, ys = zip(*open_value_list)
        xs = np.arange(len(labels)) 
        width = 0.8
        y = list(ys)

        fig = plt.figure(figsize=(18,10))                                                               
        ax = fig.gca()  #get current axes
        ax.barh(xs, ys, width, align='center')
        ax.set_yticks(xs)
        ax.set_yticklabels(labels)
        ax.set_axisbelow(True)
        plt.grid(b=None, which='major', axis='both')
        plt.ylabel('Contract', fontdict={'fontsize': 32})
        plt.title(str(open_value_list[0][0])[3:]+' Open Value for '+date+'\n'+'Total Open Value = '+str(total_open_value)+' BTC', fontdict={'fontsize': 32})
        plt.xlabel('BTC Open Value', fontdict={'fontsize': 32})
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(14)
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(14)
        for i, v in enumerate(y):
            ax.text(v, i, '{:,.2f}'.format(v), color='black', fontweight='bold', fontsize=14)
        plt.tight_layout(True)
        plt.savefig(chart_directory+'open_value.png',bbox_inches='tight',dpi=100)
        plt.clf();

        filenames.append(chart_directory+'open_value.png')


def open_interest(contracts, filenames, date, chart_directory):
    open_interest_list = [(x['symbol'], x['openInterest']) for x in contracts if 'XBT' in x['symbol'] or 'USD' in x['symbol']]
    
    all_open_interest = []
    for x in range(len(open_interest_list)):
        if open_interest_list[x][0] != 'XBTUSD':
            all_open_interest.append(open_interest_list[x][1])
    total_all_open_interest = sum(all_open_interest)

    open_interest_list.append(('Total-XBTUSD', total_all_open_interest))
    open_interest_list = sortTuple(open_interest_list, 1)

    labels, ys = zip(*open_interest_list)
    xs = np.arange(len(labels)) 
    width = 0.8
    y = list(ys)

    fig = plt.figure(figsize=(18,10))                                                               
    ax = fig.gca()  #get current axes
    ax.barh(xs, ys, width, align='center')
    ax.set_yticks(xs)
    ax.set_yticklabels(labels)
    ax.set_axisbelow(True)
    plt.grid(b=None, which='major', axis='both')
    plt.ylabel('Contract', fontdict={'fontsize': 32})
    plt.title('Open Interest for '+date, fontdict={'fontsize': 32})
    plt.xlabel('USD Open Interest', fontdict={'fontsize': 32})
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    fmt = '${x:,.0f}'
    tick = mtick.StrMethodFormatter(fmt)
    ax.xaxis.set_major_formatter(tick)
    for i, v in enumerate(y):
        ax.text(v, i, '${:,.0f}'.format(v), color='black', fontweight='bold', fontsize=14)
    plt.tight_layout(True)
    plt.savefig(chart_directory+'open_interest.png',bbox_inches='tight',dpi=100)
    plt.clf();

    filenames.append(chart_directory+'open_interest.png')


def funding_rate(contracts, filenames, date, chart_directory):
    funding_rate_list = []
    for x in range(len(contracts)):
        try:
            funding_rate_list.append((contracts[x]['symbol'], round(contracts[x]['fundingRate']*100, 4)))
        except TypeError:
            pass

    funding_rate_list = sortTuple(funding_rate_list, 1)

    labels, ys = zip(*funding_rate_list)
    xs = np.arange(len(labels)) 
    width = 0.8
    y = list(ys)

    colors = []
    for x in range(len(funding_rate_list)):
        if funding_rate_list[x][1] < 0:
            colors.append('g')
        else:
            colors.append('r')

    fig = plt.figure(figsize=(18,10))                                                               
    ax = fig.gca()  #get current axes
    ax.barh(xs, ys, width, align='center', color=colors)
    ax.set_yticks(xs)
    ax.set_yticklabels(labels)
    ax.set_axisbelow(True)
    plt.grid(b=None, which='major', axis='both')
    plt.ylabel('Contract', fontdict={'fontsize': 32})
    plt.title('Funding Rates for '+date, fontdict={'fontsize': 32})
    plt.xlabel('Funding Rate', fontdict={'fontsize': 32})
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    fmt = '{x:,.4f}%'
    tick = mtick.StrMethodFormatter(fmt)
    ax.xaxis.set_major_formatter(tick)
    for i, v in enumerate(y):
        ax.text(v, i, '{:,.4f}%'.format(v), color='black', fontweight='bold', fontsize=14)
    plt.tight_layout(True)
    plt.savefig(chart_directory+'funding_rate.png',bbox_inches='tight',dpi=100)
    plt.clf();
    
    filenames.append(chart_directory+'funding_rate.png')


def daily_volume(filenames, date, chart_directory):
    #GET BITMEX VOLUME DATA
    startTime = datetime.strftime(datetime.utcnow(), '%Y-%m-%d')
    bitmex_daily = requests.get('https://www.bitmex.com/api/v1/trade/bucketed?binSize=1d&partial=false&symbol=XBTUSD&count=1&reverse=false&startTime='+startTime+'&endTime='+startTime).json()[0]
    bitmex_daily_volume = (('BITMEX', int(bitmex_daily['volume'])))

    #GET FTX VOLUME DATA
    ftx_daily = requests.get('https://www.ftx.com/api/markets/BTC-PERP/candles?resolution='+str(60*60*24)+'&limit=2').json()['result'][0]
    ftx_daily_volume = (('FTX', int(ftx_daily['volume'])))

    #GET BYBIT VOLUME DATA
    bybit_daily = requests.get('https://api.bybit.com/v2/public/kline/list?symbol=BTCUSD&interval=D&limit=1&from='+str(int(convert_to_epoch((datetime.utcnow()-timedelta(days=1)).strftime('%Y-%m-%d'))))).json()['result'][0]
    bybit_daily_volume = (('BYBIT', int(bybit_daily['volume'])))

    #GET PHEMEX VOLUME DATA
    exchange = 'phemex'
    phemex_daily = requests.get('https://api.phemex.com/md/ticker/24hr?symbol=BTCUSD').json()['result']
    phemex_daily_volume = (('PHEMEX', int(phemex_daily['volume'])))

    all_volume = [bitmex_daily_volume[1], ftx_daily_volume[1], bybit_daily_volume[1], phemex_daily_volume[1]]
    labels = [str('BITMEX'+'\n'+'XBTUSD'), str('FTX'+'\n'+'BTC-PERP'), str('BYBIT'+'\n'+'BTCUSD'), str('PHEMEX'+'\n'+'BTCUSD'+'\n'+'*Sus AF*')]

    all_volume_formatted = list(map("{:,d}".format, all_volume))
    for x in range(len(all_volume_formatted)):
        all_volume_formatted[x] = str('$'+all_volume_formatted[x])

    total_volume = sum(all_volume)
    total_volume = str('$'+"{:,d}".format(total_volume))

    plt.rcParams['font.size'] = 18.0
    fig = plt.figure(figsize=(18,10))
    def func(pct, allvals):
        absolute = int(pct/100.*np.sum(allvals))
        return "{:.1f}%".format(pct, absolute)
    explode = (0.1, 0.1, 0.1, 0.1)
    plt.pie(all_volume, labels=labels, autopct=lambda pct: func(pct, all_volume), explode=explode, shadow=True)
    plt.legend(all_volume_formatted,
              title="USD VOLUME",
              loc="center left",
              title_fontsize ='xx-large',
              fontsize='xx-large',
              bbox_to_anchor=(1, 0, 0.5, 1))
    plt.title((datetime.utcnow()-timedelta(days=1)).strftime('%m-%d-%Y')+' DAILY USD VOLUME'+'\n'+total_volume+' TOTAL')
    plt.tight_layout()
    plt.savefig(chart_directory+'total_volume.png')
    plt.clf();
    
    filenames.append(chart_directory+'total_volume.png')


def bitmex_daily(contracts, filenames, date, chart_directory):
    startTime = datetime.strftime(datetime.utcnow(), '%Y-%m-%d')
    bitmex_contract_list = [x['symbol'] for x in contracts]
    bitmex_daily_returns = []
    for x in bitmex_contract_list:
        resp = requests.get('https://www.bitmex.com/api/v1/trade/bucketed?binSize=1d&partial=false&symbol='+x+'&count=1&reverse=false&startTime='+startTime+'&endTime='+startTime).json()[0]
        bitmex_daily_returns.append((x, round((resp['close']-resp['open'])/resp['open']*100, 2)))
    labels, ys = zip(*bitmex_daily_returns)
    xs = np.arange(len(labels)) 
    width = 0.8
    y = list(ys)
    colors = []
    for x in range(len(bitmex_daily_returns)):
        if bitmex_daily_returns[x][1] < 0:
            colors.append('r')
        else:
            colors.append('g')

    fig = plt.figure(figsize=(18,10))                                                               
    ax = fig.gca()  #get current axes
    ax.barh(xs, ys, width, align='center', color=colors)
    ax.set_yticks(xs)
    ax.set_yticklabels(labels)
    ax.set_axisbelow(True)
    plt.grid(b=None, which='major', axis='both')
    plt.ylabel('Contract', fontdict={'fontsize': 32})
    plt.title('Bitmex Daily Returns '+(datetime.utcnow()-timedelta(days=1)).strftime('%m-%d-%Y'), fontdict={'fontsize': 32})
    plt.xlabel('Percent Return', fontdict={'fontsize': 32})
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for i, v in enumerate(y):
        ax.text(v, i, '{:,.2f}%'.format(v), color='black', fontweight='bold', fontsize=14)
    plt.savefig(chart_directory+'bitmex_daily_returns.png',bbox_inches='tight',dpi=100)
    plt.clf();

    filenames.append(chart_directory+'bitmex_daily_returns.png')


def ftx_daily(contracts, filenames, date, chart_directory):
    ftx_contract_list = [x['name'] for x in contracts if 'PERP' in x['name'] and 'USDT' not in x['name']]

    ftx_daily_returns = []
    for x in ftx_contract_list:
        resp = requests.get('https://www.ftx.com/api/markets/'+x+'/candles?resolution='+str(60*60*24)+'&limit=2').json()['result'][0]
        ftx_daily_returns.append((x, round((resp['close']-resp['open'])/resp['open']*100, 2)))

    labels, ys = zip(*ftx_daily_returns)
    xs = np.arange(len(labels)) 
    width = 0.8
    y = list(ys)
    colors = []
    for x in range(len(ftx_daily_returns)):
        if ftx_daily_returns[x][1] < 0:
            colors.append('r')
        else:
            colors.append('g')

    fig = plt.figure(figsize=(18,10))                                                               
    ax = fig.gca()  #get current axes
    ax.barh(xs, ys, width, align='center', color=colors)
    ax.set_yticks(xs)
    ax.set_yticklabels(labels)
    ax.set_axisbelow(True)
    plt.grid(b=None, which='major', axis='both')
    plt.ylabel('Contract', fontdict={'fontsize': 32})
    plt.title('FTX Daily Returns '+(datetime.utcnow()-timedelta(days=1)).strftime('%m-%d-%Y'), fontdict={'fontsize': 32})
    plt.xlabel('Percent Return', fontdict={'fontsize': 32})
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for i, v in enumerate(y):
        ax.text(v, i, '{:,.2f}%'.format(v), color='black', fontweight='bold', fontsize=12)
    plt.savefig(chart_directory+'ftx_daily_returns_returns.png',bbox_inches='tight',dpi=100)
    plt.clf();
    
    filenames.append(chart_directory+'ftx_daily_returns_returns.png')


def bybit_daily(contracts, filenames, date, chart_directory):
    bybit_contract_list = [x['name'] for x in contracts if 'USDT' not in x['name']]

    bybit_daily_returns = []
    for x in bybit_contract_list:
        resp = requests.get('https://api.bybit.com/v2/public/kline/list?symbol='+x+'&interval=D&limit=1&from='+str(int(convert_to_epoch((datetime.utcnow()-timedelta(days=1)).strftime('%Y-%m-%d'))))).json()['result'][0]
        bybit_daily_returns.append((x, round((float(resp['close'])-float(resp['open']))/float(resp['open'])*100, 2)))

    labels, ys = zip(*bybit_daily_returns)
    xs = np.arange(len(labels)) 
    width = 0.8
    y = list(ys)
    colors = []
    for x in range(len(bybit_daily_returns)):
        if bybit_daily_returns[x][1] < 0:
            colors.append('r')
        else:
            colors.append('g')

    fig = plt.figure(figsize=(18,10))                                                               
    ax = fig.gca()  #get current axes
    ax.barh(xs, ys, width, align='center', color=colors)
    ax.set_yticks(xs)
    ax.set_yticklabels(labels)
    ax.set_axisbelow(True)
    plt.grid(b=None, which='major', axis='both')
    plt.ylabel('Contract', fontdict={'fontsize': 32})
    plt.title('Bybit Daily Returns '+(datetime.utcnow()-timedelta(days=1)).strftime('%m-%d-%Y'), fontdict={'fontsize': 32})
    plt.xlabel('Percent Return', fontdict={'fontsize': 32})
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(14)
    for i, v in enumerate(y):
        ax.text(v, i, '{:,.2f}%'.format(v), color='black', fontweight='bold', fontsize=14)
    plt.savefig(chart_directory+'bybit_daily_returns.png',bbox_inches='tight',dpi=100)
    plt.clf();
    
    filenames.append(chart_directory+'bybit_daily_returns.png')


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

