#!/usr/bin/env python
# coding: utf-8

from ZalzibotFunctions import *
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, filename=sys.path[0]+'zalzibot.log', format='%(asctime)s :: %(levelname)s :: %(message)s')


bot_credentials = tg_bot_credentials();


while True:
    create_directory('charts')
    chart_directory = str(sys.path[0])+'/charts/'
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
            current_data = new_xbt_data('open_interest', bitmex_contracts, date)
            changes = {}
            for k, v in current_data.items():
                if type(v) != str:
                    changes[k] = current_data[k] - old_data[k]

            dict_formatting(old_data)
            dict_formatting(current_data)
            dict_formatting(changes)

            msg = 'Previous Data'+'\n'
            msg += dict_to_msg(old_data)

            msg += 'Current Data'+'\n'
            msg += dict_to_msg(current_data)

            msg += 'Degree of Change'+'\n'
            msg += dict_to_msg(changes)
            telegram_sendText(bot_credentials, msg)
    else:
        new_xbt_data('open_interest', bitmex_contracts, date)
        logger.info('Initial Run Complete')
    funding_intervals = ['04:00', '12:00', '20:00']
    daily_update = '00:00'
    chart_update = False
    if date[-5:] in funding_intervals:
        chart_update = True
        msg = 'Bitmex 8hr Funding Update'
        funding_rate(bitmex_contracts, filenames, date, chart_directory)
        logger.info('Funding Chart Sent')
    elif date[-5:] == daily_update:
        chart_update = True
        msg = 'Daily Update'
        open_interest(bitmex_contracts, filenames, date, chart_directory)
        open_value(bitmex_contracts, filenames, date, chart_directory)
        bitmex_daily(bitmex_contracts, filenames, date, chart_directory)
        ftx_daily(ftx_contracts, filenames, date, chart_directory)
        bybit_daily(bybit_contracts, filenames, date, chart_directory)
        daily_volume(filenames, date, chart_directory)
        logger.info('Daily Charts Sent')
    if chart_update:   
        telegram_sendText(bot_credentials, msg)
        for x in filenames:
            telegram_sendImage(bot_credentials, x)
    time.sleep(sleep_time('hour', 1, 5, 0))




