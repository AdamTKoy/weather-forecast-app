import pandas as pd
from weather.ml.features import (
    build_features,
    prepare_training_data,
    split_features_and_target,
    split_training_and_validation,
)
from weather.ml.models import create_temperature_model
from weather.ml.evaluate import calculate_seasonal_baseline, evaluate_temperature_model


def train_temperature_model(location_id, horizon=1):
    data = build_features(location_id)
    data = prepare_training_data(data, horizon=horizon)

    X, y = split_features_and_target(data)

    valid_rows = X.notna().all(axis=1) & y.notna()

    if len(X) < 2:
        raise ValueError(
            "Not enough usable weather observations to create "
            "training and validation sets."
        )

    # Removes rows with missing model inputs while keeping data, X, and y aligned. 
    # Does not invent temperatures for missing dates.
    data = data.loc[valid_rows]
    X = X.loc[valid_rows]
    y = y.loc[valid_rows]

    X_train, X_validation, y_train, y_validation = (
        split_training_and_validation(X, y)
    )

    training_data = data.iloc[:len(X_train)]
    validation_data = data.iloc[len(X_train):]

    validation_start = pd.to_datetime(validation_data["date"].iloc[0])

    eligible = training_data["target_date"] <= validation_start

    training_data = training_data.loc[eligible]
    X_train = X_train.loc[eligible]
    y_train = y_train.loc[eligible]

    model = create_temperature_model()
    model.fit(X_train, y_train)

    return model, X_validation, y_validation, training_data, validation_data

# Complete experiment for specified location
# - builds features
# - prepares target (mean temp)
# - splits chronologically (first 20% train, last 80% validate)
# - trains random forest (200 trees)
# - evalutes against persistence baseline
# - returns trained model and metrics
def run_temperature_experiment(location_id, horizon=1):
    model, X_validation, y_validation, training_data, validation_data = train_temperature_model(
        location_id, horizon=horizon
    )

    metrics = evaluate_temperature_model(
        model,
        X_validation,
        y_validation,
    )

    metrics["seasonal_baseline_mae"] = calculate_seasonal_baseline(
        training_data,
        validation_data,
    )

    return model, metrics

# Trains models using ALL available historical data (no 20/80 split for train vs validate)
# - if 'as_of' arg specified, training will only use observations available through that date
def train_forecast_model(location_id, horizon, as_of=None):
    if horizon < 1:
        raise ValueError("Forecast horizon must be at least 1 day.")

    data = build_features(location_id)

    if as_of is not None:
        data = data.loc[data["date"] <= pd.Timestamp(as_of)]

    if data.empty:
        raise ValueError("No historical weather observations available.")

    forecast_origin = data["date"].iloc[-1]

    data = prepare_training_data(data, horizon=horizon)
    data = data.loc[data["target_date"] <= forecast_origin]

    X, y = split_features_and_target(data)

    valid_rows = X.notna().all(axis=1) & y.notna()
    X = X.loc[valid_rows]
    y = y.loc[valid_rows]

    if X.empty:
        raise ValueError(
            f"Not enough usable weather observations for horizon {horizon}."
        )

    model = create_temperature_model()
    model.fit(X, y)

    return model