# prints one predicted mean temp per forecast date

from django.core.management.base import BaseCommand, CommandError

from weather.ml.forecast import generate_temperature_forecast
from weather.models import Location


class Command(BaseCommand):
    help = "Generate a multi-day mean-temperature forecast for a location"

    def add_arguments(self, parser):
        parser.add_argument("location_id", type=int)
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *args, **options):
        location_id = options["location_id"]
        days = options["days"]

        if not Location.objects.filter(id=location_id).exists():
            raise CommandError(
                f"Location with id {location_id} does not exist."
            )

        try:
            predictions = generate_temperature_forecast(
                location_id,
                days=days,
            )
        except ValueError as e:
            raise CommandError(str(e)) from e

        for prediction in predictions:
            self.stdout.write(
                f"{prediction['date']:%Y-%m-%d}: "
                f"{prediction['temperature_mean']:.1f} °F"
            )