"""
ScrapeResponse DTO 테스트
"""

from app.scrapers.dto.scrape_response import ScrapeResponse


def test_create_default_scrape_response():
    result = ScrapeResponse()
    assert result.success is True
    assert result.url == ""
    assert result.title is None


def test_create_scrape_response_with_values():
    result = ScrapeResponse(
        success=True,
        title="Test",
        description="Desc",
        url="https://example.com",
    )
    assert result.title == "Test"
    assert result.description == "Desc"
    assert result.url == "https://example.com"


def test_to_dict_excludes_none_content_and_error():
    result = ScrapeResponse(success=True, title="Test", url="https://example.com")
    payload = result.to_dict()
    assert "content" not in payload
    assert "error" not in payload


def test_to_dict_includes_content_when_set():
    result = ScrapeResponse(
        success=True,
        title="Test",
        url="https://example.com",
        content="Hello",
    )
    payload = result.to_dict()
    assert payload["content"] == "Hello"


def test_scrape_response_attribute_mutation():
    result = ScrapeResponse(success=True, title="Old")
    result.title = "New"
    result.content = "Added"
    assert result.title == "New"
    assert result.content == "Added"
