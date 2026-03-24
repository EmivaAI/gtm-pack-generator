from typing import Dict, Any
from langchain_core.output_parsers import JsonOutputParser
from gtm_pack_generator.agent.llm import get_llm_instance
from gtm_pack_generator.agent.prompts import (
    internal_brief_prompt,
    sales_snippet_prompt,
    support_snippet_prompt,
    external_asset_prompt,
)
from gtm_pack_generator.db.schema import AssetType

def generate_internal_brief(context_str: str) -> str:
    """Generates an internal brief using the LLM."""
    chain = internal_brief_prompt | get_llm_instance()
    res = chain.invoke({"context": context_str})
    return res.content

def generate_sales_snippet(context_str: str) -> str:
    """Generates a sales snippet using the LLM."""
    chain = sales_snippet_prompt | get_llm_instance()
    res = chain.invoke({"context": context_str})
    return res.content

def generate_support_snippet(context_str: str) -> str:
    """Generates a support snippet using the LLM."""
    chain = support_snippet_prompt | get_llm_instance()
    res = chain.invoke({"context": context_str})
    return res.content

def generate_external_asset_variants(
    context_str: str, 
    asset_type: AssetType, 
    preference_hint: str
) -> Dict[str, Any]:
    """
    Generates dual variants (A/B) for external assets.
    Returns a dictionary with 'variant_a' and 'variant_b'.
    """
    chain = external_asset_prompt | get_llm_instance() | JsonOutputParser()
    res_dict = chain.invoke(
        {
            "context": context_str,
            "asset_type": asset_type.value,
            "preference_hint": preference_hint,
        }
    )
    return res_dict
