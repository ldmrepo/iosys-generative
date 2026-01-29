"""
LLM service for RAG response generation using LangChain.
"""
import logging
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain_core.chat_history import InMemoryChatMessageHistory

from ..core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-based response generation using LangChain."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self._llm: Optional[ChatOpenAI] = None
        self._chat_history: Optional[InMemoryChatMessageHistory] = None

    @property
    def is_configured(self) -> bool:
        """Check if OpenAI API is configured."""
        return bool(self._settings.openai_api_key)

    def _get_llm(self) -> ChatOpenAI:
        """Get or create LangChain ChatOpenAI instance."""
        if self._llm is None:
            if not self.is_configured:
                raise ValueError("OpenAI API key not configured")
            self._llm = ChatOpenAI(
                api_key=self._settings.openai_api_key,
                model=self._settings.openai_model,
                temperature=self._settings.openai_temperature,
                max_tokens=self._settings.openai_max_tokens,
            )
        return self._llm

    def _get_chat_history(self) -> InMemoryChatMessageHistory:
        """Get or create chat history."""
        if self._chat_history is None:
            self._chat_history = InMemoryChatMessageHistory()
        return self._chat_history

    def _build_documents(self, search_results: List[dict]) -> List[Document]:
        """Convert search results to LangChain Documents."""
        documents = []
        for result in search_results:
            item_id = result.get("item_id", "N/A")
            score = result.get("score", 0)
            metadata = result.get("metadata", {})

            content = f"""[문항 ID: {item_id}] (유사도: {score:.3f})
유형: {metadata.get("category", "N/A")}
난이도: {metadata.get("difficulty", "N/A")}
내용: {metadata.get("question_text", "내용 없음")}"""

            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "item_id": item_id,
                        "score": score,
                        **metadata,
                    },
                )
            )
        return documents

    def _format_docs(self, docs: List[Document]) -> str:
        """Format documents for context."""
        if not docs:
            return "검색 결과가 없습니다."
        return "\n\n".join(doc.page_content for doc in docs)

    async def generate_response(
        self,
        query: str,
        search_results: List[dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate RAG response using LangChain.

        Args:
            query: User's question
            search_results: List of search results with metadata
            system_prompt: Optional custom system prompt

        Returns:
            Generated response text
        """
        if not self.is_configured:
            return "OpenAI API 키가 설정되지 않았습니다. 환경 변수 OPENAI_API_KEY를 설정해주세요."

        llm = self._get_llm()
        documents = self._build_documents(search_results)

        system = system_prompt or self._settings.rag_system_prompt

        # Create RAG prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", """## 검색된 문항 정보
{context}

## 사용자 질문
{question}

위 검색 결과를 참고하여 질문에 답변해주세요."""),
        ])

        # Create RAG chain
        rag_chain = (
            {
                "context": lambda x: self._format_docs(x["documents"]),
                "question": lambda x: x["question"],
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        try:
            response = await rag_chain.ainvoke({
                "documents": documents,
                "question": query,
            })
            return response

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    async def generate_response_with_memory(
        self,
        query: str,
        search_results: List[dict],
        session_id: str = "default",
    ) -> str:
        """
        Generate RAG response with conversation memory.

        Args:
            query: User's question
            search_results: List of search results with metadata
            session_id: Session identifier for memory isolation

        Returns:
            Generated response text
        """
        if not self.is_configured:
            return "OpenAI API 키가 설정되지 않았습니다."

        llm = self._get_llm()
        chat_history = self._get_chat_history()
        documents = self._build_documents(search_results)

        # Create conversational RAG prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._settings.rag_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", """## 검색된 문항 정보
{context}

## 사용자 질문
{question}

위 검색 결과와 이전 대화 내용을 참고하여 답변해주세요."""),
        ])

        # Create chain with memory
        chain = (
            RunnablePassthrough.assign(
                chat_history=lambda _: chat_history.messages,
            )
            | {
                "context": lambda x: self._format_docs(x["documents"]),
                "question": lambda x: x["question"],
                "chat_history": lambda x: x["chat_history"],
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        try:
            response = await chain.ainvoke({
                "documents": documents,
                "question": query,
            })

            # Save to history
            from langchain_core.messages import HumanMessage, AIMessage
            chat_history.add_message(HumanMessage(content=query))
            chat_history.add_message(AIMessage(content=response))

            return response

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    async def generate_similar_question(
        self,
        reference_items: List[dict],
        instructions: Optional[str] = None,
    ) -> str:
        """
        Generate a similar question based on reference items.

        Args:
            reference_items: Reference items to base the new question on
            instructions: Optional specific instructions

        Returns:
            Generated question text
        """
        if not self.is_configured:
            return "OpenAI API 키가 설정되지 않았습니다."

        llm = self._get_llm()
        documents = self._build_documents(reference_items)

        # Create question generation prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 교육 문항 출제 전문가입니다.
주어진 참고 문항들을 분석하여 유사한 유형과 난이도의 새로운 문항을 생성해주세요.
문항은 명확하고 교육적이어야 합니다."""),
            ("human", """## 참고 문항
{context}

## 요청사항
{instructions}

새 문항을 생성해주세요."""),
        ])

        # Create generation chain
        chain = (
            {
                "context": lambda x: self._format_docs(x["documents"]),
                "instructions": lambda x: x["instructions"],
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        try:
            response = await chain.ainvoke({
                "documents": documents,
                "instructions": instructions or "위 문항들과 유사한 새로운 문항을 1개 생성해주세요.",
            })
            return response

        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            raise

    def clear_memory(self) -> None:
        """Clear conversation memory."""
        if self._chat_history is not None:
            self._chat_history.clear()


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
