"""
tests/api/test_api.py
Integration tests for the FastAPI REST API (src/api/main.py).
Uses httpx TestClient (or requests with a running server).
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

# Use TestClient for synchronous testing
try:
    from fastapi.testclient import TestClient
    from src.api.main import app
    CLIENT_AVAILABLE = True
except Exception:
    CLIENT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not CLIENT_AVAILABLE,
    reason="FastAPI / testclient not available"
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
class TestHealth:
    def test_root_returns_ok(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


# ---------------------------------------------------------------------------
# /companies
# ---------------------------------------------------------------------------
class TestCompanies:
    def test_list_companies_200(self, client):
        resp = client.get("/companies")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_companies_have_expected_keys(self, client):
        resp = client.get("/companies")
        data = resp.json()
        if data:
            row = data[0]
            for key in ["id", "name", "ticker", "sector"]:
                assert key in row, f"Missing key: {key}"

    def test_sector_filter(self, client):
        # Get the first sector from the list
        resp = client.get("/companies")
        all_data = resp.json()
        if not all_data:
            pytest.skip("No companies in DB")
        sector = all_data[0].get("sector")
        if not sector:
            pytest.skip("No sector data")
        resp2 = client.get(f"/companies?sector={sector}")
        assert resp2.status_code == 200
        filtered = resp2.json()
        assert all(r["sector"] == sector for r in filtered)


# ---------------------------------------------------------------------------
# /companies/{ticker}
# ---------------------------------------------------------------------------
class TestCompanyProfile:
    def test_valid_ticker(self, client):
        resp = client.get("/companies")
        all_data = resp.json()
        if not all_data:
            pytest.skip("No companies in DB")
        ticker = all_data[0]["ticker"]
        resp2 = client.get(f"/companies/{ticker}")
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["ticker"] == ticker
        assert "latest_kpis" in data

    def test_invalid_ticker_404(self, client):
        resp = client.get("/companies/XXXXXXXXXX")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /sectors
# ---------------------------------------------------------------------------
class TestSectors:
    def test_sectors_200(self, client):
        resp = client.get("/sectors")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_sectors_have_aggregates(self, client):
        resp = client.get("/sectors")
        data = resp.json()
        if data:
            row = data[0]
            assert "sector" in row
            assert "company_count" in row


# ---------------------------------------------------------------------------
# /search
# ---------------------------------------------------------------------------
class TestSearch:
    def test_search_short_query_422(self, client):
        resp = client.get("/search?q=a")
        # min_length=2 so single char should return validation error
        assert resp.status_code == 422

    def test_search_returns_list(self, client):
        resp = client.get("/search?q=ta")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_search_empty_list_for_garbage(self, client):
        resp = client.get("/search?q=XYZXYZXYZ999")
        assert resp.status_code == 200
        assert resp.json() == []
