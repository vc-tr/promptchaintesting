#!/usr/bin/env python3
"""
Test client for the n8n prompt chain demo.
This script allows you to interact with the OpenAI prompt chain through n8n.
"""

import requests
import json
import sys
from typing import Optional

class PromptChainClient:
    def __init__(self, base_url: str = "http://localhost:5678"):
        self.base_url = base_url
        self.webhook_url = f"{base_url}/webhook/chat"
        self.conversation_history = ""
        
    def send_message(self, message: str, conversation_history: Optional[str] = None) -> dict:
        """Send a message to the prompt chain and get AI response."""
        payload = {
            "message": message
        }
        
        if conversation_history:
            payload["conversation_history"] = conversation_history
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def interactive_chat(self):
        """Start an interactive chat session."""
        print("Prompt Chain Demo - Interactive Chat")
        print("=" * 50)
        print("Type 'quit' or 'exit' to end the session")
        print("Type 'reset' to start a new conversation")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("Goodbye!")
                    break
                    
                if user_input.lower() == 'reset':
                    self.conversation_history = ""
                    print("Conversation reset!")
                    continue
                    
                if not user_input:
                    continue
                
                print("Thinking...")
                response = self.send_message(user_input, self.conversation_history)
                
                if "error" in response:
                    print(f"Error: {response['error']}")
                    continue
                
                ai_response = response.get("response", "No response received")
                print(f"\nResponse: {ai_response}")
                print(f"Demo: {ai_response}")
                
                # Update conversation history for next message
                self.conversation_history = response.get("conversation_history", "")
                    
            except KeyboardInterrupt:
                print("\nChat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"Unexpected error: {str(e)}")

def main():
    """Main function to run the test client."""
    if len(sys.argv) > 1:
        # Single message mode
        message = " ".join(sys.argv[1:])
        client = PromptChainClient()
        response = client.send_message(message)
        
        if "error" in response:
            print(f"Error: {response['error']}")
            sys.exit(1)
        
        ai_response = response.get('response', 'No response')
        print(f"Response: {ai_response}")
        print(f"Demo: {ai_response}")
    else:
        # Interactive mode
        client = PromptChainClient()
        client.interactive_chat()

if __name__ == "__main__":
    main() 