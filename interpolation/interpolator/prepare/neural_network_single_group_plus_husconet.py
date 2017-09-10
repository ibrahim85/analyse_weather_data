"""
prediction:
pws -> husconet

Uses:
/export/scratch/1kastner/neural_networks/evaluation_data_husconet.csv
"""

import os
import random
import logging
import io

import pandas

from filter_weather_data.filters import StationRepository
from filter_weather_data import get_repository_parameters
from filter_weather_data import RepositoryParameter
from filter_weather_data import PROCESSED_DATA_DIR
from gather_weather_data.husconet import StationRepository as HusconetStationRepository
from interpolation.interpolator.prepare.neural_network_single_group import fill_missing_eddh_values
from interpolation.interpolator.prepare.neural_network_single_group import load_eddh


def get_info(df):
    buf = io.StringIO()
    df.info(buf=buf)
    return buf.getvalue()


def join_to_big_vector(output_csv_file, station_dicts, husconet_dicts, eddh_df):
    """

    :param husconet_dicts: The stations to compare to
    :param station_dicts: The stations to use
    :param output_csv_file: Where to save the joined data to
    :return:
    """

    logging.debug("eddh df info: %s" % get_info(eddh_df))

    station_dfs = []
    while len(station_dicts):
        station_dict = station_dicts.pop()
        station_df = station_dict["data_frame"]
        position = station_dict["meta_data"]["position"]
        station_df['lat'] = position["lat"]
        station_df['lon'] = position["lon"]
        station_dfs.append(station_df)

    big_station_df = pandas.concat(station_dfs)
    big_station_df.columns = big_station_df.columns.map(lambda x: str(x) + "_pws")
    logging.debug("provided by PWS: %s" % str(big_station_df.head(1)))
    big_station_df.sort_index(inplace=True)
    logging.debug("rows of pws data: %i" % len(big_station_df))
    logging.debug("pws df info: %s" % get_info(big_station_df))

    common_df = big_station_df.join(eddh_df, how="left")  # eddh will be temporally interpolated later
    logging.debug("common_df with airport and pws: %s" % str(common_df.head(1)))
    logging.debug("rows of pws + airport data: %i" % len(common_df))
    logging.debug("airport + pws df info: %s" % get_info(common_df))

    husconet_dfs = []
    while len(husconet_dicts):
        husconet_dict = husconet_dicts.pop()
        station_df = husconet_dict["data_frame"]
        for attribute in station_df.columns:
            if attribute != "temperature":
                station_df.drop(attribute, 1, inplace=True)
        position = husconet_dict["meta_data"]["position"]
        station_df['lat'] = position["lat"]
        station_df['lon'] = position["lon"]
        husconet_dfs.append(station_df)

    big_husconet_df = pandas.concat(husconet_dfs)
    big_husconet_df.columns = big_husconet_df.columns.map(lambda x: str(x) + "_husconet")
    logging.debug("provided by HUSCONET: %s" % str(big_husconet_df.head(1)))
    big_husconet_df.sort_index(inplace=True)
    logging.debug("rows of husconet: %i" % len(big_husconet_df))
    logging.debug("husconet df info: %s" % get_info(big_husconet_df))

    common_df = big_husconet_df.join(common_df, how="inner")  # no temporal interpolation, so inner needed
    logging.debug("rows of all: %i" % len(common_df))
    logging.debug("airport + pws + husconet df info: %s" % get_info(common_df))
    logging.debug("airport + pws + husconet df info: %s" % str(common_df.head(1)))

    #common_df.sort_index(inplace=True)

    common_df = fill_missing_eddh_values(common_df)

    logging.debug("shortly before saving df info: %s" % get_info(common_df))
    common_df.to_csv(output_csv_file)


def run():
    start_date = "2016-01-01"
    end_date = "2016-12-31"
    eddh_df = load_eddh(start_date, end_date)
    station_repository = StationRepository(*get_repository_parameters(
        #RepositoryParameter.START_FULL_SENSOR
        RepositoryParameter.START
    ))
    station_dicts = station_repository.load_all_stations(
        start_date,
        end_date,
        # limit=5  # for testing purposes
    )

    husconet_dicts = HusconetStationRepository().load_all_stations(
        start_date,
        end_date,
        # limit=3  # for testing purposes
    )
    random.shuffle(husconet_dicts)
    split_point = int(len(husconet_dicts) * .7)
    training_dicts, evaluation_dicts = husconet_dicts[:split_point],husconet_dicts[split_point:]
    logging.info("training stations: %s" % [station["name"] for station in training_dicts])
    logging.info("evaluation stations: %s" % [station["name"] for station in evaluation_dicts])

    logging.debug("prepare evaluation")
    evaluation_csv_file = os.path.join(
        #PROCESSED_DATA_DIR,
        "/export/scratch/1kastner", #only for ccblade
        "neural_networks",
        "evaluation_data_husconet_2.csv"
    )
    join_to_big_vector(evaluation_csv_file, station_dicts[:], evaluation_dicts, eddh_df)

    logging.debug("prepare training")
    training_csv_file = os.path.join(
        #PROCESSED_DATA_DIR,
        "/export/scratch/1kastner", #only for ccblade
        "neural_networks",
        "training_data_husconet_2.csv"
    )
    join_to_big_vector(training_csv_file, station_dicts, training_dicts, eddh_df)
    logging.debug("done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    run()