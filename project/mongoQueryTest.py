from datetime import datetime, timedelta
import pymongo

#setting up the database to access
dbclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = dbclient['TFLData']
colName = 'jubilee_Stratford+Underground+Station_col'
currentCol = db[colName]

#defining two variables, one that already exists in the database and one that doesn't, for testing
existingTime = datetime(2024, 1, 4, 21, 48, 16)
newTime = datetime(2024,1,5,9,22,49)

#testing how python represents the time data from the database, to confirm that times in mongo are datetime.datetime objects
#when accessed in python
for item in currentCol.find():
    print (type(item['meta']['predictedTime']))
print ('*'*10)

#testing how to query using fields that are within dictionaries in mongo documents
indentQueryTest = currentCol.find_one({'meta.predictedTime' : existingTime})
print (indentQueryTest)

#testing that documents with a known existing datetime are corectly fouind
exists = currentCol.count_documents({'meta.predictedTime' : existingTime})
print (exists)

#testing that documents with a known non-existing datetime are correctly NOT found
n_exists = currentCol.count_documents({'meta.predictedTime' : newTime})
print (n_exists)

