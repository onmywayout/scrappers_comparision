from openai import AsyncOpenAI
from src.llm.base import BaseLLMExtractor
from src.types import LLMType
from src.models import AugmentedCompany


class OpenAIExtractor(BaseLLMExtractor):
    llm_type = LLMType.OPENAI

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)

    async def _call_llm(self, system_msg: str, user_msg: str) -> str:
        # Use Pydantic structured output for guaranteed schema conformance
        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format=AugmentedCompany,
            temperature=0,
            max_tokens=8000,
        )
        # The parsed response is already validated — return as JSON string
        parsed = response.choices[0].message.parsed
        if parsed is not None:
            return parsed.model_dump_json()
        # Fallback to raw content if parsing failed
        return response.choices[0].message.content or "{}"
