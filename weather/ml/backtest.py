# Generate forecast as it would have been issued on a past date 
# and compare w/ observations that become available afterward

from math import sqrt

from weather.ml.forecast import generate_temperature_forecast
from weather.models import WeatherObservation

# Automates comparison against seasonal baseline for every backtest,
# using only observations available on forecast's starting date
def calculate_historical_seasonal_mae(location_id, as_of, predictions):
    historical = WeatherObservation.objects.filter(
        location_id=location_id,
        date__lte=as_of,
        temperature_mean__isnull=False,
    )

    temperatures_by_day = {}

    for observation in historical:
        calendar_day = (
            observation.date.month,
            observation.date.day,
        )
        temperatures_by_day.setdefault(calendar_day, []).append(
            observation.temperature_mean
        )

    errors = []

    for prediction in predictions:
        forecast_date = prediction["date"].date()
        calendar_day = (
            forecast_date.month,
            forecast_date.day,
        )

        historical_temperatures = temperatures_by_day.get(calendar_day)

        if not historical_temperatures:
            raise ValueError(
                f"No seasonal history available for {forecast_date}."
            )

        seasonal_prediction = (
            sum(historical_temperatures) / len(historical_temperatures)
        )

        actual = WeatherObservation.objects.get(
            location_id=location_id,
            date=forecast_date,
        ).temperature_mean

        if actual is None:
            raise ValueError(
                f"Missing observed temperature for {forecast_date}."
            )

        errors.append(seasonal_prediction - actual)

    return sum(abs(error) for error in errors) / len(errors)


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

    seasonal_baseline_mae = calculate_historical_seasonal_mae(
        location_id,
        as_of,
        predictions,
    )

    return {
        "days_evaluated": len(errors),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "rmse": sqrt(
            sum(error ** 2 for error in errors) / len(errors)
        ),
        "seasonal_baseline_mae": seasonal_baseline_mae,
    }

def backtest_multiple_dates(location_id, as_of_dates, days=30):
    results = []

    for as_of in as_of_dates:
        metrics = backtest_temperature_forecast(
            location_id,
            as_of=as_of,
            days=days,
        )

        results.append({
            "as_of": as_of,
            **metrics,
        })

    return results

# forecasting is date clusters of 1st-7th, 8th-14th, 15th-30th
def backtest_forecast_horizons(location_id, as_of, days=30):
    predictions = generate_temperature_forecast(
        location_id,
        days=days,
        as_of=as_of,
    )

    # One query for historical data, using only information available then.
    seasonal_totals = {}
    for observed_date, temperature in (
        WeatherObservation.objects.filter(
            location_id=location_id,
            date__lte=as_of,
            temperature_mean__isnull=False,
        ).values_list("date", "temperature_mean")
    ):
        key = (observed_date.month, observed_date.day)
        total, count = seasonal_totals.get(key, (0, 0))
        seasonal_totals[key] = (total + temperature, count + 1)

    # One query for the observations used to score this forecast.
    actuals = dict(
        WeatherObservation.objects.filter(
            location_id=location_id,
            date__in=[p["date"].date() for p in predictions],
        ).values_list("date", "temperature_mean")
    )

    results = []

    for start, end in [(1, 7), (8, 14), (15, 30)]:
        model_errors = []
        baseline_errors = []

        for prediction in predictions:
            forecast_date = prediction["date"].date()
            lead_day = (forecast_date - as_of).days

            if not start <= lead_day <= end:
                continue

            actual = actuals.get(forecast_date)
            if actual is None:
                raise ValueError(
                    f"Missing observed temperature for {forecast_date}."
                )

            key = (forecast_date.month, forecast_date.day)
            if key not in seasonal_totals:
                raise ValueError(
                    f"No seasonal history available for {forecast_date}."
                )

            total, count = seasonal_totals[key]
            seasonal_prediction = total / count

            model_errors.append(
                abs(prediction["temperature_mean"] - actual)
            )
            baseline_errors.append(abs(seasonal_prediction - actual))

        if model_errors:
            results.append({
                "horizon": f"{start}–{end}",
                "days_evaluated": len(model_errors),
                "mae": sum(model_errors) / len(model_errors),
                "seasonal_baseline_mae": (
                    sum(baseline_errors) / len(baseline_errors)
                ),
            })

    return results