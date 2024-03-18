"""script used to create and manage all the data in the 'data' file, with mulitple different functions
that all manage and create/update different files in the folder.

This file is not intended to be called or used by any other file, and simply contains maintenance scripts."""

import csv
import json
import os
from geojson import Feature, FeatureCollection, Point, dump

from core.utils import get_url


def stationNaptanUpdater():
    final = {}
    lines = get_url("https://api.tfl.gov.uk/line/mode/tube/status")
    for line in lines:
        stop_points = get_url(f'https://api.tfl.gov.uk/line/{line["id"]}/stoppoints')
        for each in stop_points:
            if "tube" in each["modes"]:
                final.update({each["commonName"]: each["id"]})

    currentpath = os.path.dirname(os.path.realpath(__file__))
    savepath = os.path.join(currentpath, "data", "stations.json")

    with open(savepath, "w") as outputfile:
        json.dump(final, outputfile)


def stationLineCombinationUpdater():
    final = []
    lines = get_url("https://api.tfl.gov.uk/line/mode/tube/status")
    for line in lines:
        stations = []
        stop_points = get_url(f'https://api.tfl.gov.uk/line/{line["id"]}/stoppoints')
        for each in stop_points:
            if "tube" in each["modes"]:
                final.append((line["id"], each["commonName"]))

    currentpath = os.path.dirname(os.path.realpath(__file__))
    savepath = os.path.join(currentpath, "data", "stationLineCombos.json")

    print(len(final))

    with open(savepath, "w") as outputfile:
        json.dump(final, outputfile)


def stationLocationJson():
    featurearray = []
    sourceFilepath = os.path.join("data", "stationLocRaw.csv")
    destFilepath = os.path.join("data", "stationsgeo.json")
    with open(sourceFilepath, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for count, each in enumerate(reader):
            if each["NETWORK"] == "London Underground":
                geometry = Point(
                    coordinates=(float(each["y"]), float(each["x"]))
                )  # (y,x) as we are using lat, long
                properties = {
                    "name": each["NAME"],
                    "linesServed": each["LINES"],
                    "zone": each["Zone"],
                }
                featurearray.append(Feature(geometry=geometry, properties=properties))
    featurecollection = FeatureCollection(featurearray)
    with open(destFilepath, "w") as destination:
        dump(obj=featurearray, fp=destination)


if __name__ == "__main__":
    stationLocationJson()
    """while True:
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
            print ('Invalid input, try again')"""
