from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

url = "http://localhost:8086"
org = "Ghar"
token = "_WLF5xavdkGh95hlk0d4-obeE9GgfA6TDYYbMLTMOUyz2MqBaUZBOpG6hElvUR-wec0p---x2p7Mn66KuE0CQQ==" #superuser token
dbclient = InfluxDBClient(url=url, org=org, token=token)
write_api = dbclient.write_api(write_options=SYNCHRONOUS)
query_api = dbclient.query_api()