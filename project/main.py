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

from core.tfl import get_tflstation, get_crowdingdata, get_statusseverity

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

station_train_api = get_tflstation()
station_crowd_api = get_crowdingdata()
line_disruption_api = get_statusseverity()

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



@app.post('/', response_class=HTMLResponse)
def get_markerStationResponse(request: Request, markerresponse : MarkerResponse):
    returnedStation = markerresponse.station
    stationName = f'{returnedStation.title()} Underground Station'
    with open (os.path.join('data', 'stationLineCombos.json'), 'r') as f:
        stationdata = json.load(f)
    linesServed = [each[0].capitalize() for each in stationdata if each[1] == stationName] #error for hyphenated stations

    data = {
        "station": stationName,
        "linesServed" : linesServed
        }
    log.info(f'Server received marker click data for {data}')

    encoded = jsonable_encoder(data)
    return JSONResponse(content = encoded)
    


@app.get('/{line}/Arrivals/{station}')
async def getstationarrivalsdata(line, station):
    station = station.replace('+',' ')
    log.info(f"Loaded {line} arrivals page for {station}")
    output = station_train_api.get_data(line, station)
    return {"data" : output}

@app.get('/Crowding/{stationName}/Live')
async def getstationcrowdingdata(stationName):
    stationName = stationName.replace('+',' ')
    log.info(f"Loaded crowding page for {stationName}")
    output = station_crowd_api.get_data(station = stationName)
    print (output['percentageOfBaseline'])
    return {"data" : output}

@app.get('/Line/{line}/Disruption')
async def getarrivalsdata(line):
    log.info(f"Loaded {line} disruptions data page")
    output = line_disruption_api.get_data(line=line)
    return {"data":output}

@app.get('/testpage')
async def testpage(request: Request):
    return templates.TemplateResponse(
        name = 'index.html', context={'request':request, 'data':'hello'}
    )