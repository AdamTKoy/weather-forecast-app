# Run with: python3 manage.py test weather.tests.test_weather_import
# Test ALL with: python3 manage.py test weather

from datetime import date
from django.test import TestCase
from weather.models import Location, WeatherObservation
from weather.services.weather_import import import_historical_weather
from unittest.mock import patch


class WeatherImportTest(TestCase):
    # fake response for unit/integration testing because importing should be tested independently of external API
    @patch("weather.services.weather_import.fetch_historical_weather")
    def test_import_creates_location_and_observations(self, mock_fetch):
        mock_fetch.return_value = {
            "timezone": "America/Chicago",
            "daily": {
                "time": [
                    "2025-01-01",
                    "2025-01-02",
                ],
                "temperature_2m_max": [32.0, 35.0],
                "temperature_2m_min": [20.0, 22.0],
                "temperature_2m_mean": [26.0, 28.5],
                "precipitation_sum": [0.10, 0.00],
                "rain_sum": [0.05, 0.00],
                "snowfall_sum": [0.20, 0.00],
                "wind_speed_10m_max": [15.0, 18.0],
                "wind_gusts_10m_max": [25.0, 30.0],
                "cloud_cover_mean": [60.0, 40.0],
                "relative_humidity_2m_mean": [70.0, 65.0],
                "surface_pressure_mean": [1000.0, 1005.0],
                "weather_code": [3, 1],
            },
        }

        import_historical_weather(
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

        # running same query again to verify function does not allow duplicates
        import_historical_weather(
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

        # These values should stay the same no matter how many times the SAME query is run
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(WeatherObservation.objects.count(), 2)

        observation = WeatherObservation.objects.get(
            date=date(2025, 1, 1)
        )

        self.assertEqual(observation.location.name, "Chicago")
        self.assertEqual(observation.temperature_max, 32.0)
        self.assertEqual(observation.temperature_min, 20.0)
        self.assertEqual(observation.temperature_mean, 26.0)
        self.assertEqual(observation.precipitation_sum, 0.10)
        self.assertEqual(observation.rain_sum, 0.05)
        self.assertEqual(observation.snowfall_sum, 0.20)
        self.assertEqual(observation.wind_speed_max, 15.0)
        self.assertEqual(observation.wind_gusts_max, 25.0)
        self.assertEqual(observation.cloud_cover_mean, 60.0)
        self.assertEqual(observation.humidity_mean, 70.0)
        self.assertEqual(observation.pressure_mean, 1000.0)
        self.assertEqual(observation.weather_code, 3)

    # Test 
    @patch("weather.services.weather_import.fetch_historical_weather")
    def test_import_updates_existing_observation(self, mock_fetch):
        mock_fetch.return_value = {
            "timezone": "America/Chicago",
            "daily": {
                "time": ["2025-01-01"],
                "temperature_2m_max": [32.0],
                "temperature_2m_min": [20.0],
                "temperature_2m_mean": [26.0],
                "precipitation_sum": [0.10],
                "rain_sum": [0.05],
                "snowfall_sum": [0.20],
                "wind_speed_10m_max": [15.0],
                "wind_gusts_10m_max": [25.0],
                "cloud_cover_mean": [60.0],
                "relative_humidity_2m_mean": [70.0],
                "surface_pressure_mean": [1000.0],
                "weather_code": [3],
            },
        }

        # create observation
        import_historical_weather(
            id=488739,
            location_name="Chicago",
            admin1="Illinois",
            country="United States",
            country_code="US",
            latitude=41.8781,
            longitude=-87.6298,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
        )

        mock_fetch.return_value["daily"]["temperature_2m_max"] = [40.0]
        mock_fetch.return_value["daily"]["temperature_2m_min"] = [25.0]
        mock_fetch.return_value["daily"]["temperature_2m_mean"] = [32.5]

        # change values and re-query to verify database is updated (rather than added)
        import_historical_weather(
            id=488739,
            location_name="Chicago",
            admin1="Illinois",
            country="United States",
            country_code="US",
            latitude=41.8781,
            longitude=-87.6298,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
        )

        self.assertEqual(WeatherObservation.objects.count(), 1)

        observation = WeatherObservation.objects.get(
            date=date(2025, 1, 1)
        )

        self.assertEqual(observation.temperature_max, 40.0)
        self.assertEqual(observation.temperature_min, 25.0)
        self.assertEqual(observation.temperature_mean, 32.5)

    # testing that program throws error if returned data from open-meteo is missing required fields
    @patch("weather.services.weather_import.fetch_historical_weather")
    def test_import_historical_weather_missing_field(self, mock_fetch):
        mock_fetch.return_value = {
            "timezone": "America/Chicago",
            "daily": {
                "time": [],
            },
        }

        with self.assertRaises(
            ValueError,
        ) as context:
            import_historical_weather(
                id=123,
                location_name="Chicago",
                admin1="Illinois",
                country="United States",
                country_code="US",
                latitude=41.8781,
                longitude=-87.6298,
                start_date="2025-01-01",
                end_date="2025-01-03",
            )

        self.assertEqual(
            str(context.exception),
            "Missing daily weather field: temperature_2m_max",
        )

    # this also checks for missing data fields but using the length of the 'daily' array returned
    # the expected length for all fields is based on the length of the 'time' array
    @patch("weather.services.weather_import.fetch_historical_weather")
    def test_import_historical_weather_mismatched_field_length(self, mock_fetch):
        mock_fetch.return_value = {
            "timezone": "America/Chicago",
            "daily": {
                "time": ["2025-01-01", "2025-01-02"],
                "temperature_2m_max": [35.0],
                "temperature_2m_min": [25.0, 26.0],
                "temperature_2m_mean": [30.0, 31.0],
                "precipitation_sum": [0.0, 0.0],
                "rain_sum": [0.0, 0.0],
                "snowfall_sum": [0.0, 0.0],
                "wind_speed_10m_max": [10.0, 11.0],
                "wind_gusts_10m_max": [15.0, 16.0],
                "cloud_cover_mean": [50.0, 51.0],
                "relative_humidity_2m_mean": [60.0, 61.0],
                "surface_pressure_mean": [1010.0, 1011.0],
                "weather_code": [0, 1],
            },
        }

        with self.assertRaises(ValueError) as context:
            import_historical_weather(
                id=123,
                location_name="Chicago",
                admin1="Illinois",
                country="United States",
                country_code="US",
                latitude=41.8781,
                longitude=-87.6298,
                start_date="2025-01-01",
                end_date="2025-01-02",
            )

        self.assertEqual(
            str(context.exception),
            "Daily weather field has incorrect length: temperature_2m_max",
        )

    # testing that error raised if API response doesn't include 'daily' data
    @patch("weather.services.weather_import.fetch_historical_weather")
    def test_import_historical_weather_missing_daily(self, mock_fetch):
        mock_fetch.return_value = {
            "timezone": "America/Chicago",
        }

        with self.assertRaises(ValueError) as context:
            import_historical_weather(
                id=123,
                location_name="Chicago",
                admin1="Illinois",
                country="United States",
                country_code="US",
                latitude=41.8781,
                longitude=-87.6298,
                start_date="2025-01-01",
                end_date="2025-01-03",
            )

        self.assertEqual(
            str(context.exception),
            "Weather API response missing daily data",
        )