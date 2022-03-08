from datetime import datetime


def convert_time_twitter(created_time_string):
    return datetime.strptime(created_time_string, '%Y-%m-%dT%H:%M:%S.%fZ')

def convert_time_zaobao(created_time_string):
    # sample: 2022年3月6日 10:04 PM
    return datetime.strptime(created_time_string, '%Y年%m月%d日 %I:%M %p')

if __name__ == '__main__':
    print(convert_time_zaobao("2022年3月6日 10:04 PM"))