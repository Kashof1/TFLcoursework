import json
import logging
import urllib.request

log = logging.getLogger(__name__)

def get_url(url:str):
    req_info = urllib.request.urlopen(url)
    log.info(f"REQUESTED DATA FROM {url}")
    data = req_info.read()
    datastr = data.decode("utf8")
    req_info.close
    return json.loads(datastr)