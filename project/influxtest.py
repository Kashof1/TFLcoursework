import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

token = 'ATmM0ebTkop99YYbu3mvVsgQNkTPH9HU2CAlVHDwjcpyIyfxa3aNwC1spUbHWwA7d5n-DF--PdLjY6vlMwAJ8g=='
org = "Ghar"
url = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)


bucket="TFLBucket"

write_api = client.write_api(write_options=SYNCHRONOUS)
   
for value in range(5):
  point = (
    Point("measurement1")
    .tag("tagname1", "tagvalue1")
    .field(f"field{value}", value)
  )
  write_api.write(bucket=bucket, org="Ghar", record=point)
  time.sleep(1) # separate points by 1 second

query_api = client.query_api()

query = """from(bucket: "TFLBucket")
 |> range(start: -10m)
 |> filter(fn: (r) => r._measurement == "measurement1")"""
tables = query_api.query(query, org="Ghar")

for table in tables:
  for record in table.records:
    print(record)
