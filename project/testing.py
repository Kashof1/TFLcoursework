import unittest
from datetime import datetime
from unittest.mock import patch

import keras
import polars
from core.tfl import (app_keyAppender, get_crowdingdata, get_statusseverity,
                      get_tflline, get_tflstation)
from core.weather import getWeather
from data.mlData.dataRefiner import (date_bucketizer, lat_long_fetcher,
                                     time_bucketizer, weatherAppender)


class TestGetTflStation(unittest.TestCase):
    """
    checking the returned data is in the expected format
    """

    @patch("core.tfl.get_tflstation.dataFetcher")
    def test_get_data(self, mock_data_fetcher):  # normal data
        mock_data = [
            {"towards": "Station1", "timeToStation": 100},
            {"towards": "Station2", "timeToStation": 200},
        ]
        mock_data_fetcher.return_value = mock_data

        station = get_tflstation()

        data = station.get_data(line="central", station="Stratford Underground Station")

        self.assertEqual(data, mock_data)

    """
    checking if it gets the earliest train for each station
    """

    def test_get_next_unique_trains(self):  # normal data
        mock_data = [
            {"towards": "Station1", "timeToStation": 100},
            {"towards": "Station2", "timeToStation": 200},
            {"towards": "Station1", "timeToStation": 400},
        ]
        with patch.object(get_tflstation, "get_data", return_value=mock_data):
            station = get_tflstation()
            output = station.get_next_unique_trains(
                line="central", station="Stratford Underground Station"
            )

        expected_output = {"Station1": 100, "Station2": 200}

        self.assertEqual(output, expected_output)

    """
    checking if the correct error is raised when an invalid line is passed
    """

    def test_get_data_invalid_line(self):  # erroneous data
        station = get_tflstation()

        with self.assertRaises(ValueError):
            station.get_data(
                line="invalid_line", station="Stratford Underground Station"
            )

    """
    checking if the correct error is raised when an invalid station is passed
    """

    def test_get_data_invalid_station(self):  # erroneous data
        station = get_tflstation()

        with self.assertRaises(ValueError):
            station.get_data(line="central", station="invalid_station")

    """
    checking to ensure the output is correctly empty when the API provides an empty response
    """

    def test_get_next_unique_trains_empty_data(self):  # boundary data
        mock_data = []

        with patch.object(get_tflstation, "get_data", return_value=mock_data):
            station = get_tflstation()

            output = station.get_next_unique_trains(
                line="central", station="Stratford Underground Station"
            )

        self.assertEqual(output, {})


class TestGetTFLLine(unittest.TestCase):
    """
    checking if the returned data is of the expected type and length
    """

    @patch("core.tfl.app_keyAppender.dataFetcher")
    def test_valid_line(self, mock_data_fetcher):  # normal data
        mock_data_fetcher.return_value = [
            {"arrival_time": "10:00"},
            {"arrival_time": "10:15"},
        ]
        tfl_line = get_tflline("bakerloo")
        data = tfl_line.get_data()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

    """
    checking if the returned value is correctly empty if the API returns
    an empty response
    """

    @patch("core.tfl.app_keyAppender.dataFetcher")
    def test_empty_response(self, mock_data_fetcher):  # boundary data
        mock_data_fetcher.return_value = []
        tfl_line = get_tflline("victoria")
        data = tfl_line.get_data()
        self.assertEqual(data, [])

    """
    checking if a ValueError is correctly raised when the returned line is
    not valid
    """

    def test_invalid_line(self):
        with self.assertRaises(ValueError):  # erroneous data
            tfl_line = get_tflline("invalid_line")
            tfl_line.get_data()


class TestGetCrowdingData(unittest.TestCase):
    """
    Checking if the returned value is as expected
    """

    def test_valid_get_data(self):  # normal data
        with patch("core.tfl.app_keyAppender.dataFetcher") as mock_data_fetcher:
            mock_data_fetcher.return_value = {"percentageOfBaseline": 70}
            crowding_instance = get_crowdingdata()
            data = crowding_instance.get_data("Stratford Underground Station")
            self.assertEqual(data, 70)

    """
    checking if a ValueError is correctly raised when an invalid station is inputted
    """

    def test_invalid_station(self):  # erroneous data
        crowding_instance = get_crowdingdata()
        with self.assertRaises(ValueError):
            crowding_instance.get_data("invalid_station")

    """
    checking if a ValueError is correctly raised when no station is passed in
    """

    def test_no_options_provided(self):  # boundary data
        crowding_instance = get_crowdingdata()
        with self.assertRaises(ValueError):
            crowding_instance.get_data(None)


class TestGetStatusSeverity(unittest.TestCase):
    """
    checking if it correctly averages and returns the status severity for each line
    """

    def test_get_data(self):  # normal data
        with patch("core.tfl.app_keyAppender.dataFetcher") as mock_data_fetcher:
            mock_data_fetcher.return_value = [
                {"id": "bakerloo", "lineStatuses": [{"statusSeverity": 5}]},
                {
                    "id": "circle",
                    "lineStatuses": [{"statusSeverity": 3}, {"statusSeverity": 4}],
                },
            ]
            status_instance = get_statusseverity()
            data = status_instance.get_data()
            self.assertEqual(data, {"bakerloo": 5, "circle": 3.5})


class TestGetWeather(unittest.TestCase):
    """
    checking if it gets the correct temperature when apparent_temperature is passed
    """

    def test_valid_get_weather_item(self):  # normal data
        with patch("core.weather.get_url") as mock_get_url:
            mock_get_url.return_value = {"current": {"apparent_temperature": 20}}
            weather_instance = getWeather()
            temperature = weather_instance.get_weather_item("apparent_temperature")
            self.assertEqual(temperature, 20)

    """
    checking if it gets the correct precipitation when precipitation is passed
    """

    def test_valid_get_precip_item(self):
        with patch("core.weather.get_url") as mock_get_url:
            mock_get_url.return_value = {"current": {"precipitation": 5.2}}
            weather_instance = getWeather()
            precip = weather_instance.get_weather_item("precipitation")
            self.assertEqual(precip, 5.2)

    """
    checking if it correctly raises a ValueError when an incorrect option is passed
    """

    def test_invalid_weather_item(self):  # erroneous data
        weather_instance = getWeather()
        with self.assertRaises(ValueError):
            weather_instance.get_weather_item("invalid_weather_item")

    """
    checking if it correctly returns a large temperature
    """

    def test_boundary_temperature(self):  # boundary data
        with patch("core.weather.get_url") as mock_get_url:
            mock_get_url.return_value = {"current": {"apparent_temperature": -50}}
            weather_instance = getWeather()
            temperature = weather_instance.get_weather_item("apparent_temperature")
            self.assertEqual(temperature, -50)

    """
    checking if it correctly fails to return a temperature if the API does not respond
    """

    def test_error_get_url(self):  # erroneous
        with patch("core.weather.get_url") as mock_get_url:
            mock_get_url.side_effect = Exception("Error fetching URL")
            weather_instance = getWeather()
            with self.assertRaises(Exception):
                weather_instance.get_weather_item("apparent_temperature")


class TestWeatherAppender(unittest.TestCase):
    """
    checking if it correctly appends temperature when the time is within the range of
    available weather data
    """

    def test_normal_weather_appender(self):  # normal data
        raw_data = polars.DataFrame(
            {
                "predictedTime": ["2024-02-15 12:00:00"],
                "station": ["Station1"],
                "line": ["Line1"],
            }
        )
        weathered_data = weatherAppender(raw_data)
        self.assertIsNotNone(weathered_data)

    """
    checking if it correctly returns no data if the input is empty
    """

    def test_boundary_weather_appender(self):  # boundary data
        raw_data = polars.DataFrame({})
        weathered_data = weatherAppender(raw_data)
        print(weathered_data)
        self.assertIsNone(weathered_data)

    """
    checking if it correctly raises an error and stops when the time is outside the
    range of available weather data
    """

    def test_erroneous_weather_appender(self):  # erroneous data
        raw_data = polars.DataFrame({"predictedTime": ["2023-03-01 12:00:00"]})
        with self.assertRaises(polars.exceptions.NoRowsReturnedError):
            weathered_data = weatherAppender(raw_data)


class TestLatLongFetcher(unittest.TestCase):

    def setUp(self):
        data = {
            "NAME": ["Station1", "Station2"],
            "NETWORK": ["London Underground", "London Underground"],
            "x": [51.5074, 51.5074],  # Sample longitude values
            "y": [-0.1278, -0.1278],  # Sample latitude values
        }
        self.geoPolars = polars.DataFrame(data)

    """
    checking how lat_long_fetcher behaves with a valid station name
    """

    def test_normal_lat_long_fetcher(self):
        latitude, longitude = lat_long_fetcher("Station1", self.geoPolars)
        self.assertAlmostEqual(longitude, 51.5074)
        self.assertAlmostEqual(latitude, -0.1278)

    """
    checking that the lat_long_fetcher correctly returns nothing if the dataframe is empty,
    rather than producing bogus values
    """

    def test_boundary_lat_long_fetcher(self):
        # Test lat_long_fetcher with an empty geoPolars DataFrame
        latitude, longitude = lat_long_fetcher("Station1", polars.DataFrame({}))
        self.assertIsNone(latitude)
        self.assertIsNone(longitude)

    """
    checkign that lat_long_fetcher correctly halts if incorrect data is provided, rather
    than continuing and appending bogus values
    """

    def test_erroneous_lat_long_fetcher(self):
        with self.assertRaises(Exception):
            lat_long_fetcher("InvalidStation", self.geoPolars)

        # Test lat_long_fetcher with missing columns in geoPolars DataFrame
        geoPolars_missing_columns = polars.DataFrame({"NAME": ["Station1"]})
        with self.assertRaises(Exception):
            lat_long_fetcher("Station1", geoPolars_missing_columns)

        # Test lat_long_fetcher with incorrect network type
        geoPolars_incorrect_network = polars.DataFrame(
            {"NAME": ["Station1"], "NETWORK": ["Wrong Network"]}
        )
        with self.assertRaises(Exception):
            lat_long_fetcher("Station1", geoPolars_incorrect_network)


class TestTimeBucketizer(unittest.TestCase):
    """
    Checking to see if time_bucketizer functions correctly for normal datetime input
    """

    def test_normal_time_bucketizer(self):
        date_time = datetime.strptime("2024-04-07 12:15:30", "%Y-%m-%d %H:%M:%S")
        result = time_bucketizer(date_time)
        self.assertEqual(result, "12:00:00")

    """
    Checking to see if time bucketizer works for times that are on the boundary of intervals
    """

    def test_boundary_time_bucketizer(self):
        # Test time_bucketizer with boundary values for minute intervals
        date_time_1 = datetime.strptime("2024-04-07 12:00:00", "%Y-%m-%d %H:%M:%S")
        date_time_2 = datetime.strptime("2024-04-07 12:29:59", "%Y-%m-%d %H:%M:%S")
        date_time_3 = datetime.strptime("2024-04-07 12:30:00", "%Y-%m-%d %H:%M:%S")
        date_time_4 = datetime.strptime("2024-04-07 12:59:59", "%Y-%m-%d %H:%M:%S")
        result_1 = time_bucketizer(date_time_1)
        result_2 = time_bucketizer(date_time_2)
        result_3 = time_bucketizer(date_time_3)
        result_4 = time_bucketizer(date_time_4)
        self.assertEqual(result_1, "12:00:00")
        self.assertEqual(result_2, "12:00:00")
        self.assertEqual(result_3, "12:30:00")
        self.assertEqual(result_4, "12:30:00")

    """
    checking if time bucketizer correctly raises an error when given an incorrect input rather
    than generating a bogus value
    """

    def test_erroneous_time_bucketizer(self):
        # Test time_bucketizer with erroneous input
        with self.assertRaises(AttributeError):
            time_bucketizer(
                "2024-04-07 12:15:30"
            )  # Should raise AttributeError for non-datetime input


class TestDateBucketizer(unittest.TestCase):
    """
    checking if date bucketizer works with a normal date
    """

    def test_normal_date_bucketizer(self):
        date_time = datetime.strptime("2024-04-07", "%Y-%m-%d")
        result = date_bucketizer(date_time)
        self.assertEqual(result, "7")

    """
    checking if date bucketizer works with dates on the edges of its possible values
    (ISO weekday 1 and 7)
    """

    def test_boundary_date_bucketizer(self):
        date_time_1 = datetime.strptime("2024-04-07", "%Y-%m-%d")
        date_time_2 = datetime.strptime("2024-04-01", "%Y-%m-%d")
        result_1 = date_bucketizer(date_time_1)
        result_2 = date_bucketizer(date_time_2)
        self.assertEqual(result_1, "7")
        self.assertEqual(result_2, "1")

    """
    checking if date bucketizer correctly raises an error when given an incorrect input
    format rather than generating a bogus value
    """

    def test_erroneous_date_bucketizer(self):
        # Test date_bucketizer with erroneous input
        with self.assertRaises(AttributeError):
            date_bucketizer(
                "2024-04-07"
            )  # Should raise AttributeError for non-datetime input


if __name__ == "__main__":
    unittest.main()
