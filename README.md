**UNDER CONSTRUCTION**

Across 12 forecast windows issued in 2024, the Random Forest reduced MAE by approximately 9% relative to a historical seasonal baseline, including an 18% reduction during the first seven forecast days.

keys returned from fetch call to historical weather data API:

- 'latitude'
- 'longitude'
- 'generationtime_ms'
- 'utc_offset_seconds'
- 'timezone'
- 'timezone_abbreviation'
- 'elevation'
- 'daily_units'
- 'daily'

- where 'daily' contains:
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
  "weather_code"

Explanation of commands:

**python manage.py fetch_weather**

- required arg: location name, ex: "Chicago" or "Springfield, Missouri"
- required arg: period start date, ex: 2020-01-01
- required arg: period end date, ex: 2020-12-31 (dates in format YYYY-MM-DD)

EXAMPLE: python manage.py fetch_weather Paris, France 2025-10-01 2025-10-31

Flow:

- Open-Meteo
- API response
- validate data
- transform data
- PostgreSQL

**python manage.py train_model**

- required arg: location id (ex: 4 for Chicago--this will need to be updated later since users will not know location's id)
- optional arg: --horizon (days)

Flow:

- PostgreSQL
- Feature engineering
- Train models
- Evaluate models
- Save model

**python manage.py generate_forecast**

Flow:

- Database
- Latest weather
- Saved ML model
- 30-day predictions
- Forecast database
