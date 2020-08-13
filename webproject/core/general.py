from datetime import datetime
import urllib.parse


def to_date(date_in_datetime):
    date_str = date_in_datetime.strftime('%Y-%m-%d')
    return date_str


def to_human_date(date_in_datetime):
    human_date = date_in_datetime.strftime('%d.%m.%Y')
    return human_date


def human_to_datetime(my_date):
    human_datetime = datetime.strptime(my_date, '%d.%m.%Y')
    return human_datetime


def to_datetime(datetime_date):
    date_in_datetime = datetime.strptime(datetime_date, '%Y-%m-%d')
    return date_in_datetime


def take_domain(url):
    """
    Takes a long url and returns the base domain without http and www, but with sub-domains
    :param url: long url
    :return: domain name in short form like fr.example.com
    """
    # splitted = url.split('://')
    # i = (0, 1)[len(splitted) > 1]
    # domain = splitted[i].split('?')[0].split('/')[0].split(':')[0].lower()

    url_parced = urllib.parse.urlparse(url)
    return str(url_parced.netloc)


def take_uri(url):
    # splitted = url.split('://')
    # i = (0, 1)[len(splitted) > 1]
    # domain = splitted[i].split('?')[0].split('/')[0].split(':')[0]
    # uri = url.split(domain)[1]

    url_parced = urllib.parse.urlparse(url)
    return url_parced.path + url_parced.params + url_parced.query


def datetime_to_short_date(my_datetime):
    """

    :param my_datetime:
    :return:
    """
    short_date = my_datetime.strftime('%d.%m')
    return short_date


def clean_url(url):
    # TODO: Suggest if trailing slash is missing based on GA stats
    if url:
        try:
            url = url.strip()
            url_parsed = urllib.parse.urlparse(url)
            if not url_parsed.scheme:
                url = 'http://' + str(url)
        except Exception:
            pass

    return url
