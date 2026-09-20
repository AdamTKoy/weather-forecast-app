import requests

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

def fetch_historical_weather(latitude, longitude, start_date, end_date,):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join([
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
            "weather_code"
        ]),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()