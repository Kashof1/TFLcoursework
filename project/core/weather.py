import os
import sys

currentRoot = os.path.abspath(os.path.dirname(__file__))
sys.path.append(currentRoot)
from utils import get_url


class getWeather:
    def __init__(self):
        # lat and long in url set to London
        self.base_url = (
            "https://api.open-meteo.com/v1/forecast?latitude=51.5085&longitude=-0.1257"
        )

    def get_current_temperature(self):
        # getting current APPARENT temperature from open-meteo through URL
        request_url = f"{self.base_url}&current=apparent_temperature"
        response = get_url(url=request_url)
        temperature = response["current"]["apparent_temperature"]
        return temperature

    def get_current_precip(self):
        # getting current precipitation from open-meteo through URL
        request_url = f"{self.base_url}&current=precipitation"
        response = get_url(url=request_url)
        precip = response["current"]["precipitation"]
        return precip
