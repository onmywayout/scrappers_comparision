import json
from typing import List, Dict, Any

from openai import AsyncOpenAI
import anthropic
from pydantic import BaseModel, Field


class FeatureSimilarity(BaseModel):
    feature: str = Field(description="Feature name")
    similarity: float = Field(description="Similarity score between 0.0 and 1.0")
    rationale: str = Field(description="Short rationale for the similarity score")


class LLMComparisonOutput(BaseModel):
    results: List[FeatureSimilarity]


class LLMValueComparator:
    def __init__(
        self,
        openai_api_key: str,
        anthropic_api_key: str,
        openai_model: str = "gpt-4o",
        anthropic_model: str = "claude-sonnet-4-20250514",
    ):
        self.openai = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None
        self.anthropic = anthropic.AsyncAnthropic(api_key=anthropic_api_key) if anthropic_api_key else None
        self.openai_model = openai_model
        self.anthropic_model = anthropic_model

    def _build_prompt(self, extracted: Dict[str, Any], ground_truth: Dict[str, Any]) -> str:
        return (
            "Compare extracted feature values to ground truth values. "
            "For each feature, output a similarity score between 0.0 and 1.0 and a short rationale. "
            "Use partial credit for overlapping items and fuzzy matches. "
            "If both are empty/unknown, similarity should be 1.0. "
            "If ground truth is present but extracted is empty/unknown, similarity should be 0.0.\n\n"
            f"EXTRACTED:\n{json.dumps(extracted, ensure_ascii=True)}\n\n"
            f"GROUND_TRUTH:\n{json.dumps(ground_truth, ensure_ascii=True)}\n"
        )

    async def compare_openai(self, extracted: Dict[str, Any], ground_truth: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.openai:
            return []
        system_msg = "You are a precise evaluator. Return only valid JSON that matches the schema."
        user_msg = self._build_prompt(extracted, ground_truth)
        response = await self.openai.beta.chat.completions.parse(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format=LLMComparisonOutput,
            temperature=0,
            max_tokens=4000,
        )
        parsed = response.choices[0].message.parsed
        if parsed is not None:
            return [r.model_dump() for r in parsed.results]
        return []

    async def compare_claude(self, extracted: Dict[str, Any], ground_truth: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.anthropic:
            return []
        tool_schema = LLMComparisonOutput.model_json_schema()
        tool_schema.pop("title", None)
        response = await self.anthropic.messages.create(
            model=self.anthropic_model,
            max_tokens=4000,
            system="You are a precise evaluator. Return only valid JSON that matches the schema.",
            tools=[{
                "name": "compare_features",
                "description": "Compare extracted values to ground truth and score similarity.",
                "input_schema": tool_schema,
            }],
            tool_choice={"type": "tool", "name": "compare_features"},
            messages=[{"role": "user", "content": self._build_prompt(extracted, ground_truth)}],
        )
        for block in response.content:
            if block.type == "tool_use":
                data = block.input
                results = data.get("results", [])
                return results
        return []
