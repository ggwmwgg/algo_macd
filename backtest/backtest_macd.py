from backtesting.lib import TrailingStrategy
from binance import Client
from backtesting import Backtest
from utils.func import get_df


def get_data(key, secret):
    client = Client(key, secret)
    # SPOT
    # data = client.get_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_1MINUTE, limit=1000)
    # FUTURES
    # data = client.futures_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_1MINUTE, limit=1000)
    # Historical
    data = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1MINUTE, "5 day ago UTC")
    return data


class MacdStrat(TrailingStrategy):
    n1 = 50
    n2 = 200
    direction = "long"
    first_rule = False
    tp = 0
    sl = 0
    step = 0

    def init(self):
        close = self.data.Close
        # self.sma1 = self.I(EMA, close, self.n1)
        # self.sma2 = self.I(EMA, close, self.n2)
        # Obtaining the data from custom columns:
        # self.sma1 = self.data['custom1']
        # self.sma2 = self.data['custom2']

    def next(self):
        psar = self.data.psar
        close = self.data.Close
        ema_50 = self.data.ema_50
        ema_200 = self.data.ema_200
        macd = self.data.macd
        macd_signal = self.data.macd_signal
        open_price = self.data.Open
        if self.position:
            if self.position.is_long:
                if self.data.Close[-1] > self.tp:
                    new_sl = self.tp
                    new_tp = self.tp + self.step
                    if new_sl > self.sl:
                        self.sl = new_sl
                    if new_tp > self.tp:
                        self.tp = new_tp

                if self.data.Close[-1] < self.sl:
                    self.position.close()
                    print(f"Long closed by sl: {self.sl} | time: {self.data.index[-1]}")
            elif self.position.is_short:
                if self.data.Close[-1] < self.tp:
                    new_sl = self.tp
                    new_tp = self.tp - self.step
                    if new_sl < self.sl:
                        self.sl = new_sl
                    if new_tp < self.tp:
                        self.tp = new_tp

                if self.data.Close[-1] > self.sl:
                    self.position.close()
                    print(f"Short closed by sl: {self.sl} | time: {self.data.index[-1]}")
        else:
            if ema_50[-1] < ema_200[-1]:
                if self.direction == "long":
                    self.first_rule = False
                self.direction = "short"
            elif ema_50[-1] > ema_200[-1]:
                if self.direction == "short":
                    self.first_rule = False
                self.direction = "long"

            if self.data.Open[-1] < ema_50[-1] and psar[-2] < self.data.Open[-2] and psar[-1] > self.data.Open[-1] and self.direction == "short" and self.first_rule:
                if macd_signal[-1] > macd[-1]:
                    print(f"SELL {self.data.Open[-1]} | time: {self.data.index[-1]}")
                    self.sell()
                    self.step = psar[-1] - self.data.Open[-1]
                    self.sl = self.data.Open[-1] + self.step
                    self.tp = self.data.Open[-1] - (self.step * 3)
                # self.sell()
                self.first_rule = False
            elif self.data.Open[-1] > ema_50[-1] and psar[-2] > self.data.Open[-2] and psar[-1] < self.data.Open[-1] and self.direction == "long" and self.first_rule:
                if macd_signal[-1] < macd[-1]:
                    print(f"BUY {self.data.Open[-1]} | time: {self.data.index[-1]}")
                    self.buy()
                    self.step = self.data.Open[-1] - psar[-1]
                    self.sl = self.data.Open[-1] - self.step
                    self.tp = self.data.Open[-1] + (self.step * 3)
                self.first_rule = False

            if self.data.Open[-1] < ema_50[-1] and psar[-2] > self.data.Open[-2] and psar[-1] < self.data.Open[-1] and self.direction == "short":
                self.first_rule = True
            elif self.data.Open[-1] > ema_50[-1] and psar[-2] < self.data.Open[-2] and psar[-1] > self.data.Open[-1] and self.direction == "long":
                self.first_rule = True


if __name__ == "__main__":
    api_key_main = "Rsxzm6DPiZYu3VnHtUpOfzxgy2wndHMeFW24tOSd8e0kkn1bAmrwWyDj5ilmLdDK"
    api_secret_main = "YdqPvFWK4V4dzoa27elbQGEZsJcP1LHCL8IocUd93bX9kMdia6IKkYSippot66SZ"
    data = get_data(api_key_main, api_secret_main)
    dataframe = get_df(data)
    bt = Backtest(dataframe, MacdStrat, cash=100000, commission=.0008, exclusive_orders=True)
    output = bt.run()
    print(output)
    bt.plot()


