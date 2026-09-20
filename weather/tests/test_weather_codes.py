# Testing for how we convert numerical weather codes to their corresponding descriptions (cloudy, heavy rain, etc.)

from django.test import SimpleTestCase
from weather.services.weather_codes import get_weather_description

class WeatherCodeTests(SimpleTestCase):

    def test_known_weather_code(self):
        self.assertEqual(
            get_weather_description(0),
            "Clear sky",
        )

    def test_unknown_weather_code(self):
        self.assertEqual(
            get_weather_description(999),
            "Unknown",
        )

    def test_none_weather_code(self):
        self.assertEqual(
            get_weather_description(None),
            "Unknown",
        )