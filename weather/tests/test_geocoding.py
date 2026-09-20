# Run with: python3 manage.py test weather.tests.test_geocoding
# Test ALL with: python3 manage.py test weather

from django.test import SimpleTestCase
from unittest.mock import patch
from weather.services.geocoding import geocode_city

class GeocodingTest(SimpleTestCase):
    # testing that API call works
    @patch("weather.services.geocoding.requests.get")
    def test_geocode_city_returns_first_result(self, mock_get):
        mock_get.return_value.json.return_value = {
            "results": [
                {
                    "id": 488739,
                    "name": "Chicago",
                    "latitude": 41.8781,
                    "longitude": -87.6298,
                    "country": "United States",
                    "country_code": "US",
                    "admin1": "Illinois",
                }
            ]
        }

        result = geocode_city("Chicago")

        self.assertEqual(result["id"], 488739)
        self.assertEqual(result["name"], "Chicago")
        self.assertEqual(result["latitude"], 41.8781)
        self.assertEqual(result["longitude"], -87.6298)
        self.assertEqual(result["country"], "United States")
        self.assertEqual(result["country_code"], "US")
        self.assertEqual(result["admin1"], "Illinois")

    # testing that geocoding raises error if API returns empty result
    @patch("weather.services.geocoding.requests.get")
    def test_geocode_city_raises_error_when_no_results(self, mock_get):
        mock_get.return_value.json.return_value = {
            "results": []
        }

        with self.assertRaises(
            ValueError,
        ) as context:
            geocode_city("NotARealCity")

        self.assertEqual(
            str(context.exception),
            "Could not find location: NotARealCity",
        )