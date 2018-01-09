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
from collections import OrderedDict

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

    def start_requests(self):
        return [
            scrapy.Request(
                AIRPORTS_URL,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0',
                    'Referer': 'https://wizzair.com',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Upgrade-Insecure-Requests': '1',
                },
                callback=self.parse,
                meta={
                    'cookiejar': None,
                }
            )
        ]

    def parse(self, response):
        jsonresponse = json.loads(response.body_as_unicode())
        airports = self._airport_mapping(jsonresponse)
        for origin in jsonresponse['cities']:
            if origin['countryCode'].upper() not in STATES:
                continue

            for destination in origin['connections']:
                dest_iata = destination['iata']
                yield scrapy.Request(
                    TIMETABLE,
                    method='POST',
                    body=json.dumps({
                        "flightList": [
                            {
                                "departureStation": origin['iata'],
                                "arrivalStation": destination['iata'],
                                "from": "2018-01-09",
                                "to": "2018-02-04",
                            },
                            {
                                "departureStation": destination['iata'],
                                "arrivalStation": origin['iata'],
                                "from": "2018-01-09",
                                "to": "2018-02-04",
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
                        'destination_title': airports[dest_iata]['shortName'],
                        'destination_state': airports[dest_iata]['countryCode'],
                        'destination_lat': airports[dest_iata]['latitude'],
                        'destination_lon': airports[dest_iata]['longitude'],
                        'cookiejar': None,
                        'airports': airports,
                    }
                )

    def _airport_mapping(self, jsonresponse):
        return {
            city['iata']: city
            for city in jsonresponse['cities']
        }

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

            yield OrderedDict([
                (key, data[key])
                for key in [
                    'origin_airport', 'origin_title', 'origin_state', 'origin_lat', 'origin_lon',
                    'destination_airport', 'destination_title', 'destination_state',
                    'destination_lat', 'destination_lon',
                    'departureDate',  # 'arrivalDate',
                    'price', 'currencyCode',
                ]
            ])
