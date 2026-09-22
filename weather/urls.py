# Example: URL like /weather/1/
# will call: historical_weather(request, location_id=1)
#

from django.urls import path
from weather.views import (fetch_weather, forecast, historical_weather, import_city_weather, location_list)

urlpatterns = [
    path(
        "fetch/",
        fetch_weather,
        name="fetch_weather",
    ),
    path(
        "<int:location_id>/forecast/",
        forecast,
        name="forecast",
    ),
    path(
        "<int:location_id>/",
        historical_weather,
        name="historical_weather",
    ),
    path(
        "<int:location_id>/import/",
        import_city_weather,
        name="import_city_weather",
    ),
    path(
        "",
        location_list,
        name="location_list",
    ),
]