# Example: URL like /weather/1/
# will call: historical_weather(request, location_id=1)
#

from django.urls import path
from weather.views import fetch_weather, historical_weather, location_list #, adminator_test

urlpatterns = [
    path(
        "",
        location_list,
        name="location_list",
    ),
    path(
        "<int:location_id>/",
        historical_weather,
        name="historical_weather",
    ),
    path(
        "fetch/",
        fetch_weather,
        name="fetch_weather",
    ),
]