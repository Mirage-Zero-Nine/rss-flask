class NewsItem:
    title = ''
    link = ''
    description = ''
    author = ''
    created_time = ''

    def __repr__(self):
        string = "title: " + self.title + '\n' + \
                 "link: " + self.link + '\n' + \
                 "author: " + self.author + '\n' + \
                 "description: " + self.description + '\n' + \
                 "created_time: " + self.created_time

        return string
