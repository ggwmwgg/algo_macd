import os

import ta.trend
import ta.volatility
import ta.momentum
import ta.volume
import pandas as pd
import math
import requests
import csv
import time

from dotenv import load_dotenv


def notifier(text):
    load_dotenv()
    bot_token = os.getenv('tg_token')
    chat_id = os.getenv('tg_chat_id')

    with open("final.csv", "a", newline="") as file:
        writer = csv.writer(file)
        if text != "Bot started":
            writer.writerow([text])

    print(text)

    # message_text = "Hello, *bold* _italic_ 😃 test"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', json=payload)
    if response.status_code != 200:
        print(f'Failed to send the message. Error: {response.text}')


def ema(arr: pd.Series, n: int) -> pd.Series:
    """
    Returns `n`-period EMA of array `arr`.
    """
    return pd.Series(arr).ewm(span=n, adjust=False).mean()


def get_df(data):
    """
    Returns updated array with RSI, Stoch, CCI, ROC, PVO indicators.
    """
    df = pd.DataFrame(data)
    df = df.iloc[:, 0:6]
    df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    df['Time'] = pd.to_datetime(df['Time'], unit='ms')
    df.set_index('Time', inplace=True)
    df = df.astype(float)
    # df = df.iloc[::-1]

    # RSI and add to dataframe (just RSI)
    rsi = ta.momentum.RSIIndicator(close=pd.Series(df["Close"]), window=14)
    df = df.assign(rsi=rsi.rsi().round(2))

    # EMA 200 and add to dataframe
    df = df.assign(ema_200=ema(df["Close"], 200).round(2))

    # EMA 50 and add to dataframe
    df = df.assign(ema_50=ema(df["Close"], 50).round(2))

    # Stoch and add to dataframe (stoch and stoch_signal)
    stoch = ta.momentum.StochasticOscillator(high=pd.Series(df["High"]),
                                             low=pd.Series(df["Low"]),
                                             close=pd.Series(df["Close"]),
                                             window=14,
                                             smooth_window=3)
    df = df.assign(stoch=stoch.stoch().round(2))
    df = df.assign(stoch_signal=stoch.stoch_signal().round(2))

    # CCI and add to dataframe
    cci = ta.trend.CCIIndicator(high=pd.Series(df["High"]),
                                low=pd.Series(df["Low"]),
                                close=pd.Series(df["Close"]),
                                window=20,
                                constant=0.015)
    df = df.assign(cci=cci.cci().round(2))

    # ROC and add to dataframe
    roc = ta.momentum.ROCIndicator(close=pd.Series(df["Close"]),
                                   window=9)
    df = df.assign(roc=roc.roc().round(2))

    # ATR and add to dataframe
    atr = ta.volatility.AverageTrueRange(high=pd.Series(df["High"]),
                                         low=pd.Series(df["Low"]),
                                         close=pd.Series(df["Close"]),
                                         window=14)
    df = df.assign(atr=atr.average_true_range().round(2))

    # Bollinger Bands and add to dataframe (BB_upper, BB_middle, BB_lower)
    bb = ta.volatility.BollingerBands(close=pd.Series(df["Close"]),
                                      window=20,
                                      window_dev=2)
    df = df.assign(bb_high=bb.bollinger_hband().round(2))
    df = df.assign(bb_mid=bb.bollinger_mavg().round(2))
    df = df.assign(bb_low=bb.bollinger_lband().round(2))

    # MFI and add to dataframe
    mfi = ta.volume.MFIIndicator(high=pd.Series(df["High"]),
                                 low=pd.Series(df["Low"]),
                                 close=pd.Series(df["Close"]),
                                 volume=pd.Series(df["Volume"]),
                                 window=14)
    df = df.assign(mfi=mfi.money_flow_index().round(2))

    # PSAR and assign to dataframe
    psar = ta.trend.PSARIndicator(high=pd.Series(df["High"]),
                                  low=pd.Series(df["Low"]),
                                  close=pd.Series(df["Close"]),
                                  step=0.02,
                                  max_step=0.2,
                                  )
    df = df.assign(psar_up_indicator=psar.psar_up_indicator())
    df = df.assign(psar_down_indicator=psar.psar_down_indicator())
    df = df.assign(psar=psar.psar())

    # MACD and assign to dataframe
    macd = ta.trend.MACD(close=pd.Series(df["Close"]),
                         window_fast=12,
                         window_slow=26,
                         window_sign=2,
                         )
    df = df.assign(macd=macd.macd())
    df = df.assign(macd_signal=macd.macd_signal())
    df = df.assign(macd_diff=macd.macd_diff())

    # Triple EMA
    v2o_init = ta.trend.ema_indicator(df["Open"], window=8, fillna=True)
    v2c_init = ta.trend.ema_indicator(df["Close"], window=8, fillna=True)

    ema2_open = ta.trend.ema_indicator(v2o_init, 8, fillna=True)
    ema2_close = ta.trend.ema_indicator(v2c_init, 8, fillna=True)

    ema3_open = ta.trend.ema_indicator(ema2_open, 8, fillna=True)
    ema3_close = ta.trend.ema_indicator(ema2_close, 8, fillna=True)

    tema_open = 3 * (v2o_init - ema2_open) + ema3_open
    tema_close = 3 * (v2c_init - ema2_close) + ema3_close
    df = df.assign(tema_open=tema_open)
    df = df.assign(tema_close=tema_close)

    # Remove NaN values
    df = df.dropna()

    # Display all columns
    pd.set_option("display.max_columns", None)

    return df


def pos_open(client, direction, coin, stop_loss=0, t_type="futures"):
    """
    Creating a position. Direction values: long_m, long_l, short_m, short_l, close_long, close_short, long_sl, short_sl, long_tp, short_tp.
    \nMax loss is 1% of balance.
    \nFor now only implemented for futures.
    :param client:
    :param direction:
    :param coin:
    :param stop_loss:
    :param t_type:
    :return:
    """
    if t_type == "spot":
        pass
    elif t_type == "futures":
        # Better leverage is 50 1.00%, 100 high 0.50%, 125 highest 0.40%.
        acc_info = client.futures_account()
        orderbook = client.futures_orderbook_ticker()
        leverage = 125

        # Get balance
        balance = 0
        for asset in acc_info['assets']:
            if asset['asset'] == 'USDT':
                balance = float(asset['walletBalance'])
        max_loss = int(balance / 100)  # 1% of balance
        #max_loss = 0.5  # TEST VALUE REMOVE AFTER TEST

        # Set isolated margin
        for position in acc_info['positions']:
            coin_symbol = position['symbol']
            if coin_symbol == coin:
                if position['isolated']:
                    client.futures_change_margin_type(symbol=coin, marginType="CROSSED")
                if position['leverage'] != leverage:
                    client.futures_change_leverage(symbol=coin, leverage=leverage)

        if direction == "long_m":
            if balance > 0:
                entry_price = 0
                for i in orderbook:
                    if i['symbol'] == coin:
                        entry_price = float(i['askPrice'])
                        entry_price = entry_price + 1
                entry_quantity = calculate_quantity(entry_price, stop_loss, max_loss_usdt=max_loss)
                # Market
                order = client.futures_create_order(
                    symbol=coin,
                    side="BUY",
                    type="MARKET",
                    quantity=entry_quantity,
                    reduceOnly=False,
                )
                print(order)
                time.sleep(3)
                pos_check = client.futures_position_information(symbol=coin)
                if pos_check[0]['positionAmt'] != entry_quantity:
                    print(f"Position opened with lower quantity: {pos_check[0]['positionAmt']}")
        elif direction == "long_l":
            if balance > 0:
                entry_price = 0

                for i in orderbook:
                    if i['symbol'] == coin:
                        entry_price = float(i['askPrice'])
                        entry_price = entry_price + 1
                        # print(i)
                entry_quantity = calculate_quantity(entry_price, stop_loss, max_loss_usdt=max_loss)
                # Limit
                order = client.futures_create_order(
                    symbol=coin,
                    side="BUY",
                    type="LIMIT",
                    timeInForce="IOC",
                    quantity=entry_quantity,
                    price=entry_price,
                    reduceOnly=False,
                )
                # print(order)
                time.sleep(3)
                pos_check = client.futures_position_information(symbol=coin)
                if pos_check[0]['positionAmt'] != entry_quantity:
                    print(f"Position opened with lower quantity: {pos_check[0]['positionAmt']}")
        elif direction == "short_m":
            if balance > 0:
                entry_price = 0
                for i in orderbook:
                    if i['symbol'] == coin:
                        entry_price = float(i['bidPrice'])
                        entry_price = entry_price - 1
                entry_quantity = calculate_quantity(stop_loss, entry_price, max_loss_usdt=max_loss)
                # Market
                order = client.futures_create_order(
                    symbol=coin,
                    side="SELL",
                    type="MARKET",
                    quantity=entry_quantity,
                    reduceOnly=False,
                )
                print(order)
                time.sleep(3)

                pos_check = client.futures_position_information(symbol=coin)
                if pos_check[0]['positionAmt'] != entry_quantity:
                    print(f"Position opened with lower quantity: {pos_check[0]['positionAmt']}")

                pass
        elif direction == "short_l":
            if balance > 0:
                entry_price = 0
                for i in orderbook:
                    if i['symbol'] == coin:
                        entry_price = float(i['bidPrice'])
                        entry_price = entry_price - 1
                entry_quantity = calculate_quantity(stop_loss, entry_price, max_loss_usdt=max_loss)
                # Limit
                order = client.futures_create_order(
                    symbol=coin,
                    side="SELL",
                    type="LIMIT",
                    timeInForce="IOC",
                    quantity=entry_quantity,
                    price=entry_price,
                    reduceOnly=False,
                )
                print(order)
                time.sleep(3)
                pos_check = client.futures_position_information(symbol=coin)
                if pos_check[0]['positionAmt'] != entry_quantity:
                    print(f"Position opened with lower quantity: {pos_check[0]['positionAmt']}")
        elif direction == "close_long":
            for position in acc_info['positions']:
                coin_symbol = position['symbol']
                if coin_symbol == coin:
                    pos_quantity = float(position['positionAmt'])
                    order = client.futures_create_order(
                        symbol=coin,
                        side="SELL",
                        type="MARKET",
                        quantity=pos_quantity,
                        reduceOnly=True,
                    )
                    print(order)
        elif direction == "close_short":
            for position in acc_info['positions']:
                coin_symbol = position['symbol']
                if coin_symbol == coin:
                    pos_quantity = float(position['positionAmt'])
                    order = client.futures_create_order(
                        symbol=coin,
                        side="BUY",
                        type="MARKET",
                        quantity=pos_quantity,
                        reduceOnly=True,
                    )
                    print(order)
        elif direction == "long_sl":
            # Cancel previous orders
            orders = client.futures_get_open_orders(symbol=coin)
            for order in orders:
                if order['type'] == "STOP_MARKET":
                    client.futures_cancel_order(symbol=coin, orderId=order['orderId'])
            # Create new stop loss order
            sl_order = client.futures_create_order(
                symbol=coin,
                side="SELL",
                type="STOP_MARKET",
                stopPrice=stop_loss,
                closePosition=True,
            )
            print(sl_order)
        elif direction == "short_sl":
            # Cancel previous orders
            orders = client.futures_get_open_orders(symbol=coin)
            for order in orders:
                if order['type'] == "STOP_MARKET":
                    client.futures_cancel_order(symbol=coin, orderId=order['orderId'])

            # Create new stop loss order
            sl_order = client.futures_create_order(
                symbol=coin,
                side="BUY",
                type="STOP_MARKET",
                stopPrice=stop_loss,
                closePosition=True,
            )
            print(sl_order)
        elif direction == "long_tp":
            # Cancel previous orders
            orders = client.futures_get_open_orders(symbol=coin)
            for order in orders:
                if order['type'] == "TAKE_PROFIT_MARKET":
                    client.futures_cancel_order(symbol=coin, orderId=order['orderId'])

            # Create new stop loss order
            sl_order = client.futures_create_order(
                symbol=coin,
                side="SELL",
                type="TAKE_PROFIT_MARKET",
                stopPrice=stop_loss,
                closePosition=True,
            )
            print(sl_order)
        elif direction == "short_tp":
            # Cancel previous orders
            orders = client.futures_get_open_orders(symbol=coin)
            for order in orders:
                if order['type'] == "TAKE_PROFIT_MARKET":
                    client.futures_cancel_order(symbol=coin, orderId=order['orderId'])

            # Create new stop loss order
            sl_order = client.futures_create_order(
                symbol=coin,
                side="BUY",
                type="TAKE_PROFIT_MARKET",
                stopPrice=stop_loss,
                closePosition=True,
            )
            print(sl_order)


def calculate_quantity(entry, stl, max_loss_usdt=1.0):
    """
    Calculates the quantity of the position based on the entry and stop loss price.
    :param entry:
    :param stl:
    :param max_loss_usdt:
    :return:
    """
    # max_loss_usdt = 100
    quantity = max_loss_usdt / (entry - stl)
    rounded_q = math.floor(quantity * 1000) / 1000
    print(rounded_q)
    return rounded_q
