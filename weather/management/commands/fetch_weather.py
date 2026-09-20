# import pandas as pd
from datetime import date # datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from weather.services.geocoding import geocode_city
from weather.services.weather_import import import_historical_weather

# Command requires 3 arguments in this order: city, start date, end date
# Required date format for open-meteo request: YYYY-MM-DD
class Command(BaseCommand):
    help = "Fetches historical weather data based on provided arguments (location, start date, end date)"

    def add_arguments(self, parser):
        parser.add_argument("location")
        parser.add_argument("start_date")
        parser.add_argument("end_date")

    # ORIGINAL HANDLE: def fetch_weather_archive(lat, lon, start_date, end_date):
    def handle(self, *args, **options):
        city = options["location"]
        sd = options["start_date"]
        ed = options["end_date"]

        try:
            start_date = date.fromisoformat(sd)
        except ValueError:
            raise CommandError("Invalid start date.")

        try:
            end_date = date.fromisoformat(ed)
        except ValueError:
            raise CommandError("Invalid end date.")

        if start_date > end_date:
            raise CommandError("Start date must be before or equal to end date.")

        try:
            location = geocode_city(city)
        except ValueError as e:
            raise CommandError(str(e))

        # admin1 refers to state or province level
        # can replace country with country_code if brevity wanted
        self.stdout.write(
            f"Found {location["name"]}, {location["admin1"]}, {location["country"]}"
        )

        self.stdout.write(
            f"Coordinates: "
            f"{location['latitude']}, {location['longitude']}"
        )

        try:
            import_historical_weather(
                id=location["id"],
                location_name=location["name"],
                admin1=location["admin1"],
                country=location["country"],
                country_code=location["country_code"],
                latitude=location["latitude"],
                longitude=location["longitude"],
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            raise CommandError(f"Failed to import weather data: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                "Weather data successfully imported."
            )
        )