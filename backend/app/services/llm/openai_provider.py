from openai import AsyncOpenAI

from app.config import settings
from app.services.llm.base import LLMMessage, LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        openai_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""
