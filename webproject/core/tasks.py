import sys
import json
from webproject.core.general import take_domain, to_date
from webproject import create_app
from rq import get_current_job
from webproject import db
from webproject.models import Task, Url, User, GaView

from webproject.core.update_stats import update_stats

app = create_app()
app.app_context().push()


def _set_task_progress(progress, failed=0):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.meta['failed'] = failed
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress,
                                                     'failed': failed})
        if progress >= 100:
            task.complete = True
        db.session.commit()


def _inform_exceptions(e):
    job = get_current_job()
    if job:
        task = Task.query.get(job.get_id())
        task.user.add_notification('error', {'task_id': job.get_id(), 'message': e})
        db.session.commit()


def update_urls(*args, **kwargs):
    access_token = kwargs['access_token']
    user_id = kwargs['user_id']
    project_id = kwargs['project_id']

    try:
        user = User.query.get(user_id)

        urls = Url.query.filter_by(user_id=user_id, project_id=project_id).all()

        authorized_urls, not_authorized_urls = get_authorized_urls(urls, user_id)

        total_links = len(authorized_urls)

        if total_links == 0 or len(urls) == 0:
            _set_task_progress(100)
            return False

        with app.app_context():
            i = 0
            _set_task_progress(0)
            for url_item in authorized_urls:
                update_stats(user_id=user_id,
                             url=url_item.url,
                             old_link=url_item.old_url,
                             url_id=url_item.id,
                             human_date=to_date(url_item.date),
                             period_list=json.loads(user.pref.periods),
                             access_token=access_token)
                i += 1
                _set_task_progress(100 * i // total_links)
            if len(not_authorized_urls) > 0:
                _inform_exceptions(f"The following links are not authorized to check: {','.join(not_authorized_urls)}")

    except Exception as e:
        _set_task_progress(100, failed=1)
        _inform_exceptions(str(e))
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())

        # raise Exception(f'Task failed: {e}')


def update_single_url(*args, **kwargs):
    access_token = kwargs['access_token']
    user_id = kwargs['user_id']
    url_id = kwargs['url_id']

    try:
        user = User.query.get(user_id)

        url_item = Url.query.get(url_id)
        url_list = [url_item]

        authorized_urls, not_authorized_urls = get_authorized_urls(url_list, user_id)

        total_links = 1

        if total_links == 0:
            _set_task_progress(100)
            return False

        with app.app_context():
            i = 0
            _set_task_progress(0)

            update_stats(user_id=user_id,
                         url=url_item.url,
                         url_id=url_item.id,
                         old_link=url_item.old_url,
                         human_date=to_date(url_item.date),
                         period_list=json.loads(user.pref.periods),
                         access_token=access_token)
            i += 1
            _set_task_progress(100 * i // total_links)

        if len(not_authorized_urls) > 0:
            _inform_exceptions(f"The following links are not authorized to check: {not_authorized_urls}")

    except Exception as e:
        _set_task_progress(100, failed=1)
        _inform_exceptions(str(e))
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())


def get_authorized_urls(urls, user_id):
    authorized_urls = []
    not_authorized_urls = []
    ga_view_urls = []

    # Collect list of GA URLs to compare with

    for url in GaView.query.filter_by(user_id=user_id,
                                      active=True).all():
        ga_view_urls.append(take_domain(url.url))

    # Compare each user link with GA URLs

    for url in urls:
        current_url = take_domain(url.url)
        if current_url in ga_view_urls:
            authorized_urls.append(url)
        else:
            not_authorized_urls.append(url.url)
    return authorized_urls, not_authorized_urls
