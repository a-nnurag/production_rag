from typing import Optional
from typing_extensions import TypedDict,Annotated
# from langgraph.graph import StateGraph,START,END
from langgraph.graph import StateGraph
from langgraph.graph.state import START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage,BaseMessage
from langsmith import traceable

from app.config import get_settings

import os

# print("GROQ_API_KEY =", os.getenv("GROQ_API_KEY"))

from langsmith import traceable


# =====AGENT STATE====================================================================
class AgentState(TypedDict):
    """State of the agent, including conversation history
     and any relevant context."""
    messages:Annotated[list[BaseMessage],add_messages]  # Conversation history
    error:Optional[str]  # Any error messages
    retry_count:int  # Number of retries attempted
    model_used: str  # The model used for the last response

    
class ProductionAgent:
    """
    Priduction langgraph agent with:
    -Retry on failure (model fallback)
    -Graceful error handling
    -Langsmith tracing
    """

    def __init__(self):
        settings = get_settings()

        self.primary_llm = ChatGroq(model=settings.primary_model,
                                      temperature=0,
                                      timeout=30,
                                      max_retries=0 ,
                                      groq_api_key=settings.groq_api_key,
                                ).with_config({"run_name": "primary_llm"}) 
        self.fallback_llm = ChatGroq(model=settings.secondary_model,
                                      temperature=0,
                                      timeout=30,
                                      max_retries=0 ,
                                      groq_api_key=settings.groq_api_key,
                                ).with_config({"run_name": "secondary_llm"}) 
        self.max_retries = settings.max_retries
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """
        Build the langgraph state machine 
        """

        def process_message(state:AgentState) -> dict:
            """Process the latest message and generate a response."""
            try:
                response = self.primary_llm.invoke(state['messages'])
                return {
                    'messages': [response],
                    'model_used': "primary",
                    'error': None
                }
            except Exception as e:
                return {
                    'retry_count': state['retry_count'] + 1,
                    'model_used': "primary",
                    'error': str(e)
                }
            
        def try_fallback(state:AgentState) -> dict:
            """
            Fallback to secondary model
            """
            try:
                response = self.fallback_llm.invoke(state['messages'])
                return {
                    'messages': [response],
                    'model_used': "fallback",
                    'error': None
                }
            except Exception as e:
                return {
                    'model_used': "fallback",
                    'error': str(e),
                }
        
        def handle_error(state:AgentState) -> dict:
            """Handle errors gracefully."""
            return {
                "messages":[
                    AIMessage(content=(
                        "I'm sorry,I'm having trouble processing your request" \
                        "right now.Please try again in a moment"
                    ))
                ],
                "model_used":"error_handler",
                "error": state.get("error")
            }
    
        def route_after_process(state:AgentState) ->str:
            """Decide what to do after primary model attempt"""
            if state.get("error") is None:
                return "done"
            elif state["retry_count"]<=self.max_retries:
                return "fallback"
            else :
                return "error"
        
        def route_after_fallback(state:AgentState)->str:
            """Decide what to do after fallback attempt"""
            if state.get("error") is None:
                return "done"
            else :
                return "error"
        
        #Build the graph 
        graph = StateGraph(AgentState)

        graph.add_node("process", process_message)
        graph.add_node("fallback_handler",try_fallback)
        graph.add_node("error_handler",handle_error)

        graph.add_edge(START,"process")
        graph.add_conditional_edges(
            "process",
            route_after_process,
            {
                "done":END,
                "fallback":"fallback_handler",
                "error":"error_handler"
            }
        )
        graph.add_conditional_edges(
            "fallback_handler",
            route_after_fallback,
            {"done":END,"error":"error_handler"},
        )
        graph.add_edge("error_handler",END)

        return graph.compile()
    
    @traceable(name="production_agent_invoke",run_type="chain")
    def invoke(self,message:str)->dict:
        """
        Invoke the agent with a user message.
        Returns:{"response":str,"model_used":str,"error":str |None}
        """
        result =self.graph.invoke({
            "messages":[HumanMessage(content=message)],
            "error":None,
            "retry_count":0,
            "model_used":"",
        })

        return {
            "response": result["messages"][-1].content,
            "model_used": result.get("model_used","unknown"),
            "error":result.get("error")
        }