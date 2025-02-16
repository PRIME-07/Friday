# Imports
import os
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from tools.weatherTool import WeatherTool

# Load .env file
load_dotenv()

class WeatherAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.weather_tool = WeatherTool()

        # Define tools
        self.tools = [
            # Weather tool
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current temperature for provided coordinates in celsius.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"},
                        },
                        "required": ["latitude", "longitude"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            }
            # add more tools here...
        ]

        # system prompt
        self.system_prompt = ("""
            You are a weather agent. You are tasked with providing the current weather
            information for a given location.
            You have access to a weather tool that can fetch the current weather data 
            for a given set of GPS coordinates. You can use this tool to get 
            information such as current temperature, cloud cover, precipitation, 
            rain, relative humidity, wind speed, and weather code. 
            Provide a brief summary using data such as temperature, cloud cover,
            and precipitation, rain, humidity and wind speed.
            """
        )

    def get_weather_info(self, user_query: str):
        """Process user query and get weather information."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query.lower()},
        ]

        # Create completion
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=self.tools,
        )

        # Dump model response
        completion.model_dump()

        # Define response model
        class WeatherResponse(BaseModel):
            temperature: float = Field(description="The current temperature in celsius for the given location.")
            response: str = Field(description="A natural language response to the user's question.")

        # Call model again with response format
        completion_2 = self.client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=messages,
            tools=self.tools,
            response_format=WeatherResponse,
        )

        # Parse final response
        final_response = completion_2.choices[0].message.parsed
        final_response.temperature
        final_response.response
        return final_response.temperature, final_response.response

    def handle_request(self, user_query: str):
        """Handles user request by fetching and returning weather information."""
        try:
            temperature, response = self.get_weather_info(user_query)
            return f"Wingman: {response}"
        except Exception as e:
            return f"Error processing request: {str(e)}"

