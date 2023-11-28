import os
import json
import logging

from core.utils import get_url

log = logging.getLogger(__name__)

class get_tflstation():

    arrayofoptions = ["bakerloo","central","circle","district","hammersmith-city","jubilee","metropolitan","northern","piccadilly","victoria","waterloo-city"]

    def __init__(self):
        log.info("LOADED TFL STATION ARRIVALS API")
        self.base_url = 'https://api.tfl.gov.uk/Line/'
        #station name (for convenience) paired with naptanid needed for API call, in dictionary form
        self.directory = os.path.join('data','stations.json')
        with open (self.directory, 'r', encoding='utf8') as file:
            self.dictofoptions = json.load(file)

    def get_data(self, line: str, station: str):
        stationID, line = self.validate_option(line, station)
        if len(stationID) == 0 or len(line) == 0:
            log.info('Invalid option(s) provided to get_tflstation instance')
            return "No valid options provided"
        url = f"{self.base_url}{line}/Arrivals/{stationID}"
        data = get_url(url)
        return data


    def validate_option(self, line: str, station: str):
        valid = True
        if station in self.dictofoptions:
            stationID = self.dictofoptions[station]
        else:
            valid = False
        
        if line not in self.arrayofoptions:
            valid = False
        
        return (stationID, line) if valid == True else ('','') 
    
"""
confirm what type of oop construct is best used here
ALSO PENDING TESTING
"""

class get_crowdingdata():
    def __init__(self):
        log.info('LOADED CROWDING API')
        self.base_url = 'https://api.tfl.gov.uk/crowding/'
        self.directory = os.path.join('data', 'stations.json')
        with open (self.directory, 'r', encoding='utf8') as file:
            self.dictofoptions = json.load(file)

    def get_data(self, station: str):
        stationID = self.validate_option(station)
        if not stationID:
            log.info('Invalid option(s) provided to get_crowdingdata instance')
            return "No valid options provided"
        url = f"{self.base_url}{stationID}/Live"
        data = get_url(url)
        return data

    def validate_option(self, station: str):
        valid = True
        if station in self.dictofoptions:
            stationID = self.dictofoptions[station]
        else:
            valid = False
        
        return stationID if valid == True else ''