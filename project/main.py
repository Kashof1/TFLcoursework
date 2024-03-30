import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

from core.tfl import get_tflstation
from fastapi import FastAPI, Form, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

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
app.mount("/static", StaticFiles(directory="templates/static"), name="static")
templates = Jinja2Templates(directory="templates")

next_trains_api = get_tflstation()


class MarkerResponse(BaseModel):
    station: str


# fixes station names where it has an 'S such as King's Cross Station
def station_S_rectifier(string):
    searchStr = r"'S"
    matchobj = re.search(
        searchStr, string
    )  # finding to see if there is a 'S in the station name
    if matchobj:
        (apost, S) = matchobj.span()
        S -= 1  # adjusting the index of the S for 0 indexing
        return string[:S] + "s" + string[S + 1 :]
    else:
        return False


@app.get("/", response_class=HTMLResponse)
def mappage(request: Request):
    log.info("Root page loaded")
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/", response_class=JSONResponse)
def get_markerStationResponse(request: Request, markerresponse: MarkerResponse):
    returnedStation = markerresponse.station
    stationName = f"{returnedStation} Underground Station"
    with open(os.path.join("data", "stationLineCombos.json"), "r") as f:
        stationdata = json.load(f)
    linesServed = [
        each[0].capitalize() for each in stationdata if each[1] == stationName
    ]
    stationName = stationName.title()
    # outlier case due to hyphen
    if returnedStation == "Paddington (H&C Line)":
        stationName = "Paddington (H&C Line)-Underground"
    rectifiedString = station_S_rectifier(string=stationName)
    stationName = stationName if rectifiedString == False else rectifiedString

    arrivalsDict = {}
    predictionDict = {}
    for line in linesServed:
        line = line.lower()
        lineArrivals = next_trains_api.get_next_unique_trains(
            station=stationName, line=line
        )
        arrivalsDict[line] = lineArrivals

        delayPrediction = next_trains_api.inferDelayPrediction(
            line=line, station=stationName
        )
        predictionDict[line] = delayPrediction

    data = {
        "station": stationName,
        "linesServed": linesServed,
        "nextArrivals": arrivalsDict,
        "predictionDict": predictionDict,
    }
    log.info(f"Server received marker click data for {data}")

    encoded = jsonable_encoder(data)
    return JSONResponse(content=encoded)


@app.post("/sendStationData", response_class=JSONResponse)
def return_stationGeoData(request: Request):
    log.info("Station data requested by front end")
    with open(os.path.join("data", "stationsgeo.json"), "r") as file:
        data = json.load(file)

    newdata = []
    for each in data:
        lines = each["properties"]["linesServed"]
        lines = lines.replace("Hammersmith & City", "hammersmith-city")
        lines = lines.replace("Waterloo & City", "waterloo-city")
        linearray = list(map(str.lower, lines.split(", ")))
        each["properties"]["linesServed"] = linearray
        newdata.append(each)

    encoded = jsonable_encoder(newdata)
    return JSONResponse(content=encoded)
