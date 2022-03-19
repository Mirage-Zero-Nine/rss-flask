class FeedItem:

    def __init__(self, title=None, link=None, description=None, author=None, guid=None, created_time=None):
        self.title = title
        self.link = link
        self.description = description  # main content in each feed
        self.author = author
        self.created_time = created_time  # required to be a datatime object
        self.guid = guid

    def __repr__(self):
        string = "title: " + self.title + '\n' + \
                 "link: " + self.link + '\n' + \
                 "author: " + self.author + '\n' + \
                 "description: " + self.description + '\n' + \
                 "created_time: " + self.created_time

        return string
