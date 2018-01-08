# encoding: utf-8
import json

import scrapy
from datetime import datetime

from travel.utils import STATES

UAH = 31

YEAR = 2018
MONTH = 1

ORIGIN_URL = 'https://booking.ecolines.net/ajax/origins?locale=ru'
DEST_URL = 'https://booking.ecolines.net/ajax/destinations?locale=ru&origin={orig}'
DATES_URL = 'https://booking.ecolines.net/ajax/dates?origin={orig}&destination={dest}&year={year}&month={month}'
BOOKING = 'https://booking.ecolines.net/search/result?locale=ru&currency={currency}&returnOrigin={dest}&returnDestination={orig}&returning=0&type=0&outwardOrigin={orig}&outwardDestination={dest}&outwardDate={date}&adults=1&children=0&teens=0&seniors=0'

ORIGIN = '#ecolines-booking-form-origin option'
VALUE = 'option ::attr(value)'
PRICE = '.journey .btn-primary span:not(.btn-label) ::text'


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

            meta = response.meta.copy()
            meta.update({
                'price': price,
            })

            yield meta
