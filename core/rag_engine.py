import os
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage
from core.vector_store import build_vector_store, load_vector_store, get_retriever


def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.3,
    )


def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])


def _build_chain(retriever):
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert meeting assistant.

Answer the user's question ONLY using the meeting transcript context.

If the answer is not present in the context, say:
"I could not find this information in the meeting transcript."

Context from meeting transcript:
{context}
""",
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{question}"),
    ])

    rag_chain = (
        {
            "context": (
                RunnableLambda(lambda x: x["question"])
                | retriever
                | RunnableLambda(format_docs)
            ),
            "question": RunnableLambda(lambda x: x["question"]),
            "chat_history": RunnableLambda(
                lambda x: x.get("chat_history", [])
            ),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


def build_rag_chain(transcript: str, collection_name: str):
    vector_store = build_vector_store(transcript, collection_name)
    retriever = get_retriever(vector_store, k=5)
    return _build_chain(retriever)


def load_rag_chain(collection_name: str):
    vector_store = load_vector_store(collection_name)
    retriever = get_retriever(vector_store, k=5)
    return _build_chain(retriever)


def ask_question(rag_chain, question: str, history: list = None) -> str:
    """
    history format:
    [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ]
    """

    formatted_history = []

    if history:
        for msg in history[-6:]:
            if msg["role"] == "user":
                formatted_history.append(
                    HumanMessage(content=msg["content"])
                )
            else:
                formatted_history.append(
                    AIMessage(content=msg["content"])
                )

    answer = rag_chain.invoke({
        "question": question,
        "chat_history": formatted_history
    })

    return answer