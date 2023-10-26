from .core.utils import get_url


lines = get_url('https://api.tfl.gov.uk/line/mode/tube/status')
print (lines)