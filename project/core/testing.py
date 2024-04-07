import unittest
from unittest.mock import MagicMock, patch

import keras
from core.tfl import (app_keyAppender, get_crowdingdata, get_statusseverity,
                      get_tflline, get_tflstation)
from core.weather import getWeather


class TestGetTflStation(unittest.TestCase):

    @patch("core.tfl.get_tflstation.dataFetcher")
    def test_get_data(self, mock_data_fetcher):
        mock_data = [
            {"towards": "Station1", "timeToStation": 100},
            {"towards": "Station2", "timeToStation": 200},
        ]
        mock_data_fetcher.return_value = mock_data

        station = get_tflstation()

        data = station.get_data(line="central", station="Stratford Underground Station")

        self.assertEqual(data, mock_data)

    def test_get_next_unique_trains(self):
        mock_data = [
            {"towards": "Station1", "timeToStation": 100},
            {"towards": "Station2", "timeToStation": 200},
        ]
        with patch.object(get_tflstation, "get_data", return_value=mock_data):
            station = get_tflstation()
            output = station.get_next_unique_trains(
                line="central", station="Stratford Underground Station"
            )

        expected_output = {"Station1": 100, "Station2": 200}

        self.assertEqual(output, expected_output)

    def test_get_data_invalid_line(self):  # erroneous data
        station = get_tflstation()

        # check that ValueError is raised when an invalid line is provided
        with self.assertRaises(ValueError):
            station.get_data(
                line="invalid_line", station="Stratford Underground Station"
            )

    def test_get_data_invalid_station(self):  # erroneous data
        station = get_tflstation()

        # check that ValueError is raised when an invalid station is provided
        with self.assertRaises(ValueError):
            station.get_data(line="central", station="Invalid Station")

    def test_get_next_unique_trains_empty_data(self):  # boundary data
        mock_data = []

        with patch.object(get_tflstation, "get_data", return_value=mock_data):
            station = get_tflstation()

            output = station.get_next_unique_trains(
                line="central", station="Stratford Underground Station"
            )

        self.assertEqual(output, {})


class TestGetTFLLine(unittest.TestCase):
    def setUp(self):
        self.valid_line = "bakerloo"
        self.invalid_line = "invalid_line"

    @patch("core.tfl.app_keyAppender.dataFetcher")
    def test_valid_line(self, mock_data_fetcher):
        mock_data_fetcher.return_value = [
            {"arrival_time": "10:00"},
            {"arrival_time": "10:15"},
        ]
        tfl_line = get_tflline(self.valid_line)
        data = tfl_line.get_data()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    @patch("core.tfl.app_keyAppender.dataFetcher")
    def test_empty_response(self, mock_data_fetcher):
        mock_data_fetcher.return_value = []
        tfl_line = get_tflline(self.valid_line)
        data = tfl_line.get_data()
        self.assertEqual(data, [])

    def test_invalid_line(self):
        with self.assertRaises(ValueError):
            tfl_line = get_tflline(self.invalid_line)
            tfl_line.get_data()


class TestGetCrowdingData(unittest.TestCase):

    def test_valid_get_data(self):
        with patch("core.tfl.app_keyAppender.dataFetcher") as mock_data_fetcher:
            mock_data_fetcher.return_value = {"percentageOfBaseline": 70}
            crowding_instance = get_crowdingdata()
            data = crowding_instance.get_data("Stratford Underground Station")
            self.assertEqual(data, 70)

    def test_invalid_station(self):
        crowding_instance = get_crowdingdata()
        with self.assertRaises(ValueError):
            crowding_instance.get_data("thisSTATION doesnt existttt")

    def test_no_options_provided(self):
        crowding_instance = get_crowdingdata()
        with self.assertRaises(ValueError):
            crowding_instance.get_data(None)


class TestGetStatusSeverity(unittest.TestCase):

    def test_get_data(self):  # testing if it averages properly
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

    def test_valid_get_weather_item(self):
        with patch("core.weather.get_url") as mock_get_url:
            mock_get_url.return_value = {"current": {"apparent_temperature": 20}}
            weather_instance = getWeather()
            temperature = weather_instance.get_weather_item("apparent_temperature")
            self.assertEqual(temperature, 20)

    def test_invalid_weather_item(self):
        weather_instance = getWeather()
        with self.assertRaises(ValueError):
            weather_instance.get_weather_item("invalid_weather_item")

    def test_boundary_temperature(self):
        with patch("core.weather.get_url") as mock_get_url:
            mock_get_url.return_value = {"current": {"apparent_temperature": -50}}
            weather_instance = getWeather()
            temperature = weather_instance.get_weather_item("apparent_temperature")
            self.assertEqual(temperature, -50)

    def test_error_get_url(self):
        with patch("core.weather.get_url") as mock_get_url:
            mock_get_url.side_effect = Exception("Error fetching URL")
            weather_instance = getWeather()
            with self.assertRaises(Exception):
                weather_instance.get_weather_item("apparent_temperature")


if __name__ == "__main__":
    unittest.main()
