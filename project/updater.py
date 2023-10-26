import json
import os

from core.utils import get_url

final = {}

lines = get_url('https://api.tfl.gov.uk/line/mode/tube/status')
for line in lines:
    stop_points = get_url(f'https://api.tfl.gov.uk/line/{line["id"]}/stoppoints')
    for each in stop_points:
        if 'tube' in each['modes']:
            final.update({each['commonName'] : each['id']})

currentpath = os.path.dirname(os.path.realpath(__file__))
savepath = os.path.join(currentpath,'data','stations')

with open (savepath, 'w') as outputfile:
    json.dump (final, outputfile)