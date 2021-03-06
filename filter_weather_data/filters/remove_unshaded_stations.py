"""

Run with '-m filter_weather_data.filters.remove_unshaded_stations' if you want to see the demo.
"""

import logging

import numpy
import pandas
import scipy.stats

from . import StationRepository
from gather_weather_data.husconet import load_husconet_temperature_average
from gather_weather_data.husconet import load_husconet_radiation_average
from gather_weather_data.husconet import GermanWinterTime


# At least 10 W/m2
SUNSHINE_MINIMUM_THRESHOLD = 10

# statistic p value
P_VALUE = .01

# correlation coefficient
CORRELATION_COEFFICIENT = .5


def check_station(station_df, reference_temperature_df, reference_radiation_df, just_check_correlation=False):
    """
    
    :param station_df: The station to check
    :param reference_temperature_df: The reference temperatures
    :param reference_radiation_df: 
    :return: Is the station at a shaded place with high probability?
    """

    logging.debug("number of general observations: %i" % len(station_df))
    temp_df = station_df.join(reference_temperature_df, how='left', rsuffix="_reference_temperature")
    delta_temperature = (temp_df.temperature - temp_df.temperature_reference_temperature).rename("temperature_delta")
    delta_df = pandas.concat([temp_df, delta_temperature], axis=1)

    delta_df = delta_df.join(reference_radiation_df, how='left')
    df_only_sunshine = delta_df[(delta_df.radiation > SUNSHINE_MINIMUM_THRESHOLD)]
    logging.debug("sunshine only: %s" % df_only_sunshine.describe())

    examine_me_df = pandas.concat([df_only_sunshine.temperature_delta, df_only_sunshine.radiation], axis=1)
    examine_me_df.dropna(axis=0, how="any", inplace=True)
    logging.debug("compare these values: %s" % examine_me_df.describe())

    if df_only_sunshine.empty:
        logging.warning("No entries found for sunshine. Did you check for infrequent reporting?")
        return False

    try:
        slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(
            examine_me_df.temperature_delta.values,
            examine_me_df.radiation.values
        )
    except ValueError as ve:
        logging.warning("Linear regression led to error: ", ve)
        return False

    # Is the station at an unshaded position?
    station_unshaded = (r_value > CORRELATION_COEFFICIENT and p_value < P_VALUE)

    if just_check_correlation:
        logging.debug("station: r = {r}, p = {p}".format(r=r_value, p=p_value))
        logging.debug("unshaded" if station_unshaded else "shaded")
        return r_value, p_value

    if station_unshaded:
        logging.debug("station unshaded: r = {r}, p = {p}".format(r=r_value, p=p_value))
        return False
    else:
        # Remove extreme values, level C2
        upper_limit = delta_df.temperature_reference_temperature + (delta_df.temperature_std * 3)
        extreme_delta_df = delta_df.loc[delta_df.temperature > upper_limit]
        if not extreme_delta_df.empty:
            before = station_df.temperature.count()
            station_df.loc[extreme_delta_df.index.tolist(), "temperature"] = numpy.nan
            after = station_df.temperature.count()
            logging.debug("removed by sigma*3 rule: before: {before}, after: {after}, diff: {diff}".format(
                before=before, after=after, diff=before-after
            ))
            if station_df.empty:
                return False
            elif station_df.temperature.count() == 0:
                return False
            else:
                return True
        return True


def filter_stations(station_dicts, start_date, end_date):
    """

    :param start_date: The first value to load from the reference net (included)
    :param end_date: The last value to load from the reference net (included)
    :param time_zone: The time zone to apply to the reference values
    :param station_dicts: The station dicts
    """

    reference_temperature_df = load_husconet_temperature_average(start_date, end_date)
    reference_radiation_df = load_husconet_radiation_average(start_date, end_date)

    filtered_stations = []
    for station_dict in station_dicts:
        # logging.debug("unshaded " + station_dict["name"])
        if check_station(station_dict["data_frame"], reference_temperature_df, reference_radiation_df):
            filtered_stations.append(station_dict)
    return filtered_stations


def demo():
    start_date = "2016-01-01T00:00:00"
    end_date = "2016-01-30T23:59:00"
    time_zone = GermanWinterTime()
    stations = ['ISCHENEF11', 'IHAMBURG22']
    station_repository = StationRepository()
    station_dicts = filter(lambda x: x is not None, [station_repository.load_station(station, start_date, end_date,
                                                                                     time_zone)
                                                     for station in stations])
    stations_with_data = filter_stations(station_dicts, start_date, end_date)
    print([station_dict["name"] for station_dict in stations_with_data])

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    demo()
