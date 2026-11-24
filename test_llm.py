import json
from main import (
    app,
    components,
    compare,
    get_knowledge,
    analyze,
    ComparisonRequest,
    KnowledgeQueryRequest,
    AnalyzeRequest
)
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

def run_tests():
    print("=" * 60)
    print("TEST 1: Verify existing GET /components endpoint")
    print("=" * 60)
    all_comps = components()
    print(f"Components count: {len(all_comps)}")
    assert len(all_comps) == 50, "Expected 50 components"
    print("-> GET /components PASSED\n")

    print("=" * 60)
    print("TEST 2: Verify existing POST /compare endpoint")
    print("=" * 60)
    comp_res = compare(ComparisonRequest(component_a_id="CB001", component_b_id="CB002"))
    analysis = comp_res["analysis"]
    print(f"Weight difference: {analysis['weight_difference_kg']} kg")
    print(f"Weight reduction: {analysis['weight_reduction_percent']}%")
    print(f"Cost difference: ${analysis['cost_difference_usd']:.2f}")
    print(f"Cost change: {analysis['cost_change_percent']}%")
    assert analysis['weight_difference_kg'] == 1.23
    assert analysis['weight_reduction_percent'] == 35.14
    assert analysis['cost_difference_usd'] == 212.50
    assert analysis['cost_change_percent'] == 25.0
    print("-> POST /compare PASSED\n")

    print("=" * 60)
    print("TEST 3: Verify existing POST /knowledge/retrieve endpoint")
    print("=" * 60)
    rag_res = get_knowledge(KnowledgeQueryRequest(query="Steel vs Aluminum trade-offs in door panels", top_k=2))
    print(f"Retrieved passages: {len(rag_res)}")
    for r in rag_res:
        print(f"  - [{r['source_file']}] {r['source_title']} ({r['section']})")
    assert len(rag_res) == 2
    print("-> POST /knowledge/retrieve PASSED\n")

    print("=" * 60)
    print("TEST 4: Verify new POST /analyze endpoint (Valid IDs: CB001 vs CB002)")
    print("=" * 60)
    req = AnalyzeRequest(component_a_id="CB001", component_b_id="CB002")
    analyze_res = analyze(req)

    # Verify JSON serializability
    encoded = jsonable_encoder(analyze_res)
    assert "comparison" in encoded
    assert "retrieved_knowledge" in encoded
    assert "insight" in encoded
    assert "disclaimers" in encoded

    insight = encoded["insight"]
    print(f"Insight Status: {insight.get('status')}")
    print(f"Insight Model:  {insight.get('model')}")
    if insight.get("message"):
        print(f"Insight Message: {insight.get('message')}")

    sections = insight.get("sections", {})
    required_sections = [
        "comparison_summary",
        "weight_reduction_analysis",
        "cost_trade_off_analysis",
        "material_and_manufacturing_differences",
        "engineering_considerations",
        "potential_advantages",
        "risks_and_limitations",
        "final_recommendation"
    ]
    print("\nVerifying 8 structured report sections:")
    for sec_key in required_sections:
        assert sec_key in sections and len(sections[sec_key]) > 0, f"Missing or empty section: {sec_key}"
        print(f"  [OK] {sec_key}: {sections[sec_key][:70]}...")

    # Verify report contains exact numbers
    report_text = insight.get("report", "")
    assert "1.23" in report_text, "Report must cite exact weight difference 1.23 kg"
    assert "35.14" in report_text, "Report must cite exact weight reduction 35.14%"
    assert "212.5" in report_text, "Report must cite exact cost difference $212.50"
    assert "25.0" in report_text or "25%" in report_text, "Report must cite exact cost increase 25%"

    print("\nGround truth numbers verified in generated report!")
    print("-> POST /analyze PASSED\n")

    print("=" * 60)
    print("TEST 5: Verify POST /analyze error handling for invalid IDs")
    print("=" * 60)
    try:
        analyze(AnalyzeRequest(component_a_id="INVALID_ID", component_b_id="CB002"))
        assert False, "Expected 404 HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
        print(f"Successfully caught 404 for invalid ID: {e.detail}")
    print("-> Invalid ID handling PASSED\n")

    print("=" * 60)
    print("ALL 5 TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
