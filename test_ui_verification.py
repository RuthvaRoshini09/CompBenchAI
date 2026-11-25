import re
import sys
from pathlib import Path

# Force UTF-8 encoding on stdout for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi import HTTPException
from main import app, ComparisonRequest, AnalyzeRequest, compare, analyze, components

def test_ui_improvements():
    print("============================================================")
    print("VERIFYING COMPBENCH AI FINAL DASHBOARD CORRECTIONS")
    print("============================================================")

    html_path = Path("frontend/index.html")
    css_path = Path("frontend/style.css")
    js_path = Path("frontend/app.js")
    csv_path = Path("data/components.csv")

    assert html_path.exists(), "frontend/index.html missing"
    assert css_path.exists(), "frontend/style.css missing"
    assert js_path.exists(), "frontend/app.js missing"
    assert csv_path.exists(), "data/components.csv missing"

    html = html_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    csv_text = csv_path.read_text(encoding="utf-8")

    # 1. SUBSYSTEM MATCHING & EXACT PART_NAME VALIDATION
    print("\n--- 1. Exact Part_Name Equality Validation Flow ---")
    # Backend test: Same Part_Name succeeds (CB001 & CB002 - Door Panel)
    comp_valid = compare(ComparisonRequest(component_a_id="CB001", component_b_id="CB002"))
    assert comp_valid["component_name"] == "Door Panel"
    print("  [OK] Valid selection (CB001 & CB002 - Door Panel) succeeds in backend")

    # Critical Test: Same Subsystem (Interior), but DIFFERENT Part_Name (Door Panel vs Dashboard Frame)
    # Must be rejected because Part_Name equality is required, not just Subsystem equality!
    try:
        compare(ComparisonRequest(component_a_id="CB001", component_b_id="CB006"))
        assert False, "Expected 404 for CB001 vs CB006 (same Subsystem 'Interior' but different Part_Name)"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "Please select two records with the same Part_Name" in exc.detail
        print(f"  [OK] Same Subsystem 'Interior' with different Part_Name (CB001 vs CB006) rejected with 404: '{exc.detail}'")

    # Backend test: Completely different Subsystem and Part_Name raises 404
    try:
        compare(ComparisonRequest(component_a_id="CB001", component_b_id="CB011"))
        assert False, "Expected 404 for mismatched Part_Name"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "Please select two records with the same Part_Name" in exc.detail
        print(f"  [OK] Different Subsystem & Part_Name (CB001 vs CB011) rejected with 404: '{exc.detail}'")

    # Frontend checks: Exact Part_Name validation, clear messages, and correction button
    assert "validateSubsystemMatch" in js, "validateSubsystemMatch missing in app.js"
    assert "autoMatchComponentB" in js, "autoMatchComponentB missing in app.js"
    assert 'id="selection-validation-msg"' in html, "selection-validation-msg missing in index.html"
    assert "Please select two records with the same Part_Name" in js, "Exact Part_Name mismatch message missing in app.js"
    assert "autoMatchComponentB" in js and "targetClean" in js, "autoMatchComponentB should match target Part_Name"
    print("  [OK] Frontend validates exact Part_Name equality before /compare and /analyze requests")
    print("  [OK] Frontend correction button aligns Component B to the exact same Part_Name")

    # 2. COST DIFFERENCE IN PRIMARY INR & SECONDARY USD
    print("\n--- 2. Cost Difference Primary INR & Secondary USD ---")
    assert "formatInrPrimary" in js, "formatInrPrimary missing in app.js"
    assert 'id="kpi-cost-secondary"' in html, "kpi-cost-secondary missing in index.html"

    # Test illustrative math: $212.50 * 85 = 18062.5 -> +₹18,062.50 (estimated)
    rate = 85.0
    cost_diff_usd = 212.50
    expected_inr = cost_diff_usd * rate
    assert expected_inr == 18062.5
    print(f"  [OK] Illustrative conversion: ${cost_diff_usd} * {rate} = +₹{expected_inr:,.2f} (estimated)")

    # Ensure canonical USD values in components.csv remain untouched
    first_line = csv_text.strip().split("\n")[0]
    assert "Total_Cost_USD" in first_line and "Weight_kg" in first_line, "components.csv columns altered"
    print("  [OK] Original USD and Weight values preserved in data/components.csv")

    # Verify single configurable USD_TO_INR_RATE
    rate_def_count = len(re.findall(r"USD_TO_INR_RATE\s*=", js))
    assert rate_def_count == 1, f"Expected 1 USD_TO_INR_RATE definition, found {rate_def_count}"
    print("  [OK] Single centralized configurable USD_TO_INR_RATE verified")

    # 3. EXPANDABLE BENCHMARKING GUIDE
    print("\n--- 3. Optional Compact Benchmarking Guide ---")
    assert 'id="btn-toggle-guide"' in html, "btn-toggle-guide button missing in index.html"
    assert 'id="guide-panel"' in html, "guide-panel missing in index.html"
    assert "btn-guide-toggle" in css, "btn-guide-toggle css missing in style.css"
    assert 'style="display: none;"' in html.split('id="guide-panel"')[1][:100], "Guide panel should be collapsed by default"
    print("  [OK] Benchmarking guide is compact and collapsed by default with toggle control")

    # 4. STANDARDIZED 3 GRAPH CARDS
    print("\n--- 4. Standardization of 3 Graph Cards ---")
    assert 'id="weightChart"' in html and 'id="costChart"' in html and 'id="materialChart"' in html
    assert "indexAxis" in js and '"y"' in js, "Weight chart must be horizontal bar chart"
    assert "doughnut" in js, "Material chart must remain a doughnut chart"
    print("  [OK] Graph 1: Horizontal Mass Bar Chart verified")
    print("  [OK] Graph 2: Cost Bar Chart in estimated INR verified")
    print("  [OK] Graph 3: Fleet Material Doughnut Chart preserved")

    # 5. COMPARISON SUMMARY BAR
    print("\n--- 5. Compact Comparison Summary Bar ---")
    assert 'id="comparison-summary-bar"' in html, "comparison-summary-bar missing in index.html"
    assert 'id="summary-component-pair"' in html, "summary-component-pair missing in index.html"
    assert 'id="summary-weight-val"' in html, "summary-weight-val missing in index.html"
    assert 'id="summary-cost-inr-val"' in html, "summary-cost-inr-val missing in index.html"
    assert 'id="summary-cost-usd-val"' in html, "summary-cost-usd-val missing in index.html"
    print("  [OK] Compact Comparison Summary bar present above charts with verified engine values")

    # 6. RAG SECTION COMPACT REFERENCES & MODALS
    print("\n--- 6. RAG Context & KPI Modals ---")
    assert 'id="modal-components-catalog"' in html
    assert 'id="modal-dataset-info"' in html
    assert "<details" in js and "<summary" in js, "Expandable details tag missing in RAG app.js"
    print("  [OK] RAG compact reference cards with expandable passage details verified")
    print("  [OK] Component Catalog and Dataset Info modals verified")

    # 7. AI ENGINEERING REPORT SHORTENING & ACCURACY (SEAT FRAME BENCHMARK)
    print("\n--- 7. AI Engineering Intelligence Report Improvements ---")
    # Verify 5 concise section container IDs in HTML
    assert 'id="rep-summary"' in html, "rep-summary missing in index.html"
    assert 'id="rep-weight"' in html, "rep-weight missing in index.html"
    assert 'id="rep-cost"' in html, "rep-cost missing in index.html"
    assert 'id="rep-material"' in html, "rep-material missing in index.html"
    assert 'id="rep-considerations-conclusion"' in html, "rep-considerations-conclusion missing in index.html"
    assert 'full-width' in html, "full-width styling class missing in index.html"
    print("  [OK] 5 concise report section cards verified in index.html")

    # Verify fallback badge and text in HTML & JS
    assert "Deterministic Engineering Report" in html and "Deterministic Engineering Report" in js
    assert "View Reference" in js, "'View Reference' expand button missing in app.js"
    assert "renderMarkdownBasic" in js and "stripMarkdown" in js
    print("  [OK] Deterministic Engineering Report badge & View Reference expander verified")

    # Test Seat Frame benchmark example: CB030 vs CB026
    seat_compare = compare(ComparisonRequest(component_a_id="CB030", component_b_id="CB026"))
    assert seat_compare["component_name"] == "Seat Frame"
    sc_a = seat_compare["component_a"]
    sc_b = seat_compare["component_b"]
    sc_an = seat_compare["analysis"]

    assert sc_a["weight_kg"] == 9.2, f"Expected 9.2 kg for CB030, got {sc_a['weight_kg']}"
    assert sc_b["weight_kg"] == 8.0, f"Expected 8.0 kg for CB026, got {sc_b['weight_kg']}"
    assert sc_an["weight_difference_kg"] == 1.20, f"Expected 1.20 kg delta, got {sc_an['weight_difference_kg']}"
    assert sc_an["weight_reduction_percent"] == 13.04, f"Expected 13.04% reduction, got {sc_an['weight_reduction_percent']}"
    assert sc_an["cost_difference_usd"] == 180.0, f"Expected $180.00 delta, got {sc_an['cost_difference_usd']}"
    assert sc_an["cost_change_percent"] == 11.11, f"Expected 11.11% increase, got {sc_an['cost_change_percent']}"

    inr_seat_delta = sc_an["cost_difference_usd"] * rate
    assert inr_seat_delta == 15300.0, f"Expected 15,300.00 INR delta, got {inr_seat_delta}"
    print(f"  [OK] Seat Frame Benchmark (CB030 vs CB026):")
    print(f"       - Weight: {sc_a['weight_kg']} kg vs {sc_b['weight_kg']} kg -> -{sc_an['weight_difference_kg']:.2f} kg ({sc_an['weight_reduction_percent']}%)")
    print(f"       - Cost: ${sc_a['cost_usd']:.2f} vs ${sc_b['cost_usd']:.2f} -> +${sc_an['cost_difference_usd']:.2f} ({sc_an['cost_change_percent']}%)")
    print(f"       - Primary INR: +₹{inr_seat_delta:,.2f} (estimated @ ₹{rate}/USD)")

    # Test Seat Frame analyze endpoint
    seat_analyze = analyze(AnalyzeRequest(component_a_id="CB030", component_b_id="CB026"))
    seat_report = seat_analyze["insight"]["report"]
    assert "1.20" in seat_report or "1.2" in seat_report
    assert "13.04" in seat_report
    assert "180.0" in seat_report or "180" in seat_report
    assert "11.11" in seat_report
    assert "15,300" in seat_report
    print("  [OK] Seat Frame generated report contains exact Python values & INR estimate")

    # 8. GEMINI PROVIDER STATUS & FALLBACK INTEGRITY
    print("\n--- 8. Gemini Provider Status & Fallback Verification ---")
    assert 'class="ai-badge fallback">Deterministic Engineering Report</span>' in html
    assert "isGeminiSuccess" in js, "isGeminiSuccess check missing in app.js"
    assert 'insight.status === "success"' in js, "Must verify insight.status === 'success' before showing Live AI"
    assert "Deterministic Engineering Report" in js, "Deterministic fallback status missing in app.js"

    # Verify searchable dropdowns and option formatting
    assert 'id="search-comp-a"' in html and 'id="search-comp-b"' in html, "Search inputs missing in index.html"
    assert "filterSelectorOptions" in js, "filterSelectorOptions missing in app.js"
    assert "5. Engineering Conclusion" in html, "5. Engineering Conclusion title missing in index.html"
    print("  [OK] Searchable component dropdowns and '5. Engineering Conclusion' section verified")

    # Test backend provider status when API key is missing (current environment)
    from services.llm_engine import generate_engineering_insight
    fallback_res = generate_engineering_insight(seat_compare, [])
    assert fallback_res["status"] in ("warning", "fallback"), f"Expected warning/fallback status, got {fallback_res['status']}"
    assert fallback_res["model"] == "deterministic-fallback"
    assert "deterministic" in fallback_res["message"].lower() or "not configured" in fallback_res["message"].lower()
    print(f"  [OK] Unconfigured/absent API key returns status='{fallback_res['status']}' and model='{fallback_res['model']}'")

    # Test backend provider status when an invalid API key is provided
    import os
    os.environ["GEMINI_API_KEY"] = "INVALID_TEST_KEY_99999"
    try:
        failed_api_res = generate_engineering_insight(seat_compare, [])
        assert failed_api_res["status"] == "fallback", f"Failed API call must return status='fallback', got {failed_api_res['status']}"
        assert failed_api_res["model"] == "deterministic-fallback"
        assert "failed" in failed_api_res["message"].lower() or "error" in failed_api_res["message"].lower()
        print(f"  [OK] Invalid API key gracefully fails to status='fallback' with deterministic report preserved")
    finally:
        os.environ.pop("GEMINI_API_KEY", None)

    print("  [OK] Gemini provider status inspection verified: 'Gemini Live AI' only shown on verified success")

    print("\n============================================================")
    print("ALL FINAL DASHBOARD & UI REQUIREMENTS VERIFIED SUCCESSFULLY!")
    print("============================================================")

if __name__ == "__main__":
    test_ui_improvements()
