import pandas as pd
from weather.models import WeatherObservation

# Training and forecasting need to use the same features, in the same order
FEATURE_COLUMNS = [
    "month",
    "day_of_year",
    "temperature_mean",
    "temperature_mean_lag_1",
    "temperature_mean_lag_7",
    "precipitation_sum_lag_1",
    "humidity_mean_lag_1",
    "pressure_mean_lag_1",
    "wind_speed_max_lag_1",
    "cloud_cover_mean_lag_1",
    "temperature_mean_rolling_3",
    "temperature_mean_rolling_7",
]

def load_weather_data(location_id):
    observations = WeatherObservation.objects.filter(
        location_id=location_id
    ).order_by("date")

    data = [
        {
            "date": observation.date,
            "temperature_max": observation.temperature_max,
            "temperature_min": observation.temperature_min,
            "temperature_mean": observation.temperature_mean,
            "precipitation_sum": observation.precipitation_sum,
            "rain_sum": observation.rain_sum,
            "snowfall_sum": observation.snowfall_sum,
            "wind_speed_max": observation.wind_speed_max,
            "wind_gusts_max": observation.wind_gusts_max,
            "cloud_cover_mean": observation.cloud_cover_mean,
            "humidity_mean": observation.humidity_mean,
            "pressure_mean": observation.pressure_mean,
            "weather_code": observation.weather_code,
        }
        for observation in observations
    ]

    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)

def add_date_features(data):
    data = data.copy()

    data["year"] = pd.to_datetime(data["date"]).dt.year
    data["month"] = pd.to_datetime(data["date"]).dt.month
    data["day_of_year"] = pd.to_datetime(data["date"]).dt.dayofyear

    return data

def add_lag_features(data):
    data = data.copy()

    data["temperature_mean_lag_1"] = data["temperature_mean"].shift(1)
    data["temperature_mean_lag_7"] = data["temperature_mean"].shift(7)
    data["precipitation_sum_lag_1"] = data["precipitation_sum"].shift(1)
    data["humidity_mean_lag_1"] = data["humidity_mean"].shift(1)
    data["pressure_mean_lag_1"] = data["pressure_mean"].shift(1)
    data["wind_speed_max_lag_1"] = data["wind_speed_max"].shift(1)
    data["cloud_cover_mean_lag_1"] = data["cloud_cover_mean"].shift(1)

    return data

def add_rolling_features(data):
    data = data.copy()

    # shifted by 1 so we don't include today's weather observation in the window
    # b/c forecasting model cannot be given current (or future) data
    data["temperature_mean_rolling_3"] = (
        data["temperature_mean"].shift(1).rolling(window=3).mean()
    )

    data["temperature_mean_rolling_7"] = (
        data["temperature_mean"].shift(1).rolling(window=7).mean()
    )

    return data

def build_features(location_id):
    data = load_weather_data(location_id)

    if data.empty:
        return data

    data["date"] = pd.to_datetime(data["date"])

    # fills in any missing dates between min and max and populates with NaN for the weather observation fields
    data = (
        data.set_index("date")
        .reindex(pd.date_range(data["date"].min(), data["date"].max()))
        .rename_axis("date")
        .reset_index()
    )

    data = add_date_features(data)
    data = add_lag_features(data)
    data = add_rolling_features(data)

    return data

# default set to 1 but may override higher to make longer spanning predictions (7-day, 30-day, etc)
def prepare_training_data(data, horizon=1):
    data = data.copy()

    data["target_temperature_mean"] = data["temperature_mean"].shift(-horizon)
    data["target_date"] = (pd.to_datetime(data["date"]) + pd.Timedelta(days=horizon))

    actual_target_date = pd.to_datetime(data["date"].shift(-horizon))

    # discards rows where the temp selected by .shift(-horizon) belongs 
    # to a different date than the one we're trying to predict
    # (pandas shifts by ROWS not necessarily DATES)
    data = data.loc[
        actual_target_date.eq(data["target_date"])
    ]
    
    data = data.dropna(
        subset=[
            "temperature_mean_lag_1",
            "temperature_mean_lag_7",
            "temperature_mean_rolling_3",
            "temperature_mean_rolling_7",
            "target_temperature_mean",
        ]
    )

    return data

def split_features_and_target(data):
    X = data[FEATURE_COLUMNS]
    y = data["target_temperature_mean"]

    return X, y

# If latest observation data is missing, would make preduction seem more current than it should be
# - 'as_of' arg allows you to set end date for observations regardless if more in database
def get_latest_forecast_features(location_id, as_of=None):
    data = build_features(location_id)

    if as_of is not None:
        data = data.loc[data["date"] <= pd.Timestamp(as_of)]

    if data.empty:
        raise ValueError("No historical weather observations available.")

    latest_row = data.iloc[[-1]]
    X = latest_row[FEATURE_COLUMNS]

    if X.isna().any().any():
        raise ValueError(
            "The latest observation has missing forecast features."
        )

    forecast_origin = latest_row["date"].iloc[0]

    return forecast_origin, X

# TRAIN on first 20% of historical observation set
# VALIDATE on last 80% of historical observation set
def split_training_and_validation(X, y, validation_fraction=0.2):
    split_index = int(len(X) * (1 - validation_fraction))

    X_train = X.iloc[:split_index]
    X_validation = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_validation = y.iloc[split_index:]

    return X_train, X_validation, y_train, y_validation