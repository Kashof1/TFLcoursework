'''this file contains the optimised code for data collection, based on performance metrics
from the original version'''

'''database token and cpu processes are currently configured for the raspberry pi on this file'''

import concurrent.futures
from datetime import datetime
import json
import os
import threading
import time
import sys
from discord_webhook import DiscordWebhook

from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from core.tfl import get_tflline, get_crowdingdata, get_statusseverity

url = "http://localhost:8086"
org = "Ghar"
token = "zpQ87ye8X-oTBcHepculUHxKN-_Ote1JBtK8bWIjnyZQ-zQvQQYGB-Cf-tmPjg0N2nKCJi4nwuX0XRg4iiFG1A==" #superuser token - could configure token with specific perms
dbclient = InfluxDBClient(url=url, org=org, token=token)
write_api = dbclient.write_api(write_options=SYNCHRONOUS)
query_api = dbclient.query_api()

class tfl_dataCollector:
    def __init__(self, line, crowding_api):
        self.crowding_api = crowding_api #passing in the crowding api so that all line scrapers use the same one (saving resources)
        self.line = line
        self.line_api = get_tflline(line=line)
        
        #building list of stations for this line
        directory = os.path.join('data','stationLineCombos.json')
        with open (directory, 'r', encoding='utf8') as file:
            jsonf = json.load(file)
            self.stationList = [item[1] for item in jsonf if item[0] == self.line]

    def arrivals_collector(self):
        self.__currentTrains = {"TrainID" : ['Station','PredictedTime', 'ActualTime', 'Difference']} #private as this should not be monitored or changed by anything outside this method
        while True:
            arrivalsdata = self.line_api.get_data()

            #this section adds any new, previously untracked trains to the list
            for each in arrivalsdata:
                trainId = each['vehicleId']
                if trainId not in self.__currentTrains:
                    #formatting the predicted time nicely so that it can be operated on later
                    formattedPrediction = datetime.strptime(each['expectedArrival'], '%Y-%m-%dT%H:%M:%SZ')
                    stationName = each['stationName']
                    self.__currentTrains[trainId] = [stationName, formattedPrediction,'','']
            
            #this section checks to see if any trains have arrived (i.e. are no longer in the published predictions)
            for currentTrainid in list(self.__currentTrains):
                if currentTrainid == 'TrainID': #skipping header
                    pass
                elif not any(dataLine['vehicleID'] == currentTrainid for dataLine in arrivalsdata):
                    currentArray = self.__currentTrains[currentTrainid]
                    predictedTime = currentArray[1]
                    actualTime = datetime.now().replace(microsecond=0) #don't need microsecond precision, excessively redundant
                    currentStation = currentArray[0]

                    #calculating difference in times (in seconds)
                    #positive difference --> late train, negative difference --> early train
                    difference = (actualTime - predictedTime).total_seconds()
                    if difference > -600: 
                        self.database_appender(
                            predictedTime=predictedTime,
                            actualTime=actualTime,
                            difference=difference,
                            station=currentStation
                        )
                        del self.__currentTrains[currentTrainid]
            time.sleep(20)

    def database_appender(self,
            predictedTime,
            actualTime,
            difference,
            station):
        measurementName = f'{self.line}_{station.replace(" ","")}'
        crowdingValue = self.crowding_api.get_data(station=station)
        statusSeverityValue = currentStatusDictionary[self.line]

        writeData = Point(measurement_name=measurementName) \
            .tag('predictedTime', predictedTime) \
            .tag('actualTime', actualTime) \
            .tag('line', self.line) \
            .tag('station', station) \
            .tag('crowding', crowdingValue) \
            .tag('statusSeverity', statusSeverityValue) \
            .field('timeDiff', difference) \
            .time(time=actualTime)

        write_api.write(bucket='TFLBucket', org=org, record=writeData)



    def status_collector(self, status_api):
        while True:
            global currentStatusDictionary 
            currentStatusDictionary = status_api.get_statusseverity()
            time.sleep(20)


if __name__ == '__main__':
    lines = ["bakerloo","central","circle","district","hammersmith-city","jubilee","metropolitan","northern","piccadilly","victoria","waterloo-city"]
    crowding_api = get_crowdingdata()
    dictOfLineScrapers = {}
    for line in lines:
        dictOfLineScrapers[line] = tfl_dataCollector(line=line, crowding_api=crowding_api)

    threads = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=11) as executor:
        for linescraper in dictOfLineScrapers:
            print(linescraper) #to show that all threads have loaded in terminal
            threads.append(executor.submit(dictOfLineScrapers[linescraper].arrivals_collector))

    
