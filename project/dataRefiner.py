import os
import time
import csv
import json
import polars
from datetime import datetime

from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

bucket = "TFLBucket"
url = "http://localhost:8086"
org = "Ghar"
token = "_WLF5xavdkGh95hlk0d4-obeE9GgfA6TDYYbMLTMOUyz2MqBaUZBOpG6hElvUR-wec0p---x2p7Mn66KuE0CQQ==" #superuser token
dbclient = InfluxDBClient(url=url, org=org, token=token)
write_api = dbclient.write_api(write_options=SYNCHRONOUS)
query_api = dbclient.query_api()

def rawDataLoader():
    #making a list of all the measurement names (statin line combos) so that we can query all of them from the database
    stationspath = os.path.join('data', 'stationLineCombos.json')
    with open (stationspath, 'r') as jsonfile:
        measurementNames = []
        js = json.load(jsonfile)
        for each in js:
            appendvalue = f'{each[0]}_{each[1].replace(" ", "")}'
            measurementNames.append(appendvalue)

    plcolumns =  {
        "measurementName" : [],
        "predictedTime": [], 
        "station" : [],
        "line" : [],
        "crowding" : [],
        "statusSeverity" : [],
        "timeDiff" : []
                }

    measurementCount = 0
    for measurementName in measurementNames:
        measurementCount += 1
        query = f'from(bucket: "TFLBucket")\
    |> range(start: -400d)\
    |> filter(fn: (r) => r["_measurement"] == "{measurementName}")\
    |> mean()\
    |> group()'

        result = query_api.query(org=org, query=query)
        for table in result:
            for record in table:
                plcolumns["measurementName"].append(record.values['_measurement'])
                plcolumns["predictedTime"].append(record.values['predictedTime'])
                plcolumns["station"].append(record.values['station'])
                plcolumns["line"].append(record.values['line'])
                plcolumns["crowding"].append(record.values['crowding'])
                plcolumns["statusSeverity"].append(record.values['statusSeverity'])
                plcolumns["timeDiff"].append(record.values['_value'])
        print(f'measurement {measurementCount} raw data loaded')

    outputpl = polars.DataFrame(plcolumns)
    return outputpl

def weatherAppender(rawdata):
    weatherPath = os.path.join('data','weatherdata.csv')
    weatherpl = polars.read_csv(weatherPath)
    rawIterator = rawdata.iter_rows(named=True)
    weatherColumn = {
        "appTemperature" : [],
        "precipitation" : []
    }

    for row in rawIterator:
        #formatting the time for each piece of raw data to hourly, to compare with weatherdata
        timestring = row['predictedTime']
        finaltime = datetime.fromisoformat(timestring).replace(microsecond=0, second=0, minute=0)
        finaltimeStr = finaltime.isoformat(timespec='minutes') #removing the seconds on the time to match the format of the times in the weather data

        weatherRow = weatherpl.row(by_predicate=(polars.col("time") == finaltimeStr), named=True)
        weatherColumn["appTemperature"].append(weatherRow['apparent_temperature'])
        weatherColumn["precipitation"].append(weatherRow['precipitation'])
        print(finaltimeStr)
    
    weatheredData = rawdata.with_columns(
        polars.Series(name="appTemperature", values=weatherColumn["appTemperature"]),
        polars.Series(name="precipitation", values=weatherColumn["precipitation"])
    ) 
    return weatheredData


def geoDataAppender(rawdata):
    geoPath = os.path.join('data','stationLocRaw.csv')
    geopl = polars.read_csv(geoPath)
    rawIterator = rawdata.iter_rows(named=True)
    geoColumn = {
        "latitude" : [],
        "longitude" : []
    }

    for row in rawIterator:
        station = row['station']
        station = station.replace('Underground Station', '').strip() #cleaning station names to match station names in csv file
        station = station.replace('-Underground', '').strip() #for reasons unbenknownst to me, some statiosn have '-Underground' rather than ' Underground Station' at the end...
        print(station)

        georow = geopl.row(by_predicate=((polars.col("NAME") == station) & (polars.col("NETWORK") == "London Underground")), named=True)
        geoColumn["latitude"].append(georow['y'])
        geoColumn["longitude"].append(georow['x'])
    
    geodData = rawdata.with_columns(
        polars.Series(name="latitude", values=geoColumn["latitude"]),
        polars.Series(name="longitude", values=geoColumn["longitude"])
    )
    return geodData


if __name__ == '__main__':
    rawdata = rawDataLoader()
    geodata = geoDataAppender(rawdata=rawdata)
    finalData = weatherAppender(rawdata=geodata)
    savepath = os.path.join('data','trainingdataWeatherGeo.json')
    finalData.write_json(file=savepath, pretty=True, row_oriented=True)
    
    print (finalData)


