class FeedItem:

    def __init__(self,
                 title=None,
                 link=None,
                 description=None,
                 author=None,
                 guid=None,
                 created_time=None,
                 with_content=False):
        self.title = title
        self.link = link
        self.description = description  # main content in each feed
        self.author = author
        self.created_time = created_time  # required to be a datatime object
        self.guid = guid
        self.with_content = with_content  # if current item has query the source url and fill with content

    def __repr__(self):
        string = "title: " + self.title + '\n' + \
                 "link: " + self.link + '\n' + \
                 "author: " + self.author + '\n' + \
                 "description: " + self.description + '\n' + \
                 "created_time: " + str(self.created_time) + '\n'

        return string
