'''database token and cpu processes configured for raspberry pi on this file'''

import concurrent.futures
from datetime import datetime, timedelta
import json
import os
import threading
import time
import sys
from discord_webhook import DiscordWebhook #webhooks used for monitoring of data collection to ensure it is still running.


from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from core.tfl import get_tflstation, get_crowdingdata, get_disruptionstatus, get_statusseverity

url = "http://localhost:8086"
org = "Ghar"
token = "zpQ87ye8X-oTBcHepculUHxKN-_Ote1JBtK8bWIjnyZQ-zQvQQYGB-Cf-tmPjg0N2nKCJi4nwuX0XRg4iiFG1A==" #superuser token - could configure token with specific perms
dbclient = InfluxDBClient(url=url, org=org, token=token)
write_api = dbclient.write_api(write_options=SYNCHRONOUS)
query_api = dbclient.query_api()

class tfl_dataCollector:
    def __init__(self, line, station, station_api, crowding_api, disruption_api, status_api) -> None:
        self.line = line
        self.station = station
        self.station_api = station_api
        self.crowding_api = crowding_api
        #self.disruption_api = disruption_api --removed for performance reasons + redundant
        self.status_api = status_api

    def collector(self):
        measurementName = f"{self.line}_{self.station.replace(' ', '')}" #replacing the spaces with blank space for ease of referencing

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
                            writeData = Point(measurement_name=measurementName) \
                                .tag('predictedTime', predictedTime) \
                                .tag('actualTime', actualTime) \
                                .tag('line', self.line) \
                                .tag('station', self.station) \
                                .tag('crowding', crowdingdata['percentageOfBaseline']) \
                                .tag('statusSeverity', statusSeverityValue) \
                                .field('timeDiff', difference) \
                                .time(time=actualTime)
                            
                            #query to check if the data we are about to add already exists (uniquely identified by the predicted time)
                            #this avoids repeats caused by unreliability of TFL API
                            '''query = f'from(bucket:"TFLBucket")\
                            |> range(start: -1h)\
                            |> filter(fn:(r) => r["_measurement"]== "{measurementName}")\
                            |> filter(fn:(r) => r["predictedTime"]== "{predictedTime}")\ '
                            
                            try:
                                queryReturn = query_api.query(org=org, query=query)
                            except Exception as e:
                                print (e)

                            if (len(queryReturn)): 
                                write_api.write(bucket='TFLBucket', org=org, record=writeData)'''
                            
                            write_api.write(bucket='TFLBucket', org=org, record=writeData)

                        del currentTrains[currentTrainid] #removing the train that has reached from database of currently tracked trains


                time.sleep(7)
            
            except:
                webhookMessage = f'The error is: "{sys.exc_info()}", and the current thread number is {threading.active_count()}'
                errorwebhook = DiscordWebhook(url="https://discord.com/api/webhooks/1195118360057360486/ACTrZCQFrhOtda1lzj9cHklXRX9fG8DbwKQun-NybfImzhepf-loiniN1BCy6kAKX7av", content=webhookMessage)
                errorwebhook.execute()
                time.sleep(5)
    
def runStatusUpdater():
    
    while True:
        try:
            isRunningMessage = f'The current time is {datetime.now()}. The program is currently running {threading.active_count()} threads'
            isRunningwebhook = DiscordWebhook(url='https://discord.com/api/webhooks/1195117811303981197/BP2YNLMv5EQeM_ZEnY9wvv992dONJPVf-hGae9CtHO0Eu-qXF9K9F3FjRUrcLPTZz5Sn', content=isRunningMessage)
            isRunningwebhook.execute()
            time.sleep(600)
        except Exception as e: #if it errors wait a few seconds and try again until it works
            errorWebhook = DiscordWebhook(url='https://discord.com/api/webhooks/1195117811303981197/BP2YNLMv5EQeM_ZEnY9wvv992dONJPVf-hGae9CtHO0Eu-qXF9K9F3FjRUrcLPTZz5Sn', content=f'crashed: {e}')
            errorWebhook.execute()
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
    with concurrent.futures.ProcessPoolExecutor(max_workers=384) as executor:
        count = 0
        for instance in range (384):
            print (count)
            count+=1
            threads.append(executor.submit(dictOfInstances[instance].collector))
            time.sleep(0.1) #ensuring no sudden burden on processor

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
