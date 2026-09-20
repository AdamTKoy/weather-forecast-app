from sklearn.metrics import mean_absolute_error, mean_squared_error

def evaluate_temperature_model(model, X_validation, y_validation):
    predictions = model.predict(X_validation)

    # MAE: the model's predictions are off on average by this many degrees fahrenheit
    mae = mean_absolute_error(
        y_validation,
        predictions,
    )

    # RMSE: average of square root of squared differences (always positive) between predictions and y (target temp mean) validation values
    # - measures magnitude of error
    # - unit is also degrees fahrenheit
    rmse = mean_squared_error(
        y_validation,
        predictions,
    ) ** 0.5

    baseline_mae = calculate_persistence_baseline(
        X_validation,
        y_validation,
    )

    return {
        "mae": mae,
        "rmse": rmse,
        "baseline_mae": baseline_mae,
    }

# Common persistence baseline for weather: current day's temp mean == prior day's temp mean
def calculate_persistence_baseline(X_validation, y_validation):
    baseline_predictions = X_validation["temperature_mean"]

    return mean_absolute_error(
        y_validation,
        baseline_predictions,
    )

# Compares data on the same day across each year in the data sets
def calculate_seasonal_baseline(training_data, validation_data):
    training_data = training_data.copy()
    validation_data = validation_data.copy()

    training_data["calendar_day"] = (
        training_data["target_date"].dt.strftime("%m-%d")
    )
    validation_data["calendar_day"] = (
        validation_data["target_date"].dt.strftime("%m-%d")
    )

    seasonal_averages = training_data.groupby("calendar_day")[
        "target_temperature_mean"
    ].mean()

    predictions = validation_data["calendar_day"].map(seasonal_averages)

    # used when a day (like Feb 29) doesn't exist in every year in the provided data set
    predictions = predictions.fillna(
        training_data["target_temperature_mean"].mean()
    )

    return mean_absolute_error(
        validation_data["target_temperature_mean"],
        predictions,
    )