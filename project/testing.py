import unittest
from unittest.mock import patch

import keras
import polars
from core.tfl import (app_keyAppender, get_crowdingdata, get_statusseverity,
                      get_tflline, get_tflstation)
from core.weather import getWeather
from data.mlData.dataRefiner import weatherAppender


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

        # check that ValueError is raised when an invalid line is provided
        with self.assertRaises(ValueError):
            station.get_data(
                line="invalid_line", station="Stratford Underground Station"
            )

    """
    checking if the correct error is raised when an invalid station is passed
    """

    def test_get_data_invalid_station(self):  # erroneous data
        station = get_tflstation()

        # check that ValueError is raised when an invalid station is provided
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

    def test_invalid_weather_item(self):  # erroneous
        weather_instance = getWeather()
        with self.assertRaises(ValueError):
            weather_instance.get_weather_item("invalid_weather_item")

    """
    checking if it correctly returns a large temperature
    """

    def test_boundary_temperature(self):  # boundary
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

    def test_boundary_weather_appender(self):  # boundary
        raw_data = polars.DataFrame({})
        weathered_data = weatherAppender(raw_data)
        print(weathered_data)
        self.assertIsNone(weathered_data)

    """
    checking if it correctly raises an error and stops when the time is outside the
    range of available weather data
    """

    def test_erroneous_weather_appender(self):  # erroneous
        raw_data = polars.DataFrame({"predictedTime": ["2023-03-01 12:00:00"]})
        with self.assertRaises(polars.exceptions.NoRowsReturnedError):
            weathered_data = weatherAppender(raw_data)


if __name__ == "__main__":
    unittest.main()
