# Generate forecast as it would have been issued on a past date 
# and compare w/ observations that become available afterward

from math import sqrt

from weather.ml.forecast import generate_temperature_forecast
from weather.models import WeatherObservation


def backtest_temperature_forecast(location_id, as_of, days=30):
    predictions = generate_temperature_forecast(
        location_id,
        days=days,
        as_of=as_of,
    )

    actual = {
        observation.date: observation.temperature_mean
        for observation in WeatherObservation.objects.filter(
            location_id=location_id,
            date__in=[prediction["date"] for prediction in predictions],
        )
    }

    errors = []

    for prediction in predictions:
        forecast_date = prediction["date"].date()
        observed_temperature = actual.get(forecast_date)

        if observed_temperature is None:
            raise ValueError(
                f"Missing observed temperature for {forecast_date}."
            )

        errors.append(
            prediction["temperature_mean"] - observed_temperature
        )

    return {
        "days_evaluated": len(errors),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "rmse": sqrt(
            sum(error ** 2 for error in errors) / len(errors)
        ),
    }