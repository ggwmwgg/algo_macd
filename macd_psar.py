# Description: This file contains the main logic of the bot.
import os
import time
from binance import Client, ThreadedWebsocketManager
from utils.func import notifier, get_df, pos_open
import datetime
from dotenv import load_dotenv


class Position:
    def __init__(self):
        self.last_time = "none"
        self.state = "none"
        self.rule_first = False
        self.rule_second = False
        self.rule_second_time = 0
        self.is_active = False
        self.sl = 0
        self.tp = 0
        self.first_tp = False
        self.entry_price = 0
        self.entry_time = 0
        self.exit_price = 0
        self.exit_time = 0
        self.step = 0

    def reset(self):
        self.rule_first = False
        self.rule_second = False
        self.rule_second_time = 0
        self.is_active = False
        self.sl = 0
        self.tp = 0
        self.first_tp = False
        self.entry_price = 0
        self.entry_time = 0
        self.exit_price = 0
        self.exit_time = 0
        self.step = 0

    def change(self, state):
        self.state = state
        self.reset()


def checker(api_key, api_secret, coin_symbol, client):
    pos = Position()

    def process_message(message):
        nonlocal pos
        # Process the received message
        # Futures
        data = client.futures_klines(symbol=coin_symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=3000)
        # SPOT
        # data = client.get_klines(symbol=coin_symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=3000)
        df = get_df(data)

        # Assigning main variables
        curr_time = datetime.datetime.now()
        curr_time = curr_time.strftime("%d.%m.%y %H:%M")
        curr_bin_time = datetime.datetime.fromtimestamp(message["k"]["t"] / 1000)
        curr_bin_time = curr_bin_time.strftime("%d.%m.%y %H:%M")

        # EMA 50 and 200
        ema_50_curr = df["ema_50"].iloc[-1]
        ema_200_curr = df["ema_200"].iloc[-1]
        # PSAR
        psar_curr = df["psar"].iloc[-1]
        psar_prev = df["psar"].iloc[-2]
        psar_prev_2 = df["psar"].iloc[-3]
        psar_prev_3 = df["psar"].iloc[-4]
        psar_prev_4 = df["psar"].iloc[-5]

        # MACD
        macd_curr = df["macd"].iloc[-1]
        macd_prev = df["macd"].iloc[-2]
        macd_prev_2 = df["macd"].iloc[-3]


        # MACD Signal
        macd_signal_curr = df["macd_signal"].iloc[-1]
        macd_signal_prev = df["macd_signal"].iloc[-2]


        # MACD Diff
        macd_diff_curr = df["macd_diff"].iloc[-1]
        macd_diff_prev = df["macd_diff"].iloc[-2]

        # Close prices
        close_price_curr = df["Close"].iloc[-1]
        close_price_prev = df["Close"].iloc[-2]
        close_price_prev_2 = df["Close"].iloc[-3]
        close_price_prev_3 = df["Close"].iloc[-4]
        close_price_prev_4 = df["Close"].iloc[-5]

        # Update pos last time at first launch
        if pos.last_time == "none":
            pos.last_time = curr_time

        # ACTIVE POSITION TRAILING STOP IMPLEMENTATION
        if pos.is_active:
            if pos.state == "long":  # LONG
                if close_price_curr < pos.sl:
                    notifier(f"{curr_time} | Long SL hit: {pos.sl} | entry time: {pos.entry_time} | entry price: {pos.entry_price}")
                    pos.reset()
                elif close_price_curr > pos.tp:
                    if not pos.first_tp:
                        pos.sl = pos.tp
                        pos.tp = pos.tp + pos.step
                        pos.first_tp = True
                        time.sleep(5)
                    else:
                        new_sl = close_price_curr - pos.step
                        new_tp = close_price_curr + pos.step
                        if new_sl > pos.sl:
                            pos.sl = new_sl
                            pos_open(client, "long_sl", coin_symbol, pos.sl)  # Changes SL in the order
                            notifier(f"{curr_time} | Long SL moved to: {pos.sl}")

                        if new_tp > pos.tp:
                            pos.tp = new_tp
                            # pos_open(client, "long_tp", coin_symbol, pos.tp)  # Changes TP in the order
                            notifier(f"{curr_time} | Long TP moved to: {pos.tp}")

                        time.sleep(1)
            else:  # SHORT
                if close_price_curr > pos.sl:
                    notifier(f"{curr_time} | Short SL hit: {pos.sl} | entry time: {pos.entry_time} | entry price: {pos.entry_price}")
                    pos.reset()
                elif close_price_curr < pos.tp:
                    if not pos.first_tp:
                        pos.sl = pos.tp
                        pos.tp = pos.tp - pos.step
                        pos.first_tp = True
                        time.sleep(5)
                    else:
                        new_sl = close_price_curr + pos.step
                        new_tp = close_price_curr - pos.step
                        if new_sl < pos.sl:
                            pos.sl = new_sl
                            pos_open(client, "short_sl", coin_symbol, pos.sl)  # Changes SL in the order
                            notifier(f"{curr_time} | Short SL moved to: {pos.sl}")

                        if new_tp < pos.tp:
                            pos.tp = new_tp
                            # pos_open(client, "short_tp", coin_symbol, pos.tp)  # Changes TP in the order
                            notifier(f"{curr_time} | Short TP moved to: {pos.tp}")

                        time.sleep(1)
        # ENTRY POINT CHECKERS
        else:
            # --- REVERSAL CHECKERS --- #
            if ema_50_curr > ema_200_curr:  # Long Checker

                if pos.state == "none":  # if none set pos long
                    pos.state = "long"
                    print(f"{curr_time} | None to long")
                elif pos.state == "short":  # if long set pos long
                    print(f"{curr_time} | Short to long")
                    pos.change("long")

                if close_price_curr > ema_200_curr:  # if price above ema 200

                    if pos.rule_second:
                        # Last rule checker (Live)
                        if curr_bin_time == pos.rule_second_time:
                            if close_price_curr > psar_curr:
                                if macd_curr > macd_signal_curr or macd_curr > macd_prev_2:
                                    print(f"{curr_time} | Long last rule checker passed")

                                    # Position set
                                    if psar_curr < ema_200_curr:
                                        pos.sl = ema_200_curr
                                    else:
                                        pos.sl = psar_curr
                                    pos.step = close_price_curr - pos.sl
                                    pos.tp = close_price_curr + (pos.step * 2)
                                    pos.is_active = True
                                    pos.entry_price = close_price_curr
                                    pos.entry_time = curr_time
                                    pos_open(client, "long", coin_symbol, pos.entry_price, pos.sl)
                                    notifier(f"{curr_time} | Long pos opened | entry time: {pos.entry_time} | "
                                             f"entry price: {pos.entry_price}")
                                    time.sleep(60)
                        else:
                            print(f"{curr_time} | Long last rule checker failed")
                            pos.reset()
                            time.sleep(60)

                    elif pos.rule_first:
                        # Second rule checker (Every min)
                        if pos.last_time != curr_bin_time:
                            pos.last_time = curr_bin_time
                            if psar_prev < close_price_prev and psar_prev_2 > close_price_prev_2 and psar_prev_3 > close_price_prev_3:
                                print(f"{curr_time} | Long second rule checker passed")
                                pos.rule_first = False
                                pos.rule_second = True
                                pos.rule_second_time = curr_bin_time

                    else:
                        # First rule checker (Every min)
                        if pos.last_time != curr_bin_time:
                            pos.last_time = curr_bin_time
                            if psar_prev > close_price_prev and psar_prev_2 > close_price_prev_2 and psar_prev_3 < close_price_prev_3 and psar_prev_4 < close_price_prev_4:
                                pos.rule_first = True
                                print(f"{curr_time} | Long first rule checker passed")

            elif ema_50_curr < ema_200_curr:  # Short Checker
                if pos.state == "none":  # if none set pos short
                    pos.state = "short"
                    print(f"Curr time: {curr_time} | Last time: {pos.last_time} | Curr bin time: {curr_bin_time}")
                    print("None to short")
                elif pos.state == "long":  # if long set pos short
                    print(f"Curr time: {curr_time} | Last time: {pos.last_time} | Curr bin time: {curr_bin_time}")
                    print("Long to short")
                    #logger(curr_time, curr_bin_time, "Long to short reversal")
                    pos.change("short")

                if close_price_curr < ema_200_curr:  # if price below ema 200

                    if pos.rule_second:
                        # Last rule checker (Live)
                        if curr_bin_time == pos.rule_second_time:
                            if close_price_curr < psar_curr:
                                if macd_curr < macd_signal_curr or macd_curr < macd_prev_2:
                                    print(f"{curr_time} | Short last rule checker passed")

                                    # Position set
                                    if psar_curr > ema_200_curr:
                                        pos.sl = ema_200_curr
                                    else:
                                        pos.sl = psar_curr
                                    pos.step = pos.sl - close_price_curr
                                    pos.tp = close_price_curr - (pos.step * 2)
                                    pos.is_active = True
                                    pos.entry_price = close_price_curr
                                    pos.entry_time = curr_time
                                    pos_open(client, "short", coin_symbol, pos.entry_price, pos.sl)
                                    notifier(f"{curr_time} | Short pos opened | entry time: {pos.entry_time} | "
                                             f"entry price: {pos.entry_price}")

                                    time.sleep(60)
                        # If failed
                        else:
                            print(f"{curr_time} | Short last rule checker failed")
                            pos.reset()
                            time.sleep(60)

                    elif pos.rule_first:
                        # Second rule checker (Every min)
                        if pos.last_time != curr_bin_time:
                            pos.last_time = curr_bin_time
                            if psar_prev > close_price_prev and psar_prev_2 < close_price_prev_2 and psar_prev_3 < close_price_prev_3:
                                print(f"{curr_time} | Short second rule checker passed")
                                pos.rule_first = False
                                pos.rule_second = True
                                pos.rule_second_time = curr_bin_time
                    else:
                        # First rule checker (Every min)
                        if pos.last_time != curr_bin_time:
                            pos.last_time = curr_bin_time
                            if psar_prev < close_price_prev and psar_prev_2 < close_price_prev_2 and psar_prev_3 > close_price_prev_3 and psar_prev_4 > close_price_prev_4:
                                pos.rule_first = True
                                print(f"{curr_time} | Short first rule checker passed")

    # Create a websocket manager instance
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    # Start the websocket manager
    twm.start()
    # Futures
    # twm.start_kline_futures_socket(callback=process_message, symbol=coin_symbol, interval="1m")
    # Spot
    twm.start_kline_socket(callback=process_message, symbol=coin_symbol, interval="1m")

    twm.join()


if __name__ == "__main__":
    load_dotenv()
    api_key_main = os.getenv("binance_key")
    api_secret_main = os.getenv("binance_secret")
    coin_name = "BTCUSDT"
    client_main = Client(api_key_main, api_secret_main)
    checker(api_key_main, api_secret_main, coin_name, client_main)
