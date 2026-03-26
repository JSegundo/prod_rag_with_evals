from anthropic import AsyncAnthropic

from app.config import settings
from app.services.llm.base import LLMMessage, LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        # Extract system message
        system_content = ""
        user_messages = []
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                user_messages.append({"role": msg.role, "content": msg.content})

        response = await self.client.messages.create(
            model=self.model,
            system=system_content,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.content[0].text
