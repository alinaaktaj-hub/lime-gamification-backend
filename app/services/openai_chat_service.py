from openai import AsyncOpenAI, OpenAIError

from app.config import OPENAI_API_KEY, OPENAI_MODEL


class OpenAIChatService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    async def generate_response(self, message: str) -> str:
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        try:
            response = await self.client.responses.create(
                model=OPENAI_MODEL,
                input=message,
            )
        except OpenAIError as exc:
            raise RuntimeError("OpenAI request failed") from exc

        text = response.output_text.strip()
        if not text:
            raise RuntimeError("OpenAI request failed")
        return text
