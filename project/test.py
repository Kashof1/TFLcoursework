'''TO DO: 
-When a train arrives at its station, that vehicleId is removed from the dataset (i.e. no longer found)
-find a way to loop the code to repeatedly call new data from API (every 30 seconds).
-when a train has had its ActualTime field filled, remove it from the dictionary and put the information into a separate file'''
from datetime import datetime, timedelta
import time

from core.tfl_station import get_tflstation

tfl_api = get_tflstation()

line = 'jubilee'
station = 'Stratford Underground Station'

'''Currently developing for Jubilee at Stratford; need to ensure that code works for any line at any station before implementing
multiple stations and lines at once'''

'''data[0]['currentLocation'] - sample index for data'''

currentTrains = {
    "TrainID" : ['PredictedTime', 'ActualTime', 'Difference']
}

while True:
    data = tfl_api.get_tubedata(line=line, station=station) 

    for each in data:
        trainId = each['vehicleId'] #defining trainId as a variable for readability; it is used often

        if trainId not in currentTrains:
            currentTrains[trainId] = [each['expectedArrival'],'','']

    for currentTrainline in currentTrains:
        if not any(dataLine['vehicleId'] == currentTrainline for dataLine in data): 
            eachArray = currentTrainline
            predictedTime = eachArray[0] 
            actualDateTime = datetime.now().replace(microsecond=0)

            #generating python datetime objects for each time, using tflapi's format of '%Y-%m-%dT%H:%M:%SZ'
            predictedDateTime = datetime.strptime(predictedTime, '%Y-%m-%dT%H:%M:%SZ')

            #calculating difference in times (in seconds)
            #positive difference --> late train, negative difference --> early train
            difference = (actualDateTime - predictedDateTime).total_seconds()
            
            eachArray[1] = actualDateTime
            eachArray[2] = difference
            currentTrains[each['vehicleId']] = eachArray


    print (currentTrains)
    time.sleep(10)

