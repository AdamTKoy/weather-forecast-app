# This will convert a city name to its corresponding latitude and longitude values

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

def geocode_city(search_location):
    params = {
        "name": search_location,
        "count": 1, # modify to allow multiple results (ex: Springfield is a city in several US states)
        "language": "en",
        "format": "json",
    }

    response = requests.get(
        GEOCODING_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    results = data.get("results")

    if not results:
        raise ValueError(f"Could not find location: {search_location}")

    return results[0]

    # TODO: validate locations with same city names (ie, Springfield) using admin1
    # for result in results:
    #     if (
    #         result.get("name", "").lower() == search_location.lower()
    #         and result.get("admin1")
    #     ):
    #         return result

    # return results[0]