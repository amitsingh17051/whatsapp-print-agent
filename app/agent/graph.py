"""LangGraph graph definition for WhatsApp Print Agent."""

from langgraph.graph import END, StateGraph

from app.agent.nodes import detect_intent, extract_options, process_response
from app.agent.state import AgentState


def build_agent_graph():
    """Construct and compile the conversational LangGraph state machine."""
    workflow = StateGraph(AgentState)

    # Add processing nodes
    workflow.add_node("detect_intent", detect_intent)
    workflow.add_node("extract_options", extract_options)
    workflow.add_node("process_response", process_response)

    # Set linear workflow connections
    workflow.set_entry_point("detect_intent")
    workflow.add_edge("detect_intent", "extract_options")
    workflow.add_edge("extract_options", "process_response")
    workflow.add_edge("process_response", END)

    return workflow.compile()


agent_graph = build_agent_graph()
