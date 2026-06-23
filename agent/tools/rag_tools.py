from langchain_core.tools import tool

from agent.tools.runtime import add_source_reference, get_request_user_id, run_audited_tool
from rag.rag_service import RagSummarizeService


rag_service = RagSummarizeService()


def rag_summarize_for_user(query: str, user_id: str | None = None) -> str:
    answer, sources = rag_service.rag_summarize_with_sources(query, user_id=user_id)
    for source in sources:
        add_source_reference(source)
    return answer


@tool
def rag_summarize(query: str) -> str:
    """Search shared knowledge and the current user's private knowledge for product support answers."""

    return run_audited_tool(
        tool_name="rag_summarize",
        args={"query": query},
        callback=lambda: rag_summarize_for_user(query, user_id=get_request_user_id()),
    )
