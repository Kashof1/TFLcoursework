import re

string = "King'S Cross St Pancras"
searchstr = r"'S"
x = re.search(searchstr, string)
(apost, s) = x.span()
s -= 1
newstring = string[:s] + "s" + string[s + 1 :]

print(newstring)
