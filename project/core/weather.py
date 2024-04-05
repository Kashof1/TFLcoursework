import os
import sys

currentRoot = os.path.abspath(os.path.dirname(__file__))
sys.path.append(currentRoot)
from utils import get_url


class getWeather:
    def __init__(self):
        # lat and long in url set to London
        self.__base_url = (
            "https://api.open-meteo.com/v1/forecast?latitude=51.5085&longitude=-0.1257"
        )
        self.__valid_options = ["apparent_temperature", "precipitation"]

    def get_weather_item(self, item: str) -> float:
        option = self.validate_option(item)
        request_url = f"{self.__base_url}&current={option}"
        response = get_url(url=request_url)
        val = response["current"][option]
        return val

    def validate_option(self, option: str) -> str:
        if option in self.__valid_options:
            return option
        else:
            raise ValueError(
                f"Selected weather event to get data for is not in the list of supported events. The supported events are: {self.__valid_options}"
            )
