# tests/test_aquatic_search_index.py
import json
import pandas as pd
from scripts.build_aquatic_search_index import build_search_index

def test_search_index_has_all_groups():
    df = pd.DataFrame({
        "id": ["1", "2", "3"],
        "group": ["shark", "whale", "jellyfish"],
        "scientific_name": ["Carcharodon carcharias", "Megaptera novaeangliae", "Aurelia aurita"],
    })
    index = build_search_index(df)
    assert "shark" in index["groups"]
    assert "whale" in index["groups"]
    assert "jellyfish" in index["groups"]
    assert "1" in index["groups"]["shark"]["specIds"]

def test_search_index_by_spec_id():
    df = pd.DataFrame({
        "id": ["1"],
        "group": ["shark"],
        "scientific_name": ["Carcharodon carcharias"],
    })
    index = build_search_index(df)
    assert index["bySpecId"]["1"] == "shark"
