import os

import pypdf
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[4] / ".env")


class PDFDocumentLoaderRAGService:
    def __init__(self, file_path: str, collection_name: str = "example_collection"):
        self.file_path = file_path
        print(f"Using embeddings model: {os.getenv('EMBEDDING_MODEL')}")
        self.embeddings = OllamaEmbeddings(model=os.getenv("EMBEDDING_MODEL"))
        self.collection_name = collection_name
        self._vector_store = self._init_vector_store()

    def _init_vector_store(self) -> Chroma:
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=os.getenv(
                "CHROMA_PERSIST_DIRECTORY"
            ),  # Where to save data locally, remove if not necessary
        )

    def load_pdf_pages(self) -> list[Document]:
        """Load and return the pages of a PDF document as a list of Document."""
        documents = []
        with open(self.file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    documents.append(Document(page_content=text))
        return documents

    def split_text_into_chunks(self, text: str, chunk_size: int = 1000) -> list[str]:
        """Divide o texto em chunks de tamanho especificado."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=0
        )
        return text_splitter.split_text(text)

    def index_chunks_into_vector_store(self, chunks: list[str]):
        """Indexa os chunks em uma loja de vetores (exemplo fictício)."""
        return self._vector_store.add_texts(chunks)

    def load_and_process_document(self):
        """Carrega, divide e indexa o documento PDF."""
        documents = self.load_pdf_pages()
        for doc in documents:
            chunks = self.split_text_into_chunks(doc.page_content)
            self.index_chunks_into_vector_store(chunks)
        result = self._vector_store.similarity_search(
            "Qual o sentido da vida de Rafael?"
        )
        print(f"Resultados da busca: {result[0]}")


if __name__ == "__main__":
    # Exemplo de uso
    loader = PDFDocumentLoaderRAGService(
        file_path="C:\\Users\\rafae\\Documents\\Projetos\\Ticket-Assessor\\ticket-triage\\app\\vector_store\\RAFAEL.pdf",
        collection_name="example_collection",
    )
    loader.load_and_process_document()
