import os
import time
import random
from datetime import datetime
from pprint import pprint
import requests
import requests.exceptions

from webproject.core.general import take_domain, take_uri, to_date
from webproject.models import GaView

curr_path = os.path.abspath(os.path.dirname(__file__))


def detect_view(user_id, url):
    """

    """
    user_domain_name = take_domain(url)

    view_id = None
    time_shift = 0

    for view_entry in GaView.query.filter_by(user_id=user_id,
                                             active=True).all():
        if user_domain_name == take_domain(view_entry.url):
            view_id = str(view_entry.profile_id)
            time_shift = int(view_entry.time_shift)
            break

    if view_id is None:
        raise Exception(f"There is no Google Analytics profiles associated with this url: {url}")

    return view_id, time_shift


def update_landing(user_id, view_id, start_date, finish_date, url, ga_stats_dict, access_token):
    """
    Sends parameters related to landing to GA function, gets response by chunks,
    parses it and updates the GA stats dict
    :param access_token:
    :param user_id:
    :param ga_stats_dict:
    :param view_id:
    :param start_date:
    :param finish_date:
    :param url:
    :return:
    """
    metrics = [{'name': 'sessions'}, {'name': 'engagedSessions'}, {'name': 'transactions'}]
    dimensions = [{'name': 'date'}, {'name': 'landingPage'}]
    custom_filter = 'landingPage'
    filter_type = 'exact'

    google_response = request_google_core_api(user_id=user_id,
                                              view_id=view_id,
                                              start_date=start_date,
                                              finish_date=finish_date,
                                              metrics=metrics,
                                              dimensions=dimensions,
                                              url_item=url,
                                              custom_filter=custom_filter,
                                              filter_type=filter_type,
                                              access_token=access_token)
    try:
        for row in iter(google_response):  # Iterate over yielded chunk of data
            current_date_datetime = datetime.strptime(row['dimensionValues'][0]['value'], '%Y%m%d')
            current_date = to_date(current_date_datetime)
            # if row.get('dimensions', [])[1] == uri:
            current_sessions = int(row.get('metricValues')[0]['value'])
            current_bounces = int(row.get('metricValues')[1]['value'])
            current_trans = int(row.get('metricValues')[2]['value'])

            ga_stats_dict.setdefault(url, {})
            ga_stats_dict[url].setdefault('metrics', {})
            ga_stats_dict[url]['metrics'].setdefault(current_date, {})
            ga_stats_dict[url]['metrics'][current_date]['landing'] = current_sessions
            ga_stats_dict[url]['metrics'][current_date]['bounces'] = current_bounces
            ga_stats_dict[url]['metrics'][current_date]['transactions'] = current_trans
    except KeyError:
        pprint(google_response)

    return ga_stats_dict


def update_pageviews(user_id, view_id, start_date, finish_date, url, ga_stats_dict, access_token):
    """
    Sends parameters related to pageviews to GA function, gets response by chunks,
    parses it and updates the GA stats dict
    :param user_id:
    :param access_token:
    :param url:
    :param view_id:
    :param start_date:
    :param finish_date:
    :param ga_stats_dict:
    :return:
    """
    metrics = [{'name': 'screenPageViews'}]
    dimensions = [{'name': 'date'}, {'name': 'landingPage'}]
    custom_filter = 'landingPage'
    filter_type = 'contains'

    google_response = request_google_core_api(user_id=user_id,
                                              view_id=view_id,
                                              start_date=start_date,
                                              finish_date=finish_date,
                                              metrics=metrics,
                                              dimensions=dimensions,
                                              url_item=url,
                                              custom_filter=custom_filter,
                                              filter_type=filter_type,
                                              access_token=access_token)
    try:
        for row in iter(google_response):
            current_date_datetime = datetime.strptime(row.get('dimensionValues')[0]['value'], '%Y%m%d')
            current_date = to_date(current_date_datetime)

            pageviews = int(row.get('metricValues')[0]['value'])
            ga_stats_dict.setdefault(url, {})
            ga_stats_dict[url].setdefault('metrics', {})
            ga_stats_dict[url]['metrics'].setdefault(current_date, {})
            ga_stats_dict[url]['metrics'][current_date]['pageviews'] = pageviews
    except KeyError:
        raise Exception(google_response)
    return ga_stats_dict


def get_error_reason(resp):
    """Calculate the reason for the error from the Google response content."""
    reason = None
    error_details = None
    try:
        if isinstance(resp, dict):
            reason = resp['error']['message']
            if 'details' in resp['error']:
                error_details = resp['error']['details']
        elif isinstance(resp, list) and len(resp) > 0:
            first_error = resp[0]
            reason = first_error['error']['message']
            if 'details' in first_error['error']:
                error_details = first_error['error']['details']
    except (ValueError, KeyError, TypeError):
        pass
    if reason is None:
        reason = ''
    return reason, error_details


def request_google_core_api(user_id, view_id, start_date, finish_date, metrics, dimensions, custom_filter, filter_type, url_item,
                            access_token):
    """
    Sends requests with metrics and dates to Google Core API,
    gets requested data as JSON and yields responses by chunks.
    :param access_token:
    :param user_id:
    :param url_item:
    :param custom_filter:
    :param view_id:
    :param start_date:
    :param finish_date:
    :param metrics:
    :param dimensions:
    :return:
    """
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{view_id}:batchRunReports"
    uri = take_uri(url_item)

    #page_token = '0'

    #while page_token is not None:

    body = {
        "requests": [
            {
                "dateRanges": [
                    {
                        "startDate": start_date,
                        "endDate": finish_date
                        #"startDate": "2023-08-20",
                        #"endDate": "2023-08-27"
                    }
                ],
                "metrics": metrics,
                "dimensions": dimensions,
                "limit": 5000,
                #"return_property_quota": "true",
                "dimensionFilter": {
                    "filter": {
                        "fieldName": custom_filter,
                        "stringFilter": {
                            #"matchType": "EXACT",
                            "matchType": filter_type,
                            "value": uri
                        }
                    }
                }
            }
        ]
    }

    for n in range(0, 5):

            try:
                params = {"access_token": access_token, "quotaUser": str(user_id)}
                r = requests.post(url, json=body, params=params)
                google_response = r.json()

                if google_response.get('error'):
                    if google_response['error']['code'] in [429]:
                        time.sleep((2 ** n) + random.random())

                    elif google_response['error']['code'] in [401]:
                        raise Exception('Request had invalid authentication credentials.')

                    elif google_response['error']['code'] in [403]:
                        raise Exception('User does not have sufficient permissions for this profile.')

                    elif google_response['error']['code'] in [400]:
                        raise Exception(google_response['error']['message'])

                    else:
                        raise Exception('Something went wrong')
                else:

                    if len(google_response.get('reports', [])) >= 1:
                        #page_token = google_response.get('reports', [])[0].get('nextPageToken')
                        for report in google_response.get('reports', []):
                            for row in report.get('rows', []):
                                yield row
                        break

                    else:
                        raise Exception('Google request or response is bad')

            except requests.exceptions.ConnectionError:
                raise Exception(
                    'Something is wrong with connection between the server and data source! Try again later!')

            except Exception as e:
                raise Exception(str(e))
