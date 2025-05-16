# market_research/dialog.py
import re
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage
from crewai import Task, Crew

from market_research.config import AppConfig, ResearchParameters
from market_research.agents import ResearchAgents

logger = logging.getLogger(__name__)

class DialogIntent:
    """Represents a recognized user intent"""
    
    def __init__(self, intent_type: str, parameters: Dict[str, Any] = None):
        self.type = intent_type
        self.parameters = parameters or {}
        self.confidence = 1.0  # Default confidence
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DialogIntent':
        """Create from dictionary"""
        intent = cls(data["type"], data["parameters"])
        intent.confidence = data.get("confidence", 1.0)
        intent.timestamp = data.get("timestamp", datetime.now().isoformat())
        return intent

class DialogContext:
    """Maintains conversation context and history"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.history: List[Dict[str, Any]] = []
        self.current_topic: Optional[str] = None
        self.current_research_id: Optional[str] = None
        self.user_preferences: Dict[str, Any] = {}
        self.last_intent: Optional[DialogIntent] = None
        self.conversation_state: str = "greeting"  # greeting, researching, discussing, etc.
        self.metadata: Dict[str, Any] = {
            "session_start": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a message to the conversation history"""
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.history.append(message)
        self.metadata["last_activity"] = datetime.now().isoformat()
        return message
    
    def get_last_n_messages(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get the last n messages from history"""
        return self.history[-n:] if len(self.history) > 0 else []
    
    def get_formatted_history(self, n: int = 5) -> str:
        """Get formatted conversation history for context"""
        messages = self.get_last_n_messages(n)
        formatted = []
        
        for msg in messages:
            role_prefix = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role_prefix}: {msg['content']}")
            
        return "\n\n".join(formatted)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            "session_id": self.session_id,
            "history": self.history,
            "current_topic": self.current_topic,
            "current_research_id": self.current_research_id,
            "user_preferences": self.user_preferences,
            "last_intent": self.last_intent.to_dict() if self.last_intent else None,
            "conversation_state": self.conversation_state,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DialogContext':
        """Create from dictionary"""
        context = cls(data.get("session_id"))
        context.history = data.get("history", [])
        context.current_topic = data.get("current_topic")
        context.current_research_id = data.get("current_research_id")
        context.user_preferences = data.get("user_preferences", {})
        
        if data.get("last_intent"):
            context.last_intent = DialogIntent.from_dict(data["last_intent"])
            
        context.conversation_state = data.get("conversation_state", "greeting")
        context.metadata = data.get("metadata", {
            "session_start": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        })
        
        return context

class DialogManager:
    """Handles conversation flow and intent recognition"""
    
    # Intent types
    INTENT_GREETING = "greeting"
    INTENT_RESEARCH = "research_request"
    INTENT_FOLLOWUP = "followup_question"
    INTENT_CLARIFICATION = "clarification_request"
    INTENT_COMPARISON = "comparison_request"
    INTENT_COMMAND = "system_command"
    INTENT_FEEDBACK = "user_feedback"
    INTENT_SMALLTALK = "small_talk"
    INTENT_UNKNOWN = "unknown"
    
    def __init__(self, config: AppConfig, research_agents: ResearchAgents = None):
        self.config = config
        self.research_agents = research_agents or ResearchAgents(config)
        
    def create_context(self, session_id: str = None) -> DialogContext:
        """Create a new dialog context"""
        return DialogContext(session_id)
    
    def classify_intent(self, message: str, context: DialogContext) -> DialogIntent:
        """Classify the intent of a user message"""
        # Simple rule-based classification first
        message_lower = message.lower().strip()
        
        # Check for system commands
        if re.search(r'\b(reset|start over|clear|new conversation)\b', message_lower):
            return DialogIntent(self.INTENT_COMMAND, {"command": "reset"})
        
        if re.search(r'\b(help|how does this work|what can you do)\b', message_lower):
            return DialogIntent(self.INTENT_COMMAND, {"command": "help"})
        
        # Check for greetings
        if len(message_lower.split()) <= 3 and re.search(r'\b(hi|hello|hey|greetings|howdy)\b', message_lower):
            return DialogIntent(self.INTENT_GREETING)
        
        # Check for research requests (using keywords that suggest research)
        research_keywords = ['research', 'find', 'look up', 'search', 'investigate', 'analyze', 'study', 
                             'get info', 'tell me about', 'what is', 'who is', 'market', 'industry', 
                             'company', 'trends', 'statistics', 'data on', 'report on']
        
        if any(keyword in message_lower for keyword in research_keywords):
            # Extract the research topic
            topic = message
            for keyword in research_keywords:
                if keyword in message_lower:
                    # Remove the keyword and get the rest as the topic
                    pattern = rf'\b{re.escape(keyword)}\b\s*'
                    topic = re.sub(pattern, '', message, flags=re.IGNORECASE)
                    break
                    
            return DialogIntent(self.INTENT_RESEARCH, {
                "topic": topic.strip(),
                "original_query": message
            })
        
        # Check for follow-up questions if we have a current topic
        if context.current_topic:
            followup_keywords = ['more about', 'tell me more', 'expand on', 'elaborate', 'details', 
                                'additional info', 'what about', 'how about', 'why', 'how', 'when']
            
            if any(keyword in message_lower for keyword in followup_keywords) or message_lower.endswith('?'):
                return DialogIntent(self.INTENT_FOLLOWUP, {
                    "topic": context.current_topic,
                    "question": message,
                    "related_to": context.current_research_id
                })
        
        # Check for comparison requests
        if 'compare' in message_lower or 'vs' in message_lower or 'versus' in message_lower or 'differences between' in message_lower:
            return DialogIntent(self.INTENT_COMPARISON, {"comparison_query": message})
        
        # Check for clarification requests
        if re.search(r'\b(what do you mean|clarify|explain|confused|don\'t understand)\b', message_lower):
            return DialogIntent(self.INTENT_CLARIFICATION, {"request": message})
        
        # Check for feedback
        if re.search(r'\b(good job|well done|thanks|thank you|helpful|not helpful|useless|wrong)\b', message_lower):
            sentiment = "positive" if any(word in message_lower for word in ['good', 'well', 'thanks', 'thank', 'helpful']) else "negative"
            return DialogIntent(self.INTENT_FEEDBACK, {"sentiment": sentiment, "feedback": message})
        
        # If nothing else matched and the message is short, treat as small talk
        if len(message_lower.split()) <= 5:
            return DialogIntent(self.INTENT_SMALLTALK, {"message": message})
        
        # If we reach here and have a current topic, assume it's a follow-up
        if context.current_topic:
            return DialogIntent(self.INTENT_FOLLOWUP, {
                "topic": context.current_topic,
                "question": message,
                "related_to": context.current_research_id
            })
        
        # For longer messages without a clear intent, attempt more sophisticated classification
        if len(context.history) > 0:
            return self._classify_with_llm(message, context)
        
        # Default to unknown intent
        return DialogIntent(self.INTENT_UNKNOWN, {"message": message})
    
    def _classify_with_llm(self, message: str, context: DialogContext) -> DialogIntent:
        """Use LLM to classify more complex intents"""
        try:
            # Get dialog agent
            dialog_agent = self.research_agents.get_dialog_agent()
            
            # Create context for classification
            recent_history = context.get_formatted_history(3)
            current_topic = context.current_topic or "None"
            
            # Create the classification task
            classification_task = Task(
                description=f"""
                Classify the user's intent based on this message: "{message}"
                
                Recent conversation history:
                {recent_history}
                
                Current topic: {current_topic}
                
                Classify the intent into one of these categories:
                - greeting: General greetings or introduction
                - research_request: Asking for research on a specific topic
                - followup_question: Asking for more details about the current topic
                - clarification_request: Asking for clarification about something you said
                - comparison_request: Asking to compare multiple items or concepts
                - system_command: Request to perform a system action (like reset)
                - user_feedback: Providing feedback about your responses
                - small_talk: General conversation not requiring specific information
                - unknown: Intent cannot be determined
                
                For research requests, extract the main topic.
                For followup questions, identify what specifically they want to know more about.
                For comparison requests, identify what items are being compared.
                
                Return your analysis as a JSON object with:
                - "intent_type": The classified intent type
                - "parameters": Any extracted parameters relevant to the intent
                - "confidence": Your confidence in this classification (0.0-1.0)
                
                ONLY return the JSON object, nothing else.
                """,
                expected_output="JSON object with intent classification",
                agent=dialog_agent
            )
            
            # Create a small crew for this task
            crew = Crew(
                agents=[dialog_agent],
                tasks=[classification_task],
                verbose=False
            )
            
            # Run the classification
            result = crew.kickoff()
            
            # Parse the result (extract JSON if needed)
            try:
                # Try to extract JSON from the result
                json_match = re.search(r'(\{.*\})', result.raw, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    intent_data = json.loads(json_str)
                else:
                    intent_data = json.loads(result.raw)
                
                # Create intent from the classification result
                intent = DialogIntent(
                    intent_data.get("intent_type", self.INTENT_UNKNOWN),
                    intent_data.get("parameters", {})
                )
                intent.confidence = intent_data.get("confidence", 0.7)
                
                return intent
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse intent classification result: {result.raw}")
                # Fall back to simple classification
                if "research" in result.raw.lower():
                    return DialogIntent(self.INTENT_RESEARCH, {"topic": message})
                elif "followup" in result.raw.lower():
                    return DialogIntent(self.INTENT_FOLLOWUP, {"question": message})
                else:
                    return DialogIntent(self.INTENT_UNKNOWN, {"message": message})
                    
        except Exception as e:
            logger.error(f"Error in LLM intent classification: {str(e)}")
            # Fall back to simple unknown intent
            return DialogIntent(self.INTENT_UNKNOWN, {"message": message})
    
    def generate_response(self, intent: DialogIntent, context: DialogContext) -> str:
        """Generate a response based on the recognized intent"""
        # Placeholder - this would be replaced with actual response generation
        # based on the intent and context - see process_message for full implementation
        return f"You asked about: {intent.parameters.get('topic', 'unknown topic')}"
    
    def process_message(self, message: str, context: DialogContext) -> Tuple[str, DialogIntent]:
        """
        Process a user message and update the dialog context
        
        Args:
            message: The user message
            context: The current dialog context
            
        Returns:
            Tuple of (response, intent)
        """
        # Add user message to context
        context.add_message("user", message)
        
        # Classify the intent
        intent = self.classify_intent(message, context)
        context.last_intent = intent
        
        # Update conversation state based on intent
        if intent.type == self.INTENT_GREETING:
            context.conversation_state = "greeting"
        elif intent.type == self.INTENT_RESEARCH:
            context.conversation_state = "researching"
            context.current_topic = intent.parameters.get("topic")
        elif intent.type == self.INTENT_FOLLOWUP:
            context.conversation_state = "discussing"
        
        # Process different intents
        response = ""
        
        if intent.type == self.INTENT_COMMAND:
            command = intent.parameters.get("command")
            if command == "reset":
                # Reset context but keep session ID
                session_id = context.session_id
                context.__init__(session_id)
                response = "I've reset our conversation. How can I help you today?"
            elif command == "help":
                response = self._generate_help_message()
        
        elif intent.type == self.INTENT_GREETING:
            response = self._generate_greeting(context)
        
        elif intent.type in [self.INTENT_RESEARCH, self.INTENT_COMPARISON]:
            # These require using the dialog agent for a more sophisticated response
            response = self._generate_research_response(intent, context)
        
        elif intent.type == self.INTENT_FOLLOWUP:
            response = self._generate_followup_response(intent, context)
        
        elif intent.type == self.INTENT_CLARIFICATION:
            response = self._generate_clarification(intent, context)
        
        elif intent.type == self.INTENT_FEEDBACK:
            response = self._acknowledge_feedback(intent)
        
        elif intent.type == self.INTENT_SMALLTALK:
            response = self._handle_small_talk(intent, context)
        
        else:  # INTENT_UNKNOWN or any other
            response = self._handle_unknown_intent(context)
        
        # Add assistant response to context
        context.add_message("assistant", response)
        
        return response, intent
    
    def _generate_help_message(self) -> str:
        """Generate a help message explaining capabilities"""
        return """
I'm your AI Market Research Assistant, designed to help you with comprehensive market research. Here's what I can do:

• **Research Topics**: Ask me to research any market, industry, technology, or company
• **Answer Follow-ups**: Ask clarifying questions about any research I provide
• **Compare Items**: Request comparisons between companies, products, or markets
• **Voice Interaction**: Toggle voice mode to speak with me directly

To get started, try asking something like:
- "Research the electric vehicle market in Europe"
- "Tell me about emerging fintech trends"
- "Analyze the competitive landscape for cloud storage providers"
- "What's the market size for plant-based meat alternatives?"

You can reset our conversation anytime by saying "reset" or "start over".
        """
    
    def _generate_greeting(self, context: DialogContext) -> str:
        """Generate a greeting response"""
        if len(context.history) <= 2:  # First interaction
            return """
Hello! I'm your AI Market Research Assistant. I can help you with in-depth research on companies, markets, industries, and trends.

What topic would you like me to research today?
            """
        else:
            return "Hello again! How can I help with your market research today?"
    
    def _generate_research_response(self, intent: DialogIntent, context: DialogContext) -> str:
        """Generate a response for research intent using the dialog agent"""
        try:
            # Get dialog agent
            dialog_agent = self.research_agents.get_dialog_agent()
            
            # Create the response generation task
            topic = intent.parameters.get("topic", "")
            original_query = intent.parameters.get("original_query", topic)
            comparison_query = intent.parameters.get("comparison_query", "")
            
            query_text = comparison_query if intent.type == self.INTENT_COMPARISON else original_query
            
            task = Task(
                description=f"""
                Generate an initial response to this research query: "{query_text}"
                
                This is the initial response before conducting in-depth research. Your response should:
                
                1. Acknowledge the user's request with enthusiasm and professionalism
                2. Briefly explain what kind of information you plan to gather
                3. Mention 3-4 specific aspects of the topic you'll focus on researching
                4. Ask if there are any specific aspects of this topic they're most interested in
                
                Make your response conversational, helpful, and engaging. Don't actually conduct 
                the research yet - just create a thoughtful initial response.
                
                The key topic is: {topic if topic else query_text}
                
                NOTE: This is just the initial response before research starts.
                """,
                expected_output="An engaging initial response to the research request",
                agent=dialog_agent
            )
            
            # Create a small crew for this task
            crew = Crew(
                agents=[dialog_agent],
                tasks=[task],
                verbose=False
            )
            
            # Generate the response
            result = crew.kickoff()
            
            # Update context with the research topic
            context.current_topic = topic if topic else query_text
            
            return result.raw
            
        except Exception as e:
            logger.error(f"Error generating research response: {str(e)}")
            return f"I'd be happy to research {topic if topic else 'that topic'} for you. Let me gather some information and I'll provide you with insights shortly."
    
    def _generate_followup_response(self, intent: DialogIntent, context: DialogContext) -> str:
        """Generate a response for follow-up questions"""
        try:
            # Get dialog agent
            dialog_agent = self.research_agents.get_dialog_agent()
            
            question = intent.parameters.get("question", "")
            topic = intent.parameters.get("topic", context.current_topic)
            
            # Recent conversation history
            history = context.get_formatted_history(3)
            
            task = Task(
                description=f"""
                Generate a response to this follow-up question: "{question}"
                
                The user previously asked about: {topic}
                
                Recent conversation history:
                {history}
                
                Your response should:
                1. Directly address their specific question
                2. Acknowledge how it relates to the previous research topic
                3. Be conversational and helpful
                4. If you don't have enough information yet, explain that you'll need to research more
                
                If the question seems to be asking for information you don't have yet, 
                offer to research it in more detail.
                """,
                expected_output="A response to the follow-up question",
                agent=dialog_agent
            )
            
            # Create a small crew for this task
            crew = Crew(
                agents=[dialog_agent],
                tasks=[task],
                verbose=False
            )
            
            # Generate the response
            result = crew.kickoff()
            return result.raw
            
        except Exception as e:
            logger.error(f"Error generating followup response: {str(e)}")
            return "That's a great follow-up question. Let me explore that aspect in more detail for you."
    
    def _generate_clarification(self, intent: DialogIntent, context: DialogContext) -> str:
        """Generate a clarification response"""
        # Get the last assistant message to clarify
        last_assistant_messages = [msg for msg in reversed(context.history) 
                                  if msg["role"] == "assistant"]
        
        if last_assistant_messages:
            last_message = last_assistant_messages[0]["content"]
            return f"I apologize if I wasn't clear. Let me clarify: {last_message[:100]}... Would you like me to explain any specific part in more detail?"
        else:
            return "I apologize for any confusion. Could you please specify what you'd like me to clarify?"
    
    def _acknowledge_feedback(self, intent: DialogIntent) -> str:
        """Acknowledge user feedback"""
        sentiment = intent.parameters.get("sentiment", "neutral")
        
        if sentiment == "positive":
            return "Thank you for the positive feedback! I'm glad I could help. Is there anything else you'd like to know?"
        else:
            return "I appreciate your feedback. I'll do my best to improve my responses. What specific information would be more helpful for you?"
    
    def _handle_small_talk(self, intent: DialogIntent, context: DialogContext) -> str:
        """Handle small talk interactions"""
        message = intent.parameters.get("message", "").lower()
        
        # Simple rule-based responses
        if any(word in message for word in ["how", "are", "you"]):
            return "I'm functioning well, thank you for asking! I'm ready to help with your market research needs. What would you like to know about?"
        
        if any(word in message for word in ["thanks", "thank"]):
            return "You're welcome! I'm happy to assist with your research needs. Let me know if you have any other questions."
        
        if any(word in message for word in ["who", "are", "you"]):
            return "I'm an AI Market Research Assistant designed to help you with in-depth research on markets, industries, companies, and trends. How can I assist you today?"
        
        # Default small talk response
        return "I'm here to help with market research. Would you like me to research a specific topic or company for you?"
    
    def _handle_unknown_intent(self, context: DialogContext) -> str:
        """Handle unknown intent"""
        if context.current_topic:
            return f"I see we were discussing {context.current_topic}. Would you like me to research a specific aspect of this topic, or would you prefer to explore something else?"
        else:
            return "I'm not quite sure what you're asking. I can help with market research on companies, industries, or trends. Could you provide more details about what you'd like to know?"
