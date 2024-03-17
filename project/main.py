import logging
import os
import json
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.tfl import get_tflstation

logs_file = Path(Path().resolve(), "log.txt")
logs_file.touch(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=os.environ.get("LOGLEVEL", "INFO"),
    handlers=[logging.FileHandler(logs_file), logging.StreamHandler()],
)

log = logging.getLogger(__name__)

app = FastAPI()
app.mount('/static', StaticFiles(directory='templates/static'), name='static')
templates = Jinja2Templates(directory='templates')

next_trains_api = get_tflstation()

class MarkerResponse(BaseModel):
    station: str

'''@app.get('/', response_class=HTMLResponse)
def root(request : Request):
    log.info("Loaded root page")
    return templates.TemplateResponse(
        'index.html',
        {'request' : request,
         'data': ['home page']}
    )'''

@app.get('/', response_class=HTMLResponse)
def mappage(request: Request):
    log.info('Root page loaded')
    return templates.TemplateResponse(
        'index.html',
        {'request' : request}
    )


@app.post('/', response_class=JSONResponse)
def get_markerStationResponse(request: Request, markerresponse : MarkerResponse):
    returnedStation = markerresponse.station
    log.info(markerresponse.station)
    stationName = f'{returnedStation} Underground Station'
    with open (os.path.join('data', 'stationLineCombos.json'), 'r') as f:
        stationdata = json.load(f)
    linesServed = [each[0].capitalize() for each in stationdata if each[1] == stationName] 
    stationName = stationName.title()

    arrivalsDict = {}
    for line in linesServed:
        lineArrivals = next_trains_api.get_next_unique_trains(station=stationName, line=line)
        arrivalsDict[line] = lineArrivals

    data = {
        "station": stationName,
        "linesServed" : linesServed,
        'nextArrivals' : arrivalsDict
        }
    log.info(f'Server received marker click data for {data}')

    encoded = jsonable_encoder(data)
    return JSONResponse(content = encoded)
    

@app.post('/sendStationData', response_class=JSONResponse)
def return_stationGeoData(request: Request):
    log.info('Station data requested by front end')
    with open(os.path.join('data','stationsgeo.json'),'r') as file:
        data = json.load(file)
        
    newdata = []
    for each in data:
        lines = each['properties']['linesServed']
        lines = lines.replace('Hammersmith & City', 'hammersmith-city')
        lines = lines.replace('Waterloo & City', 'waterloo-city')
        linearray = list(map(str.lower, lines.split(', ')))
        each['properties']['linesServed'] = linearray
        newdata.append(each)

    encoded = jsonable_encoder(newdata)
    return JSONResponse(content = encoded)

    






@app.get('/testpage')
async def testpage(request: Request):
    return templates.TemplateResponse(
        name = 'index.html', context={'request':request, 'data':'hello'}
    )