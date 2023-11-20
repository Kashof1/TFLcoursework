"""TO DO: 
-remove trains that have been found from dictionary
-investiage time format for mongosh, and unify this so all time data is same format
-filter out trains that are being cancelled (absurdly early)
-find other metadata that could be used
"""
from datetime import datetime, timedelta
import time

import pymongo

from core.tfl_station import get_tflstation

tfl_api = get_tflstation()

line = 'jubilee'
station = 'Stratford Underground Station'

"""Currently developing for Jubilee at Stratford; need to ensure that code works for any line at any station before implementing
multiple stations and lines at once"""

"""data[0]['currentLocation'] - sample index for data"""

dbclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = dbclient['TFLData']

existingCols = db.list_collection_names()
colName = f"{line}-{station.replace(' ', '+')}-col" #replacing the spaces with + for ease of referencing

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
    data = tfl_api.get_tubedata(line=line, station=station) 

    for each in data:
        trainId = each['vehicleId'] #defining trainId as a variable for readability; it is used often

        if trainId not in currentTrains:
            #formatting the predicted time nicely so that it can be operated on later
            formattedPrediction = datetime.strptime(each['expectedArrival'], '%Y-%m-%dT%H:%M:%SZ')
            currentTrains[trainId] = [formattedPrediction,'','']

    for currentTrainid in list(currentTrains):
        if currentTrainid == 'TrainID': #skipping header
            pass
        elif not any(dataLine['vehicleId'] == currentTrainid for dataLine in data): #if trainid no longer in api data, then train has reached station
            print('TRAIN REACHED STATION')
            eachArray = currentTrains[currentTrainid]
            predictedTime = eachArray[0]
            actualTime = datetime.now().replace(microsecond=0)

            #calculating difference in times (in seconds)
            #positive difference --> late train, negative difference --> early train
            difference = (actualTime - predictedTime).total_seconds()
            
            metavals = { #could investigate more metadata to be used
                'predictedTime' : predictedTime, 
                'actualTime' : actualTime,
                'line' : line,
                'station' : station.replace(' ','+')
                }

            currentCol.insert_one({ 
                'meta' : metavals,
                'time' : actualTime,
                'timediff' : difference
            })
            del currentTrains[currentTrainid]


    print (currentTrains)
    print ('*' * 90)
    results = currentCol.find()


    print ('*' * 90)
    time.sleep(5) #each train needs to get popped out into a separate file and deleted from here you fucking idiot thanks (deleted before loop)
    # trains that are super early could be being cancelled, decide a criteria to filter these out

