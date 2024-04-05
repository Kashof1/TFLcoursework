"""
this program takes the best model found by the hyperparameter tuner, and retrains a model for longer using those hyperparameters.
it then saves the trained model with a meaningful name for later use by the final application

"""

import datetime
import json
import os

import hyperparamFinder
import keras
import keras_tuner as kt
import pandas as pd
import tensorflow as tf

if __name__ == "__main__":
    pipeline = hyperparamFinder.dataPipeline()
    (
        raw_input_layers,
        encoded_input_layers,
        training_dataset,
        testing_dataset,
        validating_dataset,
    ) = pipeline.input_layers_builder()

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
    tensorboard_callback = keras.callbacks.TensorBoard(
        log_dir=log_dir, histogram_freq=0
    )

    early_callback = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=2,
    )

    besttrial = tuner.oracle.get_best_trials()[0]
    model = tuner.hypermodel.build(besttrial.hyperparameters)
    model.fit(
        training_dataset,
        epochs=50,
        callbacks=[early_callback, tensorboard_callback],
        validation_data=validating_dataset,
    )

    model.save("tflDelayPredictor.keras")
