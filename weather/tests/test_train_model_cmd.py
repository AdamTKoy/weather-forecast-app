from unittest.mock import patch

from datetime import date

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from io import StringIO

from weather.models import Location


class TrainModelCommandTests(TestCase):
    def test_train_model_command(self):
        location = Location.objects.create(
            open_meteo_id=12345,
            name="Chicago",
            latitude=41.8781,
            longitude=-87.6298,
            timezone="America/Chicago",
        )

        metrics = {
            "mae": 3.2,
            "rmse": 4.1,
            "baseline_mae": 4.5,
            "seasonal_baseline_mae": 6.0,
        }

        with patch(
            "weather.management.commands.train_model.run_temperature_experiment"
        ) as mock_experiment:
            mock_experiment.return_value = (None, metrics)

            call_command("train_model", location.id)

            mock_experiment.assert_called_once_with(location.id, horizon=1)

            mock_experiment.side_effect = ValueError(
                "Not enough usable weather observations to create "
                "training and validation sets."
            )

            with self.assertRaisesRegex(
                CommandError,
                "Not enough usable weather observations",
            ):
                call_command("train_model", location.id)

    # 30-day horizon
    def test_train_model_command_with_custom_horizon(self):
        location = Location.objects.create(
            open_meteo_id=54321,
            name="Chicago",
            latitude=41.8781,
            longitude=-87.6298,
            timezone="America/Chicago",
        )

        metrics = {
            "mae": 5.0,
            "rmse": 6.0,
            "baseline_mae": 5.5,
            "seasonal_baseline_mae": 7.0,
        }

        with patch(
            "weather.management.commands.train_model.run_temperature_experiment"
        ) as mock_experiment:
            mock_experiment.return_value = (None, metrics)

            call_command("train_model", location.id, horizon=30)

            mock_experiment.assert_called_once_with(
                location.id,
                horizon=30,
            )

    # Confirms custom command forwards requested forecast length (days=2)
    # and prints expected dates and temps (without training models)
    def test_generate_forecast_command(self):
        location = Location.objects.create(
            open_meteo_id=67890,
            name="Chicago",
            latitude=41.8781,
            longitude=-87.6298,
            timezone="America/Chicago",
        )

        predictions = [
            {
                "date": date(2026, 1, 1),
                "temperature_mean": 32.5,
            },
            {
                "date": date(2026, 1, 2),
                "temperature_mean": 34.2,
            },
        ]

        output = StringIO()

        with patch(
            "weather.management.commands.generate_forecast.generate_temperature_forecast"
        ) as mock_forecast:
            mock_forecast.return_value = predictions

            call_command(
                "generate_forecast",
                location.id,
                days=2,
                stdout=output,
            )

            mock_forecast.assert_called_once_with(
                location.id,
                days=2,
            )

        self.assertIn("2026-01-01: 32.5 °F", output.getvalue())
        self.assertIn("2026-01-02: 34.2 °F", output.getvalue())