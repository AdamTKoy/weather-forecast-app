**UNDER CONSTRUCTION**

- Use something like Chart.js on the frontend for graphs

postgreSQL
command to interact with databases via terminal: psql postgres
to list databases: \l
to quit: \q

If typing commands into the terminal gets tedious, you can download a visual database management tool. Popular desktop clients for macOS include pgAdmin 4, DBeaver, or the native Mac application TablePlus. They will automatically detect your local Homebrew installation once you point them to localhost

keys returned from fetch to historical weather data request:
['latitude', 'longitude', 'generationtime_ms', 'utc_offset_seconds', 'timezone', 'timezone_abbreviation', 'elevation', 'daily_units', 'daily']

Explanation of commands:

python manage.py fetch_weather [location name, ex: "Chicago" or "Springfield, Missouri"] [period start date, ex: 2020-01-01] [period end date, ex: 2020-12-31]

- Open-Meteo
- API response
- validate data
- transform data
- PostgreSQL

python manage.py train_model

- PostgreSQL
- Feature engineering
- Train models
- Evaluate models
- Save model

python manage.py generate_forecast

- Database
- Latest weather
- Saved ML model
- 30-day predictions
- Forecast database

**Shell command to compare known 30-day mean temps against model's predictions:**
python3 manage.py shell <<'PY'
from datetime import date
from math import sqrt
from pathlib import Path

from weather.models import WeatherObservation

predictions = {}
for line in Path("chicago_january_2026_forecast.txt").read_text().splitlines():
date_text, temperature_text = line.split(": ", 1)
predictions[date.fromisoformat(date_text)] = float(
temperature_text.removesuffix(" °F")
)

observations = WeatherObservation.objects.filter(
location_id=4,
date\_\_in=predictions,
)
actual = {obs.date: obs.temperature_mean for obs in observations}

missing = sorted(set(predictions) - set(actual))
if missing:
print(f"Missing actual temperatures for: {missing}")
else:
errors = [
predictions[day] - actual[day]
for day in sorted(predictions)
]
mae = sum(abs(error) for error in errors) / len(errors)
rmse = sqrt(sum(error \*\* 2 for error in errors) / len(errors))

    print(f"Forecast days evaluated: {len(errors)}")
    print(f"MAE: {mae:.2f} °F")
    print(f"RMSE: {rmse:.2f} °F")

PY

**Shell command to predict each Jan 2026 day using historical average for that calendar day,**
**using only observations through December 31, 2025**
python3 manage.py shell <<'PY'
from datetime import date
from math import sqrt

from weather.models import WeatherObservation

historical = WeatherObservation.objects.filter(
location_id=4,
date**lte=date(2025, 12, 31),
temperature_mean**isnull=False,
)

temperatures_by_day = {}
for observation in historical:
key = (observation.date.month, observation.date.day)
temperatures_by_day.setdefault(key, []).append(
observation.temperature_mean
)

actual = WeatherObservation.objects.filter(
location_id=4,
date**range=(date(2026, 1, 1), date(2026, 1, 30)),
temperature_mean**isnull=False,
)

errors = []
for observation in actual:
key = (observation.date.month, observation.date.day)
historical_temperatures = temperatures_by_day[key]
prediction = sum(historical_temperatures) / len(historical_temperatures)
errors.append(prediction - observation.temperature_mean)

print(f"Days evaluated: {len(errors)}")
print(f"Seasonal MAE: {sum(abs(e) for e in errors) / len(errors):.2f} °F")
print(f"Seasonal RMSE: {sqrt(sum(e \*\* 2 for e in errors) / len(errors)):.2f} °F")
PY
