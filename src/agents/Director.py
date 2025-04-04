import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
from .WeatherAgent import WeatherAgent
from .EmailAgent import EmailAgent
from .WebSearchAgent import WebSearchAgent
import json
from datetime import datetime

# Load environment variables
load_dotenv()

class Director:
    def __init__(self):
        """Initialize Director with available agents and OpenAI client."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize agents
        self.agents = {
            "weather": WeatherAgent(),
            "email": EmailAgent(),
            "web": WebSearchAgent()  # Add the new WebSearchAgent
        }

        # Give EmailAgent a reference to the Director for context
        self.agents["email"]._director = self
        
        self.conversation_history = []  # Store conversation history
        self.last_email_context = None  # Store context of last viewed email
        
        # Update system prompt to include web search capabilities
        self.system_prompt = """
        You are WingMan's Director, a helpful and intelligent assistant that can both handle general conversations 
        and coordinate with specialized agents. You have access to:

        1. Email Agent: For tasks involving:
           - Reading/checking emails
           - Sending emails
           - Managing inbox
           - Email searches

        2. Weather Agent: For tasks involving:
           - Current weather conditions
           - Weather forecasts
           - Location-based weather info

        3. Web Search Agent: For tasks involving:
           - Quick factual queries
           - Detailed research questions
           - Current events and news
           - General knowledge queries

        For general queries (like casual conversation, facts, explanations, etc.), you can answer directly.
        
        For specialized tasks, delegate to the appropriate agent using these exact JSON formats:

        Email tasks:
        {
            "agent": "email",
            "action": "read|send",
            "parameters": {
                "type": "unread|from_sender|search|send_new",
                "sender": "sender name or null",
                "query": "search query or null"
            }
        }

        Weather tasks:
        {
            "agent": "weather",
            "action": "get_weather",
            "parameters": {
                "location": "location name or null",
                "current_location": true/false
            }
        }

        Web Search tasks:
        {
            "agent": "web",
            "action": "search",
            "parameters": {
                "type": "quick|detailed",
                "query": "search query"
            }
        }

        For general conversation:
        {
            "agent": "self",
            "response": "your direct response here"
        }

        Always analyze the context and choose the most appropriate way to handle each request.
        """

        # System prompt for response validation
        self.validation_prompt = """
        You are WingMan's Quality Controller. Evaluate if the agent's response adequately answers the user's question.
        Consider:
        1. Does it address the main query?
        2. Is the information complete?
        3. Is it clear and understandable?

        Respond with JSON:
        {
            "satisfactory": true/false,
            "missing_info": ["list", "of", "missing", "elements"],
            "suggestion": "how to improve the response"
        }
        """

    def add_to_history(self, role: str, content: str, metadata: Dict = None):
        """Add a message to conversation history with timestamp and optional metadata."""
        history_entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # If there's additional metadata (like email summaries), add it
        if metadata:
            history_entry["metadata"] = metadata
            
        self.conversation_history.append(history_entry)

    def get_recent_context(self, limit: int = 5) -> List[Dict]:
        """Get recent conversation context for the AI."""
        # Convert history to format expected by OpenAI
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add recent history, including metadata for context
        for entry in self.conversation_history[-limit:]:
            content = entry["content"]
            
            # If there's metadata, add it to the content for context
            if "metadata" in entry:
                if entry["metadata"].get("type") == "email":
                    content = f"[Email Content: {content}]"
                elif entry["metadata"].get("type") == "weather":
                    content = f"[Weather Update: {content}]"
            
            messages.append({
                "role": entry["role"],
                "content": content
            })
            
        return messages

    def analyze_request(self, user_query: str) -> Dict[str, Any]:
        """Analyze user request and determine whether to handle directly or delegate."""
        try:
            # Get conversation context
            recent_messages = self.conversation_history[-3:]
            
            messages = [
                {"role": "system", "content": """
                You are WingMan's conversation analyzer. Analyze the conversation context and current query to determine the best way to handle it.
                
                IMPORTANT: You must ALWAYS respond with a valid JSON object, nothing else.
                
                For web search tasks (use when user wants to find information, search, or learn about something):
                {
                    "agent": "web",
                    "action": "search",
                    "parameters": {
                        "type": "quick",  # or "detailed" for complex queries
                        "query": "user's search query"
                    },
                    "reason": "user wants to search for information"
                }

                For weather tasks (use when user asks about weather, temperature, forecast):
                {
                    "agent": "weather",
                    "action": "get_weather",
                    "parameters": {
                        "location": "location name or null",
                        "current_location": true
                    },
                    "reason": "user wants weather information"
                }

                For email tasks (keep existing email handling):
                {
                    "agent": "email",
                    "action": "read|send|reply",
                    "parameters": {
                        "type": "unread|from_sender|search|send_new",
                        "sender": "sender name or null",
                        "query": "email content or null"
                    }
                }

                For general conversation (when query doesn't match other agents):
                {
                    "agent": "self",
                    "response": null,
                    "reason": "general conversation"
                }

                Common patterns:
                - Search/find/what is/tell me about -> web agent
                - Weather/temperature/forecast -> weather agent
                - Email/mail/inbox/send/reply -> email agent
                - General chat/questions/advice -> self (general conversation)
                """},
                {"role": "user", "content": f"""
                Recent conversation:
                {json.dumps([{
                    'role': msg['role'],
                    'content': msg['content']
                } for msg in recent_messages], indent=2)}

                Current query: {user_query}

                Return ONLY a JSON object for handling this query.
                """}
            ]

            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0
            )

            response = completion.choices[0].message.content.strip()
            
            # Clean up the response
            if response.startswith("```json"):
                response = response[7:-3]
            elif response.startswith("```"):
                response = response[3:-3]
            
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    response = json_match.group()
            except:
                pass
            
            try:
                analysis = json.loads(response.strip())
                print(f"Debug - Analysis: {json.dumps(analysis, indent=2)}")  # Debug print
                return analysis
            except json.JSONDecodeError:
                # Smart fallback based on query content
                query_lower = user_query.lower()
                
                # Check for weather-related queries
                if any(x in query_lower for x in ["weather", "temperature", "forecast", "rain", "sunny"]):
                    return {
                        "agent": "weather",
                        "action": "get_weather",
                        "parameters": {
                            "location": None,
                            "current_location": True
                        },
                        "reason": "user wants weather information"
                    }
                
                # Check for search-related queries
                elif any(x in query_lower for x in ["search", "find", "what is", "what are", "tell me about", "how to"]):
                    return {
                        "agent": "web",
                        "action": "search",
                        "parameters": {
                            "type": "quick",
                            "query": user_query
                        },
                        "reason": "user wants to search for information"
                    }
                
                # Check for email-related queries (keep existing email handling)
                elif any(x in query_lower for x in ["read", "check", "mail", "inbox", "emails"]):
                    return {
                        "agent": "email",
                        "action": "read",
                        "parameters": {
                            "type": "unread",
                            "sender": None,
                            "max_results": 5
                        },
                        "reason": "user wants to check their emails"
                    }
                
                # Default to general conversation
                return {
                    "agent": "self",
                    "response": None,
                    "reason": "general conversation"
                }

        except Exception as e:
            print(f"Analysis error: {e}")
            # Smart error fallback
            query_lower = user_query.lower()
            
            if any(x in query_lower for x in ["search", "find", "what is", "what are", "tell me about"]):
                return {
                    "agent": "web",
                    "action": "search",
                    "parameters": {
                        "type": "quick",
                        "query": user_query
                    },
                    "reason": "user wants to search for information"
                }
            
            # Default to self for general conversation
            return {
                "agent": "self",
                "response": None,
                "reason": "Error in analysis, defaulting to general conversation"
            }

    def validate_response(self, original_query: str, agent_response: str) -> Dict[str, Any]:
        """Validate if the agent's response adequately answers the user's question."""
        try:
            # Skip validation for certain types of responses
            if "weather" in original_query.lower() and "temperature" in agent_response.lower():
                return {"satisfactory": True, "suggestion": None}
                
            if "email" in original_query.lower() and any(x in agent_response.lower() for x in ["message", "email", "inbox"]):
                return {"satisfactory": True, "suggestion": None}

            messages = [
                {"role": "system", "content": """
                You are a response validator. Check if the response adequately answers the user's question.
                Return JSON in this format:
                {
                    "satisfactory": true/false,
                    "suggestion": "additional info needed or null"
                }
                
                Be lenient - if the response contains relevant information, mark it as satisfactory.
                Only mark as unsatisfactory if the response is completely off-topic or empty.
                """},
                {"role": "user", "content": f"""
                Original question: {original_query}
                Response received: {agent_response}
                
                Is this response satisfactory?
                """}
            ]

            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0
            )

            response = completion.choices[0].message.content.strip()
            
            # Clean up the response
            if response.startswith("```json"):
                response = response[7:-3]
            elif response.startswith("```"):
                response = response[3:-3]
            
            validation = json.loads(response.strip())
            
            # Default to satisfactory if we can't parse the validation
            if not isinstance(validation, dict):
                return {"satisfactory": True, "suggestion": None}
                
            return validation

        except Exception as e:
            print(f"Validation error: {e}")
            # If validation fails, assume the response is good enough
            return {"satisfactory": True, "suggestion": None}

    def format_response(self, agent_response: str, user_query: str = "") -> str:
        """Format the agent's response to be concise and match the user's tone."""
        try:
            messages = [
                {"role": "system", "content": """
                Rewrite the given response to match the user's tone and style while keeping it concise.
                
                Tone matching rules:
                - If user is casual/informal (uses slang, abbreviations, emojis):
                  → Reply casually with similar energy
                - If user is formal/professional:
                  → Keep response formal and straightforward
                - If user shows emotion (excitement, frustration, etc.):
                  → Acknowledge and mirror appropriate emotion level
                - If user is brief/direct:
                  → Keep response similarly brief
                
                Content rules:
                - Weather: Include key info (temperature, main conditions)
                - Emails: Focus on important details
                - Keep technical info but present it in matching style
                - Maintain factual accuracy while adjusting presentation
                
                Example tone matches:
                User: "hey what's the temp rn?"
                → "It's a toasty 30°C out there!"
                
                User: "Could you check the current temperature?"
                → "The current temperature is 30°C with clear conditions."
                """},
                {"role": "user", "content": f"""
                User's message: {user_query}
                Response to restyle: {agent_response}
                
                Rewrite the response to match the user's tone while keeping it concise.
                """}
            ]

            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7
            )

            return completion.choices[0].message.content.strip()

        except Exception as e:
            return agent_response

    def handle_request(self, user_query: str) -> str:
        """Main method to handle user requests and coordinate with agents."""
        try:
            # Add user query to history
            self.add_to_history("user", user_query)
            analysis = self.analyze_request(user_query)
            
            # Store the last used agent for context
            self.last_used_agent = analysis["agent"]
            
            if analysis["agent"] == "self":
                # Handle general conversation using GPT
                messages = [
                    {"role": "system", "content": """
                    You are WingMan, a friendly and helpful AI assistant. Keep your responses:
                    - Natural and conversational
                    - Engaging and personable
                    - Informative when needed
                    - Brief but complete
                    - Match the user's tone and energy
                    
                    You can handle casual chat, answer questions, give opinions, and engage in general conversation.
                    Use emojis when appropriate to match the tone.
                    """},
                    # Add recent conversation context
                    *[{
                        "role": msg["role"],
                        "content": msg["content"]
                    } for msg in self.conversation_history[-5:]], # Last 5 messages for context
                    {"role": "user", "content": user_query}
                ]

                completion = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7  # Add some variety to responses
                )

                response = completion.choices[0].message.content.strip()
                self.add_to_history("assistant", response)
                return response
            
            elif analysis["agent"] == "email":
                agent = self.agents["email"]
                
                if analysis["action"] == "read":
                    # Handle read email requests
                    email_request = {
                        "action": "read",
                        "parameters": {
                            "type": analysis["parameters"].get("type", "unread"),
                            "sender": analysis["parameters"].get("sender"),
                            "max_results": 5
                        }
                    }
                elif analysis["action"] == "reply":
                    # Check if this is a reply request
                    if self.last_email_context:
                        email_request = {
                            "action": "reply",
                            "parameters": {
                                "message_id": self.last_email_context["id"],
                                "to": self.last_email_context["sender"],
                                "query": analysis["parameters"].get("query") or user_query
                            }
                        }
                    else:
                        response = "I'm not sure how to reply to that. Please ask me to read your mail first."
                        self.add_to_history("assistant", response)
                        return response
                else:
                    # Handle new email send requests
                    # Check if this is a confirmation for a pending email
                    if "yes" in user_query.lower():
                        email_request = {
                            "action": "send",
                            "parameters": {
                                "query": "yes"  # This signals to EmailAgent that it's a confirmation
                            }
                        }
                    else:
                        # Create a new email request
                        email_request = {
                            "action": "send",
                            "parameters": {
                                "to": analysis["parameters"].get("sender"),
                                "query": analysis["parameters"].get("query"),
                                "type": "send_new"
                            }
                        }
                        
                        # If the query contains an email address and content, make sure both are passed
                        if '@' in user_query:
                            email_parts = user_query.split(' ')
                            for part in email_parts:
                                if '@' in part:
                                    email_request["parameters"]["to"] = part
                                    # Remove the email address from the query to get clean content
                                    email_request["parameters"]["query"] = user_query.replace(part, '').strip()
                                    break
                
                agent_response = agent.handle_request(email_request)
                formatted_response = self.format_response(agent_response, user_query)
                self.add_to_history("assistant", formatted_response, {
                    "type": "email",
                    "raw_response": agent_response,
                    "action": email_request["action"],
                    "parameters": email_request["parameters"]
                })
                
                return formatted_response
                
            elif analysis["agent"] in self.agents:
                agent = self.agents[analysis["agent"]]
                if analysis["agent"] == "weather":
                    # Weather agent expects string
                    agent_response = agent.handle_request(user_query)
                    formatted_response = self.format_response(agent_response, user_query)
                    self.add_to_history("assistant", formatted_response, {
                        "type": "weather",
                        "raw_response": agent_response
                    })
                
                elif analysis["agent"] == "web":
                    # Web search agent expects structured request
                    agent_response = agent.handle_request(analysis)
                    if "error" in agent_response:
                        # If search failed, try again with detailed search
                        analysis["parameters"]["type"] = "detailed"
                        agent_response = agent.handle_request(analysis)
                    
                    formatted_response = self.format_response(agent_response, user_query)
                    self.add_to_history("assistant", formatted_response, {
                        "type": "web",
                        "raw_response": agent_response,
                        "query": analysis["parameters"]["query"]
                    })
                    
                return formatted_response
            
            else:
                response = "I'm not sure how to handle that request. Could you please rephrase it?"
                self.add_to_history("assistant", response)
                return response

        except Exception as e:
            response = f"Aw snap, something went wrong: {str(e)}"
            self.add_to_history("assistant", response)
            return response

    def get_agent_status(self) -> Dict[str, bool]:
        """Check the status of all agents."""
        status = {}
        for agent_name, agent in self.agents.items():
            try:
                # Simple initialization check
                status[agent_name] = agent is not None
            except Exception as e:
                status[agent_name] = False
        return status 