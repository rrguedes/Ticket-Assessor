from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.services.agent.rag.requirements_retriever import RequirementsRetriever


def test_search_combines_collections_and_returns_best_results():
    cbl_store = MagicMock()
    cbl_store.similarity_search_with_score.return_value = [
        (Document(page_content="CBL relevante"), 0.40),
    ]
    twc_store = MagicMock()
    twc_store.similarity_search_with_score.return_value = [
        (Document(page_content="TWC menos relevante"), 0.80),
        (Document(page_content="TWC mais relevante"), 0.20),
    ]

    with (
        patch(
            "app.services.agent.rag.requirements_retriever.OllamaEmbeddings"
        ),
        patch(
            "app.services.agent.rag.requirements_retriever.Chroma",
            side_effect=[cbl_store, twc_store],
        ),
    ):
        retriever = RequirementsRetriever()
        results = retriever.search("ticket sobre mudança de modo", k=2)

    assert [document.page_content for document in results] == [
        "TWC mais relevante",
        "CBL relevante",
    ]
    assert results[0].metadata["collection"] == "Modos_Operacao_TWC"
    assert results[1].metadata["collection"] == "Modos_Operacao_CBL"
    cbl_store.similarity_search_with_score.assert_called_once_with(
        "ticket sobre mudança de modo", k=2
    )
    twc_store.similarity_search_with_score.assert_called_once_with(
        "ticket sobre mudança de modo", k=2
    )


def test_search_does_not_query_for_empty_input_or_invalid_k():
    with (
        patch(
            "app.services.agent.rag.requirements_retriever.OllamaEmbeddings"
        ),
        patch("app.services.agent.rag.requirements_retriever.Chroma") as chroma,
    ):
        retriever = RequirementsRetriever()

        assert retriever.search("   ") == []
        assert retriever.search("ticket", k=0) == []

    assert chroma.call_count == 2
