from datetime import datetime
import datetime as dt
import pytz

import constant.constants as c


def convert_time_twitter(created_time_string):
    return datetime.strptime(created_time_string, '%Y-%m-%dT%H:%M:%S.%fZ')


def convert_time_with_pattern(created_time_string, pattern, shift_hours=0):
    converted_time = datetime.strptime(created_time_string, pattern)
    if shift_hours >= 0:  # convert it to UTC, for instance, UTC +1 -> shift_hour=1
        converted_time = converted_time - dt.timedelta(hours=shift_hours)
    else:
        converted_time = converted_time + dt.timedelta(hours=shift_hours)
    converted_time_with_timezone = dt.datetime(converted_time.year,
                                               converted_time.month,
                                               converted_time.day,
                                               converted_time.hour,
                                               converted_time.minute,
                                               converted_time.second,
                                               0,
                                               pytz.UTC)
    return converted_time_with_timezone


#
# def convert_time_string_to_timestamp(created_time_string):
#     return round(datetime.strptime(created_time_string, '%Y年%m月%d日 %I:%M %p').timestamp() * 1000)

def convert_millisecond_to_datetime(millisecond_string, shift_hours=0):
    converted_time = datetime.fromtimestamp(int(millisecond_string) / 1000)
    converted_time = converted_time + dt.timedelta(hours=shift_hours)
    converted_time_with_timezone = dt.datetime(converted_time.year,
                                               converted_time.month,
                                               converted_time.day,
                                               converted_time.hour,
                                               converted_time.minute,
                                               converted_time.second,
                                               0,
                                               pytz.UTC)
    return converted_time_with_timezone


if __name__ == '__main__':
    print(convert_time_with_pattern("2022年3月12日 1:46 PM", c.zaobao_time_convert_pattern, 8))
    # print(convert_time_string_to_timestamp("2022年3月6日 10:04 PM"))
    print(convert_time_with_pattern("2022.03.13 , 14:32", c.jandan_time_convert_pattern, 8))
    print(convert_time_with_pattern("2022.03.18 14:35:42", c.currency_time_convert_pattern, 8))
    print(convert_millisecond_to_datetime("1647657191000", 7))
