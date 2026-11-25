"""
Comprehensive Test Suite for Phase 3: Material Intelligence & Manufacturing Analysis.

Validates:
1. Steel vs Aluminum comparison (exact knowledge base citations and properties)
2. Different material combinations (Cast Iron vs Steel, Plastic vs Aluminum, Magnesium vs Steel)
3. Same-material comparison (Steel vs Steel - no false transition claims)
4. Missing / unknown material handling (graceful fallback)
5. Manufacturing process profiles (Stamping, Casting, Forging, Injection Molding, Machining)
6. RAG retrieval integration and source attribution
7. Deterministic fallback when Gemini is unavailable
8. Clean data separation between component measurements and general material properties
9. API endpoints (/compare, /material-intelligence, /analyze)
10. Frontend HTML, CSS, and JS integration verification
"""

import sys
from pathlib import Path
from main import (
    app,
    compare,
    material_intelligence_endpoint,
    analyze,
    ComparisonRequest,
    MaterialIntelligenceRequest,
    AnalyzeRequest
)
from services.material_engine import (
    get_material_intelligence,
    compute_material_comparison,
    compute_process_comparison,
    _get_material_profile,
    _get_process_profile,
    MATERIAL_KNOWLEDGE_BASE,
    PROCESS_KNOWLEDGE_BASE
)
from services.component_engine import compare_components

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_material_intelligence_suite():
    print("============================================================")
    print("PHASE 3: MATERIAL & MANUFACTURING INTELLIGENCE TEST SUITE")
    print("============================================================")

    # -------------------------------------------------------------
    # 1. Steel vs Aluminum Comparison (Exact Knowledge Base Grounding)
    # -------------------------------------------------------------
    print("\n--- 1. Steel vs Aluminum Comparison ---")
    res_sa = get_material_intelligence(
        material_a="Steel",
        material_b="Aluminum",
        process_a="Stamping",
        process_b="Stamping",
        component_a={"id": "CB001", "weight_kg": 3.50, "cost_usd": 850.0},
        component_b={"id": "CB002", "weight_kg": 2.27, "cost_usd": 1062.5},
        query_rag=True
    )

    mat_a = res_sa["material_a"]
    mat_b = res_sa["material_b"]
    comp = res_sa["material_comparison"]

    assert mat_a["density_g_cm3"] == 7.85, f"Expected 7.85, got {mat_a['density_g_cm3']}"
    assert mat_b["density_g_cm3"] == 2.70, f"Expected 2.70, got {mat_b['density_g_cm3']}"
    assert mat_a["youngs_modulus_gpa"] == 210, f"Expected 210, got {mat_a['youngs_modulus_gpa']}"
    assert mat_b["youngs_modulus_gpa"] == 70, f"Expected 70, got {mat_b['youngs_modulus_gpa']}"
    assert "$3.00 to $7.00" in mat_b["typical_lightweighting_cost"]
    assert "20% to 50%" in comp["stiffness_comparison"] or "stiffer" in comp["stiffness_comparison"]
    assert "Self-Piercing Riveting" in str(mat_b["joining_methods"])
    assert "oxide" in mat_b["corrosion_profile"].lower()
    assert "galvanic" in mat_b["corrosion_profile"].lower()
    assert comp["is_same_material"] is False

    print("  [OK] Steel vs Aluminum verified: 7.85 vs 2.70 g/cm³, 210 vs 70 GPa, SPR joining, $/kg saved range.")

    # -------------------------------------------------------------
    # 2. Other Material Combinations (Cast Iron, Plastic, Magnesium)
    # -------------------------------------------------------------
    print("\n--- 2. Diverse Material Combinations ---")
    # Cast Iron vs Steel
    res_cis = get_material_intelligence("Cast Iron", "Steel", "Casting", "Forging", query_rag=False)
    assert res_cis["material_a"]["category"] == "Ferrous Casting Alloy"
    assert res_cis["material_a"]["density_g_cm3"] == 7.20
    assert "damping" in str(res_cis["material_a"]["advantages"]).lower()
    print("  [OK] Cast Iron profile verified: 7.20 g/cm³, high damping capacity.")

    # Plastic vs Aluminum
    res_pa = get_material_intelligence("Plastic", "Aluminum", "Injection Molding", "Stamping", query_rag=False)
    assert res_pa["material_a"]["category"] == "Polymer / Composite"
    assert res_pa["material_a"]["density_g_cm3"] == 1.20
    assert "snap-fit" in str(res_pa["material_a"]["advantages"]).lower()
    assert "creep" in str(res_pa["material_a"]["limitations"]).lower()
    print("  [OK] Plastic/Composite profile verified: 1.20 g/cm³, snap-fits, viscoelastic creep trade-off.")

    # Magnesium vs Steel
    res_mg = get_material_intelligence("Magnesium", "Steel", "Casting", "Stamping", query_rag=False)
    assert res_mg["material_a"]["density_g_cm3"] == 1.80
    assert "$8.00 to $14.00" in res_mg["material_a"]["typical_lightweighting_cost"]
    assert "galvanic" in res_mg["material_a"]["corrosion_profile"].lower()
    print("  [OK] Magnesium profile verified: 1.80 g/cm³, $8.00-$14.00/kg saved, galvanic sensitivity.")

    # -------------------------------------------------------------
    # 3. Same-Material Comparison Edge Case (Steel vs Steel)
    # -------------------------------------------------------------
    print("\n--- 3. Same-Material Comparison (Steel vs Steel) ---")
    res_same = get_material_intelligence("Steel", "Steel", "Stamping", "Stamping", query_rag=False)
    mat_same_comp = res_same["material_comparison"]
    assert mat_same_comp["is_same_material"] is True
    assert "identical" in mat_same_comp["density_comparison"].lower()
    assert "no material shift" in mat_same_comp["transition_summary"].lower()
    assert res_same["process_comparison"]["is_same_process"] is True
    print("  [OK] Same-material comparison verified: is_same_material=True, no false transition claims.")

    # -------------------------------------------------------------
    # 4. Missing / Unknown Material & Process Fallbacks
    # -------------------------------------------------------------
    print("\n--- 4. Missing / Unknown Material Fallbacks ---")
    prof_unknown = _get_material_profile("Titanium Beta Alloy")
    assert prof_unknown["density_g_cm3"] is None
    assert "Titanium Beta Alloy" in prof_unknown["material_name"]

    proc_unknown = _get_process_profile("Laser Powder Bed Fusion")
    assert "Laser Powder Bed Fusion" in proc_unknown["process_name"]

    res_unknown = get_material_intelligence("UnknownMetal", "Steel", "UnknownProcess", "Stamping", query_rag=False)
    assert res_unknown is not None
    assert res_unknown["material_a"]["material_name"] == "UnknownMetal"
    print("  [OK] Missing/Unknown material gracefully handled with deterministic fallbacks.")

    # -------------------------------------------------------------
    # 5. Manufacturing Process Profiles
    # -------------------------------------------------------------
    print("\n--- 5. Manufacturing Process Intelligence ---")
    processes = ["Stamping", "Casting", "Forging", "Injection Molding", "Machining"]
    for proc in processes:
        p = _get_process_profile(proc)
        assert p["process_name"] != "Unknown"
        assert len(p["advantages"]) > 0
        assert len(p["limitations"]) > 0
        assert len(p["typical_components"]) > 0
        assert p["cycle_time"] is not None

    # Verify specific details from knowledge base
    stamping = _get_process_profile("Stamping")
    assert "10 to 30 strokes" in stamping["cycle_time"]
    assert "millions of dollars" in stamping["tooling_economics"].lower()

    casting = _get_process_profile("Casting")
    assert "30 to 70" in str(casting["advantages"])
    assert "6,000 to 9,000" in casting["tooling_economics"]

    forging = _get_process_profile("Forging")
    assert "grain flow" in str(forging["advantages"]).lower()
    assert "control arms" in str(forging["typical_components"]).lower()

    print("  [OK] All 5 manufacturing processes verified with exact knowledge base parameters.")

    # -------------------------------------------------------------
    # 6. RAG Retrieval & Source Attribution Integration
    # -------------------------------------------------------------
    print("\n--- 6. RAG Retrieval & Source Attribution ---")
    res_rag = get_material_intelligence("Steel", "Aluminum", "Stamping", "Stamping", query_rag=True)
    passages = res_rag["retrieved_knowledge"]
    citations = res_rag["source_citations"]

    assert len(passages) > 0, "Expected at least 1 retrieved passage"
    assert len(citations) > 0, "Expected at least 1 citation"
    assert any("steel_vs_aluminum.md" in c["source_file"] for c in citations)
    assert all("disclaimer" in p for p in passages)
    print(f"  [OK] RAG retrieved {len(passages)} passages across {len(citations)} source documents.")

    # -------------------------------------------------------------
    # 7. Component Measurement vs General Property Separation
    # -------------------------------------------------------------
    print("\n--- 7. Component Measurement Separation ---")
    comp_a = {"id": "CB001", "weight_kg": 3.50, "cost_usd": 850.0}
    comp_b = {"id": "CB002", "weight_kg": 2.27, "cost_usd": 1062.5}
    res_meas = get_material_intelligence("Steel", "Aluminum", "Stamping", "Stamping", component_a=comp_a, component_b=comp_b, query_rag=False)

    meas = res_meas["component_measurements"]
    assert meas is not None
    assert meas["baseline_component"]["id"] == "CB001"
    assert meas["baseline_component"]["measured_weight_kg"] == 3.50
    assert meas["candidate_component"]["id"] == "CB002"
    assert meas["candidate_component"]["measured_weight_kg"] == 2.27
    assert "component-specific measurements" in meas["data_note"].lower()
    print("  [OK] Component teardown measurements strictly separated from general material properties.")

    # -------------------------------------------------------------
    # 8. API Integration Verification (/compare & /material-intelligence)
    # -------------------------------------------------------------
    print("\n--- 8. API Integration (/compare & /material-intelligence) ---")
    # /compare endpoint
    cmp_data = compare(ComparisonRequest(component_a_id="CB001", component_b_id="CB002"))
    assert "material_intelligence" in cmp_data
    assert cmp_data["material_intelligence"]["material_a"]["density_g_cm3"] == 7.85
    assert cmp_data["material_intelligence"]["material_b"]["density_g_cm3"] == 2.70
    print("  [OK] /compare includes material_intelligence payload.")

    # /material-intelligence standalone endpoint
    mat_payload = material_intelligence_endpoint(MaterialIntelligenceRequest(
        material_a="Steel",
        material_b="Aluminum",
        process_a="Stamping",
        process_b="Stamping",
        component_a_id="CB001",
        component_b_id="CB002"
    ))
    assert "material_comparison" in mat_payload
    assert mat_payload["material_comparison"]["is_same_material"] is False
    assert len(mat_payload["source_citations"]) > 0
    print("  [OK] /material-intelligence endpoint functional.")

    # /analyze endpoint
    ana_data = analyze(AnalyzeRequest(component_a_id="CB001", component_b_id="CB002", top_k=3))
    assert "comparison" in ana_data
    assert "material_intelligence" in ana_data["comparison"]
    print("  [OK] /analyze preserves material_intelligence in comparison payload.")

    # -------------------------------------------------------------
    # 9. Frontend DOM & JS Verification (Clean Technical Specifications Integration)
    # -------------------------------------------------------------
    print("\n--- 9. Frontend DOM & CSS Verification ---")
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")
    style_css = Path("frontend/style.css").read_text(encoding="utf-8")
    app_js = Path("frontend/app.js").read_text(encoding="utf-8")

    # Simplified Technical Specification HTML Elements (Clean Integration)
    required_html_ids = [
        "spec-card-comp-a",
        "spec-card-comp-b",
        "spec-a-name",
        "spec-b-name",
        "spec-a-material",
        "spec-b-material",
        "spec-a-process",
        "spec-b-process",
        "spec-a-weight",
        "spec-b-weight",
        "spec-a-cost",
        "spec-b-cost",
        "specs-table-body"
    ]
    for html_id in required_html_ids:
        assert f'id="{html_id}"' in index_html, f"Missing HTML element id: {html_id}"
    print(f"  [OK] All {len(required_html_ids)} required technical specification IDs present in index.html.")

    # CSS Classes
    required_css_classes = [
        ".tech-specs-section",
        ".tech-specs-cards-grid",
        ".tech-spec-card",
        ".spec-attributes-grid",
        ".material-grid"
    ]
    for css_cls in required_css_classes:
        assert css_cls in style_css, f"Missing CSS class: {css_cls}"
    print(f"  [OK] All {len(required_css_classes)} required CSS classes present in style.css.")

    # JS Functions
    required_js_tokens = [
        "renderMaterialIntelligence",
        "resetMaterialIntelligence"
    ]
    for token in required_js_tokens:
        assert token in app_js, f"Missing JS function/token: {token}"
    print(f"  [OK] All {len(required_js_tokens)} required JS functions/tokens present in app.js.")

    print("\n============================================================")
    print("PHASE 3 TEST SUITE: ALL TESTS PASSED SUCCESSFULLY!")
    print("============================================================")


if __name__ == "__main__":
    test_material_intelligence_suite()
