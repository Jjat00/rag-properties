"""LangGraph agent factory: builds a ReAct agent for property search."""

import logging

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agent.prompt import SYSTEM_PROMPT
from agent.state import AgentState
from config import EmbeddingModel, Settings
from embeddings.registry import EmbeddingRegistry
from search.query_parser import QueryParser
from vectorstore.qdrant_manager import QdrantManager

from .tools import create_search_tool

logger = logging.getLogger(__name__)


def create_agent(
    settings: Settings,
    query_parser: QueryParser,
    embedding_registry: EmbeddingRegistry,
    qdrant_manager: QdrantManager,
    model: EmbeddingModel | None = None,
    top_k: int = 10,
):
    """Create and compile the conversational agent graph.

    Returns a compiled StateGraph with MemorySaver checkpointer.
    """
    embedding_model = model or settings.default_embedding_model

    search_tool = create_search_tool(
        query_parser=query_parser,
        embedding_registry=embedding_registry,
        qdrant_manager=qdrant_manager,
        model=embedding_model,
        top_k=top_k,
    )
    tools = [search_tool]

    llm = ChatGoogleGenerativeAI(
        model=settings.agent_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.3,
    )
    llm_with_tools = llm.bind_tools(tools)

    system_message = SystemMessage(content=SYSTEM_PROMPT)

    async def agent_node(state: AgentState):
        """Call the LLM with tools bound."""
        messages = [system_message] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        """Route: if last message has tool_calls → tools, else → end."""
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
