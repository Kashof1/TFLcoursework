from core.tfl_station import get_tflstation

tfl_api = get_tflstation()

data = tfl_api.get_tubedata('jubilee', 'Stratford Underground Station') 
'''Currently developing for Jubilee at Stratford; need to ensure that code works for any line at any station before implementing
multiple stations and lines at once'''

'''data[0]['currentLocation'] - sample index for data'''

currentTrains = [['TrainID','PredictedTime','ActualTime','Difference']]

for each in data:
    if each['vehicleId'] not in currentTrains:
        pass

test  = [['a',1,2,3],['b',4,5,6],['c',7,8,9]]
if any('a' in sub for sub in test):
    print ('yes')