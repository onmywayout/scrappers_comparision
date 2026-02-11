import json
import anthropic
from src.llm.base import BaseLLMExtractor
from src.types import LLMType
from src.models import AugmentedCompany


class ClaudeExtractor(BaseLLMExtractor):
    llm_type = LLMType.CLAUDE

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key, model)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def _call_llm(self, system_msg: str, user_msg: str) -> str:
        # Build the tool schema from AugmentedCompany's JSON schema
        tool_schema = AugmentedCompany.model_json_schema()

        # Remove the 'title' key (not needed for Claude tool_use)
        tool_schema.pop("title", None)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            temperature=0,  # Deterministic extraction (no creativity)
            system=system_msg,
            tools=[{
                "name": "extract_company_data",
                "description": "Extract structured company data from website content.",
                "input_schema": tool_schema,
            }],
            tool_choice={"type": "tool", "name": "extract_company_data"},
            messages=[{"role": "user", "content": user_msg}],
        )

        # Extract the tool_use result
        for block in response.content:
            if block.type == "tool_use":
                return json.dumps(block.input)

        # Fallback: try text content
        for block in response.content:
            if block.type == "text":
                return block.text

        return "{}"
