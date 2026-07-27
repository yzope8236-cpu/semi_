import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app
import apps.api.app.analytics as analytics

client = TestClient(app)

def test_unknown_wafer_returns_404(monkeypatch):
    monkeypatch.setattr(analytics, "rows", lambda *args, **kwargs: [])
    response = client.get('/api/v1/analytics/wafers/fake-wafer-123/summary')
    assert response.status_code == 404

    response = client.get('/api/v1/analytics/wafers/fake-wafer-123/tests')
    assert response.status_code == 404

    response = client.get('/api/v1/analytics/wafers/fake-wafer-123/sites')
    assert response.status_code == 404

    response = client.get('/api/v1/analytics/wafers/fake-wafer-123/retests')
    assert response.status_code == 404

def test_invalid_comparison_returns_400():
    # Same wafer
    response = client.get('/api/v1/analytics/wafer-comparison?left=WAF-1&right=WAF-1')
    assert response.status_code == 400

    # Missing params
    response = client.get('/api/v1/analytics/wafer-comparison?left=WAF-1')
    assert response.status_code == 422 # FastAPI handles missing query param

def test_comparison_unknown_wafer_returns_404(monkeypatch):
    monkeypatch.setattr(analytics, "rows", lambda *args, **kwargs: [])
    # Valid params but unknown wafer
    response = client.get('/api/v1/analytics/wafer-comparison?left=fake1&right=fake2')
    assert response.status_code == 404

def test_queries_use_all_observations(monkeypatch):
    queries = []
    def fake_rows(query, params=None):
        queries.append(query)
        q = query.lower()
        if "from wafers" in q:
            return [{"wafer_id": "W1", "lot_id": "L1"}]
        if "sum(passed) pass_count" in q:
            return [{"total_dies": 1, "pass_count": 1, "fail_count": 0, "yield_pct": 100.0, "dppm": 0, "retest_count": 0, "retest_rate_pct": 0.0}]
        if "group by hardware_bin" in q:
            return [{"bin": 1, "count": 1}]
        if "group by software_bin" in q:
            return [{"bin": 1, "count": 1}]
        if "select site, count() count" in q:
            return [{"site": 1, "count": 1}]
        if "edge_failed" in q:
            return [{"failed": 0, "edge_failed": 0}]
        if "top_failing_tests" in q or "failure_rate" in q:
            return [{"test_num": 1, "test_name": "T1", "observations": 1, "failures": 1, "failure_rate": 100.0}]
        return []
    
    import apps.api.app.analytics as analytics
    monkeypatch.setattr(analytics, "rows", fake_rows)
    client.get('/api/v1/analytics/wafers/W1/summary')
    client.get('/api/v1/analytics/conclusions')
    
    test_queries = [q for q in queries if "failure_rate" in q.lower() and "t.test_name" in q.lower()]
    assert len(test_queries) > 0, "No test queries captured"
    for q in test_queries:
        assert "*100/count()" in q.lower(), "Must use total count as denominator"
        assert "having failures > 0" in q.lower() or "having sum(t.passed=0) > 0" in q.lower(), "Must filter after aggregation"
        lower_q = q.lower()
        assert "where" in lower_q, "Query must have a WHERE clause"
        where_clause = lower_q.split("where", 1)[1].split("group by", 1)[0]
        assert "t.passed=0" not in where_clause, "Do not filter out passing tests in WHERE clause"
        assert "passed = 0" not in where_clause, "Do not filter out passing tests in WHERE clause"

def test_conclusions_logic(monkeypatch):
    def mock_rows(query, params=None):
        query = query.lower()
        if "group by wafer_id, lot_id" in query:
            return [{'wafer_id': 'W1', 'lot_id': 'L1', 'devices': 100, 'yield_pct': 85.0}]
        if "select x_coord, y_coord, passed" in query:
            return [
                {'x_coord': 0, 'y_coord': 0, 'passed': 0},
                {'x_coord': 9, 'y_coord': 0, 'passed': 0},
                {'x_coord': 5, 'y_coord': 5, 'passed': 1},
            ]
        if "select t.test_name, count() observations" in query:
            return [
                {'test_name': 'IDDQ', 'observations': 100, 'failures': 20, 'failure_rate': 20.0},
                {'test_name': 'VTH', 'observations': 100, 'failures': 15, 'failure_rate': 15.0},
                {'test_name': 'NOISE', 'observations': 2, 'failures': 2, 'failure_rate': 100.0} # Too few obs
            ]
        if "select site, count() dies" in query:
            return [
                {'site': 1, 'dies': 50, 'yield_pct': 90.0},
                {'site': 2, 'dies': 50, 'yield_pct': 50.0}
            ]
        if "first_pass" in query:
            return [{'devices': 10, 'first_pass': 0, 'final_pass': 1}]
        return []
    
    monkeypatch.setattr(analytics, "rows", mock_rows)
    response = client.get('/api/v1/analytics/conclusions')
    assert response.status_code == 200
    data = response.json()
    
    # max 1 yield, 1 spatial, 1 test, 1 site, 1 retest
    assert len(data) == 5
    
    categories = [c['category'] for c in data]
    assert categories.count('test') == 1, "Should be at most 1 test conclusion"
    
    test_c = next(c for c in data if c['category'] == 'test')
    assert test_c['title'] == 'High Impact Test: IDDQ', "Highest failure rate meeting threshold should be selected"
    
    for c in data:
        assert c['evidence'].strip() != "", "Evidence must not be empty"

def test_site_imbalance_one_site(monkeypatch):
    def fake_rows(query, params=None):
        query = query.lower()
        if "group by wafer_id, lot_id" in query:
            return [{'wafer_id': 'W1', 'lot_id': 'L1', 'devices': 100, 'yield_pct': 99.0}]
        if "select site, count() dies" in query:
            return [{'site': 1, 'dies': 100, 'yield_pct': 99.0}] # only 1 site
        if "edge_failed" in query:
            return [{'failed': 0, 'edge_failed': 0}]
        if "select t.test_name, count() observations" in query:
            return []
        return []
    
    import apps.api.app.analytics as analytics
    monkeypatch.setattr(analytics, "rows", fake_rows)
    response = client.get('/api/v1/analytics/conclusions')
    data = response.json()
    assert not any(c['category'] == 'site' for c in data), "Should not emit site imbalance for 1 site"
