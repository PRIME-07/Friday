from tools.weatherTool import WeatherTool
from agents.WeatherAgent import WeatherAgent

# Initialize weather agent
weather_agent = WeatherAgent()

while True:
    # Get user query
    user_query = input("You: ")
    user_query = user_query.lower()

    # exit chat
    if user_query.lower() == "/bye":
        print("Goodbye!")
        break

    # Process request
    response = weather_agent.handle_request(user_query)

    # Print response
    print(response)


