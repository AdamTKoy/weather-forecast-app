
from django.core.management.base import BaseCommand, CommandError

from weather.ml.forecast import generate_temperature_forecast
from weather.models import Location
from weather.services.forecast_storage import save_temperature_forecast


class Command(BaseCommand):
    help = "Generate and save daily mean-temperature forecasts"

    def add_arguments(self, parser):
        parser.add_argument("location_id", type=int)

        # optional arg--can override length of window if desired
        parser.add_argument("--days", type=int, default=7)

    def handle(self, *args, **options):
        location_id = options["location_id"]
        days = options["days"]

        if days < 1:
            raise CommandError("Forecast days must be at least 1.")

        if not Location.objects.filter(id=location_id).exists():
            raise CommandError(
                f"Location with id {location_id} does not exist."
            )

        try:
            predictions = generate_temperature_forecast(
                location_id,
                days=days,
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if not predictions:
            raise CommandError("No forecast predictions were generated.")

        forecast_origin = save_temperature_forecast(location_id, predictions)

        self.stdout.write(f"Forecast origin: {forecast_origin}")

        for prediction in predictions:
            self.stdout.write(
                f"{prediction['date']:%Y-%m-%d}: "
                f"{prediction['temperature_mean']:.1f} °F"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Saved {len(predictions)} forecast days."
            )
        )