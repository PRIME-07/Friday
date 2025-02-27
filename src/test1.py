from tools.weatherTool import WeatherTool
from agents.WeatherAgent import WeatherAgent


def print_help():
    """Print available commands and example queries."""
    print("\WingMan's Weather Module - Available Commands:")
    print("----------------------------------------")
    print("Example queries:")
    print("  - 'How's the weather?'")
    print("  - 'What's the weather like in New York?'")
    print("  - 'Is it raining in London?'")
    print("  - 'Weather forecast for Tokyo'")
    print("\nSystem commands:")
    print("  /help  - Show this help message")
    print("  /bye   - Exit the program")
    print("----------------------------------------\n")


def main():
    print("\nInitializing WingMan's Weather Module...")
    try:
        # Initialize weather agent
        weather_agent = WeatherAgent()
        print("WingMan Weather Module initialized successfully!")
        print("Type /help for example commands and queries")
        print("Type /bye to exit\n")

        while True:
            try:
                # Get user query
                user_query = input("You: ").strip()

                # Handle system commands
                if user_query.lower() == "/bye":
                    print("WingMan: Goodbye, buddy!")
                    break
                elif user_query.lower() == "/help":
                    print_help()
                    continue
                elif not user_query:
                    continue

                # Process weather request
                response = weather_agent.handle_request(user_query)
                print(response)

            except KeyboardInterrupt:
                print(
                    "\nWingMan: Detected interrupt signal. Shutting down...")
                break
            except Exception as e:
                print(
                    f"WingMan: I encountered an error processing that request: {str(e)}")
                print("Type /help for example commands or /bye to exit")

    except Exception as e:
        print(f"Error initializing WingMan's Weather Module: {str(e)}")
        print("Please check your API keys and internet connection.")
        return


if __name__ == "__main__":
    main()
