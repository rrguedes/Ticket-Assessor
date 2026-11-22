import os
from pathlib import Path

import pypdf
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv(Path(__file__).resolve().parents[4] / ".env")


class PDFDocumentLoaderRAGService:
    def __init__(self, file_path: str, collection_name: str = "example_collection"):
        self.file_path = file_path
        if os.getenv("DEBUG_MODE") == "true":
            print(f"Using embeddings model: {os.getenv('EMBEDDING_MODEL')}")
        self.embeddings = OllamaEmbeddings(
            base_url=str(os.getenv("LOCAL_MODELS_BASE_URL")),
            model=str(os.getenv("EMBEDDING_MODEL")),
        )
        self.collection_name = collection_name
        self._vector_store = self._init_vector_store()

    def _init_vector_store(self) -> Chroma:
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(os.getenv("CHROMA_PERSIST_DIRECTORY")),
        )

    def load_pdf_pages(self) -> list[Document]:
        """Load and return the pages of a PDF document as a list of Document."""
        documents = []
        with open(self.file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": self.file_path,
                                "page": page.page_number,
                                "collection": self.collection_name,
                            },
                        )
                    )
        return documents

    def split_text_into_chunks(self, text: str, chunk_size: int = 1000) -> list[str]:
        """Divide o texto em chunks de tamanho especificado."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=100
        )
        return text_splitter.split_text(text)

    def index_chunks_into_vector_store(self, chunks: list[str], metadata: dict):
        """Indexa os chunks em uma loja de vetores (exemplo fictício)."""
        for chunk in chunks:
            self._vector_store.add_texts([chunk], [metadata])

    def load_and_process_document(self):
        """Carrega, divide e indexa o documento PDF."""
        documents = self.load_pdf_pages()
        for doc in documents:
            metadata = {
                "source": self.file_path,
                "collection": self.collection_name,
                "page": doc.metadata.get("page"),
            }
            chunks = self.split_text_into_chunks(doc.page_content)
            self.index_chunks_into_vector_store(chunks, metadata)
        if os.getenv("DEBUG_MODE") == "true":
            print(f"Documento processado e indexado na coleção: {self.collection_name}")


def _detect_files(directory: str, extensions: list[str]) -> list[str]:
    """Detecta arquivos em um diretório com extensões específicas."""
    detected_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                detected_files.append(os.path.join(root, file))
    return detected_files


if __name__ == "__main__":
    # Arquivos para indexar
    files = _detect_files(
        directory="/home/rafael/Documentos/Projects/Ticket-Assessor/ticket-triage/app/vector_store/inputs",
        extensions=[".pdf"],
    )
    for file_path in files:
        loader = PDFDocumentLoaderRAGService(
            file_path=file_path,
            collection_name=os.path.splitext(os.path.basename(file_path))[0],
        )
        loader.load_and_process_document()
