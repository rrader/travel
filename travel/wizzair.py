# encoding: utf-8

# https://stackoverflow.com/questions/41771502/wizzair-scraping
# https://be.wizzair.com/7.7.5/Api/search/flightDates?departureStation=SZY&arrivalStation=LTN&from=2018-01-08&to=2018-03-11
# https://be.wizzair.com/7.7.5/Api/search/timetable
# flightList	[…]
# 0	{…}
# departureStation	SZY
# arrivalStation	LTN
# from	2018-01-08
# to	2018-02-04
# 1	{…}
# departureStation	LTN
# arrivalStation	SZY
# from	2018-02-26
# to	2018-04-01
# priceType	regular
# adultCount	1
# childCount	0
# infantCount	0

# https://be.wizzair.com/7.7.5/Api/asset/map?languageCode=en-gb

import json

import scrapy
from datetime import datetime

from scrapy import Request

from travel.utils import STATES

YEAR = 2018
MONTH = 1
DAY_FROM = 1
DAY_TO = 31

AIRPORTS_URL = 'https://be.wizzair.com/7.7.5/Api/asset/map?languageCode=en-gb'
TIMETABLE = 'https://be.wizzair.com/7.7.5/Api/search/timetable'


class WizzairSpider(scrapy.Spider):
    name = 'wizzair'
    allowed_domains = ['be.wizzair.com']
    start_urls = [AIRPORTS_URL]

    def parse(self, response):
        jsonresponse = json.loads(response.body_as_unicode())
        for origin in jsonresponse['cities']:
            if origin['countryCode'].upper() not in STATES:
                continue

            for destination in origin['connections']:
                yield scrapy.Request(
                    TIMETABLE,
                    method='POST',
                    body=json.dumps({
                        "flightList": [
                            {
                                "departureStation": origin['iata'],
                                "arrivalStation": destination['iata'],
                                "from": "2018-01-08",
                                "to": "2018-02-04"
                            },
                            {
                                "departureStation": destination['iata'],
                                "arrivalStation": origin['iata'],
                                "from": "2018-01-08",
                                "to": "2018-02-04"
                            }
                        ],
                        "priceType": "regular",
                        "adultCount": 1,
                        "childCount": 0,
                        "infantCount": 0,
                    }),
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0',
                        'Referer': 'https://wizzair.com/en-gb/flights/timetable/tallinn/london-luton',
                    },
                    callback=self.timetable,
                    meta={
                        'origin_airport': origin['iata'],
                        'origin_title': origin['shortName'],
                        'origin_state': origin['countryCode'],
                        'origin_lat': origin['latitude'],
                        'origin_lon': origin['longitude'],
                        'destination_airport': destination['iata'],
                        'cookiejar': None,
                    }
                )

    def timetable(self, response):
        jsonresponse = json.loads(response.body_as_unicode())
        for item in jsonresponse['outboundFlights']:
            if not item.get('price'):
                continue
            data = response.meta.copy()
            data.update({
                'departureDate': item['departureDate'],
                'price': item['price']['amount'],
                'currencyCode': item['price']['currencyCode'],
                'classOfService': item['classOfService'],
            })
            yield data
