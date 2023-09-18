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
