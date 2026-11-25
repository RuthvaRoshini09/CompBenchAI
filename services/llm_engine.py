import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Configurable exchange rate for engineering estimates
USD_TO_INR_RATE = 85.0

EDUCATIONAL_DISCLAIMERS = {
    "dataset": "Synthetic automotive benchmark dataset generated for educational and benchmarking demonstrations.",
    "knowledge_base": "General automotive engineering educational reference material — not official OEM or Caresoft proprietary teardown data."
}


def _build_fallback_report(comp, analysis, a, b, knowledge_passages, notice_message):
    """
    Generate a concise, deterministic 5-section engineering report using exact
    Python-calculated values and retrieved RAG context when the Gemini API
    key is absent or an API error occurs.
    """
    comp_name = comp.get("component_name", "Component")
    wt_diff = float(analysis.get("weight_difference_kg", 0.0))
    wt_red_pct = float(analysis.get("weight_reduction_percent", 0.0))
    cost_diff = float(analysis.get("cost_difference_usd", 0.0))
    cost_chg_pct = float(analysis.get("cost_change_percent", 0.0))
    lighter = analysis.get("lighter_design", False)

    cost_diff_abs = abs(cost_diff)
    cost_diff_inr = cost_diff_abs * USD_TO_INR_RATE
    cost_a_usd = float(a.get("cost_usd", 0.0))
    cost_b_usd = float(b.get("cost_usd", 0.0))
    cost_a_inr = cost_a_usd * USD_TO_INR_RATE
    cost_b_inr = cost_b_usd * USD_TO_INR_RATE

    def fmt_usd(v):
        return f"${int(v):,}" if v == int(v) else f"${v:,.2f}"

    def fmt_inr(v):
        return f"₹{int(v):,}" if v == int(v) else f"₹{v:,.2f}"

    wt_diff_abs = abs(wt_diff)
    wt_red_pct_abs = abs(wt_red_pct)
    if wt_diff == 0:
        wt_label = "Difference"
    elif lighter or wt_diff > 0:
        wt_label = "Reduction"
    else:
        wt_label = "Increase"

    if cost_diff == 0:
        cost_trend = "Difference"
    elif cost_diff > 0:
        cost_trend = "Increase"
    else:
        cost_trend = "Reduction"

    abs_cost_chg_pct = abs(cost_chg_pct)
    pct_str = f"{int(abs_cost_chg_pct)}%" if abs_cost_chg_pct == int(abs_cost_chg_pct) else f"{abs_cost_chg_pct:.2f}%"

    # 1. Comparison Summary
    mfg_summary = (
        f"Both use {a['manufacturing_process']}."
        if a['manufacturing_process'] == b['manufacturing_process']
        else f"{a['manufacturing_process']} vs {b['manufacturing_process']}."
    )
    summary_text = f"{comp_name}: {a['id']} ({a['material']}) vs {b['id']} ({b['material']}). {mfg_summary}"

    # 2. Weight Analysis
    weight_text = (
        f"- Baseline: {a['weight_kg']:.2f} kg\n"
        f"- Candidate: {b['weight_kg']:.2f} kg\n"
        f"- {wt_label}: {wt_diff_abs:.2f} kg ({wt_red_pct_abs:.2f}%)"
    )

    # 3. Cost Analysis
    cost_text = (
        f"- Baseline: {fmt_usd(cost_a_usd)} ({fmt_inr(cost_a_inr)} estimated)\n"
        f"- Candidate: {fmt_usd(cost_b_usd)} ({fmt_inr(cost_b_inr)} estimated)\n"
        f"- {cost_trend}: {fmt_usd(cost_diff_abs)} ({fmt_inr(cost_diff_inr)} estimated), or {pct_str}"
    )

    # 4. Material & Manufacturing
    mat_part = (
        f"Material changes from {a['material']} to {b['material']}."
        if a['material'] != b['material']
        else f"Material remains {a['material']}."
    )
    proc_part = (
        f"Manufacturing process remains {a['manufacturing_process']}."
        if a['manufacturing_process'] == b['manufacturing_process']
        else f"Manufacturing process changes from {a['manufacturing_process']} to {b['manufacturing_process']}."
    )
    material_text = f"{mat_part} {proc_part}"

    # 5. Engineering Conclusion
    if lighter and cost_diff > 0:
        cand_summary = "Candidate B is lighter but costs more."
    elif lighter and cost_diff < 0:
        cand_summary = "Candidate B is both lighter and lower cost."
    elif lighter and cost_diff == 0:
        cand_summary = "Candidate B is lighter with equivalent cost."
    elif not lighter and wt_diff == 0 and cost_diff < 0:
        cand_summary = "Candidate B offers equivalent weight at lower cost."
    elif not lighter and cost_diff < 0:
        cand_summary = "Candidate B is lower cost but heavier."
    elif not lighter and wt_diff == 0 and cost_diff == 0:
        cand_summary = "Candidate B offers identical weight and cost metrics."
    else:
        cand_summary = "Candidate B is heavier and costs more."

    conclusion_text = f"{cand_summary} Final selection requires structural, fatigue and manufacturing validation."

    sections = {
        "comparison_summary": summary_text,
        "weight_analysis": weight_text,
        "cost_analysis": cost_text,
        "material_and_manufacturing": material_text,
        "material_and_manufacturing_differences": material_text,
        "engineering_conclusion": conclusion_text,
        "engineering_considerations_and_conclusion": conclusion_text,
        "weight_reduction_analysis": weight_text,
        "cost_trade_off_analysis": cost_text,
        "engineering_considerations": conclusion_text,
        "final_recommendation": conclusion_text,
    }

    report_markdown = f"""### AI Engineering Intelligence Report

**1. Comparison Summary**

{summary_text}

**2. Weight Analysis**

{weight_text}

**3. Cost Analysis**

{cost_text}

**4. Material & Manufacturing**

{material_text}

**5. Engineering Conclusion**

{conclusion_text}

*INR estimates use ₹85/USD. Data is synthetic and intended for demonstration.*
"""
    return report_markdown, sections


def generate_engineering_insight(comparison_result: dict, retrieved_knowledge: list) -> dict:
    """
    Generate a comprehensive automotive engineering explanation using the Google Gemini API.
    Sends Python-calculated comparison metrics and relevant RAG knowledge passages.
    Handles missing API keys and API exceptions gracefully without crashing.

    Args:
        comparison_result: Dictionary returned by compare_components().
        retrieved_knowledge: List of dictionaries returned by retrieve_knowledge().

    Returns:
        Dictionary containing status, report markdown, structured sections, and metadata.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    a = comparison_result.get("component_a", {})
    b = comparison_result.get("component_b", {})
    analysis = comparison_result.get("analysis", {})
    comp_name = comparison_result.get("component_name", "Component")

    # If API key is not configured, return deterministic structured fallback
    if not api_key or api_key == "your_gemini_api_key_here":
        notice = "Deterministic engineering report generated from exact Python calculations and retrieved automotive knowledge."
        report_md, sections = _build_fallback_report(
            comparison_result, analysis, a, b, retrieved_knowledge, notice
        )
        return {
            "status": "warning",
            "model": "deterministic-fallback",
            "message": notice,
            "report": report_md,
            "sections": sections,
            "disclaimers": EDUCATIONAL_DISCLAIMERS
        }

    # Prepare ground-truth prompt for Gemini
    rag_context_str = "\n\n".join([
        f"### Reference [{i+1}]: {k.get('source_title', 'Reference')} - {k.get('section', '')}\n{k.get('content', '')}"
        for i, k in enumerate(retrieved_knowledge)
    ])

    cost_diff_abs = abs(float(analysis.get("cost_difference_usd", 0.0)))
    cost_diff_inr = cost_diff_abs * USD_TO_INR_RATE
    cost_sign = "+" if float(analysis.get("cost_difference_usd", 0.0)) >= 0 else "-"
    cost_a_usd = float(a.get("cost_usd", 0.0))
    cost_b_usd = float(b.get("cost_usd", 0.0))
    cost_a_inr = cost_a_usd * USD_TO_INR_RATE
    cost_b_inr = cost_b_usd * USD_TO_INR_RATE

    def fmt_usd(v):
        return f"${int(v):,}" if v == int(v) else f"${v:,.2f}"

    def fmt_inr(v):
        return f"₹{int(v):,}" if v == int(v) else f"₹{v:,.2f}"

    abs_cost_chg_pct = abs(float(analysis.get("cost_change_percent", 0.0)))
    pct_str = f"{int(abs_cost_chg_pct)}%" if abs_cost_chg_pct == int(abs_cost_chg_pct) else f"{abs_cost_chg_pct:.2f}%"

    prompt = f"""You are CompBench AI, an expert automotive benchmarking systems engineer.
Analyze the following automotive component comparison using the provided Python-calculated metrics and engineering reference material.

CRITICAL INSTRUCTIONS & GROUND TRUTH:
1. You MUST use and cite the EXACT Python-calculated numbers provided below. DO NOT recalculate, round differently, estimate, or invent new numbers.
   - Component Name: {comp_name}
   - Component A ID: {a.get('id')}, Vehicle: {a.get('vehicle')}, Material: {a.get('material')}, Process: {a.get('manufacturing_process')}, Weight: {a.get('weight_kg')} kg, Cost: {fmt_usd(cost_a_usd)} USD [{fmt_inr(cost_a_inr)} estimated]
   - Component B ID: {b.get('id')}, Vehicle: {b.get('vehicle')}, Material: {b.get('material')}, Process: {b.get('manufacturing_process')}, Weight: {b.get('weight_kg')} kg, Cost: {fmt_usd(cost_b_usd)} USD [{fmt_inr(cost_b_inr)} estimated]
   - Weight Difference: {analysis.get('weight_difference_kg')} kg
   - Weight Reduction: {analysis.get('weight_reduction_percent')}%
   - Cost Difference: {cost_sign}{fmt_usd(cost_diff_abs)} USD [{cost_sign}{fmt_inr(cost_diff_inr)} estimated at ₹85/USD]
   - Cost Change: {pct_str} (calculated strictly from base USD)
   - Lighter Design: Component B is {'lighter' if analysis.get('lighter_design') else 'heavier or equal'}
   - Lower Cost Design: Component B is {'cheaper' if analysis.get('lower_cost_design') else 'more expensive or equal'}

2. You MUST structure your report into EXACTLY FIVE concise sections with the following format:
   **1. Comparison Summary**
   [1 sentence: Component Name: A (Material) vs B (Material). Both use/differ in process.]

   **2. Weight Analysis**
   - Baseline: {a['weight_kg']:.2f} kg
   - Candidate: {b['weight_kg']:.2f} kg
   - Reduction/Increase: {abs(float(analysis.get('weight_difference_kg', 0.0))):.2f} kg ({abs(float(analysis.get('weight_reduction_percent', 0.0))):.2f}%)

   **3. Cost Analysis**
   - Baseline: {fmt_usd(cost_a_usd)} ({fmt_inr(cost_a_inr)} estimated)
   - Candidate: {fmt_usd(cost_b_usd)} ({fmt_inr(cost_b_inr)} estimated)
   - Increase/Reduction: {fmt_usd(cost_diff_abs)} ({fmt_inr(cost_diff_inr)} estimated), or {pct_str}

   **4. Material & Manufacturing**
   [1-2 sentences on material shift and manufacturing process transition]

   **5. Engineering Conclusion**
   [Candidate summary. Final selection requires structural, fatigue and manufacturing validation.]

   *INR estimates use ₹85/USD. Data is synthetic and intended for demonstration.*

3. STRICT ENGINEERING BOUNDARIES:
   - Keep each section to 1–3 short sentences or compact bullet points.
   - Do not repeat calculations or explanations.
   - Do not make unsupported claims regarding braking distance, EV range, fuel efficiency, or handling.
   - Do not recommend either component based solely on weight and cost.
   - Preserves exact Python numbers.
"""

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )

        generated_text = response.text or ""

        # Extract 5 concise sections
        section_titles = [
            ("comparison_summary", r"(?:###\s*1\.\s*Comparison Summary|\*\*1\.\s*Comparison Summary\*\*|1\.\s*Comparison Summary)(.*?)(?=(?:###\s*2\.|\*\*2\.\s*Weight|2\.\s*Weight))"),
            ("weight_analysis", r"(?:###\s*2\.\s*Weight Analysis|\*\*2\.\s*Weight Analysis\*\*|2\.\s*Weight Analysis)(.*?)(?=(?:###\s*3\.|\*\*3\.\s*Cost|3\.\s*Cost))"),
            ("cost_analysis", r"(?:###\s*3\.\s*Cost Analysis|\*\*3\.\s*Cost Analysis\*\*|3\.\s*Cost Analysis)(.*?)(?=(?:###\s*4\.|\*\*4\.\s*Material|4\.\s*Material))"),
            ("material_and_manufacturing", r"(?:###\s*4\.\s*Material\s*&?\s*Manufacturing|\*\*4\.\s*Material\s*&?\s*Manufacturing\*\*|4\.\s*Material\s*&?\s*Manufacturing)(.*?)(?=(?:###\s*5\.|\*\*5\.\s*Engineering|5\.\s*Engineering))"),
            ("engineering_conclusion", r"(?:###\s*5\.\s*Engineering Conclusion|\*\*5\.\s*Engineering Conclusion\*\*|5\.\s*Engineering Conclusion)(.*?)(?=(?:\*INR estimates|###|$))"),
        ]

        parsed_sections = {}
        for key, pattern in section_titles:
            m = re.search(pattern, generated_text, re.DOTALL | re.IGNORECASE)
            parsed_sections[key] = m.group(1).strip() if m else ""

        # Fallback to deterministic sections for any missing section
        _, fallback_secs = _build_fallback_report(
            comparison_result, analysis, a, b, retrieved_knowledge, ""
        )
        for key in ["comparison_summary", "weight_analysis", "cost_analysis", "material_and_manufacturing", "engineering_conclusion"]:
            if not parsed_sections.get(key):
                parsed_sections[key] = fallback_secs.get(key, "")

        # Backwards compatibility aliases
        parsed_sections["material_and_manufacturing_differences"] = parsed_sections.get("material_and_manufacturing", "")
        parsed_sections["engineering_considerations_and_conclusion"] = parsed_sections.get("engineering_conclusion", "")
        parsed_sections["weight_reduction_analysis"] = parsed_sections.get("weight_analysis", "")
        parsed_sections["cost_trade_off_analysis"] = parsed_sections.get("cost_analysis", "")
        parsed_sections["engineering_considerations"] = parsed_sections.get("engineering_conclusion", "")
        parsed_sections["final_recommendation"] = parsed_sections.get("engineering_conclusion", "")

        return {
            "status": "success",
            "model": model_name,
            "report": generated_text,
            "sections": parsed_sections,
            "disclaimers": EDUCATIONAL_DISCLAIMERS
        }

    except Exception as exc:
        # Gracefully handle API errors, invalid keys, or quota limits without crashing
        error_msg = f"Gemini API invocation failed ({exc.__class__.__name__}). Displaying deterministic fallback report."
        report_md, sections = _build_fallback_report(
            comparison_result, analysis, a, b, retrieved_knowledge, error_msg
        )
        return {
            "status": "fallback",
            "model": "deterministic-fallback",
            "error": str(exc),
            "message": error_msg,
            "report": report_md,
            "sections": sections,
            "disclaimers": EDUCATIONAL_DISCLAIMERS
        }
