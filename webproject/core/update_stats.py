import os
from datetime import datetime, timedelta

from webproject import db
from webproject.core.ga import detect_view, update_landing, update_pageviews
from webproject.core.general import to_date, to_datetime
from webproject.models import Stats
from pprint import pprint

curr_path = os.path.abspath(os.path.dirname(__file__))


def update_db(url_id, metric, period, value):
    entry = Stats.query.filter_by(url_id=url_id,
                                  metric=metric,
                                  period=period).first()
    if not entry:

        entry = Stats(
            url_id=url_id,
            metric=metric,
            period=period,
            value=str(value)[:6]
        )
    else:

        # if not existing_entry.value or existing_entry.value == "None":
        entry.value = str(value)[:6]

    db.session.add(entry)


def update_stats(user_id, url, url_id, human_date, period_list, access_token, old_link=None):
    """

    """

    metrics = ('pageviews', 'landing', 'bounces', 'transactions')

    ga_stats_dict = {}

    view_id, time_shift = detect_view(user_id, url)

    yesterday = datetime.today() - timedelta(hours=time_shift) - timedelta(days=1)

    date_datetime = to_datetime(human_date)

    min_value = max_value = date_datetime

    for period in period_list:
        if date_datetime + timedelta(days=period) <= yesterday:
            max_value = date_datetime + timedelta(days=period)
            min_value = date_datetime - timedelta(days=period)

    start_date = to_date(min_value)
    finish_date = to_date(max_value)

    update_landing(user_id=user_id,
                   view_id=view_id,
                   start_date=start_date,
                   finish_date=finish_date,
                   url=url,
                   ga_stats_dict=ga_stats_dict,
                   access_token=access_token)

    update_pageviews(user_id=user_id,
                     view_id=view_id,
                     start_date=start_date,
                     finish_date=finish_date,
                     url=url,
                     ga_stats_dict=ga_stats_dict,
                     access_token=access_token)

    if old_link:
        update_landing(user_id=user_id,
                       view_id=view_id,
                       start_date=start_date,
                       finish_date=finish_date,
                       url=old_link,
                       ga_stats_dict=ga_stats_dict,
                       access_token=access_token)

        update_pageviews(user_id=user_id,
                         view_id=view_id,
                         start_date=start_date,
                         finish_date=finish_date,
                         url=old_link,
                         ga_stats_dict=ga_stats_dict,
                         access_token=access_token)

    for period in period_list:
        start_datetime = date_datetime - timedelta(days=period)
        change_datetime = date_datetime
        finish_datetime = date_datetime + timedelta(days=period)

        if (yesterday - change_datetime).days < period:

            continue  # Skip the period, if the period is not passed yet
        else:
            for metric in metrics:
                metric_before = metric_after = 0

                if ga_stats_dict.get(url):
                    new_metric_before, new_metric_after = update_metric(url=url,
                                                                        start_datetime=start_datetime,
                                                                        change_datetime=change_datetime,
                                                                        end_datetime=finish_datetime,
                                                                        stats_dict=ga_stats_dict,
                                                                        metric=metric)

                    metric_before += new_metric_before
                    metric_after += new_metric_after

                if old_link and ga_stats_dict.get(old_link):
                    old_metric_before, old_metric_after = update_metric(url=old_link,
                                                                        start_datetime=start_datetime,
                                                                        change_datetime=change_datetime,
                                                                        end_datetime=finish_datetime,
                                                                        stats_dict=ga_stats_dict,
                                                                        metric=metric)

                    metric_before += old_metric_before
                    metric_after += old_metric_after

                try:
                    metric_change = (metric_after - metric_before) / metric_before

                except ZeroDivisionError:
                    if metric_after == 0:
                        metric_change = 0
                    else:
                        metric_change = 1

                # Save metric before

                update_db(url_id=url_id, metric=metric, period=str('-' + str(period)), value=metric_before)

                # Save metric after

                update_db(url_id=url_id, metric=metric, period=str(period), value=metric_after)

                # Save metric change

                update_db(url_id=url_id, metric=metric + '_change', period=str(period), value=metric_change)

                db.session.commit()

    return None


def update_metric(url, start_datetime, change_datetime, end_datetime, stats_dict, metric):
    metric_before = metric_after = 0

    while start_datetime < change_datetime:
        curr_day_before = to_date(start_datetime)

        metric_before += stats_dict.get(url, {}).get('metrics', {}).get(curr_day_before, {}).get(metric, 0)

        start_datetime += timedelta(days=1)

    while change_datetime < end_datetime:
        curr_day_after = to_date(change_datetime)

        metric_after += stats_dict.get(url, {}).get('metrics', {}).get(curr_day_after, {}).get(metric, 0)

        change_datetime += timedelta(days=1)

    return metric_before, metric_after
