#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from datetime import datetime, timedelta, timezone
from sympy import symbols, Eq, solve
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
from MyFunctions import *


# In[ ]:


def close_position(client, contract_to_view):
    resp = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]
    if resp['currentQty'] > 0:
        client.Order.Order_new(symbol=contract_to_view, execInst='Close', side='Sell').result()
    else:
        client.Order.Order_new(symbol=contract_to_view, execInst='Close', side='Buy').result()
    client.Order.Order_cancelAll(symbol=contract_to_view).result()
    return print(contract_to_view+' Position Closed')


# In[ ]:


def open_positions(client):
    postions = []
    resp = client.Position.Position_get(filter = json.dumps({'isOpen': True})).result()[0]
    for x in range(len(resp)):
        time.sleep(1)
        current_bitmex = client.Position.Position_get(filter=json.dumps({'symbol': resp[x]['symbol']})).result()[0][0]    
        open_orders = client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true'})).result()[0]
        time.sleep(1)
        if len(client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Limit', 'MarketIfTouched', 'StopLimit', 'LimitIfTouched']})).result()[0]) != 0:
            close_order = client.Order.Order_getOrders(symbol = resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Limit', 'MarketIfTouched', 'StopLimit', 'LimitIfTouched']})).result()[0]
            close_price = usd_str(close_order[0]['price'])
        else:
            close_order = 'No Close Order Set'
            close_price = 'No Close Order Set'
        time.sleep(1)
        if len(client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Stop', 'TrailingStop']})).result()[0]) > 0:
            stop_order = client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Stop', 'TrailingStop']})).result()[0]
            stop_price = usd_str(stop_order[0]['stopPx'])
        else:
            stop_order = 'NO STOP SET!!!'
            stop_price = 'NO STOP SET!!!'
        time.sleep(1)
        mex = {}
        mex['Contract'] = resp[x]['symbol']
        if current_bitmex['currentQty'] < 0:
            mex['Side'] = 'Short'
        elif current_bitmex['currentQty'] > 0:
            mex['Side'] = 'Long'
        else:
            mex['Side'] = 'None'
        if mex['Side'] == 'Short':
            mex['Size'] = current_bitmex['currentQty']*-1
        else:
            mex['Size'] = current_bitmex['currentQty']
        mex['Entry'] = current_bitmex['avgEntryPrice']
        mex['Target'] = close_price
        mex['Stop'] = stop_price
        mex['OpenValue'] = btc_float_round(mex['Size']*((1/mex['Entry'])-(1/mex['Entry'])*0.00075))
        mex['MarketPrice'] = current_bitmex['markPrice']
        mex['MarketValue'] = btc_float_round(mex['Size']*((1/mex['MarketPrice'])-(1/mex['MarketPrice'])*0.00075))
        mex['Entry'] = usd_str(current_bitmex['avgEntryPrice'])
        mex['MarketPrice'] = usd_str(current_bitmex['markPrice'])
        if mex['Side'] == 'Long':
            mex['UnrealisedPnL'] = btc_str(mex['OpenValue'] - mex['MarketValue'])
        else:
            mex['UnrealisedPnL'] = btc_str(mex['MarketValue'] - mex['OpenValue'])
        postions.append(mex)
    return postions


# In[ ]:


def active_contracts(client):
    contracts = requests.get('https://www.bitmex.com/api/v1/instrument/active').json()
    contract_list = [x['symbol'] for x in bitmex_contracts]
    return contract_list


# In[ ]:


def new_trade(client, contract, size, entry, target, stop, order_type):
    if order_type == 'Market':
        client.Order.Order_cancelAll(symbol=contract).result()
        client.Order.Order_new(symbol=contract, orderQty=size, ordType='Market').result()
        client.Order.Order_new(symbol=contract, price=target, execInst='ReduceOnly', orderQty=(size*-1), ordType='Limit').result()
        client.Order.Order_new(symbol=contract, stopPx=stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='Stop').result()
    else:
        client.Order.Order_cancelAll(symbol=contract).result()
        client.Order.Order_new(symbol=contract, orderQty=size, price=entry).result()
        if target < entry:
            stop_limit_trigger = float(float(entry)+0.5)
        else:
            stop_limit_trigger = float(float(entry)-0.5)
        client.Order.Order_new(symbol=contract, stopPx=stop_limit_trigger, price=target, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='StopLimit').result()
        client.Order.Order_new(symbol=contract, stopPx=stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='Stop').result()
    return None


# In[ ]:


def amend_order(client, new_stop, new_target, contract_to_view):
    if len(client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Stop'})).result()[0]) > 0:
        stop = client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Stop'})).result()[0][0]
    else:
        stop = []
    if len(client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'Close'})).result()[0]) > 0:
        close = client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'Close'})).result()[0][0]
    elif len(client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ParticipateDoNotInitiate,ReduceOnly'})).result()[0]) > 0:
        close = client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ParticipateDoNotInitiate,ReduceOnly'})).result()[0][0]
    elif len(client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ReduceOnly'})).result()[0]) > 0:
        close = client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ReduceOnly'})).result()[0][0]
    else:
        close = []
    qty = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]['currentQty']
    orderQty = qty*-1
    if new_stop != 0:
        if len(stop) > 0:
            client.Order.Order_amend(orderID=stop['orderID'], stopPx=new_stop).result()
            print('Stop for '+contract_to_view+' Amended to '+usd_str(new_stop))
        elif len(stop) == 0:
            client.Order.Order_new(symbol=contract_to_view, stopPx=new_stop, execInst=str('LastPrice, ReduceOnly'), orderQty=orderQty, ordType='Stop').result()
            print('Stop for '+contract_to_view+' Set to '+usd_str(new_stop))
    else:
        print('Stop Unchanged')
    if new_target != 0 :
        if len(close) > 0:
            client.Order.Order_amend(orderID=close['orderID'], price=new_target).result()
            print('Target for '+contract_to_view+' Amended to '+usd_str(new_target))
        elif len(close) == 0:
            client.Order.Order_new(symbol=contract_to_view, price=new_target, execInst='ReduceOnly', orderQty=orderQty, ordType='Limit').result()
            print('Target for '+contract_to_view+' Set to '+usd_str(new_target))
    else:
        print('Target Unchanged')
        
        
    return print('\n'+'Updated Positions'), print_dict(open_positions(client))


# In[ ]:


def take_profit_order(client, take_profit, new_stop, new_target, contract_to_view):
    resp = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]
    take_profit_size = round(((resp['currentQty']*(int(take_profit)/100))*-1), 0)
    client.Order.Order_cancelAll(symbol=contract_to_view).result()
    client.Order.Order_new(symbol=contract_to_view, orderQty=take_profit_size, ordType='Market').result()
    new_size = client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]['currentQty']
    if new_target != 0:
        client.Order.Order_new(symbol=contract_to_view, price=new_target, execInst='ReduceOnly', orderQty=(new_size*-1), ordType='Limit').result()
        print('Target for '+contract_to_view+' Set to '+usd_str(new_target))
    if new_stop != 0:
        client.Order.Order_new(symbol=contract_to_view, stopPx=new_stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(new_size*-1), ordType='Stop').result()
        print('Stop for '+contract_to_view+' Set to '+usd_str(new_stop))
    return print('\n'+'Updated Positions'), print_dict(open_positions(client))


# In[ ]:


def risk_amount_XBT(entry_value, stop_value, size):
    risk_amount = (size*(entry_value - stop_value))
    risk_amount = float(round(risk_amount, 8))
    return risk_amount


# In[ ]:


def reward_amount_XBT(entry_value, target_value, size):
    reward_amount = (size*(target_value - entry_value))
    reward_amount = float(round(reward_amount, 8))
    return reward_amount


# In[ ]:


def r_calc(reward_amount, risk_amount):
    r_r = reward_amount/risk_amount
    return r_r


# In[ ]:


def position_size(entry, stop, balance, risk, target, takerFee, makerFee, order_type):
    x = symbols('x')
    if target > entry:
        target_value = (1/target)+((1/target)*takerFee)
        stop_value = (1/stop)+((1/stop)*takerFee)
        if order_type == 'Limit':
            entry_value = (1/entry)-((1/entry)*makerFee)
            eq1 = Eq((x*(entry_value - stop_value)) + (balance*risk/100)) 
        else:
            entry_value = (1/entry)-((1/entry)*takerFee)
            eq1 = Eq((x*(entry_value - stop_value)) + (balance*risk/100))
    elif target < entry:
        target_value = (1/target)-((1/target)*takerFee)
        stop_value = (1/stop)-((1/stop)*takerFee)
        if order_type == 'Limit':
            entry_value = (1/entry)+((1/entry)*makerFee)
            eq1 = Eq((x*(stop_value - entry_value)) - (balance*risk/100))
        else:
            entry_value = (1/entry)+((1/entry)*takerFee)
            eq1 = Eq((x*(stop_value - entry_value)) - (balance*risk/100))
    size = solve(eq1)
    size = [ '%.0f' % elem for elem in size ]
    size = size[0]
    return size, entry_value, stop_value, target_value

