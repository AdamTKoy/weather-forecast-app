from django.contrib import messages
from django.views.decorators.http import require_http_methods
from weather.ml.forecast import generate_temperature_forecast
from weather.services.forecast_storage import save_temperature_forecast
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg, Count, Max, Min, Sum
import requests
from weather.models import Location
from weather.forms import CitySearchForm, SelectedCityImportForm, WeatherImportForm, WeatherFilterForm
from weather.services.geocoding import geocode_city, search_cities
from weather.services.weather_import import import_historical_weather
from weather.services.weather_codes import get_weather_description

def historical_weather(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    filter_form = WeatherFilterForm(request.GET or None)

    filter_start_date = None
    filter_end_date = None

    observations = location.weather_observations.all() # using related name for weather observations table

    if filter_form.is_valid():
        start_date = filter_form.cleaned_data["start_date"]

        if start_date:
            observations = observations.filter(date__gte=start_date)
            filter_start_date = start_date

        end_date = filter_form.cleaned_data["end_date"]

        if end_date:
            observations = observations.filter(date__lte=end_date)
            filter_end_date = end_date

    observation_count = observations.count()

    highest_temperature = observations.aggregate(highest=Max("temperature_max"))["highest"]
    lowest_temperature = observations.aggregate(lowest=Min("temperature_min"))["lowest"]
    average_temperature = observations.aggregate(average=Avg("temperature_mean"))["average"]
    average_precipitation = observations.aggregate(average=Avg("precipitation_sum"))["average"]
    total_precipitation = observations.aggregate(total=Sum("precipitation_sum"))["total"]
    average_humidity = observations.aggregate(average=Avg("humidity_mean"))["average"]
    average_wind_speed = observations.aggregate(average=Avg("wind_speed_max"))["average"]
    average_pressure = observations.aggregate(average=Avg("pressure_mean"))["average"]
    average_wind_gusts = observations.aggregate(average=Avg("wind_gusts_max"))["average"]

    dates = [observation.date.isoformat() for observation in observations]
    temperature_max = [observation.temperature_max for observation in observations]
    temperature_min = [observation.temperature_min for observation in observations]
    precipitation = [observation.precipitation_sum for observation in observations]
    rain = [observation.rain_sum for observation in observations]
    snowfall = [observation.snowfall_sum for observation in observations]
    humidity = [observation.humidity_mean for observation in observations]
    wind_speed = [observation.wind_speed_max for observation in observations]
    wind_gusts = [observation.wind_gusts_max for observation in observations]
    pressure = [observation.pressure_mean for observation in observations]
    weather_descriptions = [get_weather_description(observation.weather_code) for observation in observations]

    observation_rows = zip(observations, weather_descriptions)

    return render(
        request,
        "weather/historical_weather.html",
        {
            "location": location,
            "observations": observations,
            "dates": dates,
            "temperature_max": temperature_max,
            "temperature_min": temperature_min,
            "precipitation": precipitation,
            "rain": rain,
            "snowfall": snowfall,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "wind_gusts": wind_gusts,
            "pressure": pressure,
            "weather_descriptions": weather_descriptions,
            "observation_rows": observation_rows,
            "filter_form": filter_form,
            "filter_start_date": filter_start_date,
            "filter_end_date": filter_end_date,
            "observation_count": observation_count,
            "highest_temperature": highest_temperature,
            "lowest_temperature": lowest_temperature,
            "average_temperature": average_temperature,
            "average_precipitation": average_precipitation,
            "total_precipitation": total_precipitation,
            "average_humidity": average_humidity,
            "average_wind_speed": average_wind_speed,
            "average_pressure": average_pressure,
            "average_wind_gusts": average_wind_gusts,
        },
    )

# GET for searches
# POST for user selection from search results
def location_list(request):
    submitted_data = (
        request.POST if request.method == "POST" else request.GET
    )
    form = CitySearchForm(submitted_data or None)
    cities = []

    if form.is_bound and form.is_valid():
        try:
            cities = search_cities(form.cleaned_data["query"])
        except (requests.RequestException, ValueError):
            form.add_error(
                None,
                "City search is temporarily unavailable. Please try again.",
            )
        else:
            if not cities:
                form.add_error(
                    "query",
                    "No matching cities found. Try another city name.",
                )
            elif request.method == "POST":
                # Verify the selection against the search provider.
                selected_id = request.POST.get("city_id", "")
                selected_city = next(
                    (
                        city for city in cities
                        if str(city["id"]) == selected_id
                    ),
                    None,
                )

                if selected_city is None:
                    form.add_error(
                        None,
                        "Please search again and choose a matching city.",
                    )
                else:
                    location, _ = Location.objects.update_or_create(
                        open_meteo_id=selected_city["id"],
                        defaults={
                            "name": selected_city["name"],
                            "latitude": selected_city["latitude"],
                            "longitude": selected_city["longitude"],
                            "timezone": selected_city.get("timezone", ""),
                            "admin1": selected_city.get("admin1", ""),
                            "country": selected_city.get("country", ""),
                            "country_code": selected_city.get(
                                "country_code", ""
                            ),
                        },
                    )
                    return redirect(
                        "historical_weather",
                        location_id=location.id,
                    )

    return render(
        request,
        "weather/location_list.html",
        {
            "form": form,
            "cities": cities,
        },
    )

def fetch_weather(request):
    if request.method == "POST":
        form = WeatherImportForm(request.POST)

        if form.is_valid():
            try:
                location_data = geocode_city(form.cleaned_data["location"])

                location = import_historical_weather(
                    id=location_data["id"],
                    location_name=location_data["name"],
                    admin1=location_data.get("admin1", ""),
                    country=location_data.get("country", ""),
                    country_code=location_data.get("country_code", ""),
                    latitude=location_data["latitude"],
                    longitude=location_data["longitude"],
                    start_date=form.cleaned_data["start_date"].isoformat(),
                    end_date=form.cleaned_data["end_date"].isoformat(),
                )
                return redirect("historical_weather", location_id=location.id)
            except Exception as e:
                form.add_error(None, f"Unable to fetch weather data: {e}")
    else:
        form = WeatherImportForm()

    return render(
        request,
        "weather/fetch_weather.html",
        {
            "form": form,
        },
    )

@require_http_methods(["GET", "POST"])
def forecast(request, location_id):
    location = get_object_or_404(Location, id=location_id)

    generation_error = None
    if request.method == "POST":
        try:
            predictions = generate_temperature_forecast(location.id, days=7)
            save_temperature_forecast(location.id, predictions)
        except ValueError as exc:
            generation_error = str(exc)
        else:
            messages.success(request, "Your seven-day forecast has been generated and saved.")
            return redirect("forecast", location_id=location.id)

    latest_observation = location.weather_observations.aggregate(
        latest=Max("date")
    )["latest"]

    latest_origin = location.weather_forecasts.aggregate(
        latest=Max("forecast_origin")
    )["latest"]

    forecasts = location.weather_forecasts.none()

    if latest_origin is not None:
        forecasts = location.weather_forecasts.filter(
            forecast_origin=latest_origin,
        ).order_by("forecast_date")[:7]

    return render(
        request,
        "weather/forecast.html",
        {
            "location": location,
            "forecast_origin": latest_origin,
            "latest_observation": latest_observation,
            "generation_error": generation_error,
            "forecasts": forecasts,
        },
    )

def import_city_weather(request, location_id):
    location = get_object_or_404(Location, id=location_id)

    form = SelectedCityImportForm(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST" and form.is_valid():
        try:
            import_historical_weather(
                id=location.open_meteo_id,
                location_name=location.name,
                admin1=location.admin1,
                country=location.country,
                country_code=location.country_code,
                latitude=location.latitude,
                longitude=location.longitude,
                start_date=form.cleaned_data["start_date"].isoformat(),
                end_date=form.cleaned_data["end_date"].isoformat(),
            )
        except (requests.RequestException, ValueError):
            form.add_error(
                None,
                "Unable to import weather for this date range. "
                "Please try again.",
            )
        else:
            return redirect(
                "historical_weather",
                location_id=location.id,
            )

    return render(
        request,
        "weather/fetch_weather.html",
        {
            "form": form,
            "location": location,
        },
    )