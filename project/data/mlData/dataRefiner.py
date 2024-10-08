import csv
import json
import os
import re
import time
from datetime import datetime

import polars
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


def rawDataLoader(days=400) -> polars.DataFrame:
    # making a list of all the measurement names (statin line combos) so that we can query all of them from the database
    stationspath = os.path.join("data", "stationLineCombos.json")
    with open(stationspath, "r") as jsonfile:
        measurementNames = []
        js = json.load(jsonfile)
        for each in js:
            appendvalue = f'{each[0]}_{each[1].replace(" ", "")}'
            measurementNames.append(appendvalue)

    plcolumns = {
        "measurementName": [],
        "predictedTime": [],
        "station": [],
        "line": [],
        "crowding": [],
        "statusSeverity": [],
        "timeDiff": [],
    }

    measurementCount = 0
    for measurementName in measurementNames:
        measurementCount += 1
        query = f'from(bucket: "TFLBucket")\
    |> range(start: -{days}d)\
    |> filter(fn: (r) => r["_measurement"] == "{measurementName}")\
    |> mean()\
    |> group()'

        result = query_api.query(org=org, query=query)
        for table in result:
            for record in table:
                if record.values["_value"] < 600 and record.values["_value"] > -300:
                    plcolumns["measurementName"].append(record.values["_measurement"])
                    plcolumns["predictedTime"].append(record.values["predictedTime"])
                    plcolumns["station"].append(record.values["station"])
                    plcolumns["line"].append(record.values["line"])
                    plcolumns["crowding"].append(record.values["crowding"])
                    plcolumns["statusSeverity"].append(record.values["statusSeverity"])
                    plcolumns["timeDiff"].append(record.values["_value"])
        print(f"measurement {measurementCount} raw data loaded")

    outputpl = polars.DataFrame(plcolumns)
    return outputpl


# adds the hourly precipitation and apparent temperature for each datapoint to the datapoint
def weatherAppender(rawdata: polars.DataFrame) -> polars.DataFrame:
    if rawdata.is_empty():
        return None
    weatherPath = os.path.join("data", "weatherdata.csv")
    weatherpl = polars.read_csv(weatherPath)
    rawIterator = rawdata.iter_rows(named=True)
    weatherColumn = {"appTemperature": [], "precipitation": []}

    for row in rawIterator:
        # formatting the time for each piece of raw data to hourly, to compare with weatherdata
        timestring = row["predictedTime"]
        finaltime = datetime.fromisoformat(timestring).replace(
            microsecond=0, second=0, minute=0
        )
        finaltimeStr = finaltime.isoformat(
            timespec="minutes"
        )  # removing the seconds on the time to match the format of the times in the weather data

        weatherRow = weatherpl.row(
            by_predicate=(polars.col("time") == finaltimeStr), named=True
        )
        weatherColumn["appTemperature"].append(weatherRow["apparent_temperature"])
        weatherColumn["precipitation"].append(weatherRow["precipitation"])
        print(finaltimeStr)

    weatheredData = rawdata.with_columns(
        polars.Series(name="appTemperature", values=weatherColumn["appTemperature"]),
        polars.Series(name="precipitation", values=weatherColumn["precipitation"]),
    )
    return weatheredData


# fetches the latitude and longitude for a given station
def lat_long_fetcher(station: str, geoPolars: polars.DataFrame) -> polars.DataFrame:
    station = station.replace(
        "Underground Station", ""
    ).strip()  # cleaning station names to match station names in csv file
    station = station.replace(
        "-Underground", ""
    ).strip()  # for reasons unbenknownst to me, some stations have '-Underground' rather than ' Underground Station' at the end...
    print(station)

    georow = geoPolars.row(
        by_predicate=(
            (polars.col("NAME") == station)
            & (polars.col("NETWORK") == "London Underground")
        ),
        named=True,
    )
    latitude = georow["y"]
    longitude = georow["x"]

    return (latitude, longitude)


# adds the latitude and longitude for the station of each datapoint to the datapoint
def geoDataAppender(rawdata: polars.DataFrame) -> polars.DataFrame:
    geoPath = os.path.join("data", "stationLocRaw.csv")
    geopl = polars.read_csv(geoPath)
    rawIterator = rawdata.iter_rows(named=True)
    geoColumn = {"latitude": [], "longitude": []}

    for row in rawIterator:
        station = row["station"]
        (latitude, longitude) = lat_long_fetcher(station=station, geoPolars=geopl)

        geoColumn["latitude"].append(latitude)
        geoColumn["longitude"].append(longitude)

    geodData = rawdata.with_columns(
        polars.Series(name="latitude", values=geoColumn["latitude"]),
        polars.Series(name="longitude", values=geoColumn["longitude"]),
    )
    return geodData


"""station line encoding method is now OBSOLETE
instead using one-hot/multi-hot encoding when
normalising the data before feeding it to the ML model"""


def station_lineEncoder(
    rawdata: polars.DataFrame,
) -> (
    polars.DataFrame
):  # this must occur last, as the other functions rely on the station name and do not work with station number
    stationPath = os.path.join("data", "stations.json")
    # assigning each line a number, between 1 and 11
    lineDict = {
        "bakerloo": 1,
        "central": 2,
        "circle": 3,
        "district": 4,
        "hammersmith-city": 5,
        "jubilee": 6,
        "metropolitan": 7,
        "northern": 8,
        "piccadilly": 9,
        "victoria": 10,
        "waterloo-city": 11,
    }
    # assigning each station a number, between 1 and 272
    with open(stationPath, "r") as file:
        stationDict = json.load(file)
        for number, name in enumerate(stationDict):
            stationDict[name] = number + 1

    appendCols = {"stationNumber": [], "lineNumber": []}
    rawIterator = rawdata.iter_rows(named=True)

    for row in rawIterator:
        station = row["station"]
        line = row["line"]
        stationN = stationDict[station]
        lineN = lineDict[line]
        appendCols["stationNumber"].append(stationN)
        appendCols["lineNumber"].append(lineN)
        print(f"replacing {station} with {stationN} and {line} with {lineN}")

    finalData = rawdata.with_columns(
        polars.Series(name="stationNumber", values=appendCols["stationNumber"]),
        polars.Series(name="lineNumber", values=appendCols["lineNumber"]),
    )
    finalData.drop_in_place("station")  # removing the named stations at this point
    return finalData


# groups the time into half-hour intervals and formats
def time_bucketizer(date_time: datetime) -> str:
    strtime = date_time.time().replace(microsecond=0).strftime("%H:%M:%S")

    # getting the hour and minute values using regex
    minuteSearch = re.search(pattern=r":\d+:", string=strtime)
    hourSearch = re.search(pattern=r"\d+:", string=strtime)
    minuteInt = int(minuteSearch.group().strip(":"))
    hourStr = hourSearch.group().strip(":")
    interval = 30  # currently groups into 30-minute groups.
    minStr = str((minuteInt // interval) * interval).ljust(
        2, "0"
    )  # numbers between 0-30 return '00', 30-59 return '30', hence grouping into 30m intervals
    finalTime = f"{hourStr}:{minStr}:00"

    return finalTime


# converts the day to a string between 1 and 7
def date_bucketizer(date_time: datetime) -> str:
    day = str(date_time.isoweekday())
    return day


# groups the time into half-hour intervals (bucketizes it) and also
# acquiring and appending the day of the week from the date
def dateTimeConvertor(rawdata: polars.DataFrame) -> polars.DataFrame:
    appendCols = {"day": [], "time": []}
    rawIterator = rawdata.iter_rows(named=True)

    for row in rawIterator:
        oldTime = datetime.strptime(row["predictedTime"], f"%Y-%m-%d %H:%M:%S")

        finalTime = time_bucketizer(date_time=oldTime)
        day = date_bucketizer(date_time=oldTime)

        appendCols["day"].append(day)
        appendCols["time"].append(finalTime)
        print(f"time is {finalTime} and day is {day}")

    finalData = rawdata.with_columns(
        polars.Series(name="day", values=appendCols["day"]),
        polars.Series(name="time", values=appendCols["time"]),
    )

    finalData.drop_in_place("predictedTime")
    return finalData


if __name__ == "__main__":
    bucket = "TFLBucket"
    url = "http://localhost:8086"
    org = "Ghar"
    token = "_WLF5xavdkGh95hlk0d4-obeE9GgfA6TDYYbMLTMOUyz2MqBaUZBOpG6hElvUR-wec0p---x2p7Mn66KuE0CQQ=="  # superuser token
    dbclient = InfluxDBClient(url=url, org=org, token=token)
    write_api = dbclient.write_api(write_options=SYNCHRONOUS)
    query_api = dbclient.query_api()

    rawdata = rawDataLoader()
    geodata = geoDataAppender(rawdata=rawdata)
    weatherData = weatherAppender(rawdata=geodata)
    finalData = dateTimeConvertor(rawdata=weatherData)
    finalData.drop_in_place(
        "measurementName"
    )  # this data won't be used to train the model and is therefore dropped here

    trainPath = os.path.join("data", "mlData", "trainingdata.json")
    testPath = os.path.join("data", "mlData", "testingdata.json")
    valPath = os.path.join("data", "mlData", "validatingdata.json")

    finalData = finalData.sample(
        fraction=1, shuffle=True, seed=80626
    )  # randomly shuffling the dataset
    dataSize = len(finalData)
    trainSize = int(0.8 * dataSize)  # 80% of data used for training
    testandvalSize = dataSize - trainSize
    trainData, testandvalData = finalData.head(trainSize), finalData.tail(
        testandvalSize
    )  # 20% goes to testing and validating, which is split then in half for 80:10:10 train:test:validate
    testData, valData = testandvalData.head(
        int(0.5 * testandvalSize)
    ), testandvalData.tail(int(0.5 * testandvalSize))

    trainData.write_json(file=trainPath, pretty=True, row_oriented=True)
    testData.write_json(file=testPath, pretty=True, row_oriented=True)
    valData.write_json(file=valPath, pretty=True, row_oriented=True)
    print("TRAINING DATA")
    print(trainData)
    print("*" * 30)
    print("TESTING DATA")
    print(testData)
    print("*" * 30)
    print("VALIDATING DATA")
    print(valData)
