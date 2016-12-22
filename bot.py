# -*- coding:utf-8 -*-

import re
from sys import path
from decimal import Decimal

from configparser import ConfigParser

from telegram import ParseMode, Emoji
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from mdapi import DataStorage, MDApiConnector
from fundamental import FundamentalApi

import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# read config
config = ConfigParser()
config.read_file(open('config.ini'))

# create connectors to API
api = MDApiConnector(
    client_id=config['API']['client_id'],
    app_id=config['API']['app_id'],
    key=config['API']['shared_key']
)

fapi = FundamentalApi()

# Create telegram poller with token from settings
up = Updater(token=config['Telegram']['token'], workers=32)
dispatcher = up.dispatcher

# start stock storage
storage = DataStorage(api)
storage.start()


# Welcome message
def start(bot, update):
    msg = "Привет, {user_name}! \n\n" + \
    "Меня можно спросить об акциях фондового рынка США \n" + \
    "и я покажу их оценку P/E и текущую цену. \n\n" + \
    "Например: расскажи об AAPL или NVDA"

    # Send the message
    bot.send_message(chat_id=update.message.chat_id,
                     text=msg.format(
                         user_name=update.message.from_user.first_name,
                         bot_name=bot.name))

@run_async
def process(bot, update):
    if update.message.text.find("брокера посоветуешь") > 0:
        update.message.reply_text("Лично я рекомендую EXANTE!")
        return

    tickers = re.findall(r'[A-Z]{1,4}', update.message.text)

    msg = ""
    for ticker in tickers:
        stock = storage.stocks.get(ticker)
        if not stock: continue

        eps = fapi.request(ticker).get('EarningsShare')
        if not eps:
            logger.warning("Can't fetch EPS for {}".format(ticker))
            continue

        price = api.get_last_ohlc_bar(stock['id'])
        ratio = Decimal("%.4f" % price['close']) / Decimal(eps)

        msg += "{ticker} ({name}, {exchange}): EPS {eps}, P/E {ratio}, цена ${price} \n".format(
            ticker = ticker,
            name = stock['description'],
            exchange = stock['exchange'],
            ratio = "%.2f" % ratio,
            price = price['close'],
            eps = eps
        )

    if not msg:
        msg = "Не удалось получить данные по тикерам из запроса :(\n" +\
              "Попробуйте спросить о чем-то популярном, вроде GOOG или AAPL."

    bot.send_message(chat_id=update.message.chat_id, text=msg)


if __name__ == "__main__":
    # Add handlers to dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text, process))

    up.start_polling()
    up.idle()
