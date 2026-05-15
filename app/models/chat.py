"""Chat/Conversational AI API models (Pydantic schemas)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Message role types."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageBase(BaseModel):
    """Base chat message model."""

    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class ChatMessageCreate(ChatMessageBase):
    """Chat message creation model."""

    conversation_id: int | None = Field(None, description="Conversation ID")
    context_window: list[int] | None = Field(None, description="List of message IDs in context")


class ChatMessageResponse(ChatMessageBase):
    """Chat message response model."""

    id: int = Field(..., description="Message ID")
    conversation_id: int = Field(..., description="Conversation ID")
    timestamp: datetime = Field(..., description="Message timestamp")
    extra_data: dict | None = Field(None, description="Additional extra data")

    model_config = ConfigDict(
        from_attributes=True,
    )


class ConversationBase(BaseModel):
    """Base conversation model."""

    title: str | None = Field(None, description="Conversation title")


class ConversationCreate(ConversationBase):
    """Conversation creation model."""

    initial_message: str | None = Field(None, description="Initial message content")


class ConversationResponse(ConversationBase):
    """Conversation response model."""

    id: int = Field(..., description="Conversation ID")
    user_id: int = Field(..., description="User ID")
    last_message_at: datetime | None = Field(None, description="Last message timestamp")
    message_count: int = Field(..., description="Number of messages")
    created_at: datetime = Field(..., description="Conversation creation timestamp")
    updated_at: datetime = Field(..., description="Conversation update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
    )


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., description="User message")
    conversation_id: int | None = Field(None, description="Conversation ID")
    context_type: str | None = Field("recent", description="Context type: recent, full, summary")
    max_context_messages: int = Field(10, description="Maximum context messages to include")
    include_patterns: bool = Field(True, description="Include pattern analysis in context")
    include_glucose_data: bool = Field(False, description="Include glucose data in context")
    stream: bool = Field(False, description="Stream response")


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str = Field(..., description="Assistant response")
    conversation_id: int = Field(..., description="Conversation ID")
    message_id: int = Field(..., description="Message ID")
    timestamp: datetime = Field(..., description="Response timestamp")
    context_used: dict | None = Field(None, description="Context information used")
    sources: list[str] | None = Field(None, description="Data sources referenced")
    streaming: bool = Field(False, description="Is response streaming")


class StreamingChunk(BaseModel):
    """Streaming response chunk."""

    chunk: str = Field(..., description="Text chunk")
    conversation_id: int = Field(..., description="Conversation ID")
    message_id: int = Field(..., description="Message ID")
    is_complete: bool = Field(False, description="Is this the final chunk")


class SafetyCheck(BaseModel):
    """Safety check result."""

    is_safe: bool = Field(..., description="Is the content safe")
    safety_level: str = Field(..., description="Safety level: safe, warning, unsafe")
    reasons: list[str] | None = Field(None, description="Reasons for safety rating")
    requires_moderation: bool = Field(..., description="Requires human moderation")


class SafetyCheckRequest(BaseModel):
    """Safety check request."""

    content: str = Field(..., description="Content to check")
    content_type: str = Field("user_message", description="Type of content: user_message, assistant_response, system_prompt")
    strict_mode: bool = Field(True, description="Use strict safety checking")
