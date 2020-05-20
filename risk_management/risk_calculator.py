#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import MyBitmex as bm
import MyBybit as bb
from MyFunctions import *


# In[ ]:


print('Begin Risk Manager')
while True:
    exchanges = ['Bitmex', 'Bybit', 'Exit']
    exchange = list_user_prompt('Choose an Exchange', exchanges)
    if exchange == 'Exit':
        print('Exiting Script')
        break
    verification = check_credentials(exchange)
    client = verification[1]
    bot_credentials = verification[2]
    order_types = ['Market', 'Limit']
    valid_ticks = list(range(10))
    percent_ticks = list(float_range(0, 100, '0.01'))[1:]+[100.00]
    null_orders = ['Deactivated', 'Cancelled', 'Filled']

    if exchange == 'Bitmex':
        contracts = [x['symbol'] for x in client.Instrument.Instrument_getActive().result()[0] if 'XBT' in x['symbol']]
        while True:
            step1_options = ['View/Manage Open Positions', 'Plan New Trade', 'Change Exchange']
            step1 = list_user_prompt('Choose Starting Option', step1_options)
            if step1 == 'Change Exchange':
                break
            elif step1 == 'View/Manage Open Positions':
                mex_positions = bm.open_positions(client)
                active_contracts = [x['Contract'] for x in mex_positions]+['Return to Start']
                print('\n'+'Your Bitmex Open Positions'+'\n')
                print_dict(mex_positions)
                step2_options = ['Close Position', 'Amend Orders', 'Take Profit', 'Return to Start']
                step2 = list_user_prompt('Choose an Option', step2_options)
                if step2 != 'Return to Start':
                    contract_to_view = list_user_prompt('Choose a Position to Manage', active_contracts)
                    if contract_to_view == 'Return to Start':
                        print('\n')
                        continue
                    if step2 == 'Close Position':
                        print('\n')
                        bm.close_position(client, contract_to_view)
                        continue
                    elif step2 == 'Amend Orders':
                        print('\n')
                        new_stop = input_price(client, 'Enter New Stop Price or 0 to Skip', valid_ticks)
                        new_target = input_price(client, 'Enter New Target Price or 0 to Skip', valid_ticks)
                        bm.amend_order(client, new_stop, new_target, contract_to_view)
                        continue
                    elif step2 == 'Take Profit':
                        print('\n')
                        while True:
                            try:
                                take_profit = float(input('Percent of '+contract_to_view+' position to close'+'\n'+'> '))
                            except TypeError:
                                print('Must be a number'+'\n')
                                continue
                            if take_profit == 0:
                                break
                            else:
                                if take_profit not in percent_ticks:
                                    print('Invalid Entry'+'\n')
                                    continue
                                break
                        if take_profit == 0:
                            continue
                        else:
                            new_stop = input_price(client, 'Enter New Stop Price or 0 to Skip', valid_ticks)
                            new_target = input_price(client, 'Enter New Target Price or 0 to Skip', valid_ticks)
                            bm.take_profit_order(client, take_profit, new_stop, new_target, contract_to_view)
                            continue

            elif step1 == 'Plan New Trade':
                contract = list_user_prompt('Choose Contract to Trade', contracts)
                order_type = list_user_prompt('Choose Order Type for Entry', order_types)
                stop = input_price(client, 'Enter Stop Price', valid_ticks)
                target = input_price(client, 'Enter Target Price', valid_ticks)
                contract_data = client.Instrument.Instrument_getActive().result()[0] 
                contract_data = next(item for item in contract_data if item["symbol"] == contract)
                bidPrice = float(contract_data['bidPrice'])
                askPrice = float(contract_data['askPrice'])
                makerFee = float(contract_data['makerFee'])
                takerFee = float(contract_data['takerFee'])
                if order_type == 'Limit':
                    entry = input_price(client, 'Enter Entry Price', valid_ticks)
                else:
                    if stop > target:
                        entry = bidPrice
                    else:
                        entry = askPrice
                while True:
                    try:
                        risk = float(input('Account Percent Risk'+'\n'+'> '))
                    except TypeError:
                        print('Must be a number'+'\n')
                        continue
                    if risk == 0:
                        risk = (stop - entry) / entry
                        break
                    else:
                        if risk not in percent_ticks:
                            print('Invalid Entry'+'\n')
                            continue
                    break
                balance = client.User.User_getWalletHistory().result()[0][0]['walletBalance']/100000000
                position_size_1 = bm.position_size(entry, stop, balance, risk, target, takerFee, makerFee, order_type)
                size = int(position_size_1[0])
                entry_value = float(position_size_1[1])
                stop_value = float(position_size_1[2])
                target_value = float(position_size_1[3])
                risk_amount = bm.risk_amount_XBT(entry_value, stop_value, size)*-1
                reward_amount = bm.reward_amount_XBT(entry_value, target_value, size)*-1
                r_r = bm.r_calc(reward_amount, risk_amount)
                r_r = format(r_r, '.2f')
                new_trade = {}
                new_trade['Contract'] = contract
                if target < entry:
                    new_trade['Direction'] = 'Short'
                else:
                    new_trade['Direction'] = 'Long'
                new_trade['Risk Percentage'] = str(risk)+'%'
                new_trade['Size'] = size
                new_trade['Entry'] = usd_str(entry)
                new_trade['Stop'] = usd_str(stop)
                new_trade['Target'] = usd_str(target)
                new_trade['BTC Risk'] = btc_str(risk_amount)
                new_trade['BTC Reward'] = btc_str(reward_amount)
                new_trade['R:R'] = r_r
                new_trade['Starting Balance'] = str(btc_str(balance)+', '+usd_str(balance*entry))
                new_trade['Win Balance'] = str(btc_str(balance+reward_amount)+', '+usd_str((balance+reward_amount)*target))
                new_trade['Loss Balance'] = str(btc_str(balance-risk_amount)+', '+usd_str((balance-reward_amount)*stop))
                print_dict(new_trade)
                print('Execute Trade?'+'\n'+'WARNING: ALL EXISTING OPEN POSITIONS AND ORDERS FOR THIS CONTRACT WILL BE CLOSED')
                resp = y_n_prompt()
                if resp == 'No':
                    print('TRADE NOT EXECUTED'+'\n')
                    continue
                else:
                    if len(client.Position.Position_get(filter = json.dumps({'symbol': str(contract)})).result()[0]) != 0:
                        if client.Position.Position_get(filter = json.dumps({'symbol': str(contract)})).result()[0][0]['currentQty'] < 0:
                            client.Order.Order_new(symbol=contract, execInst='Close', side='Buy').result()
                        else:
                            client.Order.Order_new(symbol=contract, execInst='Close', side='Sell').result()
                        bm.new_trade(client, contract, size, entry, target, stop, order_type)
                    else:
                        bm.new_trade(client, contract, size, entry, target, stop, order_type)
                    print('TRADE EXECUTED')
                    continue

    elif exchange == 'Bybit':
        contract = 'BTCUSD'
        while True:
            step1_options = ['View/Manage Open Positions', 'Plan New Trade', 'Change Exchange']
            step1 = list_user_prompt('Choose Starting Option', step1_options)
            if step1 == 'Change Exchange':
                break
            elif step1 == 'View/Manage Open Positions':
                bybit_position = bb.open_positions(client, contract)
                print('\n'+'Your Bybit Open Position'+'\n')
                print_dict(bybit_position)
                step2_options = ['Close Position', 'Amend Orders', 'Take Profit', 'Return to Start']
                step2 = list_user_prompt('Choose an Option', step2_options)
                if step2 != 'Return to Start':
                    contract_to_view = list_user_prompt('Choose a Position to Manage', [contract, 'Return to Start'])
                    if contract_to_view == 'Return to Start':
                        print('\n')
                        continue
                    if step2 == 'Close Position':
                        print('\n')
                        bb.close_position(client, contract_to_view)
                        client.Conditional.Conditional_cancelAll(symbol=contract).result()
                        client.Order.Order_cancelAll(symbol=contract).result()
                        continue
                    elif step2 == 'Amend Orders':
                        print('\n')
                        print_dict(bb.open_positions(client, contract_to_view))
                        new_stop = input_price(client, 'Enter New Stop Price or 0 to Skip', valid_ticks)
                        new_target = input_price(client, 'Enter New Target Price or 0 to Skip', valid_ticks)
                        bb.amend_order(client, new_stop, new_target, contract_to_view);
                        print_dict(bb.open_positions(client, contract_to_view))
                        continue
                    elif step2 == 'Take Profit':
                        print('\n')
                        while True:
                            print_dict(bb.open_positions(client, contract_to_view))
                            try:
                                take_profit = float(input('Percent of '+contract_to_view+' position to close'+'\n'+'> '))
                            except TypeError:
                                print('Must be a number'+'\n')
                                continue
                            if take_profit == 0:
                                break
                            else:
                                if take_profit not in percent_ticks:
                                    print('Invalid Entry'+'\n')
                                    continue
                                break
                        if take_profit != 0:
                            new_stop = input_price(client, 'Enter New Stop Price or 0 to Skip', valid_ticks)
                            new_target = input_price(client, 'Enter New Target Price or 0 to Skip', valid_ticks)
                            bb.take_profit_order(client, take_profit, new_stop, new_target, contract_to_view);
                            time.sleep(1)
                            print_dict(bb.open_positions(client, contract_to_view))
                            continue

            elif step1 == 'Plan New Trade':
                order_type = list_user_prompt('Choose Order Type for Entry', order_types)
                stop = input_price(client, 'Enter Stop Price', valid_ticks)
                target = input_price(client, 'Enter Target Price', valid_ticks)
                contract_data = client.Market.Market_symbolInfo(symbol='BTCUSD').result()[0]['result'][0]
                bidPrice = float(contract_data['bid_price'])
                askPrice = float(contract_data['ask_price'])
                makerFee = [float(x['maker_fee']) for x in client.Symbol.Symbol_get().result()[0]['result'] if x['name'] == 'BTCUSD'][0]
                takerFee = [float(x['taker_fee']) for x in client.Symbol.Symbol_get().result()[0]['result'] if x['name'] == 'BTCUSD'][0]
                if order_type == 'Limit':
                    entry = input_price(client, 'Enter Entry Price', valid_ticks)
                else:
                    if stop > target:
                        entry = bidPrice
                    else:
                        entry = askPrice
                while True:
                    try:
                        risk = float(input('Account Percent Risk'+'\n'+'> '))
                    except TypeError:
                        print('Must be a number'+'\n')
                        continue
                    if risk == 0:
                        risk = (stop - entry) / entry
                        break
                    else:
                        if risk not in percent_ticks:
                            print('Invalid Entry'+'\n')
                            continue
                    break
                balance = client.Wallet.Wallet_getBalance(coin='BTC').result()[0]['result']['BTC']['available_balance']
                position_size_1 = bb.position_size(entry, stop, balance, risk, target, takerFee, makerFee, order_type)
                size = int(position_size_1[0])
                entry_value = float(position_size_1[1])
                stop_value = float(position_size_1[2])
                target_value = float(position_size_1[3])
                risk_amount = bb.risk_amount_XBT(entry_value, stop_value, size)*-1
                reward_amount = bb.reward_amount_XBT(entry_value, target_value, size)*-1
                r_r = bb.r_calc(reward_amount, risk_amount)
                r_r = format(r_r, '.2f')
                new_trade = {}
                new_trade['Contract'] = contract
                if target < entry:
                    new_trade['Direction'] = 'Short'
                else:
                    new_trade['Direction'] = 'Long'
                new_trade['Risk Percentage'] = str(risk)+'%'
                new_trade['Size'] = size
                new_trade['Entry'] = usd_str(entry)
                new_trade['Stop'] = usd_str(stop)
                new_trade['Target'] = usd_str(target)
                new_trade['BTC Risk'] = btc_str(risk_amount)
                new_trade['BTC Reward'] = btc_str(reward_amount)
                new_trade['R:R'] = r_r
                new_trade['Starting Balance'] = str(btc_str(balance)+', '+usd_str(balance*entry))
                new_trade['Win Balance'] = str(btc_str(balance+reward_amount)+', '+usd_str((balance+reward_amount)*target))
                new_trade['Loss Balance'] = str(btc_str(balance-risk_amount)+', '+usd_str((balance-risk_amount)*stop))
                print_dict(new_trade)
                print('Execute Trade?'+'\n'+'WARNING: ALL EXISTING OPEN POSITIONS AND ORDERS FOR THIS CONTRACT WILL BE CLOSED')
                resp = y_n_prompt()
                if resp == 'No':
                    print('TRADE NOT EXECUTED'+'\n')
                    continue
                else:
                    client.Conditional.Conditional_cancelAll(symbol=contract).result()
                    client.Order.Order_cancelAll(symbol=contract).result()
                    if len(bb.open_positions(client, contract)) != 0:
                        bb.close_position(client, contract)
                    bb.new_trade(client, contract, size, entry, target, stop, order_type)
                    print('TRADE EXECUTED')
                    continue


# In[ ]:




