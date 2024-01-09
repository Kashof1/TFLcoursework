import concurrent.futures
from datetime import datetime, timedelta
import json
import os
import threading
import time
import sys

import pymongo

from core.tfl import get_tflstation, get_crowdingdata, get_disruptionstatus, get_statusseverity

dbclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = dbclient['TFLData']

class tfl_dataCollector:
    def __init__(self, line, station, station_api, crowding_api, disruption_api, status_api) -> None:
        self.line = line
        self.station = station
        self.station_api = station_api
        self.crowding_api = crowding_api
        self.disruption_api = disruption_api
        self.status_api = status_api

    def collector(self):
        colName = f"{self.line}_{self.station.replace(' ', '+')}_col" #replacing the spaces with + for ease of referencing
        existingCols = db.list_collection_names()
        if colName not in existingCols:
            currentCol = db.create_collection(colName, timeseries={
                    'timeField': "time",
                    'metaField': "meta",
                    'granularity': "seconds"
            })
        currentCol = db[colName] 

        currentTrains = {
            "TrainID" : ['PredictedTime', 'ActualTime', 'Difference']
        }
        while True:
            try:
                arrivalsdata = self.station_api.get_data(line=self.line, station=self.station) 
                crowdingdata = self.crowding_api.get_data(station=self.station)
                disruptionStatus = self.disruption_api.get_data(line=self.line)
                statusSeverityValue = self.status_api.get_data(line=self.line)


                for each in arrivalsdata:
                    trainId = each['vehicleId'] #defining trainId as a variable for readability; it is used often

                    if trainId not in currentTrains:
                        #formatting the predicted time nicely so that it can be operated on later
                        formattedPrediction = datetime.strptime(each['expectedArrival'], '%Y-%m-%dT%H:%M:%SZ')
                        currentTrains[trainId] = [formattedPrediction,'','']

                for currentTrainid in list(currentTrains):
                    if currentTrainid == 'TrainID': #skipping header
                        pass
                    elif not any(dataLine['vehicleId'] == currentTrainid for dataLine in arrivalsdata): #if trainid no longer in api data, then train has reached station
                        eachArray = currentTrains[currentTrainid]
                        predictedTime = eachArray[0]
                        actualTime = datetime.now().replace(microsecond=0)

                        #calculating difference in times (in seconds)
                        #positive difference --> late train, negative difference --> early train
                        difference = (actualTime - predictedTime).total_seconds()

                        if difference > -600: #trains arriving more than 10 minutes early are outliers, likely cancelled trains
                            metavals = { #could investigate more metadata to be used
                                'predictedTime' : predictedTime, 
                                'actualTime' : actualTime,
                                'line' : self.line,
                                'station' : self.station.replace(' ','+'),
                                'crowding' : crowdingdata['percentageOfBaseline'], #value for crowding
                                'disruptionStatus' : disruptionStatus,
                                'statusSeverity' : statusSeverityValue
                                }

                            #only adding this new prediction to the database if it isn't already there (uniquely identified using predictedTime)
                            if not currentCol.count_documents({'meta.predictedTime' : predictedTime}): 
                                print ('should be appending')
                                currentCol.insert_one({ 
                                    'meta' : metavals,
                                    'time' : actualTime,
                                    'timediff' : difference
                                })
                        del currentTrains[currentTrainid] #removing the train that has reached from database of currently tracked trains
            except:
                print(sys.exc_info())
                time.sleep(10)

            print (currentTrains)
            time.sleep(5)


if __name__ == '__main__':
    #getting file with all the station line pairs
    stationLineDirectory = os.path.join('data', 'stationLineCombos.json')
    with open (stationLineDirectory, 'r', encoding='utf8') as file:
        stationLine = json.load(file)

    amountOfPairs = len(stationLine)

    station_api = get_tflstation()
    crowding_api = get_crowdingdata()
    disruption_api = get_disruptionstatus() 
    status_api = get_statusseverity() 

    dictOfInstances = {}
    for x in range(amountOfPairs):
        line = stationLine[x][0]
        station = stationLine[x][1]
        dictOfInstances[x] = tfl_dataCollector(
            line=line,
            station=station,
            station_api=station_api,
            crowding_api=crowding_api,
            disruption_api=disruption_api,
            status_api=status_api
        )

    threads = []
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=384) as executor:
        for instance in dictOfInstances:
            threads.append(executor.submit(dictOfInstances[instance].collector))
            print (threading.active_count())
    end = time.time()
    print ('final time = ', end-start)

    '''while True:
        for each in dictOfInstances:
            start = time.time()
            dictOfInstances[each].collector()
            end = time.time()
            print ('final time is', end-start)
        time.sleep(5)'''

"""investigating api request cap"""