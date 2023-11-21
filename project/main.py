import logging
import os
from pathlib import Path
from fastapi import FastAPI
from core.tfl_line import get_tflline
from core.tfl_station import get_tflstation
from core.crowding import get_crowdingdata

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
station_train_api = get_tflstation()
station_crowd_api = get_crowdingdata()

@app.get('/')
async def root():
    log.info("Loaded root page")
    return {"message": "this is the root page"}


'''@app.get('/{line}')
async def getarrivalsdata(line):
    log.info(f"Loaded {line} arrivals data")
    output = tfl_api.get_tubedata(options=line)
    return {"data":output}'''

@app.get('/{line}/Arrivals/{station}')
async def getstationarrivalsdata(line, station):
    station = station.replace('+',' ')
    log.info(f"Loaded {line} arrivals page for {station}")
    output = station_train_api.get_data(line, station)
    return {"data" : output}

@app.get('/Crowding/{stationName}/Live')
async def getstationcrowdingdata(stationName):
    stationName = stationName.replace('+',' ')
    print (stationName)
    log.info(f"Loaded crowding page for {stationName}")
    output = station_crowd_api.get_data(station = stationName)
    return {"data" : output}
