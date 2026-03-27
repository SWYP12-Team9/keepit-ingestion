"""
본문 추출 전처리와 구조화 데이터 fallback 회귀 테스트
"""

import pytest
from bs4 import BeautifulSoup

from app.scrapers.service.strategy.static_strategy import (
    extract_content,
    extract_meta_tags,
    sanitize_content_html,
    should_force_dynamic_render,
)


WORDPRESS_ARTICLE_URL = "https://example.com/tencent-job-post"
NEXTJS_ARTICLE_URL = "https://example.com/blog/nextjs-hydration-article"
JSON_LD_ARTICLE_URL = "https://example.com/articles/structured-data-post"

LONG_BODY_TEXT = (
    "Business Unit Cloud & Smart Industries Group (CSIG) is responsible for promoting "
    "the company's cloud and industry Internet strategy. CSIG explores the interactions "
    "between users and industries to create innovative solutions for smart industries."
)


def test_sanitize_content_html_preserves_article_wrapped_in_noisy_classes():
    html = f"""
    <html>
      <body>
        <nav>global navigation</nav>
        <div class="entry-content related share social">
          <article>
            <h1>Tencent Cloud Trainee</h1>
            <p>{LONG_BODY_TEXT}</p>
          </article>
        </div>
        <footer>footer links</footer>
        <script>window.analytics = true;</script>
      </body>
    </html>
    """

    sanitized = sanitize_content_html(html)

    assert "global navigation" not in sanitized
    assert "footer links" not in sanitized
    assert "window.analytics" not in sanitized
    assert "Tencent Cloud Trainee" in sanitized
    assert "Cloud &amp; Smart Industries Group" in sanitized
    assert "innovative solutions for smart industries" in sanitized


def test_extract_content_uses_dom_content_before_structured_data():
    html = f"""
    <html>
      <body>
        <article>
          <h1>Tencent Cloud Trainee</h1>
          <p>{LONG_BODY_TEXT}</p>
        </article>
        <script type="application/ld+json">
          {{"headline":"Ignored headline","articleBody":"Ignored body"}}
        </script>
      </body>
    </html>
    """

    content = extract_content(html, max_length=1000)

    assert content is not None
    assert LONG_BODY_TEXT in content
    assert "Ignored body" not in content


def test_extract_content_falls_back_to_json_ld_article_body():
    html = """
    <html>
      <body>
        <div class="loading-shell">Loading...</div>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "JSON-LD Headline",
            "description": "Structured description",
            "articleBody": "Structured article body with enough text to exceed the minimum content length for extraction."
          }
        </script>
      </body>
    </html>
    """

    content = extract_content(html, max_length=1000)

    assert content is not None
    assert "JSON-LD Headline" in content
    assert "Structured article body" in content


def test_extract_content_falls_back_to_hydration_payload():
    html = """
    <html>
      <body>
        <div id="__next"></div>
        <script id="__NEXT_DATA__" type="application/json">
          {
            "props": {
              "pageProps": {
                "headline": "Hydration Headline",
                "description": "Hydration description",
                "articleBody": "Hydration article body that contains enough useful text to be returned by the scraper."
              }
            }
          }
        </script>
      </body>
    </html>
    """

    content = extract_content(html, max_length=1000)

    assert content is not None
    assert "Hydration Headline" in content
    assert "Hydration article body" in content


def test_extract_content_does_not_fall_back_to_meta_description_only():
    html = """
    <html>
      <head>
        <title>Meta Only</title>
        <meta name="description" content="This should not become content by itself.">
      </head>
      <body>
        <div>Short</div>
      </body>
    </html>
    """

    content = extract_content(
        html,
        max_length=1000,
        title="Meta Only",
        description="This should not become content by itself.",
    )

    assert content is None


def test_should_force_dynamic_render_for_spa_shell_with_hydration():
    html = """
    <html>
      <body>
        <div id="__next"></div>
        <div class="loading-skeleton">Loading...</div>
        <script id="__NEXT_DATA__" type="application/json">
          {"props":{"pageProps":{"articleBody":"Hydration content"}}}
        </script>
      </body>
    </html>
    """

    force_dynamic_render, reason = should_force_dynamic_render(html, content=None)

    assert force_dynamic_render is True
    assert reason in {
        "loading-ui",
        "loading-text",
        "spa-root-with-hydration",
        "large-hydration-payload",
        "sparse-article-shell",
    }


@pytest.mark.asyncio
async def test_extract_meta_tags_resolves_relative_asset_urls_from_dummy_url():
    html = """
    <html>
      <head>
        <title>Dummy article</title>
        <meta property="og:title" content="Dummy article title">
        <meta property="og:description" content="Dummy article description">
        <meta property="og:image" content="/images/cover.png">
        <meta property="og:site_name" content="Example Blog">
        <link rel="icon" href="/favicon.ico">
      </head>
      <body>
        <article><p>Body</p></article>
      </body>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")
    metadata = await extract_meta_tags(soup, WORDPRESS_ARTICLE_URL)

    assert metadata["title"] == "Dummy article title"
    assert metadata["description"] == "Dummy article description"
    assert metadata["thumbnail_url"] == "https://example.com/images/cover.png"
    assert metadata["icon"] == "https://example.com/favicon.ico"
    assert metadata["site_name"] == "Example Blog"
