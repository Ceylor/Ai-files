"""Integration tests for src/api/main.py – all API endpoints."""

import time
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def _uid(prefix="t"):
    """Generate a unique name to avoid collisions with leftover DB data."""
    return f"{prefix}_{int(time.time() * 1000) % 1_000_000}"


# ==============================================================================
# Categories CRUD
# ==============================================================================
class TestCategoriesAPI:
    """Tests for /api/categories endpoints."""

    def test_create_category(self):
        name = _uid("cat")
        resp = client.post("/api/categories", data={"name": name})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == name
        assert "id" in data

    def test_list_categories(self):
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        assert "categories" in resp.json()

    def test_get_category(self):
        name = _uid("getc")
        create = client.post("/api/categories", data={"name": name})
        cat_id = create.json()["id"]
        resp = client.get(f"/api/categories/{cat_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == name

    def test_get_category_not_found(self):
        resp = client.get("/api/categories/99999")
        assert resp.status_code == 404

    def test_update_category(self):
        name = _uid("updc")
        create = client.post("/api/categories", data={"name": name})
        cat_id = create.json()["id"]
        new_name = _uid("renamed")
        resp = client.put(f"/api/categories/{cat_id}", data={"name": new_name})
        assert resp.status_code == 200
        assert resp.json()["name"] == new_name

    def test_delete_category(self):
        name = _uid("delc")
        create = client.post("/api/categories", data={"name": name})
        cat_id = create.json()["id"]
        resp = client.delete(f"/api/categories/{cat_id}")
        assert resp.status_code == 200
        resp2 = client.get(f"/api/categories/{cat_id}")
        assert resp2.status_code == 404

    def test_delete_category_not_found(self):
        resp = client.delete("/api/categories/99999")
        assert resp.status_code == 404


# ==============================================================================
# Videos CRUD
# ==============================================================================
class TestVideosAPI:
    """Tests for /api/videos endpoints."""

    def test_list_videos(self):
        resp = client.get("/api/videos")
        assert resp.status_code == 200
        assert "videos" in resp.json()

    def test_get_video_not_found(self):
        resp = client.get("/api/videos/99999")
        assert resp.status_code == 404

    def test_delete_video_not_found(self):
        resp = client.delete("/api/videos/99999")
        assert resp.status_code == 404


# ==============================================================================
# Batch Processing
# ==============================================================================
class TestBatchAPI:
    """Tests for /api/batch/* endpoints."""

    def test_batch_list(self):
        resp = client.get("/api/batch/list")
        assert resp.status_code == 200
        assert "tasks" in resp.json()

    def test_batch_status_not_found(self):
        resp = client.get("/api/batch/status/99999")
        assert resp.status_code == 404

    def test_batch_results_not_found(self):
        resp = client.get("/api/batch/results/99999")
        assert resp.status_code == 404

    def test_batch_process_not_found(self):
        resp = client.post("/api/batch/process/99999")
        assert resp.status_code == 404

    def test_batch_upload_folder_not_found(self):
        resp = client.post("/api/batch/upload_folder", data={"folder_path": "/nonexistent/path"})
        assert resp.status_code == 404

    def test_batch_download_links_empty(self):
        # Empty string body gives 422 (required field not properly filled)
        resp = client.post("/api/batch/download_links", data={"links": ""})
        assert resp.status_code == 422


# ==============================================================================
# Learning
# ==============================================================================
class TestLearningAPI:
    """Tests for /api/learning/* endpoints."""

    def test_learning_status(self):
        resp = client.get("/api/learning/status")
        assert resp.status_code == 200

    def test_learning_categories(self):
        resp = client.get("/api/learning/categories")
        assert resp.status_code == 200
        assert "categories" in resp.json()

    def test_learning_profile_not_found(self):
        resp = client.get("/api/learning/profile/nonexistent_category_xyz")
        assert resp.status_code == 404


# ==============================================================================
# Analysis
# ==============================================================================
class TestAnalysisAPI:
    """Tests for /api/analysis/* endpoints."""

    def test_analyze_video_not_found(self):
        resp = client.post("/api/analysis/analyze/99999")
        assert resp.status_code == 404

    def test_get_analysis_not_found(self):
        resp = client.get("/api/analysis/99999")
        assert resp.status_code == 404

    def test_get_embeddings(self):
        resp = client.get("/api/analysis/1/embeddings")
        assert resp.status_code == 200


# ==============================================================================
# Status
# ==============================================================================
class TestStatusAPI:
    """Tests for /api/status endpoint."""

    def test_status(self):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["version"] == "2.0"
