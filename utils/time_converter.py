from datetime import datetime
import datetime as dt
import pytz


def convert_time_with_pattern(created_time_string, pattern, shift_hours=0):
    converted_time = datetime.strptime(created_time_string, pattern)
    if shift_hours >= 0:
        # convert it to UTC, for instance, UTC +1 -> shift_hour=1
        converted_time = converted_time - dt.timedelta(hours=shift_hours)
    else:
        converted_time = converted_time + dt.timedelta(hours=abs(shift_hours))
    converted_time_with_timezone = dt.datetime(converted_time.year,
                                               converted_time.month,
                                               converted_time.day,
                                               converted_time.hour,
                                               converted_time.minute,
                                               converted_time.second,
                                               0,
                                               pytz.UTC)

    return converted_time_with_timezone


def convert_wsdot_news_time(time_string, format):
    time_object = datetime.strptime(str(time_string), format)
    return time_object.astimezone(pytz.timezone('US/Pacific'))


def convert_millisecond_to_datetime(millisecond_string, shift_hours=0):
    converted_time = datetime.fromtimestamp(int(millisecond_string) / 1000)
    converted_time = converted_time - dt.timedelta(hours=shift_hours)
    converted_time_with_timezone = dt.datetime(converted_time.year,
                                               converted_time.month,
                                               converted_time.day,
                                               converted_time.hour,
                                               converted_time.minute,
                                               converted_time.second,
                                               0,
                                               pytz.UTC)
    return converted_time_with_timezone


def convert_millisecond_to_datetime_with_format(millisecond_string, shift_hours=0):
    # converted_time_with_timezone = convert_millisecond_to_datetime(millisecond_string, shift_hours)
    converted_time = datetime.fromtimestamp(round(int(millisecond_string) / 1000))
    converted_time = converted_time - dt.timedelta(hours=shift_hours)
    return converted_time
