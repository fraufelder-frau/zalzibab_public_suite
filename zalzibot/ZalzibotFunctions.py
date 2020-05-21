#!/usr/bin/env python
# coding: utf-8

from MyFunctions import *
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import pytz
import matplotlib.pyplot as plt
import numpy as np
import time
import dateutil.parser
from matplotlib.pyplot import figure
import matplotlib
from matplotlib import gridspec
import matplotlib.ticker as mtick
import os
import logging
import sys
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, filename=sys.path[0]+'/zalzibot.log', format='%(asctime)s :: %(levelname)s :: %(message)s')


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


def convert_to_epoch(time):
    timestamp = datetime.strptime(time, '%Y-%m-%d')
    timezone = pytz.timezone("Asia/Singapore")
    d_aware = timezone.localize(timestamp)
    timestamp = d_aware.timestamp()
    return timestamp


def dict_formatting(dict_item):
    dict_item['price'] = usd_str(dict_item['price'])
    dict_item['openInterest'] = usd_str(dict_item['openInterest'])
    dict_item['openValue'] = btc_str(dict_item['openValue'])
    dict_item['24hrVolume'] = usd_str(dict_item['24hrVolume'])
    dict_item['predictedfunding'] = '{:,.4f}%'.format(dict_item['predictedfunding'])
    return dict_item


def open_value(contracts, filenames, date):
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
        plt.savefig('short_open_value.png',bbox_inches='tight',dpi=100)
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
        plt.savefig('long_open_value.png',bbox_inches='tight',dpi=100)
        plt.clf();

        filenames.append('short_open_value.png')
        filenames.append('long_open_value.png')

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
        plt.savefig('open_value.png',bbox_inches='tight',dpi=100)
        plt.clf();

        filenames.append('open_value.png')


def open_interest(contracts, filenames, date):
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
    plt.savefig('open_interest.png',bbox_inches='tight',dpi=100)
    plt.clf();

    filenames.append('open_interest.png')


def funding_rate(contracts, filenames, date):
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
    plt.savefig('funding_rate.png',bbox_inches='tight',dpi=100)
    plt.clf();
    
    filenames.append('funding_rate.png')


def daily_volume(filenames, date):
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
    plt.savefig('total_volume.png')
    plt.clf();
    
    filenames.append('total_volume.png')


def bitmex_daily(contracts, filenames, date):
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
    plt.savefig('bitmex_daily_returns.png',bbox_inches='tight',dpi=100)
    plt.clf();

    filenames.append('bitmex_daily_returns.png')


def ftx_daily(contracts, filenames, date):
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
    plt.savefig('ftx_daily_returns_returns.png',bbox_inches='tight',dpi=100)
    plt.clf();
    
    filenames.append('ftx_daily_returns_returns.png')


def bybit_daily(contracts, filenames, date):
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
    plt.savefig('bybit_daily_returns.png',bbox_inches='tight',dpi=100)
    plt.clf();
    
    filenames.append('bybit_daily_returns.png')




