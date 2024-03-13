import logging
import os
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

'''@app.get('/', response_class=HTMLResponse)
def root(request : Request):
    log.info("Loaded root page")
    return templates.TemplateResponse(
        'index.html',
        {'request' : request,
         'data': ['home page']}
    )'''

@app.get('/', response_class=HTMLResponse)
async def mappage(request: Request, station: str = ''):
    if station == '':
        log.info('hh')
        return templates.TemplateResponse(
            'index.html',
            {'request' : request}
        )
    else:
        log.info('h')
        return templates.TemplateResponse(
            'index.html',
            {'request' : request}
        )



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