import os
from openai import OpenAI
from dotenv import load_dotenv
from tools.weatherTool import WeatherTool
from typing import Dict, Any

# Load .env file
load_dotenv()


class WeatherAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.weather_tool = WeatherTool()

        # system prompt
        self.system_prompt = """
            You are the Weather Agent of WingMan, a hyper-personalized assistant. You provide weather information in a helpful,
            friendly and concise manner.
            Include the relevant details such as the location, local time, temperature, humidity, cloud cover, precipitation, rain, and when relevant,
            add practical implications like (e.g., "Might want to use sunscreen" or "Stay hydrated" or "Might want to grab an umbrella").
            Present the information in a way that is conversational and engaging.
            """

    def _parse_location(self, query: str) -> Dict[str, Any]:
        """Parse location information from query."""
        # If no specific location mentioned, default to current location
        location_keywords = ['in', 'at', 'for', 'of']
        query_lower = query.lower()
        
        # If query doesn't contain location keywords, assume current location
        if not any(keyword + ' ' in query_lower for keyword in location_keywords):
            return {
                'current_location': True,
                'location': None
            }
            
        # ... rest of location parsing logic ...

    def check_location(self, user_query: str):
        """Analyze user query to determine location intent using natural language understanding."""
        messages = [
            {
                "role": "system",
                "content": """
                You are WingMan's location analyzer. Your task is to determine if the user is asking about:
                1. Current location weather (e.g., "how's the weather?" or "is it going to rain?")
                2. Specific location weather (e.g., "weather in New York" or "how's London looking?")
                
                For specific locations, extract ONLY the location name, no additional words.
                For current location queries, respond with "current_location".
                """
            },
            {"role": "user", "content": user_query},
        ]

        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        # Get the response and clean it
        location = completion.choices[0].message.content.strip()
        
        # Check if it's current location
        is_current = location.lower() == "current_location"
        
        return {
            "current_location": is_current,
            "location": None if is_current else location
        }

    def format_weather_response(self, weather_data, location_data):
        """Generate a natural language response from weather data using GPT."""
        location_context = "your location" if location_data[
            "current_location"] else location_data["location"]

        # Add local time to the context
        local_time = weather_data.get("local_time", "")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"Create a weather summary for {location_context} (Local time: {local_time}) based on this data: {weather_data}"
            }
        ]

        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        return completion.choices[0].message.content

    def handle_request(self, user_query: str):
        """Handles user request by fetching and returning weather information."""
        try:
            # Step 1: Determine location type from user query
            location_data = self.check_location(user_query)
            
            # Debug print
            print(f"Debug - Location data: {location_data}")

            # Step 2: Get coordinates using WeatherTool
            location_coordinates = self.weather_tool.figure_out_location(location_data)
            
            # Debug print
            print(f"Debug - Coordinates: {location_coordinates}")

            if not location_coordinates:
                return "WingMan: I couldn't pinpoint that location. Could you please specify the city name more clearly?"

            # Step 3: Get weather data using coordinates
            weather_data = self.weather_tool.get_weather(
                latitude=location_coordinates["latitude"],
                longitude=location_coordinates["longitude"]
            )

            if "error" in weather_data:
                return f"WingMan: Oops! Ran into a snag: {weather_data['error']}"

            # Step 4: Format the response using GPT
            response = self.format_weather_response(weather_data, location_data)
            return f"WingMan: {response}"

        except Exception as e:
            return f"WingMan: System error: {str(e)}"