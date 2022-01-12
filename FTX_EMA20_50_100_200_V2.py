# This backtests the EMA20/50/100/200 strategy and calculates the evolution of the price relatively to a virtual long position

import glob
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import ftx
import pandas
import pandas as pd
import requests
import ta.trend


def log_to_results(str_to_log):
    fr = open("results.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_errors(str_to_log):
    fr = open("errors.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_trades(str_to_log):
    fr = open("trades.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_evol(str_to_log):
    fr = open("evol.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_debug(str_to_log):
    fr = open("debug.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_file(str_file, str_to_log):
    fr = open(str_file, "a")
    fr.write(str_to_log + "\n")
    fr.close()


ftx_client = ftx.FtxClient(
    api_key='',
    api_secret='',
    subaccount_name=''
)

# result = client.get_balances()
# print(result)

if os.path.exists("results.txt"):
    os.remove("results.txt")

if os.path.exists("errors.txt"):
    os.remove("errors.txt")

if os.path.exists("trades.txt"):
    os.remove("trades.txt")

if os.path.exists("evol.txt"):
    os.remove("evol.txt")

for fg in glob.glob("CS_*.txt"):
    os.remove(fg)

for fg in glob.glob("scan_*.txt"):
    os.remove(fg)

for fg in glob.glob("debug.txt"):
    os.remove(fg)

for fg in glob.glob("data_history_*.db"):
    os.remove(fg)

stop_thread = False

log_data_history_to_files = True


def execute_code(symbol):
    global log_data_history_to_files
    # print("scan one : " + symbol)

    resolution = 60 * 60  # set the resolution of one japanese candlestick here
    timeframe = "H1"  # used for inserting into SQLITE database

    symbol_filename = "scan_" + str.replace(symbol, "-", "_").replace("/", "_") + ".txt"

    # resolution = 60 * 1  # set the resolution of one japanese candlestick here
    # timeframe = "M1"  # used for inserting into SQLITE database
    # max_block_of_5000_download = 1  # set to -1 for unlimited blocks (all data history)

    unixtime_endtime = time.time()
    converted_endtime = datetime.utcfromtimestamp(unixtime_endtime)
    # print("current unix time = " + str(unixtime_endtime))
    # print("converted_endtime = " + str(converted_endtime))
    tosubtract = resolution * 5000  # 60 * 60 * 1 * 5000
    # print("to substract in seconds = " + str(tosubtract))
    newunixtime_starttime = unixtime_endtime - tosubtract
    converted_starttime = datetime.utcfromtimestamp(newunixtime_starttime)
    # print("new unix time = " + str(newunixtime_starttime))
    # print("new converted_starttime = " + str(converted_starttime))

    data = []

    end_of_data_reached = False

    max_block_of_5000_download = 1
    current_block_of_5000_download = 0
    max_block_of_5000_download_reached = False

    while not end_of_data_reached and not max_block_of_5000_download_reached:

        downloaded_data = ftx_client.get_historical_data(
            market_name=symbol,
            resolution=resolution,
            limit=1000000,
            start_time=newunixtime_starttime,
            end_time=unixtime_endtime)

        converted_endtime = datetime.utcfromtimestamp(unixtime_endtime)
        converted_starttime = datetime.utcfromtimestamp(newunixtime_starttime)

        print(symbol + " : downloaded_data size = " + str(len(downloaded_data)) + " from " + str(converted_starttime) + " to " + str(converted_endtime))
        data.extend(downloaded_data)

        unixtime_endtime = newunixtime_starttime
        newunixtime_starttime = newunixtime_starttime - tosubtract

        if len(downloaded_data) == 0:
            print(symbol + " : end of data from server reached")
            end_of_data_reached = True

        if max_block_of_5000_download != -1:
            current_block_of_5000_download += 1
            if current_block_of_5000_download >= max_block_of_5000_download:
                print(symbol + " : max number of block of 5000 reached")
                max_block_of_5000_download_reached = True

    df = pandas.DataFrame(data)
    # df = df.reindex(index=df.index[::-1])
    df['EMA20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['EMA50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['EMA100'] = ta.trend.EMAIndicator(close=df['close'], window=100).ema_indicator()
    df['EMA200'] = ta.trend.EMAIndicator(close=df['close'], window=200).ema_indicator()
    # df = df.iloc[::-1]
    # for oneline in df['EMA200']:
    #     print oneline['']

    is_above_all = False
    status = ""
    previous_is_above = False
    entry_price = 0

    for i in range(0, 500):
        startTime = df['startTime'].iloc[i]
        openp = df['open'].iloc[i]
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        close = df['close'].iloc[i]
        ema20 = df['EMA20'].iloc[i]
        ema50 = df['EMA50'].iloc[i]
        ema100 = df['EMA100'].iloc[i]
        ema200 = df['EMA200'].iloc[i]

        if df['EMA20'].iloc[i] > df['EMA50'].iloc[i] and df['EMA20'].iloc[i] > df['EMA100'].iloc[i] and df['EMA20'].iloc[i] > df['EMA200'].iloc[i]:
            is_above_all = True
        else:
            is_above_all = False

        if df['EMA20'].iloc[i - 1] > df['EMA50'].iloc[i - 1] and df['EMA20'].iloc[i - 1] > df['EMA100'].iloc[i - 1] and df['EMA20'].iloc[i - 1] > df['EMA200'].iloc[i - 1]:
            previous_is_above = True
        else:
            previous_is_above = False

        status = ""
        if is_above_all:
            status += " is above all ; "
        if previous_is_above:
            status += " previous is above "

        if not previous_is_above and is_above_all:
            status += " ; should enter long here "
            entry_price = close

        if previous_is_above and is_above_all:
            evol = close - df['close'].iloc[i - 1]
            evol_percent = ((high - entry_price) / entry_price) * 100
            status += " ; evol close/previousclose = " + str(evol) + " ; evol high/entryprice = " + str(round(evol_percent, 4)) + "%"

        print(symbol, startTime, openp, high, low, close, status)
        log_to_results(symbol + " " + startTime + str(openp) + " " + str(high) + " " + str(low) + " " + str(close) + " " + status)

        previous_close = close

        # if df['open'].iloc[i] < df['EMA20'].iloc[i]:
        #     if df['close'].iloc[i] > df['EMA20'].iloc[i]:
        #         print(symbol, str(startTime), openp, close, ema20)

    log_to_results(symbol + " end of processing")


maxthreads = 5
threadLimiter = threading.BoundedSemaphore(maxthreads)


def scan_one(symbol):
    threadLimiter.acquire()
    try:
        execute_code(symbol)
    finally:
        threadLimiter.release()


threads = []


def main_thread(name):
    global ftx_client, list_results, results_count, num_req, stop_thread

    print(str(datetime.now()) + " All threads starting.")
    log_to_results(str(datetime.now()) + " All threads starting.")

    markets = requests.get('https://ftx.com/api/markets').json()
    df = pd.DataFrame(markets['result'])
    df.set_index('name')

    for index, row in df.iterrows():
        symbol = row['name']
        # symbol_type = row['type']
        vol = row['volumeUsd24h']
        change24h = row['change24h']
        change1h = row['change1h']

        # if not change1h > 0:
        #     continue

        # filter for specific symbols here
        if not symbol == "XRP/USD":
            continue

        # if not symbol.endswith("/USD"):
        #     continue

        try:
            t = threading.Thread(target=scan_one, args=(symbol,))
            threads.append(t)
            t.start()
        except requests.exceptions.ConnectionError:
            continue

    for tt in threads:
        tt.join()

    print(str(datetime.now()) + " All threads finished.")
    log_to_results(str(datetime.now()) + " All threads finished.")

    time.sleep(1)

    stop_thread = True


x = threading.Thread(target=main_thread, args=(1,))
x.start()
