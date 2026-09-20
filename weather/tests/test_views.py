from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch
from weather.models import Location, WeatherObservation
from datetime import date, timedelta

class WeatherViewTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            open_meteo_id=123,
            name="Chicago",
            latitude=41.8781,
            longitude=-87.6298,
            timezone="America/Chicago",
            country="United States",
            country_code="US",
            admin1="Illinois",
        )

        WeatherObservation.objects.create(
            location=self.location,
            date="2025-01-01",
            temperature_max=35.0,
            temperature_min=25.0,
            temperature_mean=30.0,
            weather_code=0,
        )

    def test_location_list(self):
        response = self.client.get(reverse("location_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chicago")
        self.assertContains(response, "Illinois")
        self.assertContains(response, "(1 day)")
        self.assertContains(response, "Data Range: Jan 1, 2025 to Jan 1, 2025")

    def test_historical_weather(self):
        response = self.client.get(
            reverse(
                "historical_weather",
                args=[self.location.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chicago")
        self.assertContains(response, "Jan. 1, 2025")
        self.assertContains(response, "35.0")
        self.assertContains(response, "25.0")
        self.assertContains(response, "Clear sky")
        self.assertContains(response, "Filter Historical Data")

    def test_fetch_weather(self):
        response = self.client.get(reverse("fetch_weather"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fetch Historical Weather")
        self.assertContains(response, "Location")
        self.assertContains(response, "Start Date")
        self.assertContains(response, "End Date")

    def test_fetch_weather_invalid_date_range(self):
        response = self.client.post(
            reverse("fetch_weather"),
            {
                "location": "Chicago, Illinois",
                "start_date": "2025-01-07",
                "end_date": "2025-01-01",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "End date must be on or after the start date.",
    )

    # mock data test to verify Django-side submission flow (independent of open-meteo)
    @patch("weather.views.import_historical_weather")
    @patch("weather.views.geocode_city")
    def test_fetch_weather_success(self, mock_geocode, mock_import):
        mock_geocode.return_value = {
            "id": 123,
            "name": "Chicago",
            "admin1": "Illinois",
            "country": "United States",
            "country_code": "US",
            "latitude": 41.8781,
            "longitude": -87.6298,
        }

        mock_import.return_value = self.location

        response = self.client.post(
            reverse("fetch_weather"),
            {
                "location": "Chicago, Illinois",
                "start_date": "2025-01-01",
                "end_date": "2025-01-03",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "historical_weather",
                args=[self.location.id],
            ),
        )

        mock_geocode.assert_called_once_with("Chicago, Illinois")
        mock_import.assert_called_once()

    # testing minimum-length location input validation
    def test_fetch_weather_location_too_short(self):
        response = self.client.post(
            reverse("fetch_weather"),
            {
                "location": "a",
                "start_date": "2025-01-01",
                "end_date": "2025-01-03",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Ensure this value has at least 2 characters",
        )

    # testing that user cannot request dataset larger than 10 years
    def test_fetch_weather_date_range_too_large(self):
        response = self.client.post(
            reverse("fetch_weather"),
            {
                "location": "Chicago, Illinois",
                "start_date": "2010-01-01",
                "end_date": "2025-01-01",
            },
        )

        self.assertContains(
            response,
            "The selected date range cannot exceed 10 years.",
        )

    # tests that when only specifying start date, no prior date data will be returned
    # (when it exists in the table)
    def test_historical_weather_start_date_filter(self):
        WeatherObservation.objects.create(
            location=self.location,
            date=date(2021, 1, 1),
            temperature_max=40,
            temperature_min=20,
            temperature_mean=30,
            weather_code=0,
        )
        WeatherObservation.objects.create(
            location=self.location,
            date=date(2021, 1, 3),
            temperature_max=45,
            temperature_min=25,
            temperature_mean=35,
            weather_code=1,
        )

        response = self.client.get(
            reverse("historical_weather", args=[self.location.id]),
            {"start_date": "2021-01-03"},
        )

        self.assertContains(response, "2021-01-03")
        self.assertNotContains(response, "2021-01-01")

    # tests that when only specifying end date, no later date data will be returned
    def test_historical_weather_end_date_filter(self):
        WeatherObservation.objects.create(
            location=self.location,
            date=date(2021, 1, 1),
            temperature_max=40,
            temperature_min=20,
            temperature_mean=30,
            weather_code=0,
        )
        WeatherObservation.objects.create(
            location=self.location,
            date=date(2021, 1, 3),
            temperature_max=45,
            temperature_min=25,
            temperature_mean=35,
            weather_code=1,
        )

        response = self.client.get(
            reverse("historical_weather", args=[self.location.id]),
            {"end_date": "2021-01-01"},
        )

        self.assertContains(response, "2021-01-01")
        self.assertNotContains(response, "2021-01-03")
        self.assertContains(
            response,
            "through Jan 1, 2021",
        )

    # tests that when only specifying both start and end dates, no outside date data will be returned
    def test_historical_weather_date_range_filter(self):
        WeatherObservation.objects.create(
            location=self.location,
            date=date(2021, 1, 2),
            temperature_max=42,
            temperature_min=22,
            temperature_mean=32,
            weather_code=0,
        )
        WeatherObservation.objects.create(
            location=self.location,
            date=date(2021, 1, 4),
            temperature_max=46,
            temperature_min=26,
            temperature_mean=36,
            weather_code=1,
        )

        response = self.client.get(
            reverse("historical_weather", args=[self.location.id]),
            {
                "start_date": "2021-01-02",
                "end_date": "2021-01-02",
            },
        )

        self.assertContains(response, "2021-01-02")
        self.assertNotContains(response, "2021-01-04")


    def test_historical_weather_invalid_date_range(self):
        response = self.client.get(
            reverse("historical_weather", args=[self.location.id]),
            {
                "start_date": "2021-01-05",
                "end_date": "2021-01-01",
            },
        )

        self.assertContains(
            response,
            "End date must be on or after the start date.",
        )

    def test_historical_weather_date_range_too_large(self):
        response = self.client.get(
            reverse("historical_weather", args=[self.location.id]),
            {
                "start_date": "2010-01-01",
                "end_date": "2025-01-01",
            },
        )

        self.assertContains(
            response,
            "The selected date range cannot exceed 10 years.",
        )

    def test_historical_weather_empty_date_range(self):
        response = self.client.get(
            reverse("historical_weather", args=[self.location.id]),
            {
                "start_date": "2020-01-01",
                "end_date": "2020-01-02",
            },
        )

        self.assertContains(
            response,
            "No observations found for the selected date range.",
        )

    def test_historical_weather_future_end_date(self):
        future_date = date.today() + timedelta(days=1)

        response = self.client.get(
            reverse("historical_weather", args=[self.location.id]),
            {
                "start_date": date.today().isoformat(),
                "end_date": future_date.isoformat(),
            },
        )

        self.assertContains(
            response,
            "End Date cannot be in the future.",
        )