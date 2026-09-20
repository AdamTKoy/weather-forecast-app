# Run with: python3 manage.py test weather.tests.test_fetch_weather
# Test ALL with: python3 manage.py test weather

from django.core.management import call_command
from django.test import SimpleTestCase
from django.core.management.base import CommandError
from unittest.mock import patch
from datetime import date

class FetchWeatherCommandTest(SimpleTestCase):
    # checks that command throws a CommandError as intended when start date > end date
    def test_rejects_start_date_after_end_date(self):
        with self.assertRaises(CommandError):
            call_command(
                "fetch_weather",
                "Chicago",
                "2025-01-05",
                "2025-01-01",
            )

    # tests for invalid (start) date input
    def test_rejects_invalid_date_format(self):
        with self.assertRaises(CommandError):
            call_command(
                "fetch_weather",
                "Chicago",
                "not-a-date",
                "2025-01-01",
            )

    # using fake data to test flow: command -> geocode -> import
    @patch("weather.management.commands.fetch_weather.import_historical_weather")
    @patch("weather.management.commands.fetch_weather.geocode_city")
    def test_successfully_fetches_weather(
        self,
        mock_geocode,
        mock_import,
    ):
        mock_geocode.return_value = {
            "id": 488739,
            "name": "Chicago",
            "admin1": "Illinois",
            "country": "United States",
            "country_code": "US",
            "latitude": 41.8781,
            "longitude": -87.6298,
        }

        call_command(
            "fetch_weather",
            "Chicago",
            "2025-01-01",
            "2025-01-02",
        )

        mock_geocode.assert_called_once_with("Chicago")

        mock_import.assert_called_once_with(
            id=488739,
            location_name="Chicago",
            admin1="Illinois",
            country="United States",
            country_code="US",
            latitude=41.8781,
            longitude=-87.6298,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 2),
        )

    # test when geocoding is fed location not recognized by open-meteo (should throw Command error)
    @patch("weather.management.commands.fetch_weather.geocode_city")
    def test_handles_location_not_found(self, mock_geocode):
        mock_geocode.side_effect = ValueError(
            "Could not find location: NotARealCity"
        )

        with self.assertRaises(CommandError):
            call_command(
                "fetch_weather",
                "NotARealCity",
                "2025-01-01",
                "2025-01-02",
            )

    # test when weather data import fails (should throw Command error)
    @patch("weather.management.commands.fetch_weather.import_historical_weather")
    @patch("weather.management.commands.fetch_weather.geocode_city")
    def test_handles_weather_import_failure(
        self,
        mock_geocode,
        mock_import,
    ):
        mock_geocode.return_value = {
            "id": 488739,
            "name": "Chicago",
            "admin1": "Illinois",
            "country": "United States",
            "country_code": "US",
            "latitude": 41.8781,
            "longitude": -87.6298,
        }

        mock_import.side_effect = Exception("Weather API failed")

        with self.assertRaises(CommandError):
            call_command(
                "fetch_weather",
                "Chicago",
                "2025-01-01",
                "2025-01-02",
            )