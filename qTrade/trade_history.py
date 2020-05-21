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
    msg = ''
    date = datetime.utcnow().strftime('%m-%d-%Y %H:%M:%S')
    verification = load_credentials(exchange, my_token, myID);
    logger.info('Loop Started')
    client = verification[0]
    bot_credentials = verification[1]

    if os.path.exists('last_trade_recorded'):
        last_trade_recorded = float(load_file('last_trade_recorded'))
        logger.info('Last Trade Timestamp: '+str(last_trade_recorded))
    else:
        last_trade_recorded = 0
        logger.info('No Trade History On Record')
    #Fetch Execution History
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

    last_executed = tz_to_timestamp(execution_history[-1]['created_at'])
    updated_last_trade = save_file('last_trade_recorded', last_executed);
    
    if last_trade_recorded != last_executed:
        logger.info('New Trades Detected')
        #Get list of all market_strings with execution history
        markets_traded = [x['market_string'] for x in execution_history]
        markets_traded.sort()
        markets_traded = sorted_list(markets_traded)

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
        drops = ['id', 'order_id', 'market_id']
        for x in range(len(coin_specific_dfs)):
            coin_specific_dfs[x] = coin_specific_dfs[x].drop(columns=drops)
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
            
            open_orders = client.orders(open=True)
            wallet_balances = {}
            balances = client.balances()
            for k, v in balances.items():
                if float(balances[k]) > 0:
                    wallet_balances[k] = float(balances[k])

            for k, v in wallet_balances.items():
                wallet_balances[k] += sum([float(x['market_amount_remaining']) for x in open_orders if x['order_type'] == 'sell_limit' and x['market_string'][:-4] == k])
            wallet_balances['BTC'] += sum([float(x['base_amount']) for x in open_orders if x['order_type'] == 'buy_limit'])
            
            msg += '\n'+'Final Balances'+'\n'
            msg += dict_to_msg(wallet_balances)
            telegram_sendText(bot_credentials, msg);
            logger.info('Msg Sent')
            time.sleep(sleep_time(refresh_time))
    else:
        logger.info('Loop Completed')
        time.sleep(sleep_time(refresh_time))

