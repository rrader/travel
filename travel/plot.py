import csv

import numpy as np
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt


def europe_map():
    fig = plt.figure(figsize=(10, 10))
    x1 = -25.
    x2 = 40.
    y1 = 30.
    y2 = 70.
    m = Basemap(resolution='i', projection='merc', llcrnrlat=y1, urcrnrlat=y2, llcrnrlon=x1, urcrnrlon=x2,
                lat_ts=(x1 + x2) / 2)
    m.drawcountries(linewidth=0.5)
    m.drawcoastlines(linewidth=0.5)
    m.drawparallels(np.arange(y1, y2, 15.), labels=[1, 0, 0, 1], color='black', dashes=[1, 0], labelstyle='+/-',
                    linewidth=0.2)  # draw parallels
    m.drawmeridians(np.arange(x1, x2, 15.), labels=[1, 0, 0, 1], color='black', dashes=[1, 0], labelstyle='+/-',
                    linewidth=0.2)  # draw meridians
    m.drawmapboundary(fill_color='#b2fffd')
    m.fillcontinents(color='#f6ffaa', lake_color='white')
    return m


if __name__ == '__main__':
    m = europe_map()

    routes = set()
    with open('ecolines.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat_1 = float(row['origin_lat'])
            lon_1 = float(row['origin_lon'])
            lat_2 = float(row['destination_lat'])
            lon_2 = float(row['destination_lon'])
            routes.add(((lon_1, lon_2), (lat_1, lat_2)))

    for route in routes:
        x, y = m(*route)
        color = np.random.rand(3, 1)
        color = np.append(color, [1.])
        m.plot(x, y, linewidth=0.5, color=color)

    plt.show()
