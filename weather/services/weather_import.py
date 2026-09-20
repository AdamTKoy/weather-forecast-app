from datetime import date

from weather.models import Location, WeatherObservation
from weather.services.open_meteo import fetch_historical_weather

def import_historical_weather(
    id,
    location_name,
    admin1,
    country,
    country_code,
    latitude,
    longitude,
    start_date,
    end_date,
):
    data = fetch_historical_weather(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )

    location = Location.objects.update_or_create(
        open_meteo_id=id,
        
        defaults={
            "name": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": data["timezone"],
            "country": country,
            "country_code": country_code,
            "admin1": admin1,
        },
    )[0]

    if "daily" not in data:
        raise ValueError("Weather API response missing daily data")

    daily = data["daily"]

    required_fields = [
        "time",
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "precipitation_sum",
        "rain_sum",
        "snowfall_sum",
        "wind_speed_10m_max",
        "wind_gusts_10m_max",
        "cloud_cover_mean",
        "relative_humidity_2m_mean",
        "surface_pressure_mean",
        "weather_code",
    ]

    for field in required_fields:
        if field not in daily:
            raise ValueError(f"Missing daily weather field: {field}")

    daily_length = len(daily["time"])

    for field in required_fields:
        if len(daily[field]) != daily_length:
            raise ValueError(f"Daily weather field has incorrect length: {field}")

    for i, date_string in enumerate(daily["time"]):
        WeatherObservation.objects.update_or_create(
            location=location,
            date=date.fromisoformat(date_string),
            defaults={
                "temperature_max": daily["temperature_2m_max"][i],
                "temperature_min": daily["temperature_2m_min"][i],
                "temperature_mean": daily["temperature_2m_mean"][i],
                "precipitation_sum": daily["precipitation_sum"][i],
                "rain_sum": daily["rain_sum"][i],
                "snowfall_sum": daily["snowfall_sum"][i],
                "wind_speed_max": daily["wind_speed_10m_max"][i],
                "wind_gusts_max": daily["wind_gusts_10m_max"][i],
                "cloud_cover_mean": daily["cloud_cover_mean"][i],
                "humidity_mean": daily["relative_humidity_2m_mean"][i],
                "pressure_mean": daily["surface_pressure_mean"][i],
                "weather_code": daily["weather_code"][i],
            },
        )

    return location