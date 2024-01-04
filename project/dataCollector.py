
from datetime import datetime, timedelta
import time

import pymongo

from core.tfl import get_tflstation, get_crowdingdata, get_disruptionstatus

station_api = get_tflstation()
crowding_api = get_crowdingdata()
disruption_api = get_disruptionstatus() #the datapoint we want is 'closureText'?

line = 'jubilee'
station = 'Stratford Underground Station'

dbclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = dbclient['TFLData']

colName = f"{line}_{station.replace(' ', '+')}_col" #replacing the spaces with + for ease of referencing
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
    arrivalsdata = station_api.get_data(line=line, station=station) 
    crowdingdata = crowding_api.get_data(station=station)
    disruptiondata = disruption_api.get_data(line = line)

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
                    'line' : line,
                    'station' : station.replace(' ','+'),
                    'crowding' : crowdingdata['percentageOfBaseline'], #value for crowding
                    'disruptionStatus' : disruptiondata['closureText']
                    }

                currentCol.insert_one({ 
                    'meta' : metavals,
                    'time' : actualTime,
                    'timediff' : difference
                })
            del currentTrains[currentTrainid] #removing the train that has reached from database of currently tracked trains


    print (currentTrains)
    print ('*' * 90)
    results = currentCol.find()


    print ('*' * 90)
    time.sleep(5) 

