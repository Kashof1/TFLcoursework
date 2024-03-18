import logging

from core.utils import get_url
import core.tfl_line as tfl_line
from core.databaseutils import DatabaseHandler

log = logging.getLogger(__name__)
tflinstance = tfl_line.get_tflline()


class Scraper:
    def __init__(self, linename: str, filename: str):
        log.info(f"LOADED {linename} SCRAPER INSTANCE")
        self.line = linename
        self.destinationfile = filename
        self.databasehandler = DatabaseHandler(self.destinationfile)

    def scrape(self):
        data = tflinstance.get_tubedata(self.line)
        self.databasehandler.write(data)

    """to do - loop and call data every 30 seconds from API.
    create a mock database handling class (just text file read/writing for now) and call this here
    in order to append the data to the text file every time it's been called.
    Add a method to killing the program."""
