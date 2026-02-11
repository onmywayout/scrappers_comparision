"""
Extraction prompt auto-generated from the AugmentedCompany Pydantic model.
The prompt includes explanation fields BEFORE decision fields to encourage
chain-of-thought reasoning, which improves extraction accuracy.
"""

from src.models import AugmentedCompany


def build_extraction_prompt() -> str:
    """Build the extraction prompt dynamically from AugmentedCompany field descriptions."""
    lines = [
        "You are a precise data extraction system. Analyze the following website content "
        "and extract structured information about this company.",
        "",
        "Return a JSON object conforming to the schema below. For each field that has a "
        "corresponding _explanation field, fill the explanation FIRST (provide multiple "
        "detailed reasons), then give your final answer in the decision field.",
        "",
        "IMPORTANT RULES:",
        "1. Only extract information that is EXPLICITLY stated in the content. Do not guess or infer.",
        "2. For Literal fields, return ONLY one of the allowed values shown.",
        "3. For list fields, return an empty list [] if no information is found.",
        "4. For string fields, return 'unknown' if the information is not available.",
        "5. Fill explanation fields with detailed reasoning BEFORE the corresponding decision field.",
        "6. Return ONLY valid JSON, no markdown formatting, no extra text.",
        "",
        "── SCHEMA ──",
        "",
    ]

    for name, field_info in AugmentedCompany.model_fields.items():
        annotation = field_info.annotation
        desc = field_info.description or ""

        # Format the type annotation nicely
        type_str = _format_type(annotation)
        lines.append(f"- {name} ({type_str}): {desc}")

    lines.append("")
    lines.append("── END SCHEMA ──")
    lines.append("")
    lines.append("Website content to analyze:")

    return "\n".join(lines)


def _format_type(annotation) -> str:
    """Turn a Python type annotation into a readable string for the prompt."""
    from typing import get_origin, get_args

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is list:
        inner = get_args(annotation)
        inner_str = inner[0].__name__ if inner else "str"
        return f"list[{inner_str}]"

    if args:  # Literal
        vals = ", ".join(f'"{a}"' for a in args)
        return f"one of [{vals}]"

    if hasattr(annotation, "__name__"):
        return annotation.__name__

    return str(annotation)


# Pre-built prompt (used at import time)
EXTRACTION_PROMPT = build_extraction_prompt()
