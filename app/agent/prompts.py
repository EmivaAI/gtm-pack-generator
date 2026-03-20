from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

SYSTEM_PROMPT = """You are an expert Go-To-Market (GTM) strategist and copywriter.
Your goal is to generate high-quality GTM assets based on the strict context constraints provided.
You must adhere completely to the Brand Profile tone rules, and NEVER use disallowed claims.
"""

INTERNAL_BRIEF_TEMPLATE = """Please generate a comprehensive Internal Launch Brief for cross-functional teams (Sales, Marketing, Support, Leadership).
Use the following context:
{context}

Format the brief with clear sections: Summary, Value Prop, Key Audiences, and FAQs.
Return the result directly as plain text/markdown.
"""

SALES_SNIPPET_TEMPLATE = """Please generate a Sales Snippet (a short blurb sales reps can copy-paste to prospects).
Use the following context:
{context}

Return the result directly as plain text. Keep it punchy and outcome-focused.
"""

EXTERNAL_ASSET_TEMPLATE = """Please generate content for a {asset_type}.
Use the following context constraints:
{context}

CRITICAL: You must generate EXACTLY TWO variants and return them in valid JSON format.
Variant A: "Short and Direct" (Punchy, get straight to the point)
Variant B: "Detailed and Narrative" (Story-driven, explanatory, slightly longer)

Output Format (JSON only):
{{
  "variant_a": "Text for variant A...",
  "variant_b": "Text for variant B..."
}}
"""

internal_brief_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
    HumanMessagePromptTemplate.from_template(INTERNAL_BRIEF_TEMPLATE)
])

sales_snippet_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
    HumanMessagePromptTemplate.from_template(SALES_SNIPPET_TEMPLATE)
])

external_asset_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
    HumanMessagePromptTemplate.from_template(EXTERNAL_ASSET_TEMPLATE)
])
