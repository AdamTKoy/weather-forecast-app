from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from weather.models import Location, WeatherForecast


class GenerateForecastCommandTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            open_meteo_id=4887398,
            name="Chicago",
            latitude=41.8781,
            longitude=-87.6298,
            timezone="America/Chicago",
            country="United States",
            country_code="US",
            admin1="Illinois",
        )

    @patch(
        "weather.management.commands.generate_forecast."
        "generate_temperature_forecast"
    )

    # using mock predictions so test checks function behavior without training models
    def test_saves_forecast_and_updates_without_duplicates(self, mock_generate):
        mock_generate.return_value = [
            {
                "date": date(2025, 1, 10),
                "temperature_mean": 30.0,
            },
            {
                "date": date(2025, 1, 11),
                "temperature_mean": 32.0,
            },
        ]

        call_command(
            "generate_forecast",
            self.location.id,
            days=2,
            stdout=StringIO(),
        )

        mock_generate.assert_called_once_with(
            self.location.id,
            days=2,
        )

        forecasts = WeatherForecast.objects.filter(
            location=self.location,
            forecast_origin=date(2025, 1, 9),
        )

        self.assertEqual(forecasts.count(), 2)
        self.assertEqual(
            list(
                forecasts.values_list(
                    "forecast_date",
                    "temperature_mean",
                )
            ),
            [
                (date(2025, 1, 10), 30.0),
                (date(2025, 1, 11), 32.0),
            ],
        )

        # Regenerate the same dates with an updated prediction.
        mock_generate.return_value = [
            {
                "date": date(2025, 1, 10),
                "temperature_mean": 31.5,
            },
            {
                "date": date(2025, 1, 11),
                "temperature_mean": 32.0,
            },
        ]

        call_command(
            "generate_forecast",
            self.location.id,
            days=2,
            stdout=StringIO(),
        )

        self.assertEqual(WeatherForecast.objects.count(), 2)

        updated_forecast = forecasts.get(
            forecast_date=date(2025, 1, 10)
        )
        self.assertEqual(updated_forecast.temperature_mean, 31.5)