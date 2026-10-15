"""Second-pass segmentation repairs empty pages, not recognized values."""
from pathlib import Path

from PIL import Image

from substrakt.parsers import ocr


def row(text, conf="95"):
    return dict(text=text, conf=conf, left="10", top="20", width="30", height="10")


def test_empty_page_gets_a_bounded_second_attempt(monkeypatch):
    calls = []
    def tsv(_image, _language, _threads, psm=3):
        calls.append(psm)
        return [] if psm == 3 else [row("Rechnung")]
    monkeypatch.setattr(ocr, "_tsv", tsv)
    result = ocr.read_image(Path("fake.png"))
    assert calls == [3, 11]
    assert [w.text for w in result.words] == ["Rechnung"]
    assert result.words[0].locator.y0 == 20


def test_weak_second_attempt_does_not_overwrite_good_words(monkeypatch):
    def tsv(_image, _language, _threads, psm=3):
        return [row("Original")] if psm == 3 else [row("Rauschen", "5")]
    monkeypatch.setattr(ocr, "_tsv", tsv)
    assert ocr.read_image(Path("fake.png")).words[0].text == "Original"


def test_well_read_page_needs_no_second_call(monkeypatch):
    calls = []
    def tsv(_image, _language, _threads, psm=3):
        calls.append(psm)
        return [row(str(i)) for i in range(50)]
    monkeypatch.setattr(ocr, "_tsv", tsv)
    ocr.read_image(Path("fake.png"))
    assert calls == [3]


def test_image_cleanup_gets_size_and_evidence(tmp_path, monkeypatch):
    image = tmp_path / "shadow.png"
    Image.new("L", (160, 240), 180).save(image)
    cleaned_paths = []
    def tsv(path, _language, _threads, psm=3):
        if psm == 3:
            return []
        with Image.open(path) as cleaned:
            assert cleaned.size == (160, 240)
            assert set(cleaned.getdata()) <= {0, 255}
        cleaned_paths.append(path)
        return [row("Recognized")]
    monkeypatch.setattr(ocr, "_tsv", tsv)
    result = ocr.read_image(image, page=2)
    assert result.words[0].locator.page == 2
    assert result.words[0].locator.x0 == 10
    assert result.words[0].locator.y0 == 20
    assert not cleaned_paths[0].exists()
    assert Image.open(image).getpixel((0, 0)) == 180
