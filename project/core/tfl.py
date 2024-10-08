import datetime
import json
import logging
import os
import random
import sys
import time

import keras
import pandas as pd
import polars as pl
from core.weather import getWeather
from data.mlData.dataRefiner import (date_bucketizer, lat_long_fetcher,
                                     time_bucketizer)
from machine_learning.hyperparamFinder import dataPipeline

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

    def dataFetcher(self, url: str) -> list:
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
                time.sleep(random.randint(5, 10))


class get_tflstation(app_keyAppender):

    ARRAYOFOPTIONS = [
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
        self.__base_url = "https://api.tfl.gov.uk/Line/"
        # station name (for convenience) paired with naptanid needed for API call, in dictionary form
        self.__directory = os.path.join("data", "stations.json")
        with open(self.__directory, "r", encoding="utf8") as file:
            self.__dictofoptions = json.load(file)

        # initialising these once, for whenever inference needs to be made
        self.__weatherGetter = getWeather()
        self.__statusGetter = get_statusseverity()
        self.__crowdingGetter = get_crowdingdata()
        self.__pipeline = dataPipeline()
        self.__model = keras.models.load_model("tflDelayPredictor.keras")

    def get_data(self, line: str, station: str) -> list:
        stationID, line = self.__validate_option(station=station, line=line)
        url = f"{self.__base_url}{line}/Arrivals/{stationID}"
        data = self.dataFetcher(url=url)
        return data

    def get_next_unique_trains(self, line: str, station: str) -> dict:
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

    def inferDelayPrediction(self, line: str, station: str) -> int:
        # validating only the line, as the model takes station NAME for inference
        # e.g. line = central, station = Hainault Underground Station
        line = self.__validate_line(line=line)
        currentTime = datetime.datetime.now()

        # using imported functions in order to keep data formatting consistent for inference
        processedTime = time_bucketizer(date_time=currentTime)
        processedDay = int(date_bucketizer(date_time=currentTime))

        geoPath = os.path.join("data", "raw", "stationLocRaw.csv")
        geoPolars = pl.read_csv(geoPath)
        (latitude, longitude) = lat_long_fetcher(station=station, geoPolars=geoPolars)

        appTemperature = self.__weatherGetter.get_weather_item(
            item="apparent_temperature"
        )
        precipitation = self.__weatherGetter.get_weather_item(item="precipitation")
        crowding = self.__crowdingGetter.get_data(station=station)
        statusDictionary = self.__statusGetter.get_data()
        statusSeverity = statusDictionary[line]

        inferenceData = {
            "station": station,
            "line": line,
            "crowding": crowding,
            "time": processedTime,
            "latitude": latitude,
            "longitude": longitude,
            "appTemperature": appTemperature,
            "precipitation": precipitation,
            "statusSeverity": statusSeverity,
            "day": processedDay,
            "timeDiff": -1,  # null value, used to preserve dimensions needed by pandas_to_dataset
        }

        # KEY CODE: KEEPS DIMENSIONALITY CONSISTENT WITH WHAT MODEL WANTS
        # MODEL ONLY SUCCESSFULLY INFERS WHEN TAKING BATCHED INPUTS (i.e. > 1 item per field)
        for each in inferenceData:
            inferenceData[each] = [inferenceData[each], inferenceData[each]]

        dataframe = pd.DataFrame(inferenceData)
        dataset = self.__pipeline.pandas_to_dataset(dataframe, batch_size=2)
        [(modelinput, _)] = dataset.take(1)
        rawPred = self.__model.predict(modelinput)
        rawPred = int(rawPred[0][0])  # rounding the prediction to nearest second
        return rawPred

    def __validate_option(self, line: str, station: str) -> (str, str):
        line = self.__validate_line(line=line)
        stationID = self.__validate_station(station=station)
        return (stationID, line)

    def __validate_line(self, line: str) -> str:
        if line in self.ARRAYOFOPTIONS:
            return line
        else:
            raise ValueError(f"The selected line ({line}) is not supported")

    def __validate_station(self, station: str) -> str:
        if station in self.__dictofoptions:
            return self.__dictofoptions[station]
        else:
            raise ValueError(f"The selected station ({station}) is not supported")


class get_tflline(app_keyAppender):

    ARRAYOFOPTIONS = [
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

    def __init__(self, line: str):
        log.info("LOADED TFL LINE ARRIVALS API")
        self.line = line
        self.__base_url = "https://api.tfl.gov.uk/Line/"

    def get_data(self) -> list:
        self.line = self.__validate_options(option=self.line)
        url = f"{self.__base_url}{self.line}/Arrivals"
        data = self.dataFetcher(url=url)
        return data

    def __validate_options(self, option: str) -> str:
        if option in self.ARRAYOFOPTIONS:
            return option
        else:
            raise ValueError(f"The selected line ({option}) is not supported")


class get_crowdingdata(app_keyAppender):
    def __init__(self):
        log.info("LOADED CROWDING API")
        self.__base_url = "https://api.tfl.gov.uk/crowding/"
        self.__directory = os.path.join("data", "stations.json")
        with open(self.__directory, "r", encoding="utf8") as file:
            self.__dictofoptions = json.load(file)

    def get_data(self, station: str) -> float:
        stationID = self.__validate_option(station)
        if not stationID:
            log.info("Invalid option(s) provided to get_crowdingdata instance")
            return "No valid options provided"
        url = f"{self.__base_url}{stationID}/Live"
        data = self.dataFetcher(url=url)
        crowdingPercentage = data["percentageOfBaseline"]
        return crowdingPercentage

    def __validate_option(self, station: str) -> str:
        valid = True
        if station in self.__dictofoptions:
            stationID = self.__dictofoptions[station]
            return stationID
        else:
            raise ValueError(f"The selected station ({station}) is not supported")


class get_statusseverity(app_keyAppender):
    ARRAYOFOPTIONS = [
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
        self.__request_url = "https://api.tfl.gov.uk/Line/Mode/tube/Status"

    def get_data(self) -> dict:
        url = self.__request_url
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
