"""Tests unitaires des schemas Pydantic."""
import pytest
from pydantic import ValidationError

from app.schemas import ReportCreate


def test_report_create_valid():
    """Un payload valide est accepté."""
    payload = ReportCreate(title="Test", parameters={"year": 2024})
    assert payload.title == "Test"
    assert payload.parameters == {"year": 2024}


def test_report_create_default_parameters():
    """Sans parameters, on a un dict vide par défaut."""
    payload = ReportCreate(title="Test")
    assert payload.parameters == {}


def test_report_create_empty_title_rejected():
    """Un titre vide est rejeté (min_length=1)."""
    with pytest.raises(ValidationError):
        ReportCreate(title="")


def test_report_create_too_long_title_rejected():
    """Un titre > 200 caractères est rejeté."""
    with pytest.raises(ValidationError):
        ReportCreate(title="x" * 201)


def test_report_create_missing_title_rejected():
    """Un titre absent est rejeté."""
    with pytest.raises(ValidationError):
        ReportCreate()