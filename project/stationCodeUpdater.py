"""script used to create and manage all the data in the 'data' file, with mulitple different functions
that all manage and create/update different files in the folder.

This file is not intended to be called or used by any other file, and simply contains maintenance scripts."""

import csv
import json
import os

from core.utils import get_url
from geojson import Feature, FeatureCollection, LineString, Point, dump


def stationNaptanUpdater():  # updates the file containing station names and their associated naptanids
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


def stationLineCombinationUpdater():  # updates the file that describes what lines each station serves
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


def stationLocationJson():  # processes the raw station locations downloaded from the internet and saves to a new file
    featurearray = []
    sourceFilepath = os.path.join("data", "raw", "stationLocRaw.csv")
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
    # formattign as a featurecollection for later use with leafletjs
    featurecollection = FeatureCollection(featurearray)
    with open(destFilepath, "w") as destination:
        dump(obj=featurearray, fp=destination)


def linesGeoJson():  # processes the vectors of all of the lines (removing non-underground data points)
    featurearray = []
    lines = [
        "Bakerloo",
        "Central",
        "Circle",
        "District",
        "Hammersmith and City",
        "Jubilee",
        "Metropolitan",
        "Northern",
        "Piccadilly",
        "Victoria",
        "Waterloo and City",
    ]
    source = os.path.join("data", "raw", "rawlinesgeo.json")
    dest = os.path.join("data", "geoline.json")

    with open(source, "r") as jsonfile:
        features = json.load(jsonfile)["features"]
        for each in features:
            name = each["properties"]["name"]
            # names come in formats like "Bakerloo - Marylebone to Baker Street"
            referencedLine = name.split("-")[0].strip()

            if referencedLine in lines:
                featurearray.append(each)

    with open(dest, "w") as destination:
        dump(obj=featurearray, fp=destination)


if __name__ == "__main__":
    # call one of the scripts here to execute it
    linesGeoJson()
