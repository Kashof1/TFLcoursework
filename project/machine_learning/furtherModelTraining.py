"""
this program takes the best model found by the hyperparameter tuner, and retrains a model for longer using those hyperparameters.
it then saves the trained model in a lightweight format, ready for quick inference
"""

import datetime
import os

import keras
import keras_tuner as kt
import pandas as pd
import tensorflow as tf
from hyperparamFinder import input_layers_builder, myHyperModel
from keras import backend as K

(
    raw_input_layers,
    encoded_input_layers,
    training_dataset,
    testing_dataset,
    validating_dataset,
) = input_layers_builder()

model_building_space = myHyperModel(
    encoded_input_layers=encoded_input_layers, raw_input_layers=raw_input_layers
)
tuner = kt.Hyperband(
    hypermodel=model_building_space,
    objective="val_mean_absolute_error",
    max_epochs=20,
    directory="machine_learning/hyperTuning",
    project_name="functional_model_Hyperband",
    overwrite=False,
)

log_dir = "machine_learning/logs/fit/" + datetime.datetime.now().strftime(
    "%Y%m%d-%H%M%S"
)
tensorboard_callback = keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=0)

early_callback = keras.callbacks.EarlyStopping(
    monitor="val_loss",
    patience=2,
)

besttrial = tuner.oracle.get_best_trials()[0]
model = tuner.hypermodel.build(besttrial.hyperparameters)
print(model.input_shape)
print(testing_dataset)
"""model.fit(
    training_dataset,
    epochs=3,
    callbacks=[early_callback, tensorboard_callback],
    validation_data=validating_dataset,
)

export_archive = keras.export.ExportArchive()
export_archive.track(model)
export_archive.add_endpoint(
    name='infer',
    fn=model.call,
    input_signature=[
        {
            "station" : tf.TensorSpec(shape=(None, 1), dtype=tf.string),
            "line" : tf.TensorSpec(shape=(None, 1), dtype=tf.string),
            "time" : tf.TensorSpec(shape=(None, 1), dtype=tf.string),
            "day": tf.TensorSpec(shape=(None, 1), dtype=tf.int64),
            "crowding" : tf.TensorSpec(shape=(None, 1), dtype=tf.float64),
            "appTemperature": tf.TensorSpec(shape=(None, 1), dtype=tf.float64),
            "statusSeverity": tf.TensorSpec(shape=(None, 1), dtype=tf.float64),
            "precipitation": tf.TensorSpec(shape=(None, 1), dtype=tf.float64),
            "latitude": tf.TensorSpec(shape=(None, 1), dtype=tf.float64),
            "longitude": tf.TensorSpec(shape=(None, 1), dtype=tf.float64)
        }
    ]
)

export_archive.write_out('testpathh')"""
ser = tf.saved_model.load("testpathh")
"""[(x,y)] = testing_dataset.take(1)
output = ser.infer(x)
y = list(y)
for each in range(len(y)):
    print (output[each], y[each])
"""
input = {
    "station": "Hainault Underground Station",
    "line": "central",
    "crowding": 0.120543,
    "time": "13:30:00",
    "latitude": 51.603137,
    "longitude": 0.095144,
    "appTemperature": 2.8,
    "precipitation": 0.9,
    "statusSeverity": 9.7,
    "day": 5,
}

finalInput = {}
for key, value in input.items():
    if isinstance(value, str):
        # Convert string to tf.string and reshape
        tensor = tf.convert_to_tensor(value, dtype=tf.string)
        tensor = tf.reshape(tensor, (-1, 1))
    elif isinstance(value, int):
        # Convert integer to tf.int64 and reshape
        tensor = tf.convert_to_tensor(value, dtype=tf.int64)
        tensor = tf.reshape(tensor, (-1, 1))
    elif isinstance(value, float):
        # Convert float to tf.float64 and reshape
        tensor = tf.convert_to_tensor(value, dtype=tf.float64)
        tensor = tf.reshape(tensor, (-1, 1))
    else:
        raise ValueError(f"Unsupported data type for key '{key}'")

    finalInput[key] = tensor

"""input = pd.DataFrame([input])
input = {
    key: value.values[:, tf.newaxis] for key, value in input.items()
}
input = tf.data.Dataset.from_tensor_slices(input)"""

output = ser.infer(finalInput)
print(output)
