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
            """to do - loop and call data every 30 seconds from API.
            create a mock database handling class (just text file read/writing for now) and call this here 
            in order to append the data to the text file every time it's been called.
            Add a method to killing the program."""