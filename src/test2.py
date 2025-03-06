import logging
import sys
import json
import os
from datetime import datetime
from agents.Director import Director

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class ChatMemory:
    def __init__(self, file_path="chat_history.json"):
        self.file_path = file_path
        self.history = self.load_history()
        self.current_conversation_id = None

    def load_history(self):
        """Load chat history from file."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"conversations": []}
        except Exception as e:
            logging.error(f"Error loading chat history: {e}")
            return {"conversations": []}

    def save_history(self):
        """Save chat history to file."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving chat history: {e}")

    def start_new_conversation(self):
        """Start a new conversation session."""
        conversation = {
            "id": len(self.history["conversations"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "messages": []
        }
        self.history["conversations"].append(conversation)
        self.current_conversation_id = conversation["id"]
        self.save_history()
        return conversation["id"]

    def add_message(self, role, content, metadata=None):
        """Add a message to the current conversation."""
        if not self.current_conversation_id:
            self.start_new_conversation()

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            message["metadata"] = metadata

        self.history["conversations"][self.current_conversation_id - 1]["messages"].append(message)
        self.save_history()

    def get_recent_messages(self, limit=5):
        """Get recent messages from the current conversation."""
        if not self.current_conversation_id:
            return []
        
        messages = self.history["conversations"][self.current_conversation_id - 1]["messages"]
        return messages[-limit:]

def print_help():
    """Print available commands and example queries."""
    print("\nWingMan - Available Commands:")
    print("----------------------------------------")
    print("Example queries:")
    print("Weather:")
    print("  - 'How's the weather?'")
    print("  - 'What's the weather like in New York?'")
    print("  - 'Is it raining in London?'")
    
    print("\nEmail:")
    print("  - 'Check my unread emails'")
    print("  - 'Send an email to John about the meeting'")
    print("  - 'Do I have any emails from Sarah?'")
    print("  - 'Reply to email 1 accepting the invitation'")
    
    print("\nWeb Search:")
    print("  - 'What's the latest news about SpaceX?'")
    print("  - 'Tell me about quantum computing'")
    print("  - 'Who won the last World Cup?'")
    print("  - 'Search for recent AI developments'")
    
    print("\nSystem commands:")
    print("  /help   - Show this help message")
    print("  /bye    - Exit the program")
    print("  /status - Check agents' status")
    print("  /new    - Start new conversation")
    print("----------------------------------------\n")

def main():
    print("\nInitializing WingMan...")
    try:
        director = Director()
        chat_memory = ChatMemory()
        chat_memory.start_new_conversation()
        
        print("WingMan initialized successfully!")
        print("Type /help for example commands and queries")
        print("Type /bye to exit\n")

        while True:
            user_query = input("You: ").strip()

            if user_query.lower() == "/bye":
                print("WingMan: Goodbye! 👋")
                break
            elif user_query.lower() == "/help":
                print_help()
                continue
            elif user_query.lower() == "/status":
                status = director.get_agent_status()
                print("\nAgent Status:")
                for agent, is_active in status.items():
                    status_emoji = "✅" if is_active else "❌"
                    print(f"- {agent.capitalize()}: {status_emoji} {'Active' if is_active else 'Inactive'}")
                print()
                continue
            elif user_query.lower() == "/new":
                chat_memory.start_new_conversation()
                print("\nWingMan: Started a new conversation! 🆕\n")
                continue
            elif not user_query:
                continue

            # Add user message to memory
            chat_memory.add_message("user", user_query)

            # Get recent context and add to director's conversation history
            recent_messages = chat_memory.get_recent_messages()
            director.conversation_history = [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"],
                    "metadata": msg.get("metadata", {})
                }
                for msg in recent_messages
            ]

            # Get response from director
            response = director.handle_request(user_query)
            
            # Add response to memory
            chat_memory.add_message("assistant", response, 
                                  metadata={"agent": director.last_used_agent} if hasattr(director, "last_used_agent") else None)

            print(f"\nWingMan: {response}\n")

    except Exception as e:
        print(f"Error initializing WingMan: {str(e)}")
        print("Please check your API keys and internet connection.")
        print("Required keys:")
        print("- OPENAI_API_KEY")
        print("- GMAIL_CLIENT_ID")
        print("- GMAIL_CLIENT_SECRET")
        print("- GMAIL_REFRESH_TOKEN")
        print("- TAVILY_API_KEY")

if __name__ == "__main__":
    main() 