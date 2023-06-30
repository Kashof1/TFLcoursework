from utils import get_url
import logging
import tfl
import time

log = logging.getLogger(__name__)
tflinstance = tfl.get_tfl()

class scraper:
    def __init__(self, linename: str):
        log.info("LOADED SCRAPER INSTANCE")
        self.line = linename
        
    
    def scrape(self):
        while True:
            data = tflinstance.get_tubedata(self.line)
