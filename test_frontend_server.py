from pathlib import Path
from main import app, ComparisonRequest, KnowledgeQueryRequest, AnalyzeRequest, components, compare, analyze, home, dashboard
from starlette.datastructures import Headers

class DummyRequest:
    def __init__(self, headers_dict):
        self.headers = headers_dict

def test_server():
    print("=== TEST 1: Frontend Serving via GET / and GET /dashboard ===")
    # 1. Browser request to /
    browser_req = DummyRequest({"accept": "text/html,application/xhtml+xml"})
    browser_res = home(browser_req)
    assert hasattr(browser_res, "path"), "Expected FileResponse for browser request to /"
    html_content = Path(browser_res.path).read_text(encoding="utf-8")
    assert "COMPBENCH AI" in html_content
    assert "Automotive Component Benchmarking" in html_content
    print("  [OK] GET / serves index.html to browsers")

    # 2. JSON request to /
    json_req = DummyRequest({"accept": "application/json"})
    json_res = home(json_req)
    assert json_res["status"] == "Running"
    print("  [OK] GET / serves JSON status to API clients")

    # 3. GET /dashboard
    dash_res = dashboard()
    assert hasattr(dash_res, "path"), "Expected FileResponse for /dashboard"
    print("  [OK] GET /dashboard serves index.html")

    print("\n=== TEST 2: Static Assets Verification ===")
    css_file = Path("frontend/style.css")
    js_file = Path("frontend/app.js")
    assert css_file.exists() and css_file.stat().st_size > 500
    assert js_file.exists() and js_file.stat().st_size > 500
    print(f"  [OK] style.css verified ({css_file.stat().st_size} bytes)")
    print(f"  [OK] app.js verified ({js_file.stat().st_size} bytes)")

    print("\n=== TEST 3: Existing Backend Endpoints Preservation ===")
    comps = components()
    assert len(comps) == 50
    print(f"  [OK] GET /components: {len(comps)} records")

    comp_res = compare(ComparisonRequest(component_a_id="CB001", component_b_id="CB002"))
    assert comp_res["analysis"]["weight_difference_kg"] == 1.23
    assert comp_res["analysis"]["weight_reduction_percent"] == 35.14
    assert comp_res["analysis"]["cost_difference_usd"] == 212.50
    assert comp_res["analysis"]["cost_change_percent"] == 25.0
    print("  [OK] POST /compare calculations verified (1.23kg, 35.14%, $212.50, 25.0%)")

    analyze_res = analyze(AnalyzeRequest(component_a_id="CB001", component_b_id="CB002"))
    assert "comparison" in analyze_res
    assert "retrieved_knowledge" in analyze_res
    assert "insight" in analyze_res
    print("  [OK] POST /analyze full pipeline verified")

    print("\n=== ALL FRONTEND & BACKEND SERVER TESTS PASSED! ===")

if __name__ == "__main__":
    test_server()
