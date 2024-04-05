def format_author_names(author_list):
    if not author_list:
        return ""
    elif len(author_list) == 1:
        return author_list[0]
    else:
        return ', '.join(author_list)


def check_need_to_filter(link, title, link_filter, title_filter):
    if link_filter and link.startswith(link_filter):
        return True
    if title_filter and title.startswith(title_filter):
        return True

    return False


def remove_empty_tag(div, tag_name):
    empty_p_tags = div.find_all(tag_name)
    for tag in empty_p_tags:
        if tag.text.strip() == "":
            if tag.find('img'):
                continue
            tag.extract()


def decompose_div(soup, class_name):
    decompose_tag_by_class_name(soup, 'div', class_name)


def decompose_tag_by_class_name(soup, tag_name, class_name):
    for div in soup.find_all(tag_name, class_=class_name):
        div.decompose()


def remove_certain_tag(soup, tag_name):
    for tag in soup.find_all(tag_name):
        tag.decompose()
