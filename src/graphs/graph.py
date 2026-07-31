"""Main graph definition for the terminology simplification workflow."""
from langgraph.graph import StateGraph, END
from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
)
from graphs.nodes.read_excel_node import read_excel_node
from graphs.nodes.simplify_terms_node import simplify_terms_node
from graphs.nodes.generate_html_node import generate_html_node
from graphs.nodes.upload_storage_node import upload_storage_node


def check_has_terms(state: GlobalState) -> str:
    """
    title: Check if terms data exists
    desc: Determine whether the Excel file contained valid terminology data to process
    """
    if state.terms_data and len(state.terms_data) > 0:
        return "Process Terms"
    else:
        return "No Data"


# Create the state graph with input/output schemas
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# Add nodes
builder.add_node("read_excel", read_excel_node)
builder.add_node("simplify_terms", simplify_terms_node, metadata={
    "type": "task",
    "llm_cfg": "config/simplify_terms_llm_cfg.json"
})
builder.add_node("generate_html", generate_html_node)
builder.add_node("upload_storage", upload_storage_node)

# Set entry point
builder.set_entry_point("read_excel")

# Add conditional edges after read_excel
builder.add_conditional_edges(
    source="read_excel",
    path=check_has_terms,
    path_map={
        "Process Terms": "simplify_terms",
        "No Data": END
    }
)

# Add sequential edges
builder.add_edge("simplify_terms", "generate_html")
builder.add_edge("generate_html", "upload_storage")
builder.add_edge("upload_storage", END)

# Compile the graph
main_graph = builder.compile()
