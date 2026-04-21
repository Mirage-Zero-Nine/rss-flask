import datetime as dt
from datetime import datetime

import pytz


def format_author_names(author_list):
    if not author_list:
        return ""
    if len(author_list) == 1:
        return author_list[0]
    return ", ".join(author_list)


def check_need_to_filter(link, title, link_filter, title_filter):
    if link_filter and link.startswith(link_filter):
        return True
    if title_filter and title.startswith(title_filter):
        return True
    return False


def remove_empty_tag(div, tag_name):
    for tag in div.find_all(tag_name):
        if tag.text.strip() == "":
            if tag.find("img"):
                continue
            tag.extract()


def decompose_div(soup, class_name):
    decompose_tag_by_class_name(soup, "div", class_name)


def decompose_tag_by_class_name(soup, tag_name, class_name):
    for tag in soup.find_all(tag_name, class_=class_name):
        tag.decompose()


def remove_certain_tag(soup, tag_name):
    for tag in soup.find_all(tag_name):
        tag.decompose()


def convert_time_with_pattern(created_time_string, pattern, shift_hours=0):
    converted_time = datetime.strptime(created_time_string, pattern)
    if shift_hours >= 0:
        converted_time = converted_time - dt.timedelta(hours=shift_hours)
    else:
        converted_time = converted_time + dt.timedelta(hours=abs(shift_hours))

    return dt.datetime(
        converted_time.year,
        converted_time.month,
        converted_time.day,
        converted_time.hour,
        converted_time.minute,
        converted_time.second,
        0,
        pytz.UTC,
    )


def convert_wsdot_news_time(time_string, format_string):
    time_object = datetime.strptime(str(time_string), format_string)
    return time_object.astimezone(pytz.timezone("US/Pacific"))


def convert_millisecond_to_datetime(millisecond_string, shift_hours=0):
    converted_time = datetime.fromtimestamp(int(millisecond_string) / 1000)
    converted_time = converted_time - dt.timedelta(hours=shift_hours)
    return dt.datetime(
        converted_time.year,
        converted_time.month,
        converted_time.day,
        converted_time.hour,
        converted_time.minute,
        converted_time.second,
        0,
        pytz.UTC,
    )


def convert_millisecond_to_datetime_with_format(millisecond_string, shift_hours=0):
    converted_time = datetime.fromtimestamp(round(int(millisecond_string) / 1000))
    return converted_time - dt.timedelta(hours=shift_hours)
