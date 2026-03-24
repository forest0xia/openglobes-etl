# tests/test_sprites.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.fetch_aquatic_sprites import fetch_phylopic, SOURCE_PRIORITY

def test_source_priority_order():
    assert SOURCE_PRIORITY == ["wikimedia", "fishbase", "noaa", "gbif_media"]

def test_fetch_phylopic_skips_existing(tmp_path):
    existing = tmp_path / "phylopic" / "123.svg"
    existing.parent.mkdir(parents=True)
    existing.write_text("<svg/>")
    with patch("scripts.fetch_aquatic_sprites.SPRITE_RAW_DIR", tmp_path):
        result = fetch_phylopic("Orcinus orca", "123")
    assert result is True  # already exists

def test_fetch_phylopic_returns_false_on_not_found(tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": []}
    with patch("scripts.fetch_aquatic_sprites.SPRITE_RAW_DIR", tmp_path), \
         patch("requests.get", return_value=mock_resp):
        result = fetch_phylopic("Nonexistent species", "999")
    assert result is False
