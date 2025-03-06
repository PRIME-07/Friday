import os
from openai import OpenAI
from dotenv import load_dotenv
from tools.mailTool import MailTool
from typing import List, Dict, Optional, Any
import json  # Add this to imports at top

# Load .env file
load_dotenv()

class EmailAgent:
    def __init__(self):
        """Initialize EmailAgent with its own MailTool instance."""
        self.mail_tool = MailTool()  # Create own instance like WeatherAgent does
        self.last_emails = []  # Will store the last fetched emails
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sender_name = self._get_sender_name()  # Get sender's name from Gmail

        self.compose_prompt = """
        You are an AI email assistant. Format emails professionally with clear structure:
        1. Start with an appropriate greeting (e.g., "Hi [name]," or "Dear [name],")
        2. Skip a line after greeting
        3. Write the main content in clear paragraphs
        4. Skip a line before the sign-off
        5. End with an appropriate closing (e.g., "Best regards," or "Thanks,") followed by the sender's name

        Current sender's name: {sender_name}

        Format the email with proper line breaks using \n for new lines.
        """

        self.system_prompt = """
        You are an email assistant. Analyze user requests and help manage emails.
        Keep responses conversational and match the user's tone.
        
        For email summaries:
        - Focus on the key message or request
        - Use natural language
        - Keep it brief but informative
        - Start with the sender's name
        
        Example summaries:
        "John's asking about the project deadline and needs your update by tomorrow"
        "Sarah shared the meeting notes from yesterday's team sync"
        """

    def handle_request(self, request) -> str:
        """Handle both structured requests from Director and string queries."""
        try:
            # If request is a string, convert it to structured format
            if isinstance(request, str):
                if any(word in request.lower() for word in ["check", "unread", "do i have"]):
                    request = {
                        "action": "list_unread",
                        "parameters": {
                            "max_results": 5
                        }
                    }
                else:
                    # Default to reading specific email
                    request = {
                        "action": "read_specific",
                        "parameters": {
                            "sender": request
                        }
                    }

            # Now handle the structured request
            action = request.get("action", "")
            params = request.get("parameters", {})

            if action == "list_unread":
                return self._handle_read_emails(params.get("max_results", 5))
            elif action == "read_specific":
                return self._handle_specific_email(params.get("sender"))
            else:
                return "I'm not sure what you want me to do with the emails. Could you be more specific?"

        except Exception as e:
            return f"Oops, ran into an issue with that: {str(e)}"

    def _handle_read_emails(self, max_results: int = 5) -> str:
        """Handle requests to read emails."""
        try:
            # Always refresh the email list when explicitly checking
            self.last_emails = self.mail_tool.get_unread_emails(max_results)
            
            if not self.last_emails:
                return "No unread emails at the moment! 📭"
                
            # Format emails in a conversational way
            senders = []
            for email in self.last_emails:
                sender = email['sender']
                # Clean up sender name
                sender = sender.replace('"', '').strip()
                if '<' in sender:
                    sender = sender.split('<')[0].strip()
                senders.append(sender)

            if len(senders) == 1:
                return f"You've got an unread email from {senders[0]}! Want me to tell you what it's about? 📧"
            else:
                sender_list = ", ".join(senders[:-1]) + f" and {senders[-1]}"
                return f"You've got {len(senders)} unread emails from {sender_list}! Which one you wanna hear about? 📧"

        except Exception as e:
            return f"Had trouble checking your emails: {str(e)}"

    def _handle_specific_email(self, sender: str) -> str:
        """Handle requests for specific emails."""
        try:
            if not self.last_emails:
                self.last_emails = self.mail_tool.get_unread_emails()
                if not self.last_emails:
                    return "No unread emails at the moment! 📭"

            # Find exact sender match
            for email in self.last_emails:
                if sender.lower() in email['sender'].lower():
                    return self._summarize_email(email)
            
            return f"I don't see any emails from {sender} in the current unread messages. 🤔"

        except Exception as e:
            return f"Had trouble getting that email details: {str(e)}"

    def _summarize_email(self, email: dict) -> str:
        """Create a summary of an email."""
        try:
            messages = [
                {"role": "system", "content": """
                Summarize the email content briefly and accurately.
                - Focus on the main message or purpose
                - Don't add information that's not in the email
                - Keep the tone casual but factual
                - Don't make assumptions about content not present
                """},
                {"role": "user", "content": f"""
                Summarize this email casually:
                From: {email['sender']}
                Subject: {email['subject']}
                Body: {email['body']}
                """}
            ]
            
            completion = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7
            )
            
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"Error summarizing email: {str(e)}"

    def _get_sender_name(self) -> str:
        """Get the sender's full name from Gmail profile."""
        try:
            profile = self.mail_tool.get_sender_profile()
            if profile and profile.get('name'):
                return profile['name']
            return "Anuj Sharad Mankumare"  # Fallback to your full name
        except Exception as e:
            print(f"Error getting sender name: {e}")
            return "Anuj Sharad Mankumare"  # Fallback to your full name

    def compose_email(self, to: str, subject: str, content_prompt: str) -> Dict[str, str]:
        """Compose an email using GPT-4."""
        try:
            # Generate subject if not provided
            if not subject:
                subject_completion = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Generate a concise email subject line based on the content."},
                        {"role": "user", "content": content_prompt}
                    ]
                )
                subject = subject_completion.choices[0].message.content.strip('"')

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Compose an email with the following requirements:\nTo: {to}\nSubject: {subject}\nContent guidelines: {content_prompt}"}
            ]

            completion = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )

            composed_email = completion.choices[0].message.content

            return {
                "to": to,
                "subject": subject,
                "body": composed_email,
                "status": "success"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def analyze_email_content(self, email_content: str) -> Dict[str, str]:
        """Analyze email content using GPT-4."""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Analyze this email content:\n\n{email_content}"}
            ]

            completion = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )

            analysis = completion.choices[0].message.content

            return {
                "analysis": analysis,
                "status": "success"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def send_composed_email(self, to: str, subject: str, content_prompt: str) -> Dict[str, str]:
        """Compose and send an email."""
        try:
            # First compose the email
            composed = self.compose_email(to, subject, content_prompt)
            
            if composed["status"] == "error":
                return composed

            # Send the email using MailTool
            success = self.mail_tool.send_email(
                to=to,
                subject=subject,
                body=composed["body"]
            )

            if success:
                return {
                    "status": "success",
                    "message": "Email composed and sent successfully",
                    "email_content": composed["body"]
                }
            else:
                return {
                    "status": "error",
                    "error": "Failed to send email"
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def get_unread_emails(self, max_results: int = 10) -> List[Dict]:
        """Get unread emails and mark them as read."""
        emails = self.mail_tool.get_unread_emails(max_results)
        
        # Analyze each email and mark as read
        analyzed_emails = []
        for email in emails:
            # Analyze the email content
            analysis = self.analyze_email_content(email["body"])
            
            # Mark the email as read
            self.mail_tool.mark_as_read(email["id"])
            
            # Add analysis to email data
            email["analysis"] = analysis.get("analysis", "Analysis failed")
            analyzed_emails.append(email)
        
        return analyzed_emails

    def get_emails_from_sender(self, sender_email: str, max_results: int = 10) -> List[Dict]:
        """Get emails from a specific sender with analysis."""
        emails = self.mail_tool.get_emails_from_sender(sender_email, max_results)
        
        # Analyze each email
        analyzed_emails = []
        for email in emails:
            analysis = self.analyze_email_content(email["body"])
            email["analysis"] = analysis.get("analysis", "Analysis failed")
            analyzed_emails.append(email)
        
        return analyzed_emails

    def compose_and_reply(self, original_message_id: str, to: str, content_prompt: str) -> Dict[str, str]:
        """Compose and send a reply to an email."""
        try:
            # First compose the reply
            composed = self.compose_email(to, "Re: Previous Email", content_prompt)
            
            if composed["status"] == "error":
                return composed

            # Send the reply using MailTool
            success = self.mail_tool.reply_to_email(
                original_message_id=original_message_id,
                to=to,
                body=composed["body"]
            )

            if success:
                return {
                    "status": "success",
                    "message": "Reply composed and sent successfully",
                    "email_content": composed["body"]
                }
            else:
                return {
                    "status": "error",
                    "error": "Failed to send reply"
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _suggest_contacts(self, partial_name: str) -> str:
        """Get contact suggestions based on partial name."""
        suggestions = self.mail_tool.get_email_suggestions(partial_name)
        if not suggestions:
            return f"No contacts found matching '{partial_name}'"

        response = f"Found these matching contacts for '{partial_name}':\n"
        for name, email in suggestions:
            response += f"- {name} <{email}>\n"
        return response 