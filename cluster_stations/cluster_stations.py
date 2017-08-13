"""

"""

import logging

from cluster import HierarchicalClustering

from filter_weather_data import get_repository_parameters
from filter_weather_data import RepositoryParameter
from filter_weather_data.filters import StationRepository


class Station:
    """
    This class is a necessity of the python-cluster package.
    The content here has no deeper sense, just avoiding exceptions.
    """

    def __init__(self, station_dict):
        self.station_dict = station_dict
        self.station_name = station_dict["name"]

    def __lt__(self, other):
        """
        Used for initial sorting and for memoization in python-cluster.

        :param other: another station
        :return: is it smaller
        """
        return self.station_name < other.station_name

    def __repr__(self):
        """
        used by ``cluster.hierarchical.HierarchicalClustering.display()``

        :return: representation of station
        """
        return repr(self.station_name)


class StationTimeSeriesComparator:

    # how long a measurement is valid
    DECAY = 30

    def __init__(self, station_dicts):
        self.station_dicts = station_dicts

    def compare_time_series(self, station_a, station_b):
        df_a = station_a.station_dict["data_frame"]
        df_b = station_b.station_dict["data_frame"]

        if df_a is None or df_a.empty or df_b is None or df_b.empty:
            return 999
        df = df_a.join(df_b, lsuffix="_a", rsuffix="_b", how="outer", sort=True)
        df = df.resample('1T').asfreq().ffill(limit=self.DECAY)

        # calculate euclidean distance between each data point
        distance_series = ((df["temperature_a"] - df["temperature_b"]) ** 2)
        distance = distance_series.mean()

        return distance


def log_progress(total, remaining):
    logging.debug("Calculation is %.2f %% complete" % (total / remaining))


def run_clustering(repository_parameter_name, start_date, end_date, limit):
    """

    :param repository_parameter_name: One of the types from ``RepositoryParameter``
    :param start_date: First day
    :param end_date: Last day
    :param limit: Limit the number of examined stations
    :return: Show clustering
    """
    params = get_repository_parameters(repository_parameter_name)
    station_repository = StationRepository(*params)
    station_dicts = station_repository.load_all_stations(start_date, end_date, limit=limit)
    station_time_series_comparator = StationTimeSeriesComparator(station_dicts)
    stations = [Station(station_dict) for station_dict in station_dicts]

    cluster = HierarchicalClustering(
        stations,
        station_time_series_comparator.compare_time_series,
        progress_callback=log_progress,
        num_processes=4
    )
    cluster.cluster()
    cluster.display()
    logging.info(cluster._data)


def demo():
    repository_parameter_name = RepositoryParameter.START
    start_date = "2016-01-01"
    end_date = "2016-01-01"
    limit = None
    run_clustering(repository_parameter_name, start_date, end_date, limit=limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    demo()
