"""Tests for utils.tools.

Note: per AGENTS.md and the implementation, check_need_to_filter() returns True
when the item SHOULD be filtered out — i.e. excluded from the feed. The naming
is counterintuitive and is the subject of these tests.
"""

from bs4 import BeautifulSoup

from utils.tools import (
    check_need_to_filter,
    decompose_div,
    decompose_tag_by_class_name,
    format_author_names,
    remove_certain_tag,
)


def test_format_author_names_empty_list_returns_empty_string():
    assert format_author_names([]) == ""


def test_format_author_names_none_returns_empty_string():
    assert format_author_names(None) == ""


def test_format_author_names_single_author_returned_as_is():
    assert format_author_names(["Alice"]) == "Alice"


def test_format_author_names_multiple_authors_joined_with_comma_space():
    assert format_author_names(["Alice", "Bob", "Carol"]) == "Alice, Bob, Carol"


def test_check_need_to_filter_link_prefix_match_returns_true():
    # Link prefix matches link_filter -> exclude from feed.
    assert check_need_to_filter(
        link="https://www.meta.com/blog/post-1",
        title="Some title",
        link_filter="https://www.meta",
        title_filter=None,
    ) is True


def test_check_need_to_filter_title_prefix_match_returns_true():
    assert check_need_to_filter(
        link="https://example.com/post",
        title="雇员招聘启事 - hiring",
        link_filter=None,
        title_filter="雇员招聘启事",
    ) is True


def test_check_need_to_filter_no_match_returns_false():
    assert check_need_to_filter(
        link="https://example.com/post",
        title="Normal headline",
        link_filter="https://www.meta",
        title_filter="雇员招聘启事",
    ) is False


def test_check_need_to_filter_with_no_filters_returns_false():
    assert check_need_to_filter(
        link="https://example.com",
        title="Anything",
        link_filter=None,
        title_filter=None,
    ) is False


def test_check_need_to_filter_uses_startswith_not_contains():
    # link_filter must match as a prefix; substring matches do NOT trigger filtering.
    assert check_need_to_filter(
        link="https://other.example.com/article",
        title="Title",
        link_filter="https://www.meta",
        title_filter=None,
    ) is False


def test_decompose_div_removes_only_matching_div_class():
    soup = BeautifulSoup(
        '<div class="ad">remove-me</div><div class="content">keep</div>',
        "html.parser",
    )

    decompose_div(soup, "ad")

    assert "remove-me" not in str(soup)
    assert "keep" in str(soup)


def test_decompose_tag_by_class_name_removes_all_matches():
    soup = BeautifulSoup(
        '<section class="x">a</section><section class="x">b</section><section class="y">c</section>',
        "html.parser",
    )

    decompose_tag_by_class_name(soup, "section", "x")

    sections = soup.find_all("section")
    assert len(sections) == 1
    assert sections[0].get_text() == "c"


def test_remove_certain_tag_strips_every_instance():
    soup = BeautifulSoup(
        "<article><script>evil()</script><p>hi</p><script>more()</script></article>",
        "html.parser",
    )

    remove_certain_tag(soup, "script")

    assert soup.find_all("script") == []
    assert soup.find("p").get_text() == "hi"
