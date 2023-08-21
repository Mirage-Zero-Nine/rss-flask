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
        # Handle None values by providing default values or converting to empty string
        title = self.title or ""
        link = self.link or ""
        author = self.author or ""
        created_time = str(self.created_time) if self.created_time else ""
        description = self.description or ""
        guid = self.guid or ""
        with_content = str(self.with_content)

        return "title: " + title + '\n' + \
            "link: " + link + '\n' + \
            "author: " + author + '\n' + \
            "created_time: " + created_time + '\n' + \
            "description: " + description + '\n' + \
            "guid: " + guid + '\n' + \
            "with content? " + with_content
