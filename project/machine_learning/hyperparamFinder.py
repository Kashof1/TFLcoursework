import os
from datetime import datetime

import keras
import keras_tuner as kt
import pandas as pd
import tensorboard
import tensorflow as tf
from keras import Layer, activations, layers


# error likely in this function
@keras.saving.register_keras_serializable()
class kerasSqueezeLayer(Layer):
    def __init__(self, vocab_size, **kwargs):
        self.vocab_size = vocab_size
        super(kerasSqueezeLayer, self).__init__(**kwargs)

    def call(self, x):
        return tf.cast(tf.squeeze(x), dtype="float32")

    def compute_output_shape(self):
        return (None, self.vocab_size)

    def get_config(self):
        config = super(kerasSqueezeLayer, self).get_config()
        config.update({"vocab_size": self.vocab_size})
        return config

    @classmethod
    def from_config(cls, config):
        return cls(**config)


@keras.saving.register_keras_serializable()
class kerasConcatenateLayer(Layer):
    def __init__(self, **kwargs):
        super(kerasConcatenateLayer, self).__init__(**kwargs)

    def call(self, x):
        return keras.layers.concatenate(x)


def pandas_to_dataset(pdframe, batch_size=512) -> tf.data.Dataset:
    labels = pdframe.pop("timeDiff").astype("float32")
    pdframe = {
        key: value.values[:, tf.newaxis] for key, value in pdframe.items()
    }  # [:,tf.newaxis] adds the dimensionality
    """
    'station' : array(['station1', 'station2', ...])
    BECOMES
    'station' : array([['station1'], ['station2'], ...])
    which helps preserve the dimensionality of data (prevents flattening where one key-value pair has mutliple datapoints within that value)
    """

    dataset = tf.data.Dataset.from_tensor_slices(
        (dict(pdframe), labels)
    )  # making a tensor dataset that aggregates the features and the labels

    """the dataset behaves like an array of batches. each batch contains batch_size datapoints worth of data. each batch is actually a tuple. tuple index 0 is all of the features,
    layed out as the feature name (such as crowding or appTemperature) followed by a list of batch_size number of values (almost like a dictionary). tuple index 1 is the labels.
    as there are not multiple labels, this is simply an array. ALL OF THESE ARRAYS ARE WRAPPED IN TENSOR OBJECTS"""

    dataset = dataset.batch(batch_size=batch_size)
    # not using prefetching as not using gpu
    return dataset


def normalisationGetter(featurename, dataset):
    normaliser = (
        layers.Normalization()
    )  # axis=None ensures scalar normalisation (i.e. every last entered number is normalised by the same params regardless of input shape)
    isolatedFeatures = dataset.map(
        lambda features, label: features[featurename]
    )  # mapping each item in the dataset to just the value for the featurename passed in, and removing label from dataset
    normaliser.adapt(
        isolatedFeatures
    )  # have the normaliser 'learn' the mean and s.d. based on the given data
    return normaliser


# can test this by running it twice with every line and comparing both inputs, and by checking that each one-hot encoded column only occurs once
def categoricalEncodingGetter(featurename, dataset, datatype="string"):
    # cast all types, regardless of string or int, to string (just in case integer indices are being used), as well as isolating the feature we want to use
    processedDS = dataset.map(lambda x, y: x[featurename])
    # creating a layer that 'knows' all of the possible 'words' that occur in the dataset and assigns them a number
    # alternating between string and integer depending on input data
    if datatype == "string":
        intIndexLayer = layers.StringLookup()
    elif datatype == "int":
        intIndexLayer = layers.IntegerLookup()

    intIndexLayer.adapt(data=processedDS)
    number_of_columns = intIndexLayer.vocabulary_size()

    # layer that one-hot encodes categorical indexes passed to it
    one_hot_layer = layers.CategoryEncoding(
        output_mode="one_hot", num_tokens=number_of_columns, dtype="int32"
    )

    # joining both layers together with a lambda function
    # feature --> given categorical index with intIndexLayer --> one-hot encoded with one_hot_layer --> remove one layer of dimensionality from it using squeeze
    return lambda feature: kerasSqueezeLayer(vocab_size=number_of_columns)(
        one_hot_layer(intIndexLayer(feature))
    )


"""this function turns the latitude and longitude into discrete buckets and then associates them by "crossing" them"""


def geographicalEncodingGetter(dataset):
    latitudeset = dataset.map(lambda x, y: x["latitude"])
    longitudeset = dataset.map(lambda x, y: x["longitude"])
    lat_bucket_layer, long_bucket_layer = layers.Discretization(
        num_bins=8, output_mode="int"
    ), layers.Discretization(
        num_bins=8, output_mode="int"
    )  # 8 divisions lengthwise and 8 divisions widthwise of coordinates
    # generating buckets of even sizes BASED ON THE DISTRIBUTION OF THE DATA
    lat_bucket_layer.adapt(latitudeset)
    long_bucket_layer.adapt(longitudeset)

    crossedlayer = layers.HashedCrossing(
        num_bins=64, output_mode="one_hot"
    )  # essentially splitting the map of London into 64 pieces, into which coordinates are grouped

    return lambda latitude, longitude: crossedlayer(
        (lat_bucket_layer(latitude), long_bucket_layer(longitude))
    )


def input_layers_builder():
    trainpath = os.path.join("data", "mlData", "trainingdata.json")
    testpath = os.path.join("data", "mlData", "testingdata.json")
    valpath = os.path.join("data", "mlData", "validatingdata.json")
    traindf = pd.read_json(trainpath)
    testdf = pd.read_json(testpath)
    valdf = pd.read_json(valpath)
    print(traindf)
    print("****")
    print(testdf)
    print("****")
    print(valdf)
    print("****")

    numeric_headers = ["appTemperature", "crowding", "statusSeverity", "precipitation"]
    categorical_headers = ["station", "line", "time"]
    int_categorical_headers = ["day"]
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
        cat_input_column_raw = keras.Input(shape=(1,), name=header, dtype="string")
        catLayer = categoricalEncodingGetter(
            featurename=header, dataset=training_dataset
        )
        encoded_input_column = catLayer(cat_input_column_raw)
        raw_input_layers.append(cat_input_column_raw)
        encoded_input_layers.append(encoded_input_column)

    for header in int_categorical_headers:
        cat_input_column_raw = keras.Input(shape=(1,), name=header, dtype="int64")
        catLayer = categoricalEncodingGetter(
            featurename=header, dataset=training_dataset, datatype="int"
        )
        encoded_input_column = catLayer(cat_input_column_raw)
        raw_input_layers.append(cat_input_column_raw)
        encoded_input_layers.append(encoded_input_column)

    lat_input_column_raw = keras.Input(shape=(1,), name="latitude", dtype="float64")
    long_input_column_raw = keras.Input(shape=(1,), name="longitude", dtype="float64")
    geoLayer = geographicalEncodingGetter(dataset=training_dataset)
    encoded_geo_column = geoLayer(lat_input_column_raw, long_input_column_raw)
    raw_input_layers.append(lat_input_column_raw)
    raw_input_layers.append(long_input_column_raw)
    encoded_input_layers.append(encoded_geo_column)
    return (
        raw_input_layers,
        encoded_input_layers,
        training_dataset,
        testing_dataset,
        validating_dataset,
    )


# this is the hyperparameters model-building and search space
def model_builder(hp):
    x = keras.layers.concatenate(
        inputs=encoded_input_layers, name="input_formattting_layer"
    )  # input formatting layer

    for layerNumber in range(hp.Int("layer_num", 3, 6)):
        x = layers.Dense(
            units=hp.Int(
                f"units{layerNumber}", min_value=500, max_value=5000, step=500
            ),
            activation=hp.Choice("activation", ["linear", "tanh"]),
        )(x)

    if hp.Boolean("dropout"):
        x = layers.Dropout(
            rate=hp.Float(
                "dropoutRate", min_value=0.001, max_value=0.1, sampling="log"
            ),
            name="dropoutLayer",
        )(x)

    outputLayer = layers.Dense(units=1)(x)

    learn_rate = hp.Float("learn_rate", min_value=0.0001, max_value=0.1, sampling="log")
    model = keras.Model(raw_input_layers, outputLayer)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learn_rate),
        loss=keras.losses.mean_squared_error,
        metrics=[keras.metrics.mean_absolute_error],
    )
    return model


if __name__ == "__main__":
    # MODEL TRAINING AND CONFIG STARTS HERE
    (
        raw_input_layers,
        encoded_input_layers,
        training_dataset,
        testing_dataset,
        validating_dataset,
    ) = input_layers_builder()

    log_dir = "logs/fit/" + datetime.now().strftime("%Y%m%d-%H%M%S")
    tensorboard_callback = keras.callbacks.TensorBoard(
        log_dir=log_dir, histogram_freq=0
    )

    tuner = kt.Hyperband(
        hypermodel=model_builder,
        objective="val_mean_absolute_error",
        max_epochs=20,
        directory="hyperTuning",
        project_name="functional_model_Hyperband2",
        overwrite=False,
    )

    early_callback = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=2,
    )

    tuner.search(
        training_dataset,
        epochs=3,
        validation_data=validating_dataset,
        callbacks=[tensorboard_callback, early_callback],
    )

    bestModels = tuner.get_best_models(num_models=2)
    bestModel = bestModels[0]
    bestModel.summary()

    bestModel.save("bestmodel.keras")

    # loading the model up again and printing some of its inference in order to review the model
    newbest = keras.models.load_model("bestmodel.keras")
    [(x, y)] = testing_dataset.take(1)
    predictions = newbest.predict(x)
    y = list(y)
    predictions = list(predictions)
    for each in range(len(predictions)):
        print(predictions[each], y[each])
