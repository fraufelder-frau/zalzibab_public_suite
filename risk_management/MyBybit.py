#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from datetime import datetime, timedelta, timezone
from sympy import symbols, Eq, solve
from bybit import bybit
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
import decimal
import sys
from MyFunctions import *


# In[ ]:


#Pull Bucketed Trade Data
def bybit_kline_data(client, interval, timestamp):
    params = {"symbol": 'BTCUSD',
          "interval": interval,
          "from": timestamp,
          "limit": "1"}
    pull_data = client.Kline.Kline_get(**params).result()
    return pull_data


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


def new_trade(client, contract, size, entry, target, stop, order_type):
    if order_type == 'Market':
        if target > entry:
            order_side = 'Buy'
            stop_side = 'Sell'
        else:
            order_side = 'Sell'
            stop_side = 'Buy'
        client.Order.Order_newV2(symbol=contract, side=order_side, order_type='Market', qty=size, time_in_force='GoodTillCancelled').result()
        client.Order.Order_newV2(side=stop_side, symbol=contract, order_type='Limit', qty=size, price=target, time_in_force='GoodTillCancelled', reduce_only=True, close_on_trigger=True).result()
    else:
        client.Order.Order_newV2(side=order_side, symbol=contract, order_type='Limit', qty=size, price=entry, time_in_force='GoodTillCancelled').result()
        if target < entry:
            stop_limit_trigger = entry+0.5
        else:
            stop_limit_trigger = entry-0.5
        client.Conditional.Conditional_new(side=stop_side, base_price=round(float(client.Market.Market_symbolInfo(symbol='BTCUSD').result()[0]['result'][0]['mark_price']), 0),  symbol=contract, order_type='Limit', qty=size, time_in_force='ImmediateOrCancel', price=target, stop_px=stop_limit_trigger, close_on_trigger=True).result()
    client.Conditional.Conditional_new(side=stop_side, base_price=round(float(client.Market.Market_symbolInfo(symbol='BTCUSD').result()[0]['result'][0]['mark_price']), 0),  symbol=contract, order_type='Market', qty=size, time_in_force='ImmediateOrCancel', stop_px=stop, close_on_trigger=True).result()
    return None


# In[ ]:


def open_positions(client, contract):
    null_orders = ['Deactivated', 'Cancelled', 'Filled']
    resp = client.Positions.Positions_myPositionV2(symbol=contract).result()[0]['result']
    open_orders = [x for x in client.Order.Order_getOrders().result()[0]['result']['data'] if x['order_status'] not in  null_orders]
    bit = {}
    bit['Timestamp'] = tz_to_str(resp['updated_at'], '%m-%d-%Y %H:%M:%S')
    bit['Contract'] = contract
    bit['Side'] = resp['side']
    bit['Size'] = resp['size']
    bit['Entry'] = round(float(resp['entry_price']), 2)
    if bit['Side'] == 'Buy':
        for x in open_orders:
            if x['side'] != bit['Side']:
                if x['order_type'] == 'Market':
                    if float(x['ext_fields']['trigger_price']) > bit['Entry']:
                        bit['Target'] = usd_str(x['ext_fields']['trigger_price'])
                    else:
                        bit['Stop'] = usd_str(x['ext_fields']['trigger_price'])
                else:
                    if float(x['price']) > bit['Entry']:
                        bit['Target'] = usd_str(x['price'])
                    else:
                        bit['Stop'] = usd_str(x['ext_fields']['trigger_price'])
    else:
        for x in open_orders:
            if x['side'] != bit['Side']:
                if float(x['price']) < bit['Entry']:
                    bit['Target'] = usd_str(x['price'])
                else:
                    bit['Stop'] = usd_str(x['ext_fields']['trigger_price'])
    bit['UnrealisedPnL'] = btc_str(resp['unrealised_pnl'])
    bit['Entry'] = usd_str(bit['Entry'])
    return bit


# In[ ]:


def close_position(client, contract_to_view):
    orderQty = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']['size']
    side = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']['side']
    if side == 'Buy':
        client.Order.Order_newV2(symbol=contract_to_view, side='Sell', order_type='Market', qty=orderQty, time_in_force='GoodTillCancelled').result()
    elif side == 'Sell':
        client.Order.Order_newV2(symbol=contract_to_view, side='Buy', order_type='Market', qty=orderQty, time_in_force='GoodTillCancelled').result()
    return print(contract_to_view+' Position Closed')


# In[ ]:


def amend_order(client, new_stop, new_target, contract_to_view):
    null_orders = ['Deactivated', 'Cancelled', 'Filled']
    resp = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']
    side = resp['side']
    entry = round(float(resp['entry_price']), 2)
    open_orders = [x for x in client.Order.Order_getOrders().result()[0]['result']['data'] if x['order_status'] not in  null_orders]
    if side == 'Buy':
        for x in open_orders:
            if x['side'] != side:
                if x['order_type'] == 'Market':
                    if float(x['ext_fields']['trigger_price']) > entry:
                        close_id = x['order_id']
                    else:
                        stop_id = x['order_id']
                else:
                    if float(x['price']) > entry:
                        close_id = x['order_id']
                    else:
                        stop_id = x['order_id']
    else:
        for x in open_orders:
            if x['side'] != side:
                if x['order_type'] == 'Market':
                    if float(x['ext_fields']['trigger_price']) < entry:
                        close_id = x['order_id']
                    else:
                        stop_id = x['order_id']
                else:
                    if float(x['price']) > entry:
                        close_id = x['order_id']
                    else:
                        stop_id = x['order_id']
    if new_stop != 0:
        client.Conditional.Conditional_replace(symbol=contract_to_view, order_id=stop_id, p_r_trigger_price=new_stop).result()
        print('Stop Amended to '+usd_str(new_stop))
    if new_target != 0:
        client.Order.Order_replace(order_id=close_id, symbol=contract_to_view, p_r_price=new_target).result()
        print('Close Amended to '+usd_str(new_target))
    return None


# In[ ]:


def take_profit_order(client, take_profit, new_stop, new_target, contract_to_view):
    resp = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']
    side = resp['side']
    take_profit_size = round(((resp['size']*(int(take_profit)/100))), 0)
    client.Conditional.Conditional_cancelAll(symbol=contract_to_view).result()
    client.Order.Order_cancelAll(symbol=contract_to_view).result()
    if side == 'Buy':
        order_side = 'Sell'
    else:
        order_side = 'Buy'
    client.Order.Order_newV2(side=order_side, symbol=contract_to_view, order_type='Market', qty=take_profit_size, time_in_force='GoodTillCancelled').result()
    time.sleep(1)
    new_size = client.Positions.Positions_myPositionV2(symbol=contract_to_view).result()[0]['result']['size']
    if new_target != 0:
        client.Order.Order_newV2(side=order_side, symbol=contract_to_view, order_type='Limit', qty=new_size, price=new_target, time_in_force='GoodTillCancelled', reduce_only=True, close_on_trigger=True).result()
        print('Target for '+contract_to_view+' Set to '+usd_str(new_target))
    if new_stop != 0:
        client.Conditional.Conditional_new(side=order_side, base_price=round(float(client.Market.Market_symbolInfo(symbol='BTCUSD').result()[0]['result'][0]['mark_price']), 0),  symbol=contract_to_view, order_type='Market', qty=new_size, time_in_force='ImmediateOrCancel', stop_px=new_stop, close_on_trigger=True).result()
        print('Stop for '+contract_to_view+' Set to '+usd_str(new_stop))
    return None

