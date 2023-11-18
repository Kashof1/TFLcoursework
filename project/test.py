"""TO DO: 
-When a train arrives at its station, that vehicleId is removed from the dataset (i.e. no longer found)
-find a way to loop the code to repeatedly call new data from API (every 30 seconds).
-when a train has had its ActualTime field filled, remove it from the dictionary and put the information into a separate file"""
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

    currentTrainIterator = iter(currentTrains) #iterator used to skip the first item in currentTrains, which serves as a header
    next(currentTrainIterator)
    for currentTrainid in currentTrainIterator:
        if not any(dataLine['vehicleId'] == currentTrainid for dataLine in data): #if trainid no longer in api data, then train has reached station
            print('TRAIN REACHED STATION')
            eachArray = currentTrains[currentTrainid]
            predictedTime = eachArray[0]
            actualTime = datetime.now().replace(microsecond=0)

            #calculating difference in times (in seconds)
            #positive difference --> late train, negative difference --> early train
            difference = (actualTime - predictedTime).total_seconds()
            
            metavals = { #could investigate more metadata to be used
                'predictedTime' : predictedTime, #FIGURE OUT HOW TO MAKE THIS ISO 
                'actualTime' : actualTime,
                'line' : line,
                'station' : station.replace(' ','+')
                }

            currentCol.insert_one({ #ERROR IN HOW COLLECTION IS BEING REFERENCED (potentially resolved?)
                'meta' : metavals,
                'time' : actualTime,
                'timediff' : difference
            })


    print (currentTrains)
    print ('*' * 90)
    results = currentCol.find()
    for doc in results: #GETS STUCK IN INFINITE LOOP HERE(?)... USE MONGOSH TO MONITOR DATABASE STATES
        print(doc)

    print ('*' * 90)
    time.sleep(5) #each train needs to get popped out into a separate file and deleted from here you fucking idiot thanks
    # trains that are super early could be being cancelled

