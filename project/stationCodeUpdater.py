'''This script updates the json file of all of the common station names and their associated naptanIDs'''

import json
import os

from core.utils import get_url

def stationNaptanUpdater():
    final = {}
    lines = get_url('https://api.tfl.gov.uk/line/mode/tube/status')
    for line in lines:
        stop_points = get_url(f'https://api.tfl.gov.uk/line/{line["id"]}/stoppoints')
        for each in stop_points:
            if 'tube' in each['modes']:
                final.update({each['commonName'] : each['id']})

    currentpath = os.path.dirname(os.path.realpath(__file__))
    savepath = os.path.join(currentpath,'data','stations.json')

    with open (savepath, 'w') as outputfile:
        json.dump(final, outputfile)

def stationLineCombinationUpdater():
    final = []
    lines = get_url('https://api.tfl.gov.uk/line/mode/tube/status')
    for line in lines:
        stations = []
        stop_points = get_url(f'https://api.tfl.gov.uk/line/{line["id"]}/stoppoints')
        for each in stop_points:
            if 'tube' in each['modes']:
                final.append((line['name'], each['commonName']))
    
    currentpath = os.path.dirname(os.path.realpath(__file__))
    savepath = os.path.join(currentpath,'data','stationLineCombos.json')

    print (len(final))

    with open (savepath, 'w') as outputfile:
        json.dump(final, outputfile)



if __name__ == '__main__':
    while True:
        decision = int(input('Enter 1 to update the stations and their naptanIDs, enter 2 to update the station-line combinations, enter 3 to break'))
        if decision == 1:
            stationNaptanUpdater()
            break
        elif decision == 2:
            stationLineCombinationUpdater()
            break
        elif decision == 3:
            break
        else:
            print ('Invalid input, try again')