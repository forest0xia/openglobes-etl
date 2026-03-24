# tests/test_normalize_sprites.py
from scripts.normalize_sprites import normalize_svg, is_valid_svg

def test_normalize_strips_fill():
    svg_in = '<svg viewBox="0 0 200 100"><path d="M0,0L10,10" fill="red" stroke="black"/></svg>'
    result = normalize_svg(svg_in)
    assert 'fill="none"' in result or "fill:none" in result
    assert 'fill="red"' not in result

def test_normalize_sets_viewbox():
    svg_in = '<svg viewBox="0 0 200 100"><path d="M0,0L10,10"/></svg>'
    result = normalize_svg(svg_in)
    assert 'viewBox="0 0 100 60"' in result

def test_normalize_sets_stroke_color():
    svg_in = '<svg viewBox="0 0 200 100"><path d="M0,0L10,10" stroke="blue"/></svg>'
    result = normalize_svg(svg_in)
    assert 'stroke="#fff"' in result or "stroke:#fff" in result

def test_is_valid_svg():
    assert is_valid_svg('<svg viewBox="0 0 100 60"><path d="M0,0"/></svg>')
    assert not is_valid_svg("not xml at all")
    assert not is_valid_svg('<div>not svg</div>')
