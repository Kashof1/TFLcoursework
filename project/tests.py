import json
import os

with open(os.path.join('project', 'data','stationsgeo.json'),'r') as file:
    data = json.load(file)
    
newarray = []
for each in data:
    lines = each['properties']['linesServed']
    lines = lines.replace('Hammersmith & City', 'hammersmith-city')
    lines = lines.replace('Waterloo & City', 'waterloo-city')
    linearray = list(map(str.lower, lines.split(', ')))
    each['properties']['linesServed'] = linearray
    newarray.append(each)





