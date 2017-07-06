"""
Depends on filter_weather_data.filters.preparation.average_husconet_temperature
"""
import logging
import os

import pandas
from matplotlib import pyplot
import seaborn

from gather_weather_data.husconet import HUSCONET_STATIONS
from filter_weather_data.filters import PROCESSED_DATA_DIR

seaborn.set(style='ticks')


def plot_stations(start, end):
    """
    Plots all HUSCONET weather stations in the background.
    """
    plot_df = pandas.DataFrame()

    for husconet_station in HUSCONET_STATIONS[start:end]:
        csv_file = os.path.join(PROCESSED_DATA_DIR, "husconet", husconet_station + ".csv")
        logging.debug("loading " + csv_file)
        husconet_station_df = pandas.read_csv(csv_file, index_col="datetime", parse_dates=["datetime"])
        plot_df[husconet_station] = husconet_station_df.temperature

    logging.debug("start plotting")
    ax = seaborn.boxplot(data=plot_df, width=.5)
    ax.set(xlabel="HUSCONET Station", ylabel="Temperature (in °C)")
    pyplot.show()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    for start, end in [(0, 5), (5, 10)]:
        plot_stations(start, end)