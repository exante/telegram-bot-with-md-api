from datetime import datetime

import requests


class FundamentalApi():
    def __init__(self):
        self.cache = {}

    def request(self, symbol):
        now = datetime.now()

        result = self.cache.get(symbol)

        # if data is already stored for current day
        if result and (now - result[1]).days < 1:
            return result[0]

        params = {
            "q": "select EarningsShare from yahoo.finance.quotes where symbol = '{}'".format(symbol),
            "env": "store://datatables.org/alltableswithkeys",
            "format": "json"
        }

        url = "https://query.yahooapis.com/v1/public/yql"
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()['query']['results']['quote']
        self.cache[symbol] = (data, now)

        return self.cache[symbol][0]
