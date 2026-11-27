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

    print("\n=== TEST 4: Authentication Frontend Interface Verification ===")
    from main import login_page
    unauth_req = DummyRequest({})
    login_res = login_page(unauth_req)
    assert hasattr(login_res, "path"), "Expected FileResponse for GET /login"
    login_html = Path(login_res.path).read_text(encoding="utf-8")

    # 1. Sign In
    assert "id=\"signin-form\"" in login_html
    assert "id=\"signin-email\"" in login_html
    assert "id=\"signin-password\"" in login_html
    assert "id=\"btn-login\"" in login_html
    print("  [OK] Sign In form elements verified")

    # 2. Create Account
    assert "id=\"register-form\"" in login_html
    assert "id=\"register-name\"" in login_html
    assert "id=\"register-email\"" in login_html
    assert "id=\"register-password\"" in login_html
    assert "id=\"register-confirm-password\"" in login_html
    assert "id=\"btn-register\"" in login_html
    print("  [OK] Create Account form elements verified")

    # 3. Forgot Password
    assert "id=\"forgot-form\"" in login_html
    assert "id=\"forgot-email\"" in login_html
    assert "id=\"btn-forgot\"" in login_html
    print("  [OK] Forgot Password form elements verified")

    # 4. Reset Password & Email Verification
    assert "id=\"reset-form\"" in login_html
    assert "id=\"reset-token\"" in login_html
    assert "id=\"btn-reset\"" in login_html
    assert "id=\"verify-form\"" in login_html
    assert "id=\"verify-token\"" in login_html
    assert "id=\"btn-verify\"" in login_html
    assert "id=\"btn-resend\"" in login_html
    print("  [OK] Password reset & email verification interfaces verified")

    # 5. Security & Safe Storage Check
    assert "localStorage.setItem(\"token\"" not in login_html
    assert "sessionStorage.setItem(\"token\"" not in login_html
    assert "localStorage.setItem(\"password\"" not in login_html
    assert "sessionStorage.setItem(\"password\"" not in login_html
    print("  [OK] Confirmed zero session token or password exposure in frontend storage")

    print("\n=== ALL FRONTEND & BACKEND SERVER TESTS PASSED! ===")

if __name__ == "__main__":
    test_server()
