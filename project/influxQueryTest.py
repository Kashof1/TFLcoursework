from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime

url = "http://localhost:8086"
org = "Ghar"
token = "HSy9SVrTr0ALjgmiru2TBcBaKeIQN28broEcB4qBfPb2qNaw-zP4asKs5Pp89ShjMDRMdtV4l77PjRQ3NFTccQ==" #superuser token - could configure token with specific perms
dbclient = InfluxDBClient(url=url, org=org, token=token)
write_api = dbclient.write_api(write_options=SYNCHRONOUS)

query_api = dbclient.query_api()

measurementName = 'bakerloo_BakerStreetUndergroundStation'
predictedTime = datetime.datetime(2024,1,21,15,53,22)

query1 = f'from(bucket : "TFLBucket")\
|> range(start: -10h)\
|> filter(fn:(r) => r["_measurement"] == "{measurementName}")\
|> filter(fn:(r) => r["predictedTime"]== "{predictedTime}")'


item = query_api.query(org=org, query=query1)
if len(item):
    print ('h')