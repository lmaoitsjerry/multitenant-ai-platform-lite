"""
Helpdesk Agent - AI-Powered Travel Assistant

Orchestrates helpdesk interactions using OpenAI function calling to:
1. Search knowledge base (RAG) for travel info
2. Generate quotes for customers
3. Answer platform questions
4. Route complex queries to human support

Uses OpenAI tool/function calling for intelligent routing.
Maintains persona as "Zara" - friendly Zorah Travel assistant.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from config.loader import ClientConfig

logger = logging.getLogger(__name__)


# Tool definitions for OpenAI function calling
HELPDESK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the travel knowledge base for information about hotels, destinations, rates, and general travel advice. Use this for questions about properties, locations, amenities, pricing, and travel tips.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query - what information to look for"
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["hotel_info", "pricing", "destination", "comparison", "general"],
                        "description": "Type of query for optimized search"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_quote",
            "description": "Start the quote generation process for a customer. Use this when a user wants to get pricing or book a trip to a specific destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Travel destination (e.g., 'Mauritius', 'Maldives', 'Zanzibar')"
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Check-in date in YYYY-MM-DD format"
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Check-out date in YYYY-MM-DD format"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adults (default: 2)"
                    },
                    "children": {
                        "type": "integer",
                        "description": "Number of children (default: 0)"
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Customer's name if provided"
                    },
                    "customer_email": {
                        "type": "string",
                        "description": "Customer's email if provided"
                    }
                },
                "required": ["destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "platform_help",
            "description": "Get help with using the Zorah platform features - quotes, invoices, CRM, settings, etc. Use this for 'how do I...' type questions about the platform.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": ["quotes", "invoices", "crm", "pipeline", "clients", "settings", "pricing", "general"],
                        "description": "Platform topic to get help with"
                    },
                    "question": {
                        "type": "string",
                        "description": "The specific question about the platform"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "route_to_human",
            "description": "Route the conversation to a human support agent. Use this for complex issues, complaints, account problems, or when the user explicitly asks to speak to a person.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why human support is needed"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Priority level for the support ticket"
                    },
                    "context": {
                        "type": "string",
                        "description": "Summary of the conversation so far"
                    }
                },
                "required": ["reason"]
            }
        }
    }
]


# System prompt for the agent
AGENT_SYSTEM_PROMPT = """You are Zara, a friendly and knowledgeable travel assistant at Zorah Travel. You help travel agents and their clients with travel inquiries.

YOUR PERSONALITY:
- Warm, enthusiastic, and genuinely helpful
- Confident in your knowledge but honest when unsure
- Professional but personable - not corporate or robotic
- You take pride in helping people plan amazing trips

AVAILABLE TOOLS:
1. search_knowledge_base - Search for hotel info, destinations, rates, travel tips
2. start_quote - Begin generating a quote for a customer (need destination + dates)
3. platform_help - Get help with using the Zorah platform
4. route_to_human - Transfer to human support for complex issues

GUIDELINES:
- Use tools to provide accurate, helpful responses
- For travel questions, always search the knowledge base first
- For platform questions (how do I...), use platform_help
- If someone wants pricing/booking, gather destination and dates, then start_quote
- Route to human for: complaints, account issues, complex problems, or if asked

RESPONSE STYLE:
- Keep responses conversational and natural
- Include specific details from tool results
- End with a helpful next step or question
- Never say "as an AI" - you're Zara from Zorah Travel"""


class HelpdeskAgent:
    """
    AI-powered helpdesk agent using OpenAI function calling.

    Orchestrates knowledge search, quote generation, platform help,
    and human routing based on user intent.
    """

    def __init__(self, config: Optional[ClientConfig] = None):
        """
        Initialize helpdesk agent.

        Args:
            config: Optional client config for tenant-specific features
        """
        self.config = config
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self._client = None

        # Track conversation for context
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 10  # Keep last 10 exchanges

        # Tool execution stats
        self.tool_calls = []

        logger.info("Helpdesk agent initialized")

    @property
    def client(self):
        """Lazy-load OpenAI client"""
        if self._client is None and self.openai_api_key:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized for helpdesk agent")
            except Exception as e:
                logger.error(f"Failed to create OpenAI client: {e}")
                self._client = None
        return self._client

    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return an AI response.

        Uses function calling to determine the best action:
        - Search knowledge base
        - Generate quote
        - Platform help
        - Route to human

        Args:
            user_message: The user's message/question

        Returns:
            Dict with 'response', 'tool_used', 'tool_result', 'sources'
        """
        if not self.client:
            return self._fallback_response(user_message)

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Trim history if too long
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

        try:
            # Call OpenAI with tools
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    *self.conversation_history
                ],
                tools=HELPDESK_TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=800
            )

            message = response.choices[0].message

            # Check if the model wants to use a tool
            if message.tool_calls:
                return self._handle_tool_calls(message, user_message)

            # Direct response (no tool needed)
            assistant_response = message.content or "I'm here to help! What would you like to know?"

            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_response
            })

            return {
                "response": assistant_response,
                "tool_used": None,
                "tool_result": None,
                "sources": []
            }

        except Exception as e:
            logger.error(f"Agent chat failed: {e}", exc_info=True)
            return self._fallback_response(user_message)

    def _handle_tool_calls(self, message, user_message: str) -> Dict[str, Any]:
        """Handle function/tool calls from the model"""
        tool_results = []
        sources = []

        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            logger.info(f"Tool call: {func_name}({func_args})")
            self.tool_calls.append({
                "timestamp": datetime.now().isoformat(),
                "tool": func_name,
                "args": func_args
            })

            # Execute the tool
            if func_name == "search_knowledge_base":
                result, src = self._execute_search(func_args)
                sources.extend(src)
            elif func_name == "start_quote":
                result = self._execute_start_quote(func_args)
            elif func_name == "platform_help":
                result = self._execute_platform_help(func_args)
            elif func_name == "route_to_human":
                result = self._execute_route_to_human(func_args)
            else:
                result = f"Unknown tool: {func_name}"

            tool_results.append({
                "tool": func_name,
                "result": result
            })

        # Get final response with tool results
        # Add tool results to conversation
        tool_results_text = "\n".join([
            f"[{r['tool']}]: {r['result']}" for r in tool_results
        ])

        self.conversation_history.append({
            "role": "assistant",
            "content": f"[Tool results]\n{tool_results_text}"
        })

        # Get synthesized response
        final_response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": AGENT_SYSTEM_PROMPT + "\n\nYou just used tools and got results. Now provide a natural, helpful response to the user based on what you found. Don't mention 'tool results' - just answer naturally."},
                *self.conversation_history,
                {"role": "user", "content": f"Based on the tool results above, provide a helpful response to: {user_message}"}
            ],
            temperature=0.7,
            max_tokens=600
        )

        assistant_response = final_response.choices[0].message.content

        # Update history with final response
        self.conversation_history[-1] = {
            "role": "assistant",
            "content": assistant_response
        }

        return {
            "response": assistant_response,
            "tool_used": tool_results[0]["tool"] if tool_results else None,
            "tool_result": tool_results[0]["result"] if tool_results else None,
            "sources": sources
        }

    def _execute_search(self, args: Dict) -> tuple:
        """Execute knowledge base search"""
        try:
            from src.services.faiss_helpdesk_service import get_faiss_helpdesk_service
            from src.services.rag_response_service import generate_rag_response

            query = args.get("query", "")
            query_type = args.get("query_type", "general")

            # Search FAISS
            service = get_faiss_helpdesk_service()
            results = service.search_with_context(query, top_k=5, min_score=0.3)

            if not results:
                return "No relevant information found in the knowledge base.", []

            # Format results
            content_summary = []
            sources = []
            for r in results[:3]:
                content = r.get('content', '')[:500]
                content_summary.append(content)
                sources.append({
                    "source": r.get('source', 'Knowledge Base'),
                    "score": r.get('score', 0)
                })

            return "\n---\n".join(content_summary), sources

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Search error: {str(e)}", []

    def _execute_start_quote(self, args: Dict) -> str:
        """Start quote generation process"""
        destination = args.get("destination", "")
        check_in = args.get("check_in", "")
        check_out = args.get("check_out", "")
        adults = args.get("adults", 2)
        children = args.get("children", 0)

        if not destination:
            return "Need a destination to create a quote. Where would you like to go?"

        if not check_in or not check_out:
            return f"Great choice - {destination}! To put together a quote, I'll need your travel dates. When are you looking to travel?"

        # For now, return guidance - full integration would call QuoteAgent
        return f"Ready to generate a quote for {destination} ({check_in} to {check_out}) for {adults} adults and {children} children. To proceed, please provide customer name and email, or create the quote from the Quotes section in the dashboard."

    def _execute_platform_help(self, args: Dict) -> str:
        """Get platform help"""
        topic = args.get("topic", "general")

        help_content = {
            "quotes": "To create a quote: Go to Quotes > Generate Quote. Fill in client details, select destination and dates, pick hotels, then generate. You can send it directly via email or download as PDF.",
            "invoices": "Create an invoice from Invoices > Create Invoice, or convert an existing quote to invoice with one click. Track payments and send reminders automatically.",
            "crm": "Manage clients in CRM > All Clients. Add new clients, track their pipeline status, and see their complete history of quotes and bookings.",
            "pipeline": "The Pipeline shows your sales stages: Quoted > Negotiating > Booked > Paid > Travelled. Drag and drop clients between stages to update their status.",
            "clients": "Add clients from CRM > Add Client. Fill in their contact info and how they found you. All their quotes, invoices, and interactions are tracked automatically.",
            "settings": "Customize your platform in Settings: Profile, Company info, Branding (logo, colors), Notifications, and Integrations.",
            "pricing": "Manage rates in Pricing Guide > Rates. Set prices by date range, import from spreadsheets, and rates auto-populate in quotes.",
            "general": "I can help with quotes, invoices, CRM, pipeline, clients, settings, or pricing. What would you like to know more about?"
        }

        return help_content.get(topic, help_content["general"])

    def _execute_route_to_human(self, args: Dict) -> str:
        """Route to human support"""
        reason = args.get("reason", "User requested human support")
        priority = args.get("priority", "medium")

        # In production, this would create a support ticket
        logger.info(f"Routing to human: {reason} (priority: {priority})")

        return f"I'm connecting you with our support team. A human agent will be with you shortly. Reference: {datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Fallback when OpenAI is unavailable"""
        return {
            "response": "Hey! I'm Zara from Zorah Travel. I'm having a small technical hiccup right now, but I can still help! Try asking about:\n\n- Hotels and destinations (e.g., 'Tell me about Mauritius hotels')\n- Creating quotes\n- Using the platform\n\nOr if you need immediate help, our support team is available via the Help menu.",
            "tool_used": None,
            "tool_result": None,
            "sources": [],
            "method": "fallback"
        }

    def reset_conversation(self):
        """Clear conversation history for a new session"""
        self.conversation_history = []
        self.tool_calls = []
        logger.info("Conversation history cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "conversation_length": len(self.conversation_history),
            "tool_calls_count": len(self.tool_calls),
            "recent_tools": [t["tool"] for t in self.tool_calls[-5:]] if self.tool_calls else [],
            "openai_available": self.client is not None
        }


# Singleton instance
_agent_instance = None


def get_helpdesk_agent(config: Optional[ClientConfig] = None) -> HelpdeskAgent:
    """Get singleton helpdesk agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HelpdeskAgent(config)
    return _agent_instance


def reset_helpdesk_agent():
    """Reset the singleton agent instance"""
    global _agent_instance
    if _agent_instance:
        _agent_instance.reset_conversation()
    _agent_instance = None


if __name__ == "__main__":
    # Test the agent
    print("Testing Helpdesk Agent")
    print("=" * 60)

    agent = HelpdeskAgent()

    test_messages = [
        "Hi, what luxury hotels do you have in Mauritius?",
        "How do I create a quote?",
        "I want to book a trip to Zanzibar for 2 adults next month",
    ]

    for msg in test_messages:
        print(f"\nUser: {msg}")
        result = agent.chat(msg)
        print(f"Zara: {result['response'][:300]}...")
        if result['tool_used']:
            print(f"  [Tool: {result['tool_used']}]")
        print()
