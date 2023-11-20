import logging
import os
from pathlib import Path
from fastapi import FastAPI
from core.tfl_line import get_tflline
from core.tfl_station import get_tflstation

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
tfl_api = get_tflstation()

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
    print (station)
    log.info(f"Loaded {line} arrivals page for {station}")
    output = tfl_api.get_data(line, station)
    return {"data": output}
