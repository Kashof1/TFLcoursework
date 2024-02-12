import os
import time
import csv
import json
import polars

from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

bucket = "TFLBucket"
url = "http://localhost:8086"
org = "Ghar"
token = "_WLF5xavdkGh95hlk0d4-obeE9GgfA6TDYYbMLTMOUyz2MqBaUZBOpG6hElvUR-wec0p---x2p7Mn66KuE0CQQ==" #superuser token
dbclient = InfluxDBClient(url=url, org=org, token=token)
write_api = dbclient.write_api(write_options=SYNCHRONOUS)
query_api = dbclient.query_api()

def weatherAppender():
    #making a list of all the measurement names (statin line combos) so that we can query all of them from the database
    stationspath = os.path.join('data', 'stationLineCombos.json')
    with open (stationspath, 'r') as jsonfile:
        measurementNames = []
        js = json.load(jsonfile)
        for each in js:
            appendvalue = f'{each[0]}_{each[1].replace(" ", "")}'
            measurementNames.append(appendvalue)

    weatherPath = os.path.join('data','weatherdata.csv')
    weatherpl = polars.read_csv(weatherPath)

    plcolumns =  {
        "measurementName" : [],
        "station" : [],
        "line" : [],
        "crowding" : [],
        "statusSeverity" : [],
        "timeDiff" : []
                }

    for measurementName in measurementNames:
        query = f'from(bucket: "TFLBucket")\
    |> range(start: -30d)\
    |> filter(fn: (r) => r["_measurement"] == "{measurementName}")\
    |> mean()\
    |> group()'

        result = query_api.query(org=org, query=query)
        for table in result:
            for record in table:
                plcolumns["measurementName"].append(record.values['_measurement'])
                plcolumns["station"].append(record.values['station'])
                plcolumns["line"].append(record.values['line'])
                plcolumns["crowding"].append(record.values['crowding'])
                plcolumns["statusSeverity"].append(record.values['statusSeverity'])
                plcolumns["timeDiff"].append(record.values['_value'])
        print('measurement done')

    outputpl = polars.DataFrame(plcolumns)
    '''
    now need to add weatherdata to the outputpl
    
    MOVE ALL OF THE CONTENTS OF THIS FUNCTION INTO ANOTHER FUNCTION FOR LOADING THE DATA. CREATE FUNC FOR ADDING WEATHER DATA, AND ANOTHER FUNC FOR GEODATA, ETC ETC
    '''



    #print (reader.row(by_predicate=(polars.col('time') == '2024-02-12T19:00')))

if __name__ == '__main__':
    weatherAppender()