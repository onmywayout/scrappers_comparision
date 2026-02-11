"""
AugmentedCompany Pydantic model — the single source of truth for feature extraction.
All feature names, types, descriptions, and evaluation categories are derived from this model.
"""

from typing import Literal, get_args, get_origin
from enum import Enum
from pydantic import BaseModel, Field


# ── The Pydantic Model (provided by user) ───────────────────────────────────

class AugmentedCompany(BaseModel):
    domain: str = Field(
        description="The company's domain name"
    )
    under_maintenance_explanation: list[str] = Field(
        description="Provide multiple detailed reasons explaining why the website might be considered under "
        "maintenance, unavailable, unresponsive, or unreachable"
    )
    under_maintenance: Literal["true", "false"] = Field(
        description="Is the website currently under maintenance, unavailable, unresponsive or unreachable? "
        "Return 'true' or 'false'"
    )
    early_access_explanation: list[str] = Field(
        description="Provide multiple detailed reasons explaining why the website might be considered in early "
        "access mode, such as showing a coming soon page or being in beta"
    )
    early_access: Literal["true", "false", "unknown"] = Field(
        description="Is the website in early access mode, for example it shows a coming soon page or a beta? "
        "Return 'true', 'false', or 'unknown' if you cannot determine"
    )
    language: str = Field(
        description="What is the primary language of the website? (e.g., 'en' for English)"
    )
    capital_intensive_business_explanation: list[str] = Field(
        description="Provide multiple detailed reasons explaining whether the company operates in a "
        "capital-intensive industry that requires significant investment in physical assets, R&D facilities, "
        "or laboratory infrastructure. Consider industries like manufacturing, mining, infrastructure, "
        "scientific breakthroughs, chemistry, pharmaceuticals, biotech, and drug development as capital intensive"
    )
    capital_intensive_business: Literal["true", "false", "unknown"] = Field(
        description="Does the company operate in a capital-intensive industry that requires significant investment "
        "in physical assets, R&D facilities, or laboratory infrastructure? This includes manufacturing, mining, "
        "infrastructure, scientific breakthroughs, chemistry, pharmaceuticals, biotech, and drug development. "
        "Return 'true', 'false', or 'unknown' if you cannot determine"
    )
    people_based_service_explanation: list[str] = Field(
        description="Provide multiple detailed reasons explaining whether the company's product is primarily based "
        "on human skills, expertise, or personal services rather than manufactured goods or software"
    )
    people_based_service: Literal["true", "false", "unknown"] = Field(
        description="Identify companies where the product IS the people - businesses selling professional judgment, "
        "skills, or personal service rather than manufactured goods or software. "
        "Return 'true', 'false', or 'unknown' if you cannot determine"
    )
    product_category_explanation: list[str] = Field(
        description="Provide multiple detailed reasons explaining the company's primary product category based on "
        "their business model and target market"
    )
    product_category: Literal["non-profit", "B2B", "B2C", "SMB", "unknown"] = Field(
        description="What is the company's primary product category? Return 'non-profit' for non-profit "
        "organizations, 'B2B' for business-to-business, 'B2C' for business-to-consumer, 'SMB' for small and "
        "medium business focused, or 'unknown' if you cannot determine"
    )
    operation_country: list[str] = Field(
        description="List the countries where the company operates. Return a list of country names in ISO code, or ['unknown'] "
        "if you cannot determine"
    )
    main_product_type_explanation: list[str] = Field(
        description="Provide multiple detailed reasons explaining what the main type of product or service offered "
        "by the company is"
    )
    main_product_type: str = Field(
        description="What is the main type of product or service offered by the company? Return a description such "
        "as 'SaaS platform', 'mobile application', 'consulting services', 'hardware device', or 'unknown' if you "
        "cannot determine"
    )
    pricing_information: str = Field(
        description="How is the product priced, and what are the different pricing options available? Return a "
        "detailed description of pricing tiers, models, or 'unknown' if pricing information is not available"
    )
    industries: list[str] = Field(
        description="List the industries or product delivery methods the company operates, use NAICS codes (e.g., platform, API, "
        "mobile app, web app, plugin, extension, etc.)"
    )
    key_features: list[str] = Field(
        description="List the key features or functionalities of the product/service"
    )
    used_by: list[str] = Field(
        description="List notable companies or clients using the product/service, if mentioned on the website. "
        "Return empty list if not mentioned"
    )
    number_of_employees: str = Field(
        description="How many people are listed as working at the company? Return a number, range like ,'0-9','10-50','50-200', '200+', "
        "or 'unknown' if not mentioned"
    )
    featured_in: list[str] = Field(
        description="List media outlets or publications where the company has been featured, usually found in "
        "'As seen in' or 'Featured in' sections. Return empty list if not mentioned"
    )
    press_releases: list[str] = Field(
        description="List any press releases produced by the company itself. Return empty list if not found"
    )
    backing_funds: list[str] = Field(
        description="List venture capital firms, investors, or funds backing the company with money. Return empty list if "
        "not mentioned"
    )
    patents: str = Field(
        description="How many patents does the company hold, if mentioned on the website? Return a number or "
        "'unknown'"
    )
    customers_served: str = Field(
        description="How many units/customers has the company served, if mentioned? Return a description like "
        "'10,000+ customers', '5M users', or 'unknown'"
    )
    competitors: list[str] = Field(
        description="List competitors mentioned on the website. Return empty list if not mentioned"
    )
    conferences: list[str] = Field(
        description="List past or future conference attendance or participation mentioned on the website. Include "
        "conference names and dates if available. Return empty list if not mentioned"
    )


# ── Feature Classification (derived from model) ─────────────────────────────

class FeatureType(str, Enum):
    LITERAL_BOOL = "literal_bool"     # Literal["true", "false"] or Literal["true", "false", "unknown"]
    LITERAL_ENUM = "literal_enum"     # Literal["non-profit", "B2B", ...]
    TEXT = "text"                      # plain str
    LIST = "list"                      # list[str]


# Fields to skip during evaluation (metadata + chain-of-thought explanations)
SKIP_FIELDS = {"domain"} | {
    name for name in AugmentedCompany.model_fields
    if name.endswith("_explanation")
}

# The evaluable feature names (everything except domain and explanations)
FEATURES = [
    name for name in AugmentedCompany.model_fields
    if name not in SKIP_FIELDS
]

# Literal boolean values (the allowed string sets for bool-like fields)
_BOOL_LITERALS = {
    frozenset({"true", "false"}),
    frozenset({"true", "false", "unknown"}),
}


def _classify_field(field_name: str) -> FeatureType:
    """Determine the evaluation type of a model field."""
    annotation = AugmentedCompany.model_fields[field_name].annotation

    # Check for list[str]
    origin = get_origin(annotation)
    if origin is list:
        return FeatureType.LIST

    # Check for Literal types
    args = get_args(annotation)
    if args:  # It's a Literal
        vals = frozenset(args)
        if vals in _BOOL_LITERALS:
            return FeatureType.LITERAL_BOOL
        return FeatureType.LITERAL_ENUM

    # Plain str
    return FeatureType.TEXT


FEATURE_TYPES = {name: _classify_field(name) for name in FEATURES}


# ── Ground Truth Field Mapping (old JSONL names → new model names) ───────────

GT_FIELD_MAP = {
    # Old name → new name
    "is_working": "under_maintenance",          # INVERTED semantics
    "is_launched": "early_access",              # INVERTED semantics
    "is_capital_intensive": "capital_intensive_business",
    "is_people_based_service": "people_based_service",
    "language": "language",
    "operation_country": "operation_country",
    "main_product_type": "main_product_type",
    "pricing_information": "pricing_information",
    "industries": "industries",
    "key_features": "key_features",
    "product_category": "product_category",
    "used_by": "used_by",
    "number_of_employees": "number_of_employees",
    "Featured_in": "featured_in",
    "Press_releases": "press_releases",
    "backing_funds": "backing_funds",
    "Patents": "patents",
    "customers_served": "customers_served",
    "Competitors": "competitors",
    "conferences_attendance": "conferences",
}

# Fields where ground truth semantics are inverted relative to new model
GT_INVERTED_BOOLEANS = {"under_maintenance", "early_access"}
