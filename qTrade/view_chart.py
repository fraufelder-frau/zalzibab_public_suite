#!/usr/bin/env python
# coding: utf-8

from MyFunctions import *


print('Integrate Telegram Bot?')
use_bot = y_n_prompt()
if use_bot == 'Yes':
    bot = True
else:
    bot = False
print('\n')
exchange = 'qTrade'
check = verify_credentials(exchange, bot)


while True:
    date = datetime.utcnow().strftime('%m-%d-%Y %H:%M:%S')
    credentials = load_credentials(exchange, bot)
    client = credentials[0]
    bot_credentials = credentials[1]

    market_pull = client.tickers
    active_markets = [x['id_hr'] for x in list(market_pull.values()) if x['last_change'] is not None]
    active_markets.sort()
    active_markets = sorted_list(active_markets)
    market_to_view = list_prompt('Choose Chart to Pull', active_markets);

    #Setup valid qTrade data tfs and their candlestick width equivalents
    valid_timeframes = ['fivemin', 'fifteenmin', 'thirtymin', 'onehour', 'twohour', 'fourhour', 'oneday']
    mins_in_day = 60*24
    width_floats = [1/mins_in_day*5, 1/mins_in_day*15, 1/mins_in_day*30, 1/mins_in_day*60, 1/mins_in_day*120, 1/mins_in_day*240, 1]
    widths = {}
    for x in range(len(width_floats)):
        widths[valid_timeframes[x]] = width_floats[x]

    #Get user parameters of timeframe and lookback duration
    timeframe = list_prompt('Choose Timeframe to Pull', valid_timeframes);

    ohlcv_data = client.get("/v1/market/"+market_to_view+"/ohlcv/"+timeframe)['slices']

    max_lookback_length = len(ohlcv_data)

    print('Number of '+timeframe+' Candles to Pull'+'\n'+'Max Count: '+str(max_lookback_length)+'\n')
    while True:
        try:
            lookback_length = int(input('> '))
        except ValueError:
            print('Lookback Length Must Be Int'+'\n')
            continue
        else:
            if lookback_length > max_lookback_length:
                print('ERROR: Maximum Lookback Length Is '+str(max_lookback_length)+'\n')
                continue
            else:
                print('Selection: '+str(lookback_length))
                break

    #Parse historical data to desired lookback length
    ohlcv_data = ohlcv_data[(lookback_length-1)*-1:]

    #Create DataFrame
    chart_df = pd.DataFrame(data=ohlcv_data, index=list(range(len(ohlcv_data))))

    #Reformat values of DataFrame and create tuple for candlestick chart
    change_to_float = ['open', 'high', 'low', 'close', 'volume']
    for x in change_to_float:
        chart_df[x] = chart_df[x].astype(float)
    for x in range(len(chart_df)):
        chart_df['time'].iloc[x] = mdates.datestr2num(chart_df['time'].iloc[x])
    quotes = ([tuple(z) for z in chart_df[['time','open','high','low','close']].values])

    #Generate Chart
    figure(num=None, figsize=(30, 18), dpi=100, facecolor='white', edgecolor='black')
    gs1 = gridspec.GridSpec(2, 1, height_ratios=[3, 1])

    x_axis = chart_df['time']
    y_axis = chart_df['volume']


    plt.rcParams['font.size'] = 18.0
    ax = plt.subplot(gs1[0])
    plt.title(market_to_view+' '+timeframe+' '+str(lookback_length)+' Candle Lookback', y=0.9, fontsize=32)
    candlestick_ohlc(ax, quotes, width=widths[timeframe], colorup='g', colordown='r');
    ax.set_axisbelow(True)
    plt.grid(b=None, which='major', axis='both')
    plt.tick_params(axis='x', which='both', top=False, bottom=False, labelbottom=False)
    plt.tick_params(axis='y', which='both', left=True, right=True, labelleft=True, labelright=True)
    plt.autoscale(tight=True)
    ax.xaxis_date()
    if timeframe in valid_timeframes[:-1]:
        date_format = "%m-%d-%Y %H:%M"
    else:
        date_format = "%m-%d-%Y"
    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    plt.gcf().autofmt_xdate()

    ax1 = plt.subplot(gs1[1], sharex=ax)
    plt.plot(x_axis, y_axis)
    plt.title('BTC Volume', y=0.9, fontsize=32)
    plt.autoscale(tight=True)
    plt.tick_params(axis='x', which='both', top=False, bottom=True, labelbottom=True)
    plt.tick_params(axis='y', which='both', left=False, right=True, labelleft=False, labelright=True)
    ax1.xaxis_date()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    plt.gcf().autofmt_xdate()
    plt.ticklabel_format(axis='y', style='plain')

    plt.subplots_adjust(top=0.98, bottom=0.08, left=0.068, right=0.93, hspace=0, wspace=0)
    filename = date+'_'+market_to_view+'.png'
    plt.savefig(filename)
    plt.clf();

    if bot == True:
        print('Send Chart To Telegram?')
        send_chart = y_n_prompt()
        if send_chart == 'Yes':
            telegram_sendText(bot_credentials, date+'\n'+market_to_view+' Chart')
            telegram_sendImage(bot_credentials, filename)
    print('\n'+'Save Chart?')
    resp = y_n_prompt()
    if resp == 'No':
        os.remove(filename)
    print('\n'+'Pull Another Chart?')
    end_script = y_n_prompt()
    if end_script == 'No':
        break

