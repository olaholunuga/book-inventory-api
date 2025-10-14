from datetime import datetime

def get_timestamp():
    return datetime.now().strftime(("%Y-%m-%d %H:%M:%S"))

BOOKS = {
    "a knight of the seven kingdoms": {
        "title": "a knight of the seven kingdoms",
        "author": "George R.R. Martin",
        "published_date": get_timestamp()
    },
    "a drunken knight": {
        "title": "a drunken knight",
        "author": "George R.R. Martin",
        "published_date": get_timestamp()
    },
    "bastards of the alley": {
        "title": "bastards of the alley",
        "author": "olaoluwa olunuga",
        "published_date": get_timestamp()
    }
}

def read_all():
    return list(BOOKS.values())