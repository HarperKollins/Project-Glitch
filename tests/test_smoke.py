"""
Smoke Tests for Project Glitch
==============================
Run using: pytest
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glitch_engine
import data_manager

def test_imports():
    """Test that critical modules import without error."""
    assert glitch_engine is not None
    assert data_manager is not None

def test_predict_structure():
    """Test that predict_match_ml returns the correct dictionary structure."""
    # Mock models to avoid needing actual .pkl files during CI/CD if missing
    if os.path.exists("model_win.pkl"):
        result = glitch_engine.predict_match_ml("Arsenal", "Chelsea")
        
        assert "match" in result
        assert "predictions" in result
        assert "safest_glitch" in result
        assert "win" in result["predictions"]
        assert "confidence" in result["safest_glitch"]
    else:
        pytest.skip("Models not found, skipping prediction test")

def test_mock_fixture_generation():
    """Test data manager mock generation."""
    fixtures = data_manager.get_mock_fixtures(39)
    assert len(fixtures) > 0
    assert "home_team" in fixtures[0]
