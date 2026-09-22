"""Save a complete forecast consistently from the website or command line."""
from datetime import datetime, timedelta

from django.db import transaction

from weather.models import WeatherForecast


def save_temperature_forecast(location_id, predictions):
    if not predictions:
        raise ValueError("No forecast predictions were generated.")

    # The model returns pandas timestamps; callers may also supply dates.
    def as_date(value):
        return value.date() if isinstance(value, datetime) else value

    forecast_origin = as_date(predictions[0]["date"]) - timedelta(days=1)
    with transaction.atomic():
        for prediction in predictions:
            WeatherForecast.objects.update_or_create(
                location_id=location_id,
                forecast_origin=forecast_origin,
                forecast_date=as_date(prediction["date"]),
                defaults={"temperature_mean": prediction["temperature_mean"]},
            )
    return forecast_origin
