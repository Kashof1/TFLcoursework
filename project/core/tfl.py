import json
import logging
import os
import random
import sys
import time
from urllib.error import HTTPError

currentRoot = os.path.abspath(
    os.path.dirname(__file__)
)  # getting absolute path leading to current file
sys.path.append(
    currentRoot
)  # adding abs path to sys so abs import can be used between files in the same folder
from utils import get_url

log = logging.getLogger(__name__)

"""KEYS
mainsub a: 09e54f9b77ff469f9a72cdb1257f6ee3
mainsub b: eaacea99f66b4d40b7b93ce9f7744b90
secondarysub_one a: e6c88e6d39e1495cbb3f9d24d1fe8994
secondarysub_one b: a475df8e7e204050ae339c3884401802
secondarysub_two a: 23e0b650662d4a01b41c1ca8bfa781b2
secondarysub_two b: b85169976bd64be7acff84bbc4940f31
MiscUse a: 0ed20d25b4b74edbb330d875bbe783ba
MiscUse b: 4a80bcf6764d437ea5c4fe9cf2e134de
"""


class app_keyAppender:
    def __init__(self):
        pass

    def dataFetcher(self, url):
        keylist = [
            "0ed20d25b4b74edbb330d875bbe783ba",
            "4a80bcf6764d437ea5c4fe9cf2e134de",
        ]
        random.shuffle(
            keylist
        )  # shuffling api keys to ensure even distribution and use of all keys
        while True:
            for index in range(len(keylist)):
                try:
                    targeturl = f"{url}?app_key={keylist[index]}"
                    data = get_url(targeturl)
                    return data
                except Exception as e:
                    pass

            if (
                index >= len(keylist) - 1
            ):  # if all keys are exhausted, wait before trying again
                time.sleep(
                    random.randint(5, 10)
                )  # random seconds wait to avoid potential overlap between threads as much as possible

    def appender(self, url):  # obsolete
        return f"{url}?app_key=09e54f9b77ff469f9a72cdb1257f6ee3"


class get_tflstation(app_keyAppender):

    arrayofoptions = [
        "bakerloo",
        "central",
        "circle",
        "district",
        "hammersmith-city",
        "jubilee",
        "metropolitan",
        "northern",
        "piccadilly",
        "victoria",
        "waterloo-city",
    ]

    def __init__(self):
        log.info("LOADED TFL STATION ARRIVALS API")
        self.base_url = "https://api.tfl.gov.uk/Line/"
        # station name (for convenience) paired with naptanid needed for API call, in dictionary form
        self.directory = os.path.join("data", "stations.json")
        with open(self.directory, "r", encoding="utf8") as file:
            self.dictofoptions = json.load(file)

    def get_data(self, line: str, station: str):
        stationID, line = self.validate_option(station=station, line=line)
        '''if len(stationID) == 0 or len(line) == 0:
            log.info(
                f"Invalid option(s) provided to get_tflstation instance. Options provided were {line} and {station}"
            )
            return "No valid options provided"'''
        url = f"{self.base_url}{line}/Arrivals/{stationID}"
        data = self.dataFetcher(url=url)
        return data

    def get_next_unique_trains(self, line: str, station: str):
        # this function will get the next train for each unique 'destination' in the API call
        data = self.get_data(line=line, station=station)
        output = {}  # station:time
        for prediction in data:
            pDest = prediction[
                "towards"
            ]  # terminal station of the train that the prediction is being made for
            if pDest in output:
                currentTime = output[pDest]
                pTime = prediction["timeToStation"]
                if pTime < currentTime:
                    output[pDest] = pTime
            else:
                pTime = prediction["timeToStation"]
                output[pDest] = pTime

        return output

    def validate_option(self, line: str, station: str):
        valid = True
        if station in self.dictofoptions:
            stationID = self.dictofoptions[station]
        else:
            valid = False

        if line not in self.arrayofoptions:
            valid = False

        if valid == True:
            return (stationID, line)
        else:
            raise ValueError(
                f"The selected station ({station}) or line ({line}) are not supported"
            )


class get_tflline(app_keyAppender):

    arrayofoptions = [
        "bakerloo",
        "central",
        "circle",
        "district",
        "hammersmith-city",
        "jubilee",
        "metropolitan",
        "northern",
        "piccadilly",
        "victoria",
        "waterloo-city",
    ]

    def __init__(self, line):
        log.info("LOADED TFL LINE ARRIVALS API")
        self.line = line
        self.base_url = "https://api.tfl.gov.uk/Line/"

    def get_data(self):
        self.line = self.validate_options(option=self.line)
        url = f"{self.base_url}{self.line}/Arrivals"
        data = self.dataFetcher(url=url)
        return data

    def validate_options(self, option: str):
        if option in self.arrayofoptions:
            return option
        else:
            raise ValueError(f"The selected line ({line}) is not supported")


class get_crowdingdata(app_keyAppender):
    def __init__(self):
        log.info("LOADED CROWDING API")
        self.base_url = "https://api.tfl.gov.uk/crowding/"
        self.directory = os.path.join("data", "stations.json")
        with open(self.directory, "r", encoding="utf8") as file:
            self.dictofoptions = json.load(file)

    def get_data(self, station: str):
        stationID = self.validate_option(station)
        if not stationID:
            log.info("Invalid option(s) provided to get_crowdingdata instance")
            return "No valid options provided"
        url = f"{self.base_url}{stationID}/Live"
        data = self.dataFetcher(url=url)
        crowdingPercentage = data["percentageOfBaseline"]
        return crowdingPercentage

    def validate_option(self, station: str):
        valid = True
        if station in self.dictofoptions:
            stationID = self.dictofoptions[station]
        else:
            valid = False

        if valid == True:
            return stationID
        else:
            raise ValueError(f"The selected station ({station}) is not supported")


class get_statusseverity(app_keyAppender):
    arrayofoptions = [
        "bakerloo",
        "central",
        "circle",
        "district",
        "hammersmith-city",
        "jubilee",
        "metropolitan",
        "northern",
        "piccadilly",
        "victoria",
        "waterloo-city",
    ]

    def __init__(self):
        log.info("LOADED STATUS SEVERITY API")
        self.request_url = "https://api.tfl.gov.uk/Line/Mode/tube/Status"

    def get_data(self):
        url = self.request_url
        data = self.dataFetcher(url=url)

        """potentially multiple different severity levels can be reported for one line, each pertaining to a different section of the line. In order to gauge
        the overall performance of a line, it is best to take an average of these severity codes if there are multiple. If not, simply take the single provided
        value and assume it applies to the whole line"""
        statusDict = {}
        for entry in data:
            currentLine = entry["id"]
            statusList = entry["lineStatuses"]
            numOfReports = len(statusList)
            if numOfReports == 1:
                statusDict[currentLine] = statusList[0]["statusSeverity"]
            else:
                total = 0
                for each in statusList:
                    total += each["statusSeverity"]
                statusDict[currentLine] = total / numOfReports
        return statusDict
