import concurrent.futures
from datetime import datetime, timedelta
import json
import os
import threading
import time
import sys
from discord_webhook import DiscordWebhook #webhooks used for monitoring of data collection to ensure it is still running.

import pymongo

from core.tfl import get_tflstation, get_crowdingdata, get_disruptionstatus, get_statusseverity

dbclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = dbclient['TFLDatabase']

class tfl_dataCollector:
    def __init__(self, line, station, station_api, crowding_api, disruption_api, status_api) -> None:
        self.line = line
        self.station = station
        self.station_api = station_api
        self.crowding_api = crowding_api
        #self.disruption_api = disruption_api --removed for performance reasons + redundant
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

        crowdingStart = time.time()
        statusStart = time.time()
        while True:
            try:
                crowdingdata = self.crowding_api.get_data(station=self.station)
                statusSeverityValue = self.status_api.get_data(line=self.line)
                break
            except:
                time.sleep(1)
        #ensuring crowding and status data is available in first pass, as both timers will not be large enough for data to be collected yet
        while True:
            try:
                #disruptionStatus = self.disruption_api.get_data(line=self.line)

                crowdingEnd = time.time()
                statusEnd = time.time()
                crowdingElapsedTime = crowdingEnd - crowdingStart
                statusElapsedTime = statusEnd - statusStart

                if crowdingElapsedTime >= 45:
                    crowdingdata = self.crowding_api.get_data(station=self.station)
                    crowdingStart = time.time()
                
                if statusElapsedTime >= 75:
                    statusSeverityValue = self.status_api.get_data(line=self.line)
                    statusStart = time.time()

                arrivalsdata = self.station_api.get_data(line=self.line, station=self.station) 



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
                                'statusSeverity' : statusSeverityValue
                                }

                            #only adding this new prediction to the database if it isn't already there (uniquely identified using predictedTime)
                            if not currentCol.count_documents({'meta.predictedTime' : predictedTime}): 
                                currentCol.insert_one({ 
                                    'meta' : metavals,
                                    'time' : actualTime,
                                    'timediff' : difference
                                })
                                print(threading.active_count())
                        del currentTrains[currentTrainid] #removing the train that has reached from database of currently tracked trains


                time.sleep(3)
            
            except:
                webhookMessage = f'The error is: "{sys.exc_info()}", and the current thread number is {threading.active_count()}'
                errorwebhook = DiscordWebhook(url="https://discord.com/api/webhooks/1195118360057360486/ACTrZCQFrhOtda1lzj9cHklXRX9fG8DbwKQun-NybfImzhepf-loiniN1BCy6kAKX7av", content=webhookMessage)
                errorwebhook.execute()
                time.sleep(5)
    
def runStatusUpdater():
    isRunningMessage = f'The current time is {datetime.now()} and the program is still alive'
    isRunningwebhook = DiscordWebhook(url='https://discord.com/api/webhooks/1195117811303981197/BP2YNLMv5EQeM_ZEnY9wvv992dONJPVf-hGae9CtHO0Eu-qXF9K9F3FjRUrcLPTZz5Sn', content=isRunningMessage)
    while True:
        try:
            isRunningwebhook.execute()
            time.sleep(1800)
        except: #if it errors wait a few seconds and try again until it works
            time.sleep(5)
            isRunningwebhook.execute()
        


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

    def hook(args):
        print (f'Failed thread. {args.exc_value}')

    threading.excepthook = hook
    threads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=384) as executor:
        for instance in range (384):
            threads.append(executor.submit(dictOfInstances[instance].collector))
            #time.sleep(0.1) --> redundant on the server as it is already so slow, but needed on faster devices such as laptop
        
        statusthread = threading.Thread(target=runStatusUpdater, daemon=True) #set as daemon thread so that it terminates if all other processes die
        #... we don't want this to be the only thread running, causing us to get the false message that the program is still operational.
        statusthread.start()
        

        baselineThreads = threading.active_count()
        baselineMessage = f'The data collector has been initialised. The baseline thread count is {baselineThreads}'
        baselineWebhook = DiscordWebhook(url='https://discord.com/api/webhooks/1195117811303981197/BP2YNLMv5EQeM_ZEnY9wvv992dONJPVf-hGae9CtHO0Eu-qXF9K9F3FjRUrcLPTZz5Sn', content=baselineMessage)
        baselineWebhook.execute()
    
    #code reaches this point if the thread pool executor is closed (meaning all threads are dead)
    criticalMessage = 'CRITICAL ERROR: All threads are closed'
    criticalWebhook = DiscordWebhook(url='https://discord.com/api/webhooks/1195117811303981197/BP2YNLMv5EQeM_ZEnY9wvv992dONJPVf-hGae9CtHO0Eu-qXF9K9F3FjRUrcLPTZz5Sn', content=criticalMessage)
    criticalWebhook.execute()



