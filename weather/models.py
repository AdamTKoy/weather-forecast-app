from django.db import models

class Location(models.Model):
    open_meteo_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timezone = models.CharField(max_length=50)
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    admin1 = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name}, {self.admin1}, {self.country}"


class WeatherObservation(models.Model):
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="weather_observations",
    )

    date = models.DateField()

    temperature_max = models.FloatField(null=True)
    temperature_min = models.FloatField(null=True)
    temperature_mean = models.FloatField(null=True)

    precipitation_sum = models.FloatField(null=True)
    rain_sum = models.FloatField(null=True)
    snowfall_sum = models.FloatField(null=True)

    wind_speed_max = models.FloatField(null=True)
    wind_gusts_max = models.FloatField(null=True)

    cloud_cover_mean = models.FloatField(null=True)
    humidity_mean = models.FloatField(null=True)

    pressure_mean = models.FloatField(null=True)

    weather_code = models.IntegerField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["location", "date"],
                name="unique_weather_observation",
            )
        ]
        ordering = ["date"]

    def __str__(self):
        return f"{self.location.name} - {self.date}"
    