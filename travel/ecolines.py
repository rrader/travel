# encoding: utf-8
import json
from collections import OrderedDict

import dateutil.parser
import scrapy
from datetime import datetime

from travel.utils import STATES

UAH = 31

YEAR = 2018
MONTH = 1

ORIGIN_URL = 'https://booking.ecolines.net/ajax/origins?locale=en'
DEST_URL = 'https://booking.ecolines.net/ajax/destinations?locale=en&origin={orig}'
DATES_URL = 'https://booking.ecolines.net/ajax/dates?origin={orig}&destination={dest}&year={year}&month={month}'
BOOKING = (
    'https://booking.ecolines.net/search/result?locale=en&currency={currency}&returnOrigin={dest}&'
    'returnDestination={orig}&returning=0&type=0&outwardOrigin={orig}&outwardDestination={dest}&'
    'outwardDate={date}&adults=1&children=0&teens=0&seniors=0'
)

ORIGIN = '#ecolines-booking-form-origin option'
VALUE = 'option ::attr(value)'
PRICE = '.journey .btn-primary span:not(.btn-label) ::text'
DEPARTURE_TIME = '.journey .origin .time ::text'
DEPARTURE_DATE = '.journey .origin .date ::text'
DESTINATION_TIME = '.journey .destination .time ::text'
DESTINATION_DATE = '.journey .destination .date ::text'


class EcolinesSpider(scrapy.Spider):
    name = 'ecolines'
    allowed_domains = ['ecolines.net']
    start_urls = [ORIGIN_URL]

    def parse(self, response):
        jsonresponse = json.loads(response.body_as_unicode())
        for item in jsonresponse:
            if item['state'] not in STATES:
                continue
            yield scrapy.Request(
                DEST_URL.format(
                    orig=item['id'],
                ),
                callback=self.destination,
                meta={
                    'origin_id': item['id'],
                    'origin_title': item['title'],
                    'origin_state': item['state'],
                    'origin_lat': item['location']['latitude'],
                    'origin_lon': item['location']['longitude'],
                }
            )

    def destination(self, response):
        origin_id = response.meta['origin_id']
        jsonresponse = json.loads(response.body_as_unicode())
        for item in jsonresponse:
            meta = response.meta.copy()
            meta.update({
                'destination_id': item['id'],
                'destination_title': item['title'],
                'destination_state': item['state'],
                'destination_lat': item['location']['latitude'],
                'destination_lon': item['location']['longitude'],
            })
            if item['state'] not in STATES:
                continue
            yield scrapy.Request(
                DATES_URL.format(
                    orig=origin_id,
                    dest=item['id'],
                    year=str(YEAR),
                    month=str(MONTH),
                ),
                callback=self.dates,
                meta=meta,
            )

    def dates(self, response):
        origin_id = response.meta['origin_id']
        destination_id = response.meta['destination_id']
        jsonresponse = json.loads(response.body_as_unicode())
        currency = UAH
        for date in jsonresponse:
            meta = response.meta.copy()
            meta.update({
                'currency': currency,
                'date': date,
            })
            dt = datetime.fromtimestamp(date // 1000)
            yield scrapy.Request(
                BOOKING.format(
                    orig=origin_id,
                    dest=destination_id,
                    currency=currency,
                    date=dt.strftime('%Y-%m-%d'),
                ),
                callback=self.booking,
                meta=meta,
            )

    def booking(self, response):
        data = response.css(PRICE).extract()
        if data:
            price = data[0]
            departure_time = response.css(DEPARTURE_TIME).extract()[0]
            departure_date = response.css(DEPARTURE_DATE).extract()[0]
            arrival_time = response.css(DESTINATION_TIME).extract()[0]
            arrival_date = response.css(DESTINATION_DATE).extract()[0]

            departure_dt = dateutil.parser.parse('{} {}'.format(departure_date, departure_time))
            arrival_dt = dateutil.parser.parse('{} {}'.format(arrival_date, arrival_time))

            meta = response.meta.copy()
            meta.update({
                'price': price,
                'departureDate': departure_dt,
                'arrivalDate': arrival_dt,
                'currencyCode': meta['currency'],
            })

            yield OrderedDict([
                (key, meta[key])
                for key in [
                    'origin_id', 'origin_title', 'origin_state', 'origin_lat', 'origin_lon',
                    'destination_id', 'destination_title', 'destination_state',
                    'destination_lat', 'destination_lon',
                    'departureDate', 'arrivalDate',
                    'price', 'currencyCode',
                ]
            ])
