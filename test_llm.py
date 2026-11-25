import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
    print("TEST 4: Verify POST /analyze endpoint for 3 key benchmarks")
    print("=" * 60)

    benchmarks = [
        {
            "name": "Door Panel",
            "a_id": "CB001",
            "b_id": "CB002",
            "expected_wt_diff": "1.23",
            "expected_wt_pct": "35.14",
            "expected_cost_diff_usd": "212.5",
            "expected_cost_inr": "18,062.50",
            "expected_cost_pct": "25"
        },
        {
            "name": "Control Arm",
            "a_id": "CB020",
            "b_id": "CB016",
            "expected_wt_diff": "0.72",
            "expected_wt_pct": "13.04",
            "expected_cost_diff_usd": "150",
            "expected_cost_inr": "12,750",
            "expected_cost_pct": "11.11"
        },
        {
            "name": "Seat Frame",
            "a_id": "CB030",
            "b_id": "CB026",
            "expected_wt_diff": "1.20",
            "expected_wt_pct": "13.04",
            "expected_cost_diff_usd": "180",
            "expected_cost_inr": "15,300",
            "expected_cost_pct": "11.11"
        }
    ]

    five_concise_sections = [
        "comparison_summary",
        "weight_analysis",
        "cost_analysis",
        "material_and_manufacturing",
        "engineering_conclusion"
    ]

    for bench in benchmarks:
        print(f"\n--- Testing Benchmark: {bench['name']} ({bench['a_id']} vs {bench['b_id']}) ---")
        req = AnalyzeRequest(component_a_id=bench["a_id"], component_b_id=bench["b_id"])
        analyze_res = analyze(req)

        encoded = jsonable_encoder(analyze_res)
        assert "comparison" in encoded
        assert "retrieved_knowledge" in encoded
        assert "insight" in encoded
        assert "disclaimers" in encoded

        insight = encoded["insight"]
        assert insight.get("status") in ("warning", "fallback", "success")
        sections = insight.get("sections", {})

        for sec_key in five_concise_sections:
            assert sec_key in sections and len(sections[sec_key]) > 0, f"Missing or empty section: {sec_key}"
            lines = [l for l in sections[sec_key].strip().split("\n") if l.strip()]
            assert len(lines) <= 5, f"Section {sec_key} exceeds concise length limit: {len(lines)} lines"
            print(f"  [OK] {sec_key}: {sections[sec_key][:60]}...")

        report_text = insight.get("report", "")
        assert bench["expected_wt_diff"] in report_text, f"Missing weight diff {bench['expected_wt_diff']} in report"
        assert bench["expected_wt_pct"] in report_text, f"Missing weight pct {bench['expected_wt_pct']} in report"
        assert bench["expected_cost_diff_usd"] in report_text, f"Missing cost diff USD {bench['expected_cost_diff_usd']}"
        assert bench["expected_cost_inr"] in report_text, f"Missing cost INR {bench['expected_cost_inr']}"
        assert bench["expected_cost_pct"] in report_text, f"Missing cost pct {bench['expected_cost_pct']}"

        # Disclaimers & engineering boundaries
        assert "validation" in report_text.lower(), "Must cite structural/fatigue/manufacturing validation"
        assert "synthetic" in report_text.lower(), "Must include synthetic dataset disclaimer"
        assert "85" in report_text, "Must include 85/USD conversion rate disclaimer"

        # Prevent unsupported claims
        for unsupported in ["braking distance", "driving range", "fuel efficiency", "vehicle handling"]:
            assert unsupported not in report_text.lower(), f"Unsupported claim '{unsupported}' found in report"

        print(f"  -> {bench['name']} report verified concise and numerically accurate!")

    print("\n-> All 3 component benchmark comparisons PASSED\n")

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
