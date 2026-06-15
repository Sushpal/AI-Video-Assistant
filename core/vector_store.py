import os 
from langchain_chroma import Chroma 
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = "vector_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"}
    )


def build_vector_store(transcript: str, collection_name: str) -> Chroma:
    print(f"Building vector store for collection: {collection_name}")

    # FIX 1: Better chunking for meetings
    # Increased overlap to 100 to ensure context isn't lost between speaker turns
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700, 
        chunk_overlap=100
    )
    chunks = splitter.split_text(transcript)

    docs = [
        Document(page_content=chunk, metadata={"chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    embeddings = get_embeddings()

    # FIX 2: Prevent Duplicate/Ghost Data
    # We initialize the store and delete the collection if it already exists 
    # before adding new documents.
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )
    
    try:
        # If collection exists, delete it to ensure a fresh start
        vector_store.delete_collection()
        print(f"Existing collection '{collection_name}' cleared.")
    except Exception:
        # Collection didn't exist, which is fine
        pass

    # Now build the store fresh
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=CHROMA_DIR
    )

    return vector_store


def load_vector_store(collection_name: str) -> Chroma:
    print(f"Loading vector store: {collection_name}")
    embeddings = get_embeddings()
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )
    return vector_store


def get_retriever(vector_store: Chroma, k: int = 4):
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )