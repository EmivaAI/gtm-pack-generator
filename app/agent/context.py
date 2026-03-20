import json
from typing import List, Optional
from app.db.schema import LaunchCandidate, BrandProfile, ChangeEvent, AudienceSegment

def build_candidate_context(
    candidate: LaunchCandidate,
    change_event: ChangeEvent,
    brand_profile: BrandProfile,
    audience_segments: Optional[List[AudienceSegment]] = None
) -> str:
    """
    Takes structured candidate data and related brand/change records from the database
    and formats it into a secure, instruction-dense text string for the GTM generation LLM.
    """
    context_lines = []
    
    # 1. Change Context
    context_lines.append("=== PRODUCT CHANGE EVENT ===")
    context_lines.append(f"Title: {change_event.title}")
    if change_event.description:
        context_lines.append(f"Description: {change_event.description}")
    
    context_lines.append(f"\nLaunch Tier: {candidate.tier.value}")
    if candidate.reasons:
        context_lines.append(f"Launch Decision Reasons: {json.dumps(candidate.reasons)}")
        
    if candidate.safety_warnings:
        context_lines.append(f"Safety Warnings to Note: {json.dumps(candidate.safety_warnings)}")

    # 2. Brand Context (The Truth Sheet)
    context_lines.append("\n=== BRAND PROFILE ===")
    if brand_profile.product_summary:
        context_lines.append(f"Product Summary: {brand_profile.product_summary}")
    if brand_profile.tone_rules:
        context_lines.append(f"Tone Rules: {json.dumps(brand_profile.tone_rules)}")
    if brand_profile.allowed_claims:
        context_lines.append(f"Allowed Claims: {json.dumps(brand_profile.allowed_claims)}")
    if brand_profile.disallowed_claims:
        context_lines.append(f"DISALLOWED Claims (NEVER USE): {json.dumps(brand_profile.disallowed_claims)}")

    # 3. Audience Context
    if audience_segments:
        context_lines.append("\n=== TARGET AUDIENCES ===")
        for seg in audience_segments:
            context_lines.append(f"Persona: {seg.persona_name}")
            if seg.pain_points:
                context_lines.append(f"  - Pain Points: {json.dumps(seg.pain_points)}")
            if seg.desired_outcomes:
                context_lines.append(f"  - Desired Outcomes: {json.dumps(seg.desired_outcomes)}")
            if seg.objections:
                context_lines.append(f"  - Typical Objections: {json.dumps(seg.objections)}")
            context_lines.append("")

    return "\n".join(context_lines)
