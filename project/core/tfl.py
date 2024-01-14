import os
import json
import logging
import time
import random
from urllib.error import HTTPError

from core.utils import get_url

log = logging.getLogger(__name__)

'''KEYS
mainsub a: 09e54f9b77ff469f9a72cdb1257f6ee3
mainsub b: eaacea99f66b4d40b7b93ce9f7744b90
secondarysub_one a: e6c88e6d39e1495cbb3f9d24d1fe8994
secondarysub_one b: a475df8e7e204050ae339c3884401802
secondarysub_two a: 23e0b650662d4a01b41c1ca8bfa781b2
secondarysub_two b: b85169976bd64be7acff84bbc4940f31
'''

class app_keyAppender():
    def __init__(self):
        pass

    def dataFetcher(self, url):
        keylist = ['09e54f9b77ff469f9a72cdb1257f6ee3', 'eaacea99f66b4d40b7b93ce9f7744b90', 'e6c88e6d39e1495cbb3f9d24d1fe8994', 'a475df8e7e204050ae339c3884401802', '23e0b650662d4a01b41c1ca8bfa781b2', 'b85169976bd64be7acff84bbc4940f31']
        random.shuffle(keylist)
        while True:
            for index in range (len(keylist)):
                try:
                    targeturl = f'{url}?app_key={keylist[index]}'
                    data = get_url(targeturl)
                    return data

                except HTTPError as err:
                    pass

                except:
                    pass
                        
            if index >= len(keylist)-1:
                print ('flag 3')
                time.sleep(3)

            
    def appender(self, url): #obsolete
        return f'{url}?app_key=09e54f9b77ff469f9a72cdb1257f6ee3'


class get_tflstation(app_keyAppender):

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
        data = self.dataFetcher(url=url)
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
    

class get_crowdingdata(app_keyAppender):
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
        data = self.dataFetcher(url=url)
        return data

    def validate_option(self, station: str):
        valid = True
        if station in self.dictofoptions:
            stationID = self.dictofoptions[station]
        else:
            valid = False
        
        return stationID if valid == True else ''
    

class get_disruptionstatus(app_keyAppender):

    arrayofoptions = ["bakerloo","central","circle","district","hammersmith-city","jubilee","metropolitan","northern","piccadilly","victoria","waterloo-city"]

    def __init__(self):
        log.info('LOADED DISRUPTION STATUS API')
        self.base_url = 'https://api.tfl.gov.uk/Line/'

    def get_data(self, line: str):
        line = self.validate_option(line)
        if not line:
            log.info('Invalid line name provided to get_disruptionstatus instance')
            return "No valid options provided"
        url = f"{self.base_url}{line}/Disruption"
        data = self.dataFetcher(url=url)
        if not data:
            return None
        else:
            return data[0]['closureText']

    def validate_option(self, line: str):
        valid = True
        if line not in self.arrayofoptions:
            valid = False
        return line if valid == True else ''
    

class get_statusseverity(get_disruptionstatus, app_keyAppender): #inheritance used as only difference here is what comes after the base url

    def get_data(self, line:str):
        line = self.validate_option(line)
        if not line:
            log.info('Invalid line name provided to get_statusseverity instance')
            return "No valid options provided"
        url = f"{self.base_url}{line}/Status"
        data = self.dataFetcher(url=url)

        '''potentially multiple different severity levels can be reported for one line, each pertaining to a different section of the line. In order to gauge
        the overall performance of a line, it is best to take an average of these severity codes if there are multiple. If not, simply take the single provided 
        value and assume it applies to the whole line'''

        statusList = data[0]['lineStatuses'] #index 0 here because tfl returns a list of one item when you specify for a single line, rather than a list with each line
        numOfReports = len(statusList)
        if numOfReports == 1:
            return statusList[0]['statusSeverity']
        else:
            total = 0
            for each in statusList:
                total += each['statusSeverity']
            return (total/numOfReports)
        
if __name__ == '__main__':
    test = app_keyAppender()
    while True:
        data = test.dataFetcher('https://api.tfl.gov.uk/Line/central/Disruption')
        print (data)
        