# https://gist.github.com/vool/bbd64eeee313d27a82ab
# https://api.ryanair.com/farefinder/3/oneWayFares?&departureAirportIataCode=RIX&language=en&limit=16&market=en-gb&offset=0&outboundDepartureDateFrom=2018-01-11&outboundDepartureDateTo=2018-01-28&priceValueTo=150
# https://api.ryanair.com/aggregate/3/common?embedded=airports,countries,cities,regions,nearbyAirports,defaultAirport&market=en-gb


# encoding: utf-8
import json
from collections import OrderedDict

import iso8601
import scrapy
from datetime import datetime

from travel.utils import STATES

YEAR = 2018
MONTH = 1
DAY_FROM = 1
DAY_TO = 31

AIRPORTS_URL = 'https://api.ryanair.com/aggregate/3/common?embedded=airports&market=en-gb'
ONEWAY_FARE_URL = 'https://api.ryanair.com/farefinder/3/oneWayFares?&departureAirportIataCode={airport}&language=en&limit=16&market=en-gb&offset=0&outboundDepartureDateFrom={year}-{month}-{day_from}&outboundDepartureDateTo={year}-{month}-{day_to}&priceValueTo=300'


class RyanairSpider(scrapy.Spider):
    name = 'ryanair'
    allowed_domains = ['api.ryanair.com']
    start_urls = [AIRPORTS_URL]

    def parse(self, response):
        jsonresponse = json.loads(response.body_as_unicode())
        airports = self._airport_mapping(jsonresponse)
        for item in jsonresponse['airports']:
            if item['countryCode'].upper() not in STATES:
                continue
            yield scrapy.Request(
                ONEWAY_FARE_URL.format(
                    airport=item['iataCode'],
                    year=str(YEAR),
                    month=str(MONTH) if MONTH > 9 else '0' + str(MONTH),
                    day_from=str(DAY_FROM) if DAY_FROM > 9 else '0' + str(DAY_FROM),
                    day_to=str(DAY_TO) if DAY_TO > 9 else '0' + str(DAY_TO),
                ),
                callback=self.fares,
                meta={
                    'origin_airport': item['iataCode'],
                    'origin_title': item['name'],
                    'origin_state': item['countryCode'].upper(),
                    'origin_lat': item['coordinates']['latitude'],
                    'origin_lon': item['coordinates']['longitude'],
                    'airports': airports,
                }
            )

    def _airport_mapping(self, jsonresponse):
        return {
            ap['iataCode']: ap
            for ap in jsonresponse['airports']
        }

    def fares(self, response):
        jsonresponse = json.loads(response.body_as_unicode())
        for item in jsonresponse['fares']:
            if 'outbound' not in item:
                continue
            item = item['outbound']
            meta = response.meta.copy()
            airport = response.meta['airports'][item['arrivalAirport']['iataCode']]
            meta.update({
                'destination_airport': item['arrivalAirport']['iataCode'],
                'destination_title': item['arrivalAirport']['name'],
                'destination_state': airport['countryCode'].upper(),
                'destination_lat': airport['coordinates']['latitude'],
                'destination_lon': airport['coordinates']['longitude'],
                'price': item['price']['value'],
                'currencyCode': item['price']['currencyCode'],
                'departureDate': iso8601.parse_date(item['departureDate']),
                'arrivalDate': iso8601.parse_date(item['arrivalDate']),
            })

            yield OrderedDict([
                (key, meta[key])
                for key in [
                    'origin_airport', 'origin_title', 'origin_state', 'origin_lat', 'origin_lon',
                    'destination_airport', 'destination_title', 'destination_state',
                    'destination_lat', 'destination_lon',
                    'departureDate', 'arrivalDate',
                    'price', 'currencyCode',
                ]
            ])
