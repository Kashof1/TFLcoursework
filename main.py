import logging
import os
from pathlib import Path
from fastapi import FastAPI
from project.core.tfl_line import get_tflline

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
tfl_api = get_tflline()

@app.get('/')
async def root():
    log.info("Loaded root page")
    return {"message": "this is the root page"}


@app.get('/{line}')
async def getarrivalsdata(line):
    log.info(f"Loaded {line} arrivals data")
    output = tfl_api.get_tubedata(options=line)
    return {"data":output}


