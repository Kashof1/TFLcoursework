import os

import logging
from urllib.parse import quote, urlencode

from core.utils import get_url
from core.tfl_line import get_tflline

log = logging.getLogger(__name__)

directory = os.path.join('project','data','stations.json')
with open (directory, 'r') as file:
    print (file)

class get_tflstation():
    #station name (for convenience) paired with naptanid needed for API call
    pass