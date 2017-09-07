"""

"""

import os
import random
import logging

import pandas

from filter_weather_data.filters import StationRepository
from filter_weather_data import get_repository_parameters
from filter_weather_data import RepositoryParameter
from filter_weather_data import PROCESSED_DATA_DIR

from interpolation import load_airport


def load_eddh(start_date, end_date):
    """
    loads EDDH data

    :param start_date:
    :param end_date:
    :return:
    """
    eddh_df = load_airport("EDDH", start_date, end_date)
    eddh_df = eddh_df.add_suffix("_eddh")
    return eddh_df


def fill_missing_eddh_values(common_df):
    """
    in case of missing data just presume that the old data are still valid.
    airport data should always be back online quickly.

    :param common_df: airport and private data merged
    :return: continued airport data
    """
    common_df.cloudcover_eddh.fillna(method='pad', inplace=True)
    common_df.dewpoint_eddh.fillna(method='pad', inplace=True)
    common_df.pressure_eddh.fillna(method='pad', inplace=True)
    common_df.temperature_eddh.fillna(method='pad', inplace=True)
    common_df.winddirection_eddh.fillna(method='pad', inplace=True)
    common_df.windspeed_eddh.fillna(method='pad', inplace=True)
    common_df.info()
    common_df.head()
    common_df = common_df[pandas.notnull(common_df.lat)]  # remove eddh without pws entries
    return common_df


def join_to_big_vector(output_csv_file, station_dicts, eddh_df):
    """

    :param station_dicts: The stations to use
    :param output_csv_file: Where to save the joined data to
    :return:
    """

    common_df = eddh_df
    while True:
        if len(station_dicts) == 0:
            break
        station_dict = station_dicts.pop()
        station_df = station_dict["data_frame"]
        position = station_dict["meta_data"]["position"]
        station_df['lat'] = position["lat"]
        station_df['lon'] = position["lon"]
        common_df = pandas.concat([common_df, station_df])
    common_df.sort_index(inplace=True)
    common_df = fill_missing_eddh_values(common_df)
    common_df.to_csv(output_csv_file)


def run():
    start_date = "2016-01-01"
    end_date = "2016-12-31"
    eddh_df = load_eddh(start_date, end_date)
    station_repository = StationRepository(*get_repository_parameters(RepositoryParameter.START_FULL_SENSOR))
    station_dicts = station_repository.load_all_stations(
        start_date,
        end_date,
        # limit=5  # for testing purposes
    )

    random.shuffle(station_dicts)
    split_point = int(len(station_dicts) * .7)
    training_dicts, evaluation_dicts = station_dicts[:split_point], station_dicts[split_point:]

    logging.info("training stations: %s" % [station["name"] for station in training_dicts])
    logging.info("evaluation stations: %s" % [station["name"] for station in evaluation_dicts])

    training_csv_file = os.path.join(
        PROCESSED_DATA_DIR,
        "neural_networks",
        "training_data.csv"
    )
    join_to_big_vector(training_csv_file, training_dicts, eddh_df)

    evaluation_csv_file = os.path.join(
        PROCESSED_DATA_DIR,
        "neural_networks",
        "evaluation_data.csv"
    )
    join_to_big_vector(evaluation_csv_file, evaluation_dicts, eddh_df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    run()
