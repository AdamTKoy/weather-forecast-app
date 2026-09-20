import pandas as pd

from weather.ml.features import get_latest_forecast_features
from weather.ml.train import train_forecast_model


# Direct multi-horizon approach:
# - each model predicts a different day ahead
# - every prediction uses info available at the same forecast origin
# - does not feed predicted temps into later predictions
def generate_temperature_forecast(location_id, days=30, as_of=None):
    if days < 1:
        raise ValueError("Forecast days must be at least 1.")

    forecast_origin, X = get_latest_forecast_features(location_id, as_of=as_of)

    predictions = []

    for horizon in range(1, days + 1):
        # using 'forecast_origin' ensures models cannot use observations newer than date forecast issued
        model = train_forecast_model(location_id, horizon=horizon, as_of=forecast_origin)

        predictions.append({
            "date": forecast_origin + pd.Timedelta(days=horizon),
            "temperature_mean": float(model.predict(X)[0]),
        })

    return predictions