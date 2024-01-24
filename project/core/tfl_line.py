
import logging
from urllib.parse import quote, urlencode

from core.utils import get_url

log = logging.getLogger(__name__)

class get_tflline:

    arrayofoptions = ["bakerloo","central","circle","district","hammersmith-city","jubilee","metropolitan","northern","piccadilly","victoria","waterloo-city"]

    def __init__(self):
        log.info("LOADED TFL API")
        self.base_url = 'https://api.tfl.gov.uk/Line/'


    def get_tubedata(self, options: str):
        options = self.validate_options(options=options)
        if len(options) == 0:
            return "No options provided"
        url = f"{self.base_url}{options}/Arrivals"
        data = get_url(url)
        return data

    def validate_options(self, options:str):
        options = options.split(",")
        options = [item for item in options if item in self.arrayofoptions]
        return ",".join(options)