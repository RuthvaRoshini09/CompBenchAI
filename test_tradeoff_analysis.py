import sys
from pathlib import Path
from fastapi import HTTPException
from main import app, ComparisonRequest, compare_components, compute_tradeoff_analysis, compare

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_tradeoff_suite():
    print("============================================================")
    print("PHASE 2: ENGINEERING TRADE-OFF ANALYSIS & DECISION TESTS")
    print("============================================================")

    # 1. Scenario A: Lighter candidate with higher cost (CB001 vs CB002 Door Panel)
    print("\n--- 1. Lighter candidate with higher cost (Scenario A) ---")
    res_a = compute_tradeoff_analysis(
        weight_a=3.50,
        weight_b=2.27,
        cost_a=850.00,
        cost_b=1062.50,
        id_a="CB001",
        id_b="CB002",
        rate=85.0
    )
    assert res_a["is_lighter"] is True
    assert res_a["weight_status"] == "lighter"
    assert res_a["weight_difference_kg"] == 1.23
    assert res_a["weight_change_pct"] == 35.14
    assert res_a["is_cheaper"] is False
    assert res_a["cost_status"] == "more_expensive"
    assert res_a["additional_cost_usd"] == 212.50
    assert res_a["additional_cost_inr"] == 18062.50
    assert res_a["cost_change_pct"] == 25.00
    assert res_a["cost_per_kg_saved_applicable"] is True
    assert res_a["cost_per_kg_saved_usd"] == 172.76
    assert res_a["cost_per_kg_saved_inr"] == 14684.60
    assert res_a["cost_per_kg_type"] == "investment"
    assert res_a["decision"]["scenario_id"] == "A"
    assert "classic" in res_a["decision"]["summary_text"].lower() or "trade-off" in res_a["decision"]["summary_text"].lower()
    print("  [OK] Scenario A verified: 1.23 kg saved, $212.50 (+₹18,062.50) cost, $172.76/kg saved")

    # 2. Scenario B: Lighter candidate with lower cost (Dual Benefit)
    print("\n--- 2. Lighter candidate with lower cost (Scenario B) ---")
    res_b = compute_tradeoff_analysis(
        weight_a=5.00,
        weight_b=4.00,
        cost_a=500.00,
        cost_b=400.00,
        id_a="BASE",
        id_b="CAND",
        rate=85.0
    )
    assert res_b["is_lighter"] is True
    assert res_b["weight_status"] == "lighter"
    assert res_b["weight_difference_kg"] == 1.00
    assert res_b["is_cheaper"] is True
    assert res_b["cost_status"] == "cheaper"
    assert res_b["additional_cost_usd"] == -100.00
    assert res_b["additional_cost_inr"] == -8500.00
    assert res_b["cost_per_kg_saved_applicable"] is True
    assert res_b["cost_per_kg_type"] == "savings"
    assert res_b["cost_per_kg_saved_usd"] == 100.00
    assert res_b["cost_per_kg_saved_inr"] == 8500.00
    assert "saving" in res_b["cost_per_kg_reason"].lower()
    assert res_b["decision"]["scenario_id"] == "B"
    assert res_b["decision"]["recommendation_type"] == "favorable"
    print("  [OK] Scenario B verified: Dual benefit of weight saving (1.0 kg) and cost reduction ($100), $100/kg saved")

    # 3. Scenario C: Heavier candidate with lower cost (Economic Trade-off, CB002 vs CB001)
    print("\n--- 3. Heavier candidate with lower cost (Scenario C) ---")
    res_c = compute_tradeoff_analysis(
        weight_a=2.27,
        weight_b=3.50,
        cost_a=1062.50,
        cost_b=850.00,
        id_a="CB002",
        id_b="CB001",
        rate=85.0
    )
    assert res_c["is_lighter"] is False
    assert res_c["weight_status"] == "heavier"
    assert res_c["weight_difference_kg"] == -1.23
    assert res_c["is_cheaper"] is True
    assert res_c["cost_status"] == "cheaper"
    assert res_c["additional_cost_usd"] == -212.50
    assert res_c["cost_per_kg_saved_applicable"] is False
    assert res_c["cost_per_kg_status"] == "not_applicable_heavier"
    assert "not applicable – candidate weight increased" in res_c["cost_per_kg_reason"].lower()
    assert res_c["decision"]["scenario_id"] == "C"
    print("  [OK] Scenario C verified: Heavier (+1.23 kg), cost saving ($212.50), Cost/kg is Not Applicable")

    # 4. Scenario D: Heavier candidate with higher cost (Dual Penalty)
    print("\n--- 4. Heavier candidate with higher cost (Scenario D) ---")
    res_d = compute_tradeoff_analysis(
        weight_a=4.00,
        weight_b=5.00,
        cost_a=400.00,
        cost_b=550.00,
        id_a="BASE_D",
        id_b="CAND_D",
        rate=85.0
    )
    assert res_d["is_lighter"] is False
    assert res_d["weight_status"] == "heavier"
    assert res_d["is_cheaper"] is False
    assert res_d["cost_status"] == "more_expensive"
    assert res_d["cost_per_kg_saved_applicable"] is False
    assert res_d["cost_per_kg_status"] == "not_applicable_heavier"
    assert res_d["decision"]["scenario_id"] == "D"
    # Ensure it does not declare inferior without non-tabulated engineering evidence
    assert "inferior without" in res_d["decision"]["summary_text"].lower() or "functional" in res_d["decision"]["summary_text"].lower()
    print("  [OK] Scenario D verified: Weight increased, cost increased, not declared inferior without functional criteria")

    # 5. Equal component weights
    print("\n--- 5. Equal component weights ---")
    res_eq_w = compute_tradeoff_analysis(
        weight_a=5.00,
        weight_b=5.00,
        cost_a=500.00,
        cost_b=600.00,
        id_a="EQ_W_A",
        id_b="EQ_W_B"
    )
    assert res_eq_w["weight_status"] == "equal"
    assert res_eq_w["weight_difference_kg"] == 0.00
    assert res_eq_w["cost_per_kg_saved_applicable"] is False
    assert res_eq_w["cost_per_kg_status"] == "not_applicable_equal"
    assert "not applicable – no weight reduction" in res_eq_w["cost_per_kg_reason"].lower()
    assert res_eq_w["decision"]["scenario_id"] == "E2"
    print("  [OK] Equal weights verified: Cost/kg is Not Applicable (no weight reduction)")

    # 6. Equal component costs
    print("\n--- 6. Equal component costs ---")
    res_eq_c = compute_tradeoff_analysis(
        weight_a=6.00,
        weight_b=5.00,
        cost_a=500.00,
        cost_b=500.00,
        id_a="EQ_C_A",
        id_b="EQ_C_B"
    )
    assert res_eq_c["cost_status"] == "equal"
    assert res_eq_c["additional_cost_usd"] == 0.00
    assert res_eq_c["cost_per_kg_saved_applicable"] is True
    assert res_eq_c["cost_per_kg_saved_usd"] == 0.00
    assert res_eq_c["cost_per_kg_usd"] == 0.00
    assert res_eq_c["cost_per_kg_type"] == "neutral"
    assert res_eq_c["decision"]["scenario_id"] == "E3a"
    print("  [OK] Equal costs verified: $0.00/kg saved at cost parity")

    # 7. Zero baseline weight
    print("\n--- 7. Zero baseline weight ---")
    res_zero_w = compute_tradeoff_analysis(
        weight_a=0.00,
        weight_b=4.50,
        cost_a=500.00,
        cost_b=600.00
    )
    assert res_zero_w["decision"]["scenario_id"] == "E4"
    assert res_zero_w["decision"]["recommendation_type"] == "warning"
    print("  [OK] Zero baseline weight handled safely without ZeroDivisionError")

    # 8. Zero baseline cost
    print("\n--- 8. Zero baseline cost ---")
    res_zero_c = compute_tradeoff_analysis(
        weight_a=4.50,
        weight_b=3.50,
        cost_a=0.00,
        cost_b=500.00
    )
    assert res_zero_c["decision"]["scenario_id"] == "E4"
    print("  [OK] Zero baseline cost handled safely without ZeroDivisionError")

    # 9. Missing or invalid numeric data
    print("\n--- 9. Missing or invalid numeric data ---")
    res_invalid = compute_tradeoff_analysis(
        weight_a="invalid_str",
        weight_b=None,
        cost_a="NaN",
        cost_b=400.00
    )
    assert res_invalid["decision"]["scenario_id"] == "E4"
    assert res_invalid["weight_difference_kg"] == 0.0
    print("  [OK] Missing/invalid numeric data handled gracefully with fallback")

    # 10. Correct USD-to-INR conversion
    print("\n--- 10. USD-to-INR Conversion Accuracy ---")
    usd_val = 150.00
    rate = 85.0
    res_conv = compute_tradeoff_analysis(
        weight_a=5.00,
        weight_b=4.00,
        cost_a=500.00,
        cost_b=650.00,
        rate=rate
    )
    assert res_conv["additional_cost_usd"] == 150.00
    assert res_conv["additional_cost_inr"] == 150.00 * 85.0
    assert res_conv["cost_per_kg_saved_usd"] == 150.00
    assert res_conv["cost_per_kg_saved_inr"] == 12750.00
    print(f"  [OK] USD-to-INR verified: $150.00 * 85.0 = ₹{150.00 * 85.0:,.2f}")

    # 11. Cost per kg saved only calculated when applicable
    print("\n--- 11. Cost per kg applicability rules ---")
    # Case 1: Lighter -> Applicable
    c1 = compute_tradeoff_analysis(3.0, 2.0, 100, 200)
    assert c1["cost_per_kg_saved_applicable"] is True
    # Case 2: Heavier -> Inapplicable
    c2 = compute_tradeoff_analysis(2.0, 3.0, 100, 200)
    assert c2["cost_per_kg_saved_applicable"] is False
    assert c2["cost_per_kg_usd"] is None
    # Case 3: Equal -> Inapplicable
    c3 = compute_tradeoff_analysis(2.0, 2.0, 100, 200)
    assert c3["cost_per_kg_saved_applicable"] is False
    assert c3["cost_per_kg_usd"] is None
    print("  [OK] Cost per kg saved strictly applicable ONLY when weight is saved")

    # 12. Full Integration via /compare and /analyze
    print("\n--- 12. Full Integration via compare_components (CB030 vs CB026 Seat Frame) ---")
    seat_res = compare_components("CB030", "CB026")
    assert "tradeoff_analysis" in seat_res, "tradeoff_analysis key missing in compare_components"
    assert "tradeoff_analysis" in seat_res["analysis"], "tradeoff_analysis missing in analysis dict"
    seat_to = seat_res["tradeoff_analysis"]
    assert seat_to["baseline_weight_kg"] == 9.20
    assert seat_to["candidate_weight_kg"] == 8.00
    assert seat_to["weight_difference_kg"] == 1.20
    assert seat_to["weight_status"] == "lighter"
    assert seat_to["additional_cost_usd"] == 180.00
    assert seat_to["additional_cost_inr"] == 15300.00
    assert seat_to["cost_per_kg_saved_usd"] == 150.00
    assert seat_to["cost_per_kg_saved_inr"] == 12750.00
    assert seat_to["decision"]["scenario_id"] == "A"
    print(f"  [OK] Seat Frame Benchmark (CB030 vs CB026):")
    print(f"       Weight: 9.2 kg vs 8.0 kg -> {seat_to['weight_difference_kg']} kg saved ({seat_to['weight_change_pct']}%)")
    print(f"       Cost: $1620 vs $1800 -> +${seat_to['additional_cost_usd']} (+₹{seat_to['additional_cost_inr']:,.2f})")
    print(f"       Lightweighting: ${seat_to['cost_per_kg_saved_usd']}/kg (₹{seat_to['cost_per_kg_saved_inr']:,.2f}/kg saved)")

    # 13. Frontend UI Elements & Bindings Verification (Simplified Engineering Decision Summary)
    print("\n--- 13. Frontend UI Elements & Bindings Verification ---")
    html_text = Path("frontend/index.html").read_text(encoding="utf-8")
    css_text = Path("frontend/style.css").read_text(encoding="utf-8")
    js_text = Path("frontend/app.js").read_text(encoding="utf-8")

    assert 'id="tradeoff-decision-panel"' in html_text, "tradeoff-decision-panel missing in index.html"
    assert 'id="decision-scenario-name"' in html_text, "decision-scenario-name missing in index.html"
    assert 'id="decision-verdict-badge"' in html_text, "decision-verdict-badge missing in index.html"
    assert 'id="decision-summary-text"' in html_text, "decision-summary-text missing in index.html"

    assert "renderTradeoffAnalysis" in js_text, "renderTradeoffAnalysis missing in app.js"
    assert "resetTradeoffAnalysis" in js_text, "resetTradeoffAnalysis missing in app.js"
    assert "tradeoff-decision-panel" in css_text, "tradeoff-decision-panel missing in style.css"
    assert "decision-verdict-badge" in css_text, "decision-verdict-badge missing in style.css"

    print("  [OK] Frontend Simplified Engineering Decision Summary, CSS rules, and JS renderers verified")

    print("\n============================================================")
    print("ALL 15 PHASE 2 TRADE-OFF REQUIREMENTS VERIFIED SUCCESSFULLY!")
    print("============================================================")


if __name__ == "__main__":
    test_tradeoff_suite()
