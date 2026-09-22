from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch
from weather.models import Location, WeatherForecast, WeatherObservation
from datetime import date, timedelta
import requests

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
        self.assertContains(response, "Weather Explorer")
        self.assertContains(response, 'name="query"')
        self.assertNotContains(response, "Data Range:")

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

    def test_forecast_shows_latest_origin_and_only_seven_days(self):
        # An older forecast should not appear.
        WeatherForecast.objects.create(
            location=self.location,
            forecast_origin=date(2025, 1, 8),
            forecast_date=date(2025, 1, 10),
            temperature_mean=99.0,
        )

        latest_origin = date(2025, 1, 9)

        # Create eight days to verify the page displays only seven.
        for day in range(1, 9):
            WeatherForecast.objects.create(
                location=self.location,
                forecast_origin=latest_origin,
                forecast_date=latest_origin + timedelta(days=day),
                temperature_mean=30.0 + day,
            )

        response = self.client.get(
            reverse("forecast", args=[self.location.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "weather/forecast.html")
        self.assertEqual(
            response.context["forecast_origin"],
            latest_origin,
        )

        forecasts = list(response.context["forecasts"])

        self.assertEqual(len(forecasts), 7)
        self.assertEqual(
            [prediction.forecast_date for prediction in forecasts],
            [
                latest_origin + timedelta(days=day)
                for day in range(1, 8)
            ],
        )
        self.assertTrue(
            all(
                prediction.forecast_origin == latest_origin
                for prediction in forecasts
            )
        )
        self.assertContains(response, "31.0 °F")
        self.assertNotContains(response, "99.0 °F")
        self.assertNotContains(response, "38.0 °F")

    def test_forecast_without_saved_predictions(self):
        response = self.client.get(
            reverse("forecast", args=[self.location.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "No saved forecast is available for this location yet.",
        )

    def test_forecast_unknown_location_returns_404(self):
        response = self.client.get(
            reverse("forecast", args=[0])
        )

        self.assertEqual(response.status_code, 404)

    @patch("weather.views.search_cities")
    def test_city_search_shows_external_results(self, mock_search):
        mock_search.return_value = [
            {
                "id": 999001,
                "name": "Springfield",
                "admin1": "Illinois",
                "country": "United States",
            },
            {
                "id": 999002,
                "name": "Springfield",
                "admin1": "Massachusetts",
                "country": "United States",
            },
        ]
        original_count = Location.objects.count()

        response = self.client.get(
            reverse("location_list"),
            {"query": "Springfield"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Illinois")
        self.assertContains(response, "Massachusetts")
        mock_search.assert_called_once_with("Springfield")

        # Searching alone should not create database records.
        self.assertEqual(Location.objects.count(), original_count)

    @patch("weather.views.search_cities")
    def test_select_city_without_observations(self, mock_search):
        mock_search.return_value = [
            {
                "id": 999001,
                "name": "Springfield",
                "latitude": 39.8017,
                "longitude": -89.6436,
                "timezone": "America/Chicago",
                "admin1": "Illinois",
                "country": "United States",
                "country_code": "US",
            },
        ]

        selection = {
            "query": "Springfield",
            "city_id": "999001",
        }

        response = self.client.post(
            reverse("location_list"),
            selection,
        )

        location = Location.objects.get(open_meteo_id=999001)

        self.assertRedirects(
            response,
            reverse("historical_weather", args=[location.id]),
        )
        self.assertEqual(location.name, "Springfield")
        self.assertEqual(location.admin1, "Illinois")
        self.assertEqual(location.weather_observations.count(), 0)

        # Selecting the same city again should reuse its record.
        self.client.post(reverse("location_list"), selection)

        self.assertEqual(
            Location.objects.filter(open_meteo_id=999001).count(),
            1,
        )

    @patch("weather.views.search_cities")
    def test_city_selection_rejects_unknown_id(self, mock_search):
        mock_search.return_value = [
            {"id": 999001, "name": "Springfield"},
        ]
        original_count = Location.objects.count()

        response = self.client.post(
            reverse("location_list"),
            {
                "query": "Springfield",
                "city_id": "999999",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Please search again and choose a matching city.",
        )
        self.assertEqual(Location.objects.count(), original_count)

    @patch("weather.views.search_cities")
    def test_city_search_handles_service_failure(self, mock_search):
        mock_search.side_effect = requests.Timeout()

        response = self.client.get(
            reverse("location_list"),
            {"query": "Springfield"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "City search is temporarily unavailable. Please try again.",
        )

    @patch("weather.views.geocode_city")
    @patch("weather.views.import_historical_weather")
    def test_import_uses_selected_city(self, mock_import, mock_geocode):
        response = self.client.post(
            reverse("import_city_weather", args=[self.location.id]),
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
            },
        )

        mock_import.assert_called_once_with(
            id=self.location.open_meteo_id,
            location_name=self.location.name,
            admin1=self.location.admin1,
            country=self.location.country,
            country_code=self.location.country_code,
            latitude=self.location.latitude,
            longitude=self.location.longitude,
            start_date="2024-01-01",
            end_date="2024-01-07",
        )
        mock_geocode.assert_not_called()

        self.assertRedirects(
            response,
            reverse("historical_weather", args=[self.location.id]),
        )

    @patch("weather.views.import_historical_weather")
    def test_city_import_requires_end_date(self, mock_import):
        response = self.client.post(
            reverse("import_city_weather", args=[self.location.id]),
            {
                "start_date": "2024-01-01",
                "end_date": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "end_date",
            "This field is required.",
        )
        self.assertNotIn("location", response.context["form"].fields)
        mock_import.assert_not_called()

    @patch("weather.views.import_historical_weather")
    def test_city_import_handles_service_failure(self, mock_import):
        mock_import.side_effect = requests.Timeout()

        response = self.client.post(
            reverse("import_city_weather", args=[self.location.id]),
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Unable to import weather for this date range. "
            "Please try again.",
        )
    @patch("weather.views.generate_temperature_forecast")
    def test_forecast_get_does_not_generate(self, mock_generate):
        response = self.client.get(reverse("forecast", args=[self.location.id]))
        self.assertContains(response, "Generate 7-day forecast")
        mock_generate.assert_not_called()

    @patch("weather.views.generate_temperature_forecast")
    def test_forecast_post_saves_and_replaces_predictions(self, mock_generate):
        from datetime import datetime

        # Exercise the timestamp type returned by the model, as well as dates
        # already covered by the command test.
        mock_generate.return_value = [
            {"date": datetime(2025, 1, day), "temperature_mean": 30.0 + day}
            for day in range(2, 9)
        ]
        url = reverse("forecast", args=[self.location.id])
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, url)
        self.assertContains(response, "Your seven-day forecast has been generated and saved.")
        mock_generate.assert_called_once_with(self.location.id, days=7)
        forecasts = WeatherForecast.objects.filter(location=self.location)
        self.assertEqual(forecasts.count(), 7)
        self.assertEqual(forecasts.first().forecast_origin, date(2025, 1, 1))
        mock_generate.return_value[0]["temperature_mean"] = 42.5
        self.client.post(url)
        self.assertEqual(forecasts.count(), 7)
        self.assertEqual(forecasts.first().temperature_mean, 42.5)

    @patch("weather.views.generate_temperature_forecast")
    def test_forecast_generation_error_keeps_existing_predictions(self, mock_generate):
        saved = WeatherForecast.objects.create(
            location=self.location,
            forecast_origin=date(2025, 1, 1),
            forecast_date=date(2025, 1, 2),
            temperature_mean=32.0,
        )
        mock_generate.side_effect = ValueError("The latest observation has missing forecast features.")
        response = self.client.post(reverse("forecast", args=[self.location.id]))
        self.assertContains(response, "Unable to generate a forecast.")
        self.assertContains(response, "missing forecast features")
        saved.refresh_from_db()
        self.assertEqual(saved.temperature_mean, 32.0)

    def test_forecast_without_history_guides_user_to_import(self):
        self.location.weather_observations.all().delete()
        url = reverse("forecast", args=[self.location.id])
        response = self.client.get(url)
        self.assertContains(response, "Import historical observations for this city")
        self.assertContains(response, reverse("import_city_weather", args=[self.location.id]))
        # A direct POST must also fail gracefully without creating predictions.
        response = self.client.post(url)
        self.assertContains(response, "No historical weather observations available.")
        self.assertFalse(WeatherForecast.objects.exists())

    def test_forecast_generation_requires_csrf(self):
        from django.test import Client
        response = Client(enforce_csrf_checks=True).post(
            reverse("forecast", args=[self.location.id])
        )
        self.assertEqual(response.status_code, 403)
