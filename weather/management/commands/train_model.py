# SYNTAX: python3 manage.py train_model <location_id>

from django.core.management.base import BaseCommand, CommandError
from weather.ml.train import run_temperature_experiment
from weather.models import Location

class Command(BaseCommand):
    help = "Train and evaluate the temperature forecasting model"

    def add_arguments(self, parser):
        parser.add_argument("location_id", type=int)
        parser.add_argument("--horizon", type=int, default=1)

    def handle(self, *args, **options):
        location_id = options["location_id"]

        horizon = options["horizon"]

        if horizon < 1:
            raise CommandError("Forecast horizon must be at least 1 day.")

        try:
            Location.objects.get(id=location_id)
        except Location.DoesNotExist:
            raise CommandError(
                f"Location with id {location_id} does not exist."
            )

        try:
            _, metrics = run_temperature_experiment(
                location_id,
                horizon=horizon,
            )
        except ValueError as e:
            raise CommandError(str(e)) from e

        self.stdout.write(
            f"MAE: {metrics['mae']:.2f} °F"
        )
        self.stdout.write(
            f"RMSE: {metrics['rmse']:.2f} °F"
        )
        self.stdout.write(
            f"Persistence Baseline MAE: {metrics['baseline_mae']:.2f} °F"
        )

        self.stdout.write(
            f"Seasonal Baseline MAE: {metrics['seasonal_baseline_mae']:.2f} °F"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Temperature model trained and evaluated successfully."
            )
        )