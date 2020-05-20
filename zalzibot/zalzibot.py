#!/usr/bin/env python
# coding: utf-8

from MyFunctions import *
import ZalzibotFunctions as zf
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
logging.basicConfig(level=logging.INFO, filename=sys.path[0]+'zalzibot.log', format='%(asctime)s :: %(levelname)s :: %(message)s')


bot_credentials = zf.tg_bot_credentials();


while True:
    date = datetime.utcnow().strftime('%m-%d-%Y %H:%M')
    filenames = []
    try:
        bitmex_contracts = requests.get('https://www.bitmex.com/api/v1/instrument/active').json()
    except JSONDecodeError:
        continue
    try:
        ftx_contracts = requests.get('https://ftx.com/api/futures').json()['result']
    except JSONDecodeError:
        continue
    try:
        bybit_contracts = requests.get('https://api.bybit.com/v2/public/symbols').json()['result']
    except JSONDecodeError:
        continue
    filenames = []
    if os.path.exists('open_interest') == True:
        if date[-2:] == '00':
            old_data = load_file('open_interest')
            current_data = zf.new_xbt_data('open_interest', bitmex_contracts, date)
            changes = {}
            for k, v in current_data.items():
                if type(v) != str:
                    changes[k] = current_data[k] - old_data[k]

            zf.dict_formatting(old_data)
            zf.dict_formatting(current_data)
            zf.dict_formatting(changes)

            msg = 'Previous Data'+'\n'
            for k, v in old_data.items():
                msg += k.upper()+': '+v+'\n'
            msg += '\n'

            msg += 'Current Data'+'\n'
            for k, v in current_data.items():
                msg += k.upper()+': '+v+'\n'
            msg += '\n'

            msg += 'Degree of Change'+'\n'
            for k, v in changes.items():
                msg += k.upper()+': '+v+'\n'
            telegram_sendText(bot_credentials, msg)
    else:
        zf.new_xbt_data('open_interest', bitmex_contracts, date)
        logger.info('Initial Run Complete')
    funding_intervals = ['04:00', '12:00', '20:00']
    daily_update = '00:00'
    chart_update = False
    if date[-5:] in funding_intervals:
        chart_update = True
        msg = 'Bitmex 8hr Funding Update'
        zf.funding_rate(bitmex_contracts, filenames, date)
        logger.info('Funding Chart Sent')
    elif date[-5:] == daily_update:
        chart_update = True
        msg = 'Daily Update'
        zf.open_interest(bitmex_contracts, filenames, date)
        zf.open_value(bitmex_contracts, filenames, date)
        zf.bitmex_daily(bitmex_contracts, filenames, date)
        zf.ftx_daily(ftx_contracts, filenames, date)
        zf.bybit_daily(bybit_contracts, filenames, date)
        zf.daily_volume(filenames, date)
        logger.info('Daily Charts Sent')
    if chart_update:   
        telegram_sendText(bot_credentials, msg)
        for x in filenames:
            telegram_sendImage(bot_credentials, x)
    time.sleep(sleep_time('hour', 1, 10, 0))




