import csv
from datetime import timedelta, datetime

import dateutil.parser
import matplotlib.pyplot as plt

from travel.plot import europe_map
from travel.utils import coord_distance

KYIV = (50.5, 30.5)
TARTU = (58.4, 26.7)
BERLIN = (52.5, 13.5)
PARIS = (49.4544, 2.11278)
RIGA = (56.9236, 23.9711)


class Graph:
    def __init__(self):
        self.nodes = []
        self.connections = []
        self.coords_cache = {}

    def closest(self, lat, lon, maximum=50):
        """
        Returns closest Node to lat, lon coordinates
        :param lat: latitude
        :param lon: longitude
        :param maximum: max distance in kilometers
        :return: closest Node or None if distance exceeds maximum
        """
        cached_node = self.coords_cache.get((lat, lon))
        if cached_node:
            return cached_node

        distances = [
            (node.distance(lat, lon), node)
            for node in self.nodes
        ]
        if distances:
            distance, node = min(distances)
            if distance <= maximum:
                self.coords_cache[(lat, lon)] = node
                return node

    def add(self, lat, lon, city):
        node = self.closest(lat, lon)
        if not node:
            node = Node(lat, lon, city)
            self.nodes.append(node)
        return node

    def edge(self, n1, n2, **meta):
        c = Connection(n1, n2, **meta)
        n1.edge(c)
        self.connections.append(c)

    def path(self, n1, n2, max_price=1000, max_hops=2, path=None):
        if path is None:
            path = {
                'path': [],
                'price': 0,
                'hops': 0,
            }
        if path['price'] > max_price:
            return
        if path['path'] and path['path'][-1].contains(n2):
            return path
        if path['hops'] + 1 > max_hops:
            return
        print(path)
        pathes = []
        for c in n1.connections:
            if c.departure < datetime(2018, 1, 1) or c.departure > datetime(2018, 2, 20):
                continue
            if path['path']:
                prev_conn = path['path'][-1]
                if c.departure - prev_conn.arrival <= timedelta(days=2):
                    continue

            c_to = c.pair(n1)
            next_path = self.path(
                c_to, n2, max_price, max_hops,
                {
                    'path': path['path'] + [c],
                    'price': path['price'] + c.price,
                    'hops': path['hops'] + 1,
                }
            )
            if next_path:
                pathes.append(next_path)
        pathes = sorted(pathes, key=lambda p: p['price'])
        if pathes:
            return pathes[0]


class Node:
    def __init__(self, lat, lon, city):
        self.city = city
        self.lon = lon
        self.lat = lat
        self.connections = []

    @property
    def point(self):
        return self.lat, self.lon

    def distance(self, lat, lon):
        point = (lat, lon)
        return coord_distance(self.point, point)

    def edge(self, c):
        self.connections.append(c)

    def __repr__(self):
        return 'Node({})'.format(self.city)


class Connection:
    def __init__(self, n1, n2, price, name, departure, arrival):
        self.arrival = arrival
        self.departure = departure
        self.name = name
        self.n1 = n1
        self.n2 = n2
        self.price = price

    def pair(self, n):
        if n == self.n1:
            return self.n2
        else:
            return self.n1

    def contains(self, n):
        return self.n1 == n or self.n2 == n

    def __repr__(self):
        return 'Connection({}, {})'.format(self.n1, self.n2)


def price_in_eur(price, currency):
    if currency in ['31', 'UAH']:
        return price * 0.029678566
    elif currency == 'EUR':
        return price
    elif currency == 'PLN':
        return price * 0.239407099
    else:
        raise ValueError(currency)


def process_routes(f, name):
    reader = csv.DictReader(f)
    for row in reader:
        lat_1 = float(row['origin_lat'])
        lon_1 = float(row['origin_lon'])
        lat_2 = float(row['destination_lat'])
        lon_2 = float(row['destination_lon'])
        price = float(row['price'])
        currency = row['currencyCode']
        eur = price_in_eur(price, currency)
        node_1 = g.add(lat_1, lon_1, row['origin_title'])
        node_2 = g.add(lat_2, lon_2, row['destination_title'])
        departure = dateutil.parser.parse(row['departureDate'])
        if row.get('arrivalDate'):
            arrival = dateutil.parser.parse(row['arrivalDate'])
        else:
            arrival = departure + timedelta(hours=3)
        g.edge(node_1, node_2, price=eur, name=name, departure=departure.replace(tzinfo=None), arrival=arrival.replace(tzinfo=None))


def plot_graph(g):
    m = europe_map()
    lons = [n.lon for n in g.nodes]
    lats = [n.lat for n in g.nodes]
    x, y = m(lons, lats)
    m.scatter(x, y, 10, marker='o', color='red', zorder=4)
    for c in g.connections:
        lons = (c.n1.lon, c.n2.lon)
        lats = (c.n1.lat, c.n2.lat)
        x, y = m(lons, lats)
        color = 'orange'
        if c.name == 'wizzair':
            color = 'purple'
        elif c.name == 'ryanair':
            color = 'blue'
        m.plot(x, y, linewidth=0.2, color=color, zorder=3)
    plt.show()


def plot_route(route):
    m = europe_map()
    for c in route['path']:
        lons = (c.n1.lon, c.n2.lon)
        lats = (c.n1.lat, c.n2.lat)
        x, y = m(lons, lats)
        color = 'orange'
        if c.name == 'wizzair':
            color = 'purple'
        elif c.name == 'ryanair':
            color = 'blue'
        m.plot(
            x, y, linewidth=2, color=color, zorder=3,
        )
        plt.text(
            x[0] + (x[1] - x[0]) / 2,
            y[0] + (y[1] - y[0]) / 2,
            s='{:,.2f} EUR'.format(c.price),
            fontsize=10, fontweight='bold',
        )
        plt.text(
            x[0], y[0],
            s=c.n1.city,
            fontsize=10, fontweight='bold',
            color='blue'
        )
        plt.text(
            x[1], y[1],
            s=c.n2.city,
            fontsize=10, fontweight='bold',
            color='blue'
        )
    plt.show()


if __name__ == '__main__':
    g = Graph()

    print('Loading connections...')

    print('  => WizzAir')
    with open('wizzair.csv') as f:
        process_routes(f, name='wizzair')
    print('  => RyanAir')
    with open('ryanair.csv') as f:
        process_routes(f, name='ryanair')
    print('  => EcoLines')
    with open('ecolines.csv') as f:
        process_routes(f, 'ecolines')

    print('Looking for origin and destination points...')
    city1 = g.closest(*TARTU)
    print(city1.city)
    city2 = g.closest(*PARIS)
    print(city2.city)

    print('Looking up the best route...')
    path = g.path(city1, city2)

    plot_route(path)
