from src.types import LLMType
from src.llm.base import BaseLLMExtractor
from src.config import Config


def get_extractor(llm_type: LLMType, config: Config) -> BaseLLMExtractor:
    if llm_type == LLMType.OPENAI:
        from src.llm.openai_extractor import OpenAIExtractor
        return OpenAIExtractor(api_key=config.openai_api_key)
    elif llm_type == LLMType.CLAUDE:
        from src.llm.claude_extractor import ClaudeExtractor
        return ClaudeExtractor(api_key=config.anthropic_api_key)
    elif llm_type == LLMType.HAIKU:
        from src.llm.haiku_extractor import HaikuExtractor
        return HaikuExtractor(api_key=config.anthropic_api_key)
    else:
        raise ValueError(f"Unknown LLM type: {llm_type}")
