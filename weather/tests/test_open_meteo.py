# Run with: python3 manage.py test weather.tests.test_open_meteo
# Test ALL with: python3 manage.py test weather

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase
import requests

from weather.services.open_meteo import fetch_historical_weather

# Test that program stops if API returns error
class OpenMeteoTest(SimpleTestCase):
    @patch("weather.services.open_meteo.requests.get")
    def test_fetch_historical_weather_raises_on_api_error(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = (
            requests.HTTPError("API request failed")
        )

        with self.assertRaises(requests.HTTPError):
            fetch_historical_weather(
                latitude=41.8781,
                longitude=-87.6298,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 2),
            )