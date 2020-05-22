#!/usr/bin/env python
# coding: utf-8

#Import libraries
from MyFunctions import *
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, filename=sys.path[0]+'/trade_history.log', format='%(asctime)s :: %(levelname)s :: %(message)s')
import warnings
warnings.simplefilter("ignore")


exchange = 'qTrade'
my_token = ''
myID = ''
verification = check_credentials(exchange)
create_directory('reports')
csv_directory = str(sys.path[0])+'/reports/'
while True:
    try:
        refresh_time = int(input('Number of minutes between order updates'+'\n'+'> '))
    except TypeError:
        print('Must be a whole number'+'\n')
        continue
    break


while True:
    date = datetime.utcnow().strftime('%m-%d-%Y %H:%M:%S')
    verification = load_credentials(exchange, my_token, myID);
    logger.info('Loop Started')
    client = verification[0]
    bot_credentials = verification[1]

    if os.path.exists('last_trade_recorded'):
        last_trade_recorded = float(load_file('last_trade_recorded'))
    else:
        last_trade_recorded = 0
    #Fetch Execution History
    needed_keys = ['market_string', 'market_amount', 'price', 'base_amount', 'market_string', 'base_fee', 'side', 'created_at']
    execution_history = client.get('/v1/user/trades')['trades']
    execution_history = sorted(execution_history, key=itemgetter('created_at'))
    newer_than = execution_history[-1]['order_id']
    pull = True
    while pull:
        temp_data = client.get('/v1/user/trades', newer_than=newer_than)['trades']
        if len(temp_data) == 0:
            pull = False
        else:
            execution_history.append(temp_data)
            execution_history = sorted(execution_history, key=itemgetter('created_at'))
            newer_than = execution_history[-1]['order_id']
    for l in range(len(execution_history)):
        execution_history[l] = {your_key: execution_history[l][your_key] for your_key in needed_keys}

    #Get list of all market_strings with execution history
    markets_traded = [x['market_string'] for x in execution_history]
    markets_traded.sort()
    markets_traded = sorted_list(markets_traded)    
    partials = {}
    for m in markets_traded:
        try:
            partials[m] = [x for x in [y['trades'] for y in client.orders() if y['market_string'] == m and y['trades'] != None][0]]
            for l in range(len(partials[m])):
                partials[m][l].update({'order_type': [x['order_type'] for x in client.orders() if x['market_string'] == m][0]})
        except IndexError:
            pass
    reformatted_partials = {}
    for m in list(partials.keys()):
        market_string = m
        amounts = [float(x['market_amount']) for x in partials[m]]
        prices = [float(x['price']) for x in partials[m]]
        market_amount = sum(amounts)
        avg_price = btc_str(sum(prices[g] * amounts[g] / market_amount for g in range(len(prices))))
        base_amount = btc_str(sum([float(x['base_amount']) for x in partials[m]]))
        base_fee = btc_str(sum([float(x['base_fee']) for x in partials[m]]))
        side = partials[m][-1]['order_type']
        side_dict = {'sell_limit':'sell', 'buy_limit':'buy'}
        created_at = partials[m][-1]['created_at']
        reformatted_partials.update({'market_string': m,
                                     'market_amount': btc_str(market_amount),
                                     'price': avg_price,
                                     'base_amount': base_amount,
                                     'base_fee': base_fee,
                                     'side': side_dict[side],
                                     'created_at': created_at})
    execution_history.append(reformatted_partials)
    last_executed = tz_to_timestamp(execution_history[-1]['created_at'])
    updated_last_trade = save_file('last_trade_recorded', last_executed);

    if last_trade_recorded != last_executed:
        logger.info('New Trades Detected')
        #Parse Execution History by market and sort by timestamp
        coin_specific_trades = {}
        for x in markets_traded:
            coin_specific_trades[x] = [y for y in execution_history if y['market_string'] == x]
            coin_specific_trades[x] = sorted(coin_specific_trades[x], key=itemgetter('created_at'))

        #Create DataFrames for each coin traded
        coin_specific_dfs = []
        for x in range(len(coin_specific_trades)):
            coin_specific_dfs.append(pd.DataFrame(data=coin_specific_trades[markets_traded[x]], index=list(range(len(coin_specific_trades[markets_traded[x]])))))

        #Reformat DataFrames and save to csv
        for x in range(len(coin_specific_dfs)):
            for y in range(len(coin_specific_dfs[x])):
                coin_specific_dfs[x]['created_at'].iloc[y] = datetime.strftime(datetime.strptime(coin_specific_dfs[x]['created_at'].iloc[y], '%Y-%m-%dT%H:%M:%S.%fZ'), '%m-%d-%Y %H:%M')
            columns = list(coin_specific_dfs[x].columns)
            columns = columns[-1:] + columns[:-1]
            coin_specific_dfs[x] = coin_specific_dfs[x][columns]
            coin_specific_dfs[x].to_csv(csv_directory+markets_traded[x]+'_trades.csv', index=False)

        new_executions = {}
        for x in markets_traded:
            new_executions[x] = [y for y in execution_history if y['market_string'] == x]
            new_executions[x] = [l for l in new_executions[x] if tz_to_timestamp(l['created_at']) > last_trade_recorded]
            new_executions[x] = sorted(new_executions[x], key=itemgetter('created_at'))
            if len(new_executions[x]) == 0:
                del new_executions[x]

        new_markets = list(new_executions.keys())      
        all_new_trades= []
        for x in new_markets:
            for y in range(len(new_executions[x])):
                clean_dict = {}
                clean_dict['Market'] = new_executions[x][y]['market_string']
                clean_dict['Timestamp'] = tz_to_str(new_executions[x][y]['created_at'], '%m-%d-%Y %H:%M')
                clean_dict['Side'] = new_executions[x][y]['side'].upper()
                clean_dict['Quote'] = new_executions[x][y]['market_amount']
                clean_dict['Price'] = new_executions[x][y]['price']
                clean_dict['Base'] = new_executions[x][y]['base_amount']
                all_new_trades.append(clean_dict)
        if bot_credentials[0] is not None:
            msg = 'Updated Trades'+'\n'+date+'\n'+'\n'      
            msg += dict_to_msg(all_new_trades)

            balances = {x:str(y) for x,y in client.balances_merged().items() if float(y)!=0}
            coins_to_trade = [x for x in balances.keys() if x != 'BTC']
            for x in coins_to_trade:
                precision = len(client.tickers[x+'_BTC']['day_volume_market'].split('.')[1])
                balances[x] = coin_str(balances[x], precision)
            msg += '\n'+'Final Balances'+'\n'+date+'\n'
            msg += dict_to_msg(balances)
            telegram_sendText(bot_credentials, msg);
            logger.info('Msg Sent')
            time.sleep(sleep_time(refresh_time))
    else:
        logger.info('Loop Completed')
        time.sleep(sleep_time(refresh_time))

