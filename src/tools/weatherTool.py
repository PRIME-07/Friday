import requests
import geocoder
from geopy.geocoders import Nominatim

class WeatherTool:
    def __init__(self):
        self.latitude = None
        self.longitude = None
        self.geolocator = Nominatim(user_agent="weather_agent")

    # Get current GPS coordinates
    def get_current_gps_coordinates(self):
        try:
            g = geocoder.ip('me')
            if g.latlng is not None:
                self.latitude, self.longitude = g.latlng
                return self.latitude, self.longitude
            else:
                return None
        except Exception as e:
            print(f"Error fetching current location coordinates: {e}")
            return None

    # Get location's GPS coordinates
    def get_location_gps_coordinates(self, location: str):
        try:
            location_data = self.geolocator.geocode(location, timeout=10)
            if location_data:
                return {"latitude": location_data.latitude, "longitude": location_data.longitude}
            else:
                print(f"Could not find coordinates for {location}")
                return None
        except GeocoderTimedOut:
            print("Geocoding service timed out. Try again later.")
            return None
        except Exception as e:
            print(f"Error fetching coordinates: {e}")
            return None

    # Get weather data for provided GPS coordinates
    def get_weather(self, latitude, longitude):
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,cloudcover,precipitation,rain,relative_humidity_2m,wind_speed_10m,weather_code"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if "current" in data:
                return data["current"]
            else:
                return {"error": "Unexpected API response format."}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching weather data: {e}"}
