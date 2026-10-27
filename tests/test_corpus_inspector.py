"""Tests for Corpus & PDF Chunk Inspector endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_corpus_overview_labour(client):
    response = client.get("/api/corpus/overview?corpus=labour")
    assert response.status_code == 200
    data = response.json()
    assert data["corpus"] == "labour"
    assert data["collection_id"] == "labour_vi_v1"
    assert data["total_documents"] == 10
    assert data["total_chunks"] == 458
    assert data["total_characters"] > 400000

    docs = data["documents"]
    assert len(docs) == 10
    bll = next((d for d in docs if d["doc_code"] == "BLLD2019"), None)
    assert bll is not None
    assert bll["pdf_available"] is True
    assert bll["pdf_filename"] == "bll2019-congbao.pdf"
    assert bll["chunk_count"] == 220
    assert bll["pages"] == 93
    assert bll["document_number"] == "45/2019/QH14"
    assert bll["issued_date"] == "2019-11-20"
    assert "effective_date" in bll
    assert "extraction" in bll
    assert len(bll["chapters"]) > 0


def test_corpus_overview_hcmut(client):
    response = client.get("/api/corpus/overview?corpus=hcmut")
    assert response.status_code == 200
    data = response.json()
    assert data["corpus"] == "hcmut"
    assert data["collection_id"] == "hcmut_academic"
    assert data["total_documents"] == 10
    assert data["total_chunks"] == 143
    assert data["total_characters"] > 150000

    docs = data["documents"]
    assert len(docs) == 10
    hvdt = next((d for d in docs if d["doc_code"] == "HVDT1260"), None)
    assert hvdt is not None
    assert hvdt["pdf_available"] is True
    assert hvdt["chunk_count"] == 18
    assert hvdt["pages"] == 21


def test_corpus_overview_invalid_corpus(client):
    response = client.get("/api/corpus/overview?corpus=non_existent_corpus_xyz")
    assert response.status_code == 404
    assert "không tồn tại" in response.json()["detail"]


def test_corpus_chunks_labour_query(client):
    # Pagination
    r1 = client.get("/api/corpus/chunks?corpus=labour&limit=10&offset=0")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["total"] == 458
    assert len(d1["items"]) == 10

    item = d1["items"][0]
    assert "article_id" in item
    assert "title" in item
    assert "text" in item
    assert "char_count" in item
    assert "word_count" in item
    assert "clause_count" in item
    assert "point_count" in item
    assert "pdf_url" in item
    assert "source_pages" in item
    assert isinstance(item["source_pages"], list)
    assert len(item["source_pages"]) > 0
    assert "char_start" in item
    assert "char_end" in item
    assert item["char_end"] > item["char_start"]
    assert "extraction" in item

    # Filter by doc_code
    r2 = client.get("/api/corpus/chunks?corpus=labour&doc_code=BLLD2019")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["total"] == 220

    # Alias BLL2019
    r3 = client.get("/api/corpus/chunks?corpus=labour&doc_code=BLL2019")
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["total"] == 220

    # Search keyword
    r4 = client.get("/api/corpus/chunks?corpus=labour&q=thử+việc")
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["total"] >= 3
    assert any("thử việc" in it["title"].lower() or "thử việc" in it["text"].lower() for it in d4["items"])


def test_corpus_chunks_hcmut_query(client):
    r1 = client.get("/api/corpus/chunks?corpus=hcmut&doc_code=HVDT1260")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["total"] == 18

    r2 = client.get("/api/corpus/chunks?corpus=hcmut&doc_code=NOIQUY1924")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["total"] == 9


def test_corpus_pdf_streaming(client):
    # Labour BLLD2019
    r1 = client.get("/api/corpus/pdf/labour/BLLD2019")
    assert r1.status_code == 200
    assert r1.headers["content-type"] == "application/pdf"
    assert "inline" in r1.headers["content-disposition"]
    assert "bll2019-congbao.pdf" in r1.headers["content-disposition"]
    assert len(r1.content) == 1352965

    # Labour alias BLL2019
    r2 = client.get("/api/corpus/pdf/labour/BLL2019")
    assert r2.status_code == 200
    assert len(r2.content) == 1352965

    # HCMUT HVDT1260
    r3 = client.get("/api/corpus/pdf/hcmut/HVDT1260")
    assert r3.status_code == 200
    assert r3.headers["content-type"] == "application/pdf"
    assert len(r3.content) == 1048987


def test_corpus_pdf_security_and_traversal(client):
    # Unknown document
    r1 = client.get("/api/corpus/pdf/labour/INVALID_DOC_XYZ")
    assert r1.status_code == 404

    # Traversal attempts
    r2 = client.get("/api/corpus/pdf/labour/..%2F..%2Fetc%2Fpasswd")
    assert r2.status_code in {400, 404}

    r3 = client.get("/api/corpus/pdf/labour/../../etc/passwd")
    assert r3.status_code in {400, 404}


def test_api_v1_aliases(client):
    # /api/v1/corpus/overview
    r1 = client.get("/api/v1/corpus/overview?corpus=labour")
    assert r1.status_code == 200
    assert r1.json()["total_documents"] == 10

    # /api/v1/corpus/chunks
    r2 = client.get("/api/v1/corpus/chunks?corpus=labour&limit=3")
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 3

    # /api/v1/corpus/pdf
    r3 = client.get("/api/v1/corpus/pdf/labour/BLLD2019")
    assert r3.status_code == 200
    assert len(r3.content) > 1000000
