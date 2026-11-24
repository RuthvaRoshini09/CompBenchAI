import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

EDUCATIONAL_DISCLAIMERS = {
    "dataset": "Synthetic automotive benchmark dataset generated for educational and benchmarking demonstrations.",
    "knowledge_base": "General automotive engineering educational reference material — not official OEM or Caresoft proprietary teardown data."
}


def _build_fallback_report(comp, analysis, a, b, knowledge_passages, notice_message):
    """
    Generate a deterministic, structured engineering report using exact
    Python-calculated values and retrieved RAG context when the Gemini API
    key is absent or an API error occurs.
    """
    comp_name = comp.get("component_name", "Component")
    wt_diff = analysis.get("weight_difference_kg", 0.0)
    wt_red_pct = analysis.get("weight_reduction_percent", 0.0)
    cost_diff = analysis.get("cost_difference_usd", 0.0)
    cost_chg_pct = analysis.get("cost_change_percent", 0.0)

    # Summarize knowledge references
    knowledge_summary = "\n".join([
        f"- **{k.get('source_title', 'Ref')} ({k.get('section', 'General')})**: {k.get('content', '')[:180]}..."
        for k in (knowledge_passages[:2] if knowledge_passages else [])
    ])
    if not knowledge_summary:
        knowledge_summary = "- General engineering reference material on lightweighting and manufacturing trade-offs."

    sections = {
        "comparison_summary": (
            f"Benchmarking analysis between Component A ({a['id']} - {a['vehicle']}, {a['material']} via {a['manufacturing_process']}) "
            f"and Component B ({b['id']} - {b['vehicle']}, {b['material']} via {b['manufacturing_process']}) for the automotive {comp_name}. "
            f"Component B achieves a lighter design ({b['weight_kg']} kg vs {a['weight_kg']} kg) at a higher manufacturing cost (${b['cost_usd']:.2f} vs ${a['cost_usd']:.2f})."
        ),
        "weight_reduction_analysis": (
            f"Component A weighs {a['weight_kg']} kg, while Component B weighs {b['weight_kg']} kg. "
            f"The absolute weight difference is {wt_diff:.2f} kg, representing a {wt_red_pct:.2f}% weight reduction. "
            f"This substantial mass reduction contributes directly to vehicle lightweighting, reducing kinetic energy during dynamic events "
            f"and improving energy efficiency (extending EV battery range or reducing ICE fuel consumption)."
        ),
        "cost_trade_off_analysis": (
            f"Component A total unit cost is ${a['cost_usd']:.2f}, whereas Component B is ${b['cost_usd']:.2f}. "
            f"The cost difference is ${cost_diff:.2f}, representing a {cost_chg_pct:.2f}% cost increase. "
            f"Evaluating the cost-to-weight ratio yields approximately ${cost_diff / wt_diff:.2f} per kg of mass saved (if weight saved > 0), "
            f"which aligns with typical industry lightweighting cost premiums for automotive closures and structural sub-assemblies."
        ),
        "material_and_manufacturing_differences": (
            f"Component A employs {a['material']} fabricated via {a['manufacturing_process']}. "
            f"Component B transitions to {b['material']} fabricated via {b['manufacturing_process']}. "
            f"{'Material transition detected: ' + a['material'] + ' to ' + b['material'] + '. ' if analysis.get('material_changed') else 'Material remains unchanged. '}"
            f"{'Manufacturing process transition: ' + a['manufacturing_process'] + ' to ' + b['manufacturing_process'] + '. ' if analysis.get('process_changed') else 'Manufacturing process remains identical.'}"
        ),
        "engineering_considerations": (
            f"Key engineering considerations based on domain knowledge:\n"
            f"- Structural rigidity and elastic modulus differences between {a['material']} and {b['material']}.\n"
            f"- NVH (Noise, Vibration, and Harshness) dampening characteristics.\n"
            f"- Joining and fastening methods ({a['manufacturing_process']} vs {b['manufacturing_process']}).\n"
            f"- Corrosion protection and galvanic isolation in mixed-material body joints.\n"
            f"Reference context:\n{knowledge_summary}"
        ),
        "potential_advantages": (
            f"- Weight reduction of {wt_diff:.2f} kg ({wt_red_pct:.2f}%) improves vehicle handling, braking distance, and range efficiency.\n"
            f"- Potential secondary mass compounding benefits throughout suspension and powertrain.\n"
            f"- Enhanced corrosion resistance if transitioning to naturally passivating alloys or polymers."
        ),
        "risks_and_limitations": (
            f"- Unit production cost increase of ${cost_diff:.2f} ({cost_chg_pct:.2f}%).\n"
            f"- Capital tooling and process re-tooling expenditures for {b['manufacturing_process']}.\n"
            f"- Differences in thermal expansion rates requiring adjusted paint oven clearances and elastic adhesives."
        ),
        "final_recommendation": (
            f"Component B is recommended for applications where vehicle lightweighting, range extension, or high-performance targets "
            f"justify a unit cost increase of ${cost_diff:.2f} (+{cost_chg_pct:.2f}%). For budget-sensitive, high-volume cost-critical platforms, "
            f"Component A remains commercially viable. Note: This assessment is based on synthetic data and general educational reference material."
        )
    }

    report_markdown = f"""### 1. Comparison Summary
{sections['comparison_summary']}

### 2. Weight Reduction Analysis
{sections['weight_reduction_analysis']}

### 3. Cost Trade-Off Analysis
{sections['cost_trade_off_analysis']}

### 4. Material and Manufacturing Process Differences
{sections['material_and_manufacturing_differences']}

### 5. Engineering Considerations
{sections['engineering_considerations']}

### 6. Potential Advantages
{sections['potential_advantages']}

### 7. Risks and Limitations
{sections['risks_and_limitations']}

### 8. Final Engineering Recommendation
{sections['final_recommendation']}

---
*> **Notice**: {notice_message}*
*> **Dataset Notice**: {EDUCATIONAL_DISCLAIMERS['dataset']}*
*> **Knowledge Notice**: {EDUCATIONAL_DISCLAIMERS['knowledge_base']}*
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
        notice = "GEMINI_API_KEY is not configured in .env. Displaying deterministic benchmark report based on exact Python calculations and engineering knowledge base."
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

    prompt = f"""You are CompBench AI, an expert automotive benchmarking systems engineer.
Analyze the following automotive component comparison using the provided Python-calculated metrics and engineering reference material.

CRITICAL INSTRUCTIONS & GROUND TRUTH:
1. You MUST use and cite the EXACT Python-calculated numbers provided below. DO NOT recalculate, round differently, estimate, or invent new numbers.
   - Component Name: {comp_name}
   - Component A ID: {a.get('id')}, Vehicle: {a.get('vehicle')}, Material: {a.get('material')}, Process: {a.get('manufacturing_process')}, Weight: {a.get('weight_kg')} kg, Cost: ${a.get('cost_usd'):.2f}
   - Component B ID: {b.get('id')}, Vehicle: {b.get('vehicle')}, Material: {b.get('material')}, Process: {b.get('manufacturing_process')}, Weight: {b.get('weight_kg')} kg, Cost: ${b.get('cost_usd'):.2f}
   - Weight Difference: {analysis.get('weight_difference_kg')} kg
   - Weight Reduction: {analysis.get('weight_reduction_percent')}%
   - Cost Difference: ${analysis.get('cost_difference_usd'):.2f}
   - Cost Change: {analysis.get('cost_change_percent')}%
   - Lighter Design: Component B is {'lighter' if analysis.get('lighter_design') else 'heavier or equal'}
   - Lower Cost Design: Component B is {'cheaper' if analysis.get('lower_cost_design') else 'more expensive or equal'}

2. You MUST structure your report into the following exact sections with H3 headings:
   ### 1. Comparison Summary
   ### 2. Weight Reduction Analysis
   ### 3. Cost Trade-Off Analysis
   ### 4. Material and Manufacturing Process Differences
   ### 5. Engineering Considerations
   ### 6. Potential Advantages
   ### 7. Risks and Limitations
   ### 8. Final Engineering Recommendation

3. Use the relevant domain knowledge provided below to enrich the technical explanation:
{rag_context_str}

4. Clearly state at the conclusion that the dataset is synthetic and the reference knowledge is general educational reference material, not official OEM or Caresoft data.
"""

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )

        generated_text = response.text or ""

        # Extract sections if possible
        section_titles = [
            ("comparison_summary", r"###\s*1\.\s*Comparison Summary(.*?)(?=###\s*2\.)"),
            ("weight_reduction_analysis", r"###\s*2\.\s*Weight Reduction Analysis(.*?)(?=###\s*3\.)"),
            ("cost_trade_off_analysis", r"###\s*3\.\s*Cost Trade-Off Analysis(.*?)(?=###\s*4\.)"),
            ("material_and_manufacturing_differences", r"###\s*4\.\s*Material and Manufacturing Process Differences(.*?)(?=###\s*5\.)"),
            ("engineering_considerations", r"###\s*5\.\s*Engineering Considerations(.*?)(?=###\s*6\.)"),
            ("potential_advantages", r"###\s*6\.\s*Potential Advantages(.*?)(?=###\s*7\.)"),
            ("risks_and_limitations", r"###\s*7\.\s*Risks and Limitations(.*?)(?=###\s*8\.)"),
            ("final_recommendation", r"###\s*8\.\s*Final Engineering Recommendation(.*?)(?=$)"),
        ]

        parsed_sections = {}
        for key, pattern in section_titles:
            m = re.search(pattern, generated_text, re.DOTALL | re.IGNORECASE)
            parsed_sections[key] = m.group(1).strip() if m else ""

        return {
            "status": "success",
            "model": model_name,
            "report": generated_text,
            "sections": parsed_sections,
            "disclaimers": EDUCATIONAL_DISCLAIMERS
        }

    except Exception as exc:
        # Gracefully handle API errors, invalid keys, or quota limits without crashing
        error_msg = f"Gemini API invocation failed ({exc.__class__.__name__}: {str(exc)}). Displaying deterministic fallback report."
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
