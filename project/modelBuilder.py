import pandas as pd
import os
import tensorflow as tf
import keras
from keras import layers 
from keras import activations
from datetime import datetime
import tensorboard



def pandas_to_dataset(pdframe, batch_size=32) -> tf.data.Dataset:
    labels = pdframe.pop('timeDiff')
    pdframe = {key: value.values[:,tf.newaxis] for key, value in pdframe.items()}#[:,tf.newaxis] adds the dimensionality
    """  
    'station' : array(['station1', 'station2', ...]) 
    BECOMES
    'station' : array([['station1'], ['station2'], ...])
    which helps preserve the dimensionality of data (prevents flattening where one key-value pair has mutliple datapoints within that value)
    """

    dataset = tf.data.Dataset.from_tensor_slices((dict(pdframe), labels)) #making a tensor dataset that aggregates the features and the labels

    '''the dataset behaves like an array of batches. each batch contains batch_size datapoints worth of data. each batch is actually a tuple. tuple index 0 is all of the features,
    layed out as the feature name (such as crowding or appTemperature) followed by a list of batch_size number of values (almost like a dictionary). tuple index 1 is the labels.
    as there are not multiple labels, this is simply an array. ALL OF THESE ARRAYS ARE WRAPPED IN TENSOR OBJECTS'''

    dataset = dataset.batch(batch_size=batch_size)
    #not using prefetching as not using gpu
    return dataset

def normalisationGetter(featurename, dataset):
    normaliser = layers.Normalization(axis=None) #axis=None ensures scalar normalisation (i.e. every last entered number is normalised by the same params regardless of input shape)
    isolatedFeatures = dataset.map(lambda features, label: features[featurename]) #mapping each item in the dataset to just the value for the featurename passed in, and removing label from dataset
    normaliser.adapt(isolatedFeatures) #have the normaliser 'learn' the mean and s.d. based on the given data
    return normaliser

#can test this by running it twice with every line and comparing both inputs, and by checking that each one-hot encoded column only occurs once
def categoricalEncodingGetter(featurename, dataset, datatype = 'string'):
    #cast all types, regardless of string or int, to string (just in case integer indices are being used), as well as isolating the feature we want to use
    processedDS = dataset.map(lambda x, y: x[featurename])

    #creating a layer that 'knows' all of the possible 'words' that occur in the dataset and assigns them a number
    #alternating between string and integer depending on input data
    if datatype == 'string':
        intIndexLayer = layers.StringLookup()
    elif datatype == 'int':
        intIndexLayer = layers.IntegerLookup()

    intIndexLayer.adapt(data=processedDS)
    number_of_columns = intIndexLayer.vocabulary_size()

    #layer that one-hot encodes categorical indexes passed to it
    one_hot_layer = layers.CategoryEncoding(output_mode="one_hot", num_tokens=number_of_columns)

    #joining both layers together with a lambda function
    #feature --> given categorical index with intIndexLayer --> one-hot encoded with one_hot_layer
    return lambda feature : one_hot_layer(intIndexLayer(feature))

'''this function turns the latitude and longitude into discrete buckets and then associates them by "crossing" them'''
def geographicalEncodingGetter(dataset):
    latitudeset = dataset.map(lambda x, y: x['latitude'])
    longitudeset = dataset.map(lambda x, y: x['longitude'])
    lat_bucket_layer, long_bucket_layer = layers.Discretization(num_bins=8, output_mode="int"), layers.Discretization(num_bins=8, output_mode="int") #8 divisions lengthwise and 8 divisions widthwise of coordinates
    #generating buckets of even sizes BASED ON THE DISTRIBUTION OF THE DATA
    lat_bucket_layer.adapt(latitudeset)
    long_bucket_layer.adapt(longitudeset)

    crossedlayer = layers.HashedCrossing(num_bins=64, output_mode='one_hot') #essentially splitting the map of London into 64 pieces, into which coordinates are grouped

    return lambda latitude, longitude: crossedlayer((lat_bucket_layer(latitude), long_bucket_layer(longitude)))
    

if __name__ == '__main__':
    trainpath = os.path.join('data', 'mlData', 'trainingdata.json')
    testpath = os.path.join('data', 'mlData', 'testingdata.json')
    valpath = os.path.join('data', 'mlData', 'validatingdata.json')
    traindf = pd.read_json(trainpath)
    testdf = pd.read_json(testpath)
    valdf = pd.read_json(valpath)
    print(traindf)
    print('****')
    print(testdf)
    print('****')
    print(valdf)
    print('****')

    numeric_headers = ['appTemperature', 'crowding', 'statusSeverity', 'precipitation']
    categorical_headers = ['station', 'line', 'time']
    int_categorical_headers = ['day']
    raw_input_layers = []
    encoded_input_layers = []
    training_dataset = pandas_to_dataset(pdframe=traindf)
    testing_dataset = pandas_to_dataset(pdframe=testdf)
    validating_dataset = pandas_to_dataset(pdframe=valdf)

    
    for header in numeric_headers:
        numeric_input_column_raw = keras.Input(shape=(1,), name=header)
        normLayer = normalisationGetter(featurename=header, dataset=training_dataset)
        encoded_input_column = normLayer(numeric_input_column_raw)
        raw_input_layers.append(numeric_input_column_raw)
        encoded_input_layers.append(encoded_input_column)


    
    for header in categorical_headers:
        cat_input_column_raw = keras.Input(shape=(1,), name=header, dtype='string')
        catLayer = categoricalEncodingGetter(featurename=header, dataset=training_dataset)
        encoded_input_column = catLayer(cat_input_column_raw)
        raw_input_layers.append(cat_input_column_raw)
        encoded_input_layers.append(encoded_input_column)

    
    for header in int_categorical_headers:
        cat_input_column_raw = keras.Input(shape=(1,), name=header, dtype='int64')
        catLayer = categoricalEncodingGetter(featurename=header, dataset=training_dataset, datatype='int')
        encoded_input_column = catLayer(cat_input_column_raw)
        raw_input_layers.append(cat_input_column_raw)  
        encoded_input_layers.append(encoded_input_column)

    
    lat_input_column_raw = keras.Input(shape=(1,), name='latitude', dtype='float64') 
    long_input_column_raw = keras.Input(shape=(1,), name='longitude', dtype='float64')
    geoLayer = geographicalEncodingGetter(dataset=training_dataset)
    encoded_geo_column = geoLayer(lat_input_column_raw, long_input_column_raw)
    raw_input_layers.append(lat_input_column_raw)
    raw_input_layers.append(long_input_column_raw)
    encoded_input_layers.append(encoded_geo_column)


    input_formatting_layer = keras.layers.concatenate(encoded_input_layers)
    x = keras.layers.Dense(384, activation=activations.relu)(input_formatting_layer)
    x = keras.layers.Dense(100, activation=activations.relu)(x)
    x = keras.layers.Dense(50, activation=activations.relu)(x)
    output_layer = keras.layers.Dense(1)(x)

    log_dir = "logs/fit/" + datetime.now().strftime("%Y%m%d-%H%M%S")
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

    model = keras.Model(raw_input_layers, output_layer)
    model.compile(optimizer='adam',
                  loss = keras.losses.mean_squared_error,
                  metrics=['accuracy']
                  )
    
    print(model.summary())
    model.fit(training_dataset,
             epochs=10, 
             validation_data=validating_dataset,
             callbacks=[tensorboard_callback])
    loss, accuracy = model.evaluate(testing_dataset)
    print("Accuracy", accuracy)