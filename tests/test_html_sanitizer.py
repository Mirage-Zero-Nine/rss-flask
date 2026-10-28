"""Security and reader compatibility at the RSS rendering boundary (no I/O)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest
from bs4 import BeautifulSoup

from utils.html_sanitizer import sanitize_article_html
from utils.xml_utilities import generate_feed_object_for_new_router


def _fragment(html, base_url="https://publisher.example/news/article"):
    cleaned = sanitize_article_html(html, base_url)
    assert cleaned is not None
    return BeautifulSoup(cleaned, "html.parser")


def test_preserves_reader_article_structure_and_https_media():
    fragment = _fragment('''
        <article><h2>A &amp; B</h2><p>Hello <strong>reader</strong>
        <a href="../background?x=1&amp;y=2">background</a>.</p>
        <blockquote cite="https://source.example/story">Quote</blockquote>
        <ol start="2"><li>One</li><li>Two</li></ol><ul><li>Three</li></ul>
        <figure><img src="/image.jpg" alt="Camera &amp; lens" width="640" height="480">
        <figcaption>Photo caption</figcaption></figure>
        <table><caption>Measurements</caption><thead><tr><th scope="col">Value</th></tr></thead>
        <tbody><tr><td colspan="2">42</td></tr></tbody></table>
        <audio src="https://media.example/interview.mp3" autoplay></audio>
        <video poster="//media.example/poster.jpg" autoplay>
        <source src="https://media.example/movie.mp4" type="video/mp4"></video>
        <pre><code>a &lt; b &amp;&amp; b &gt; c</code></pre></article>
    ''')
    assert fragment.h2.get_text() == "A & B"
    assert fragment.a["href"] == "https://publisher.example/background?x=1&y=2"
    assert fragment.a["rel"] == ["noopener", "noreferrer"]
    assert fragment.blockquote["cite"] == "https://source.example/story"
    assert [li.get_text() for li in fragment.find_all("li")] == ["One", "Two", "Three"]
    assert fragment.img["src"] == "https://publisher.example/image.jpg"
    assert fragment.img["alt"] == "Camera & lens"
    assert fragment.img["width"] == "640"
    assert fragment.figcaption.get_text() == "Photo caption"
    assert fragment.table.caption.get_text() == "Measurements"
    assert fragment.th["scope"] == "col"
    assert fragment.td["colspan"] == "2"
    assert fragment.audio["src"] == "https://media.example/interview.mp3"
    assert fragment.video["poster"] == "https://media.example/poster.jpg"
    assert fragment.source["src"] == "https://media.example/movie.mp4"
    for media in [fragment.audio, fragment.video]:
        assert "controls" in media.attrs
        assert media["preload"] == "none"
        assert "autoplay" not in media.attrs
    assert fragment.code.get_text() == "a < b && b > c"


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "jav&#x61;script:alert(1)", "java&#10;script:alert(1)",
    "&#106;avascript:alert(1)", "vbscript:msgbox(1)", "data:text/html,attack",
    "file:///etc/passwd", "https://user:password@publisher.example/",
    "https://[broken/", "https://publisher.example:99999/",
    "https:\\publisher.example\\attack", "https://publisher.example/white space",
])
def test_removes_dangerous_or_ambiguous_urls(url):
    fragment = _fragment(f'<a href="{url}">link</a><img src="{url}" onerror="attack()">')
    assert "href" not in fragment.a.attrs
    assert "src" not in fragment.img.attrs
    assert "onerror" not in fragment.img.attrs


def test_removes_active_markup_css_and_hidden_network_attributes():
    fragment = _fragment('''
        <style>body { background: url(https://evil.example/track) }</style>
        <script>secret_code()</script><svg onload="evil()"><script>svg_code()</script></svg>
        <math><mi xlink:href="data:x">math_payload</mi></math>
        <template><img src="https://evil.example/hidden"></template>
        <object data="https://evil.example/object">object_payload</object>
        <form action="https://evil.example/post"><input name="credential"></form>
        <p style="background:url(javascript:attack())" class="evil" id="location" onclick="evil()">Keep</p>
        <a href="https://source.example" ping="https://evil.example" target="_blank">Source</a>
        <img src="https://media.example/image.jpg" srcset="https://evil.example/image 2x" onload="evil()">
        <!-- tracking comment -->
    ''')
    output = str(fragment)
    for tag in ["style", "script", "svg", "math", "template", "object", "form", "input"]:
        assert fragment.find(tag) is None
    for text in ["secret_code", "svg_code", "math_payload", "object_payload", "evil.example", "tracking comment"]:
        assert text not in output
    assert fragment.p.get_text() == "Keep"
    assert fragment.p.attrs == {}
    assert "ping" not in fragment.a.attrs
    assert "target" not in fragment.a.attrs
    assert fragment.img.attrs == {"src": "https://media.example/image.jpg"}


@pytest.mark.parametrize("html", [
    '<svg><style><img src=x onerror=attack()></style></svg><p>Keep</p>',
    '<math><mtext><table><mglyph><style><!--</style><img title="--><img src=x onerror=attack()>">',
    '<a href="javascript:evil()" href="https://safe.example">Duplicate</a>',
    '<IMG SRC=java\tscript:attack() onerror=attack()><p><b>Malformed',
    '<noscript><p title="</noscript><img src=x onerror=attack()>">',
])
def test_html5_parser_closes_malformed_markup_attack_paths(html):
    cleaned = sanitize_article_html(html, "https://publisher.example/article")
    assert cleaned is not None
    assert sanitize_article_html(cleaned, "https://publisher.example/article") == cleaned
    fragment = BeautifulSoup(cleaned, "html.parser")
    assert fragment.find(["script", "style", "svg", "math", "object"]) is None
    for tag in fragment.find_all(True):
        assert not any(name.lower().startswith("on") for name in tag.attrs)
        for name in ["href", "src"]:
            if name in tag.attrs:
                assert str(tag[name]).startswith("https://")


@pytest.mark.parametrize("url", [
    "https://player.vimeo.com/video/1192355275?h=abc",
    "https://www.youtube.com/embed/Abc_123-def",
    "https://www.youtube-nocookie.com/embed/Abc_123-def",
])
def test_preserves_only_vetted_sandboxed_video_players(url):
    fragment = _fragment(f'<iframe src="{url}" srcdoc="attack" allow="camera; microphone" '
                         'sandbox="allow-top-navigation allow-popups" onload="attack()"></iframe>')
    assert fragment.iframe["src"] == url
    assert set(fragment.iframe["sandbox"]) == {"allow-scripts", "allow-same-origin", "allow-presentation"}
    assert fragment.iframe["referrerpolicy"] == "no-referrer"
    assert "allowfullscreen" in fragment.iframe.attrs
    assert not {"srcdoc", "allow", "onload"}.intersection(fragment.iframe.attrs)


@pytest.mark.parametrize("url", [
    "https://evil.example/player", "http://player.vimeo.com/video/123",
    "https://player.vimeo.com.evil.example/video/123",
    "https://evil.example@player.vimeo.com/video/123",
    "https://player.vimeo.com:444/video/123", "https://player.vimeo.com/other/123",
    "https://www.youtube.com/redirect?target=https://evil.example",
    "https://www.youtube.com/embed/../redirect", "javascript:alert(1)",
])
def test_untrusted_iframes_cannot_load(url):
    fragment = _fragment(f'<iframe src="{url}"></iframe>')
    assert "src" not in fragment.iframe.attrs
    assert "sandbox" in fragment.iframe.attrs


def test_insecure_media_removed_but_hyperlinks_are_still_clickable():
    fragment = _fragment('<img src="http://media.example/image.jpg">'
                         '<a href="http://publisher.example/archive">archive</a>'
                         '<a href="mailto:editor@publisher.example">email</a>'
                         '<a href="tel:+12025550123">phone</a>')
    assert "src" not in fragment.img.attrs
    assert [a["href"] for a in fragment.find_all("a")] == [
        "http://publisher.example/archive", "mailto:editor@publisher.example", "tel:+12025550123",
    ]


def test_relative_urls_without_safe_article_base_are_removed():
    fragment = _fragment('<img src="relative.jpg"><a href="/path">link</a>', "javascript:evil()")
    assert "src" not in fragment.img.attrs
    assert "href" not in fragment.a.attrs


def test_render_protects_preexisting_cached_html_without_mutating_payload():
    cached_item = SimpleNamespace(
        title="Cached & untouched", link="https://publisher.example/archive",
        description='<p>Long-cached A &amp; B <img src="/old.jpg" onerror="attack()"></p>'
                    '<script>cached_attack()</script>',
        author="Author", guid="stable-cached-guid", created_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    original = vars(cached_item).copy()
    feed = generate_feed_object_for_new_router(
        "Feed", "https://publisher.example", "Description", "en-us",
        datetime(2026, 10, 22, tzinfo=timezone.utc), [cached_item],
    )
    rss = ElementTree.fromstring(feed.rss())
    assert rss.findtext("channel/item/title") == "Cached & untouched"
    assert rss.findtext("channel/item/link") == cached_item.link
    assert rss.findtext("channel/item/guid") == cached_item.guid
    description = rss.findtext("channel/item/description")
    assert description is not None
    assert "cached_attack" not in description
    fragment = BeautifulSoup(description, "html.parser")
    assert fragment.p.get_text() == "Long-cached A & B "
    assert fragment.img.attrs == {"src": "https://publisher.example/old.jpg"}
    assert vars(cached_item) == original


def test_plain_text_entities_unicode_and_xml_invalid_characters():
    text = 'A & B; 2 < 3; 中文 😀; "quotes"; &lt;script&gt;literal&lt;/script&gt;\x01&#11;\ud800'
    cleaned = sanitize_article_html(text)
    assert cleaned is not None
    fragment = BeautifulSoup(cleaned, "html.parser")
    assert fragment.find("script") is None
    assert fragment.get_text() == 'A & B; 2 < 3; 中文 😀; "quotes"; <script>literal</script>'
    # The XML serializer adds its own layer of escaping around safe HTML.
    item = SimpleNamespace(title="Plain", link="https://publisher.example", description=text,
                           author=None, guid="plain", created_time=None)
    feed = generate_feed_object_for_new_router("Feed", item.link, "Feed", "en-us", None, [item])
    assert ElementTree.fromstring(feed.rss()).findtext("channel/item/description") == cleaned
    assert sanitize_article_html(None) is None
    assert sanitize_article_html("") == ""


def test_sanitizing_scraper_tag_does_not_mutate_it():
    source = BeautifulSoup('<p onclick="attack()">Body <b>bold</b></p>', "html.parser").p
    original = str(source)
    assert sanitize_article_html(source) == "<p>Body <b>bold</b></p>"
    assert str(source) == original
