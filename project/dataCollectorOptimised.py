"""this file contains the optimised code for data collection, based on performance metrics
from the original version"""

"""database token and cpu processes are currently configured for the raspberry pi on this file"""

import concurrent.futures
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime

from core.tfl import get_crowdingdata, get_statusseverity, get_tflline
from discord_webhook import DiscordWebhook
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

log = logging.getLogger(__name__)

url = "http://localhost:8086"
org = "Ghar"
token = "_WLF5xavdkGh95hlk0d4-obeE9GgfA6TDYYbMLTMOUyz2MqBaUZBOpG6hElvUR-wec0p---x2p7Mn66KuE0CQQ=="  # superuser token - could configure token with specific perms
dbclient = InfluxDBClient(url=url, org=org, token=token)
write_api = dbclient.write_api(write_options=SYNCHRONOUS)
query_api = dbclient.query_api()

recentAppend = "No recent appends at the moment"


class tfl_dataCollector:
    def __init__(self, line):
        self.crowding_api = get_crowdingdata()
        self.status_api = get_statusseverity()
        self.line = line
        self.line_api = get_tflline(line=line)

        # building list of stations for this line
        directory = os.path.join("data", "stationLineCombos.json")
        with open(directory, "r", encoding="utf8") as file:
            jsonf = json.load(file)
            self.stationList = [item[1] for item in jsonf if item[0] == self.line]

    def arrivals_collector(self):
        try:
            self.__currentTrains = {
                "TrainID": ["Station", "PredictedTime", "ActualTime", "Difference"]
            }  # private as this should not be monitored or changed by anything outside this method
            while True:
                arrivalsdata = self.line_api.get_data()
                # this section adds any new, previously untracked trains to the list
                for each in arrivalsdata:
                    trainId = each["vehicleId"]
                    if trainId not in self.__currentTrains:
                        # formatting the predicted time nicely so that it can be operated on later
                        formattedPrediction = datetime.strptime(
                            each["expectedArrival"], "%Y-%m-%dT%H:%M:%SZ"
                        )
                        stationName = each["stationName"]
                        self.__currentTrains[trainId] = [
                            stationName,
                            formattedPrediction,
                            "",
                            "",
                        ]

                # this section checks to see if any trains have arrived (i.e. are no longer in the published predictions)
                for currentTrainid in list(self.__currentTrains):
                    if currentTrainid == "TrainID":  # skipping header
                        pass
                    elif not any(
                        dataLine["vehicleId"] == currentTrainid
                        for dataLine in arrivalsdata
                    ):
                        currentArray = self.__currentTrains[
                            currentTrainid
                        ]  # getting the array of data for the train that has arrived
                        predictedTime = currentArray[1]
                        actualTime = datetime.now().replace(
                            microsecond=0
                        )  # don't need microsecond precision, excessive and redundant
                        currentStation = currentArray[0]

                        # calculating difference in times (in seconds)
                        # positive difference --> late train, negative difference --> early train
                        difference = (actualTime - predictedTime).total_seconds()
                        if difference > -600:
                            self.database_appender(
                                predictedTime=predictedTime,
                                actualTime=actualTime,
                                difference=difference,
                                station=currentStation,
                            )

                            del self.__currentTrains[
                                currentTrainid
                            ]  # deleting the arrived train from the trains being tracked
                time.sleep(10)
        except Exception as e:
            print(e)

    def database_appender(self, predictedTime, actualTime, difference, station):
        measurementName = f'{self.line}_{station.replace(" ","")}'
        crowdingValue = self.crowding_api.get_data(station=station)
        statusSeverityDictionary = (
            self.status_collector()
        )  # status collector is only called when an append is made to minimise calls
        statusSeverityValue = statusSeverityDictionary[self.line]

        writeData = (
            Point(measurement_name=measurementName)
            .tag("predictedTime", predictedTime)
            .tag("actualTime", actualTime)
            .tag("line", self.line)
            .tag("station", station)
            .tag("crowding", crowdingValue)
            .tag("statusSeverity", statusSeverityValue)
            .field("timeDiff", difference)
            .time(time=actualTime)
        )

        write_api.write(bucket="TFLBucket", org=org, record=writeData)

    def status_collector(self):
        currentStatusDictionary = self.status_api.get_data()
        return currentStatusDictionary


def runStatusUpdater():
    while True:
        try:
            isRunningMessage = f"The current time is {datetime.now()}. The program is currently running {threading.active_count()} threads."
            isRunningwebhook = DiscordWebhook(
                url="https://discord.com/api/webhooks/1195117811303981197/BP2YNLMv5EQeM_ZEnY9wvv992dONJPVf-hGae9CtHO0Eu-qXF9K9F3FjRUrcLPTZz5Sn",
                content=isRunningMessage,
            )
            isRunningwebhook.execute()
            time.sleep(600)
        except (
            Exception
        ):  # if it errors wait a few seconds and try again until it works
            while True:
                time.sleep(5)
                isRunningwebhook.execute()
                break


if __name__ == "__main__":
    lines = [
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
    dictOfLineScrapers = {}
    for line in lines:
        dictOfLineScrapers[line] = tfl_dataCollector(line=line)

    statusCollectorInstance = tfl_dataCollector(line="placeholder")
    statusCollectorThread = threading.Thread(
        target=statusCollectorInstance.status_collector
    )
    statusCollectorThread.start()

    """status collector thread was started first as all the other threads need the current status. error would be thrown
    if no such status exists"""
    threads = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=11
    ) as executor:  # using process pool as this better leverages the processing power of the RPi5
        for linescraper in dictOfLineScrapers:
            print(linescraper)  # to show that all threads have loaded in terminal
            threads.append(
                executor.submit(dictOfLineScrapers[linescraper].arrivals_collector)
            )
            time.sleep(0.1)  # preventing sudden burden on processor

        runUpdateThread = threading.Thread(target=runStatusUpdater, daemon=True)
        runUpdateThread.start()
        # set as a daemon as we dont want this thread to stay alive when all other threads have died and wrongly inform us that program is running
