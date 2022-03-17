from datetime import datetime
from zoneinfo import ZoneInfo
import datetime as dt


def convert_time_twitter(created_time_string):
    return datetime.strptime(created_time_string, '%Y-%m-%dT%H:%M:%S.%fZ')


def convert_time_zaobao(created_time_string):
    """
    Build datetime object and convert to UTC.
    :param created_time_string: timestamp string
    :return: datetime object
    """
    # sample: 2022年3月12日 1:46 PM
    converted_time = datetime.strptime(created_time_string, '%Y年%m月%d日 %I:%M %p')
    converted_time = converted_time - dt.timedelta(hours=8)  # shift 8 hours earlier to fit timezone
    converted_time.replace(tzinfo=ZoneInfo('Etc/UTC'))  # set timezone to utc (somehow it doesn't seem working)
    return converted_time


def convert_time_dayone(created_time_string):
    # sample: April 07, 2021
    return datetime.strptime(created_time_string, '%B %d, %Y')


def convert_time_string_to_timestamp(created_time_string):
    return round(datetime.strptime(created_time_string, '%Y年%m月%d日 %I:%M %p').timestamp() * 1000)


def convert_time_jandan(created_time_string):
    time_string = created_time_string + " +0800"
    return datetime.strptime(time_string, '%Y.%m.%d , %H:%M %z')


if __name__ == '__main__':
    print(convert_time_zaobao("2022年3月12日 1:46 PM"))
    print(convert_time_string_to_timestamp("2022年3月6日 10:04 PM"))
    print(convert_time_jandan("2022.03.13 , 14:32"))
