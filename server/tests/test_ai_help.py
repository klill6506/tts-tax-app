"""Tests for the AI help module (instruction cache, service, views)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.ai_help.instruction_cache import (
    INSTRUCTION_FILES,
    clear_cache,
    get_instruction_text,
)
from apps.ai_help.models import HelpQuery
from apps.firms.models import Firm, FirmMembership, Role


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(
        username="helpuser", password="testpass123", email="help@example.com"
    )
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = Client()
    http.login(username="helpuser", password="testpass123")
    return user, http


# ---------------------------------------------------------------------------
# Instruction Cache Tests
# ---------------------------------------------------------------------------


class TestInstructionCache:
    def test_known_form_codes_in_mapping(self):
        """All three main form codes are registered."""
        assert "1120-S" in INSTRUCTION_FILES
        assert "1065" in INSTRUCTION_FILES
        assert "1120" in INSTRUCTION_FILES

    def test_k1_codes_map_to_parent(self):
        """K-1 form codes map to their parent form's instruction PDF."""
        assert INSTRUCTION_FILES["1120-S-K1"] == INSTRUCTION_FILES["1120-S"]
        assert INSTRUCTION_FILES["1065-K1"] == INSTRUCTION_FILES["1065"]

    def test_unknown_form_returns_none(self):
        """Unknown form code returns None."""
        clear_cache()
        result = get_instruction_text("FAKE-9999")
        assert result is None

    @patch("apps.ai_help.instruction_cache.pdfplumber")
    def test_caches_after_first_call(self, mock_pdfplumber, settings):
        """Second call returns cached value without re-parsing the PDF."""
        clear_cache()
        # Mock pdfplumber.open to return a fake PDF with pages
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Line 1 instructions"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf

        # First call — should parse
        result1 = get_instruction_text("1120-S")
        # Second call — should be cached
        result2 = get_instruction_text("1120-S")

        assert result1 == result2
        assert result1 == "Line 1 instructions"
        # pdfplumber.open should only have been called once (cached)
        assert mock_pdfplumber.open.call_count == 1

        clear_cache()

    @patch("apps.ai_help.instruction_cache.pdfplumber")
    def test_clear_cache_resets(self, mock_pdfplumber, settings):
        """clear_cache() forces re-parsing on next call."""
        clear_cache()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Some text"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf

        get_instruction_text("1120-S")
        clear_cache()
        get_instruction_text("1120-S")

        assert mock_pdfplumber.open.call_count == 2

        clear_cache()


# ---------------------------------------------------------------------------
# View / Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAskEndpoint:
    @patch("apps.ai_help.views.ask_gemini", return_value="Test answer")
    def test_defaults_to_grounded(self, mock_gemini, user_and_http):
        """Default mode should be 'grounded' when not specified."""
        _, http = user_and_http
        resp = http.post(
            "/api/v1/ai/ask/",
            data=json.dumps({"question": "What goes on line 1?", "form_code": "1120-S"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Test answer"
        assert data["mode"] == "grounded"
        mock_gemini.assert_called_once_with(
            "What goes on line 1?", form_code="1120-S", section="", mode="grounded"
        )

    @patch("apps.ai_help.views.ask_gemini", return_value="Broad answer")
    def test_accepts_broad_mode(self, mock_gemini, user_and_http):
        """Explicit 'broad' mode is passed through."""
        _, http = user_and_http
        resp = http.post(
            "/api/v1/ai/ask/",
            data=json.dumps({"question": "General tax question", "mode": "broad"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "broad"
        mock_gemini.assert_called_once_with(
            "General tax question", form_code="", section="", mode="broad"
        )

    @patch("apps.ai_help.views.ask_gemini", return_value="Fallback answer")
    def test_invalid_mode_defaults_to_grounded(self, mock_gemini, user_and_http):
        """Invalid mode value falls back to 'grounded'."""
        _, http = user_and_http
        resp = http.post(
            "/api/v1/ai/ask/",
            data=json.dumps({"question": "Test?", "mode": "invalid_mode"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "grounded"

    @patch("apps.ai_help.views.ask_gemini", return_value="Saved answer")
    def test_saves_mode_in_audit_trail(self, mock_gemini, user_and_http):
        """Mode is persisted in the HelpQuery audit record."""
        user, http = user_and_http
        http.post(
            "/api/v1/ai/ask/",
            data=json.dumps({"question": "Audit test?", "mode": "broad"}),
            content_type="application/json",
        )
        query = HelpQuery.objects.filter(user=user).first()
        assert query is not None
        assert query.mode == "broad"
        assert query.question == "Audit test?"
        assert query.response == "Saved answer"

    def test_requires_auth(self, db):
        """Unauthenticated requests are rejected."""
        http = Client()
        resp = http.post(
            "/api/v1/ai/ask/",
            data=json.dumps({"question": "Hello?"}),
            content_type="application/json",
        )
        assert resp.status_code == 403

    @patch("apps.ai_help.views.ask_gemini", return_value="Answer")
    def test_requires_question(self, mock_gemini, user_and_http):
        """Empty question returns 400."""
        _, http = user_and_http
        resp = http.post(
            "/api/v1/ai/ask/",
            data=json.dumps({"question": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "error" in resp.json()
        mock_gemini.assert_not_called()

    @patch("apps.ai_help.views.ask_gemini", return_value="Answer")
    def test_missing_question_returns_400(self, mock_gemini, user_and_http):
        """Missing question field returns 400."""
        _, http = user_and_http
        resp = http.post(
            "/api/v1/ai/ask/",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
