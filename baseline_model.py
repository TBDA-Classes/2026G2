# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 20:30:30 2026

@author: lucia
"""

# Baseline model skeleton
# Tools for Big Data Analysis - CeDInt project

import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

# --------------------------------------------------
# Dataset configuration
# --------------------------------------------------

# The final dataset will be added when Node A and Node B
# finish the data preparation and external data tasks.

DATA_PATH = "data/final_dataset.csv"

# Target variable: the variable that the model will predict
TARGET_COLUMN = "energy_consumption"

# Predictor variables will be defined when the final dataset is available
FEATURE_COLUMNS = []

# --------------------------------------------------
# Train / test preparation
# --------------------------------------------------

def prepare_train_test(df, feature_columns, target_column):

    # X contains the variables used to make the prediction
    X = df[feature_columns]

    # y contains the variable that we want to predict
    y = df[target_column]

    # Split the dataset into training data (80%) and test data (20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42
    )

    return X_train, X_test, y_train, y_test

# --------------------------------------------------
# Baseline model: Linear Regression
# --------------------------------------------------

def train_linear_regression(X_train, y_train):

    # Create the Linear Regression model
    model = LinearRegression()

    # Train the model using the training data
    model.fit(X_train, y_train)

    return model

# --------------------------------------------------
# Predictions
# --------------------------------------------------

def make_predictions(model, X_test):

    predictions = model.predict(X_test)

    return predictions

# --------------------------------------------------
# Baseline model: Random Forest
# --------------------------------------------------

def train_random_forest(X_train, y_train):

    # Create the Random Forest model
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    # Train the model using the training data
    model.fit(X_train, y_train)

    return model