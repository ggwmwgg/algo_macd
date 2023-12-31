## Binance algo (EMA/MACD/PSAR) trading bot

### Description
Task was to create macd-psar strategy that works by rules defined in rules section, after that backtest this strategy.
- In ```/utils/func.py``` there is a function ```open_pos``` that can be used to open/close/modify long and short positions (already implemented for binance api).
- This script also includes some kind of trailing stop, which is activated after the initial tp is reached. Sl moved to initial tp lvl when the price goes 1 step above (long) or below (short) the initial tp lvl.

#### Rules:
- Checking for long if:
    - ema50 > ema200
    - close price > ema200
    - if price goes below ema50 skip those bars and continue when price returns to lvls above ema50
    - if last state was short then pos class change to long
    - rule first (checking every min):
      - psar_prev > close_prev
      - psar_prev2 > close_prev2
      - psar_prev3 < close_prev3
      - psar_prev4 < close_prev4
    - rule second (if first met):
      - psar_prev < close_prev
      - psar_prev2 > close_prev2
      - psar_prev3 > close_prev3
    - rule third (if first two met and works only on second rule bar):
      - close > psar_curr
      - macd > macd_signal
      - macd_curr > macd_prev
      - if all rules met open position
      - if not completed on exact bar reset pos class
- Checking for short if:
  - ema50 < ema200
  - close price > ema200
  - if price goes above ema50 skip those bars and continue when price returns to lvls below ema50
  - if last state was long then pos class change to short
  - rule first (checking every min):
    - psar_prev < close_prev
    - psar_prev2 < close_prev2
    - psar_prev3 > close_prev3
    - psar_prev4 > close_prev4
  - rule second (if first met):
    - psar_prev > close_prev
    - psar_prev2 < close_prev2
    - psar_prev3 < close_prev3
  - rule third (if first two met and works only on second rule bar):
    - close < psar_curr
    - macd < macd_signal
    - macd_curr < macd_prev
    - if all rules met open position
    - if not completed on exact bar reset pos class

    
#### Technologies used:
- *Python*
- *Binance API*
- *TA Lib Python*
- *Pandas*


#### Configuring:
- Install ```requirements.txt```.
- Change API key and secret for binance and telegram notifications in ```.env.dist```, rename it to ```.env```. 
- Run ```python macd_psar.py``` in ```/``` directory.
- For backtesting run ```python backtest_macd.py``` in ```/backtest``` directory.

#### Docker
- Using docker:
  - Build image: ```docker build -t macd:macd .```
  - Once image is built, run container: ```docker run -it --rm --name macd macd:macd``` where ```-it``` is for interactive mode, ```--rm``` is for removing container after it is stopped, ```--name``` is for naming container, ```macd:macd``` is image name:tag.
  - Stop container: ```docker stop macd```
- Using docker with .env:
  - Build image: ```docker build --env-file .env -t macd:macd .```
  - Once image is built, run container: ```docker run -it --rm --name macd --env-file .env macd:macd``` where ```--env-file``` is for passing .env file to container.
  - Stop container: ```docker stop macd```
- Using docker-compose (.env file is passed automatically):
  - Build image: ```docker-compose build``` (optional, second step will build image if it is not built yet)
  - Once image is built, run container: ```docker-compose up```. ```-d``` flag can be used to run container in background.
  - Stop container: ```docker-compose down```
- To enter container shell: ```docker exec -it macd bash``` where ```macd``` is container name.

#### Contributing
Pull requests are welcome. For major changes please open an issue first to discuss what you would like to change.