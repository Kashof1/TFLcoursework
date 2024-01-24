'''this file contains the optimised code for data collection, based on performance metrics
from the original version'''

'''database token and cpu processes are currently configured for the raspberry pi on this file'''

import concurrent.futures
from datetime import datetime
import json
import os
import threading
import time
import sys
from discord_webhook import DiscordWebhook

from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from core.tfl import get_tflline, get_crowdingdata, get_statusseverity

url = "http://localhost:8086"
org = "Ghar"
token = "zpQ87ye8X-oTBcHepculUHxKN-_Ote1JBtK8bWIjnyZQ-zQvQQYGB-Cf-tmPjg0N2nKCJi4nwuX0XRg4iiFG1A==" #superuser token - could configure token with specific perms
dbclient = InfluxDBClient(url=url, org=org, token=token)
write_api = dbclient.write_api(write_options=SYNCHRONOUS)
query_api = dbclient.query_api()

class tfl_dataCollector:
    def __init__(self, line):
        self.line = line
        self.line_api = get_tflline(line=line)
        
        #building list of stations for this line
        directory = os.path.join('data','stationLineCombos.json')
        with open (directory, 'r', encoding='utf8') as file:
            jsonf = json.load(file)
            self.stationList = [item[1] for item in jsonf if item[0] == self.line]
            self.lineList = list(set([item[0] for item in jsonf]))

    def arrivals_collector(self):
        arrivalsdata = self.line_api.get_data()

    def database_appender(self):
        pass

    def status_runner(self):
        while True:
            global currentStatusDictionary 
            currentStatusDictionary = self.status_api.get_statusseverity()
            time.sleep(20)

    def arrivals_runner(self):
        while True:
            self.arrivals_collector()






