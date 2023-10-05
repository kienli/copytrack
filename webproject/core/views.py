import os
import json

import urllib.parse
from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, send_from_directory, url_for, jsonify, session)

from flask_login import current_user, login_required
# from pprint import pprint
from sqlalchemy.orm.exc import UnmappedInstanceError

from webproject import db

from webproject.core.forms import AddUrlForm, EditUrlForm, AddProjectForm, EditProjectForm

from webproject.models import Stats, Url, OAuth, Notification, Projects
from webproject.users.ga_oauth import ga_blueprint

from webproject.core.general import clean_url, human_to_datetime, to_human_date

from oauthlib.oauth2.rfc6749.errors import InvalidClientIdError, InvalidGrantError

core = Blueprint('core', __name__)


@core.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:

        projects = Projects.query.filter_by(user_id=current_user.id).order_by(Projects.id.asc())
    else:
        projects = []

    add_project_form = AddProjectForm()
    edit_project_form = EditProjectForm()

    add_project_error = False

    if add_project_form.project_submit.data and add_project_form.validate():
        add_project = Projects(
            name=add_project_form.project_name.data.strip(),
            description=add_project_form.project_description.data.strip(),
            user_id=current_user.id,
            notifications=add_project_form.project_notifications.data
        )

        db.session.add(add_project)
        db.session.commit()

        flash('Project successfully created!', 'success')

        return redirect(url_for('core.index'))

    else:
        if add_project_form.project_submit.data:
            add_project_error = True

    edit_project_error = False

    if edit_project_form.edit_project_submit.data and edit_project_form.validate():
        edited_project = Projects.query.get(int(edit_project_form.hidden_project_edit.data))

        edited_project.name = edit_project_form.edit_project_name.data.strip()
        edited_project.description = edit_project_form.edit_project_description.data.strip()
        edited_project.notifications = edit_project_form.edit_project_notifications.data

        db.session.add(edited_project)
        db.session.commit()

        flash('Project successfully edited!', 'success')

        return redirect(url_for('core.index'))
    else:

        # Pass error flag to the template

        if edit_project_form.edit_project_submit.data:
            edit_project_error = True

    return render_template('index.html', projects=projects, add_project_form=add_project_form,
                           edit_project_form=edit_project_form, add_project_error=add_project_error,
                           edit_project_error=edit_project_error)


@core.route('/project/<int:project_id>/', methods=['GET', 'POST'])
@login_required
def dashboard(project_id):
    session['project'] = project_id

    # Check if the user has permission to see the project

    project = Projects.query.get(project_id)

    allowed_projects = set([x.id for x in Projects.query.filter_by(user_id=current_user.id).all()])

    if project_id not in allowed_projects:
        flash("You don't have permission to see this project!", 'danger')

        return redirect(url_for('core.index'))

    # Handle forms

    add_form = AddUrlForm()
    edit_form = EditUrlForm()

    # Add URL form

    add_form_error = False

    if add_form.submit_add.data and add_form.validate():

        add_new_url = Url(url=clean_url(urllib.parse.unquote(add_form.url_add.data).strip()),
                          old_url=clean_url(urllib.parse.unquote(add_form.old_url_add.data).strip()),
                          description=str(add_form.description_add.data),
                          date=human_to_datetime(add_form.datetimepicker.data),
                          user_id=current_user.id,
                          project_id=project_id)

        if add_new_url.url[len(add_new_url.url)-1] == '/':
            add_new_url.url = add_new_url.url[:-1]

        db.session.add(add_new_url)
        db.session.commit()

        flash('Url successfully added!', 'success')

        # Automatic update of the new added URL

        if ga_blueprint.session.authorized:
            update_single_url(add_new_url.id)

        return redirect(url_for('core.dashboard', project_id=project_id))

    else:
        # Pass error flag to the template

        if add_form.submit_add.data:
            add_form_error = True

    # Edit URL form

    edit_form_error = False

    if edit_form.submit_edit.data and edit_form.validate():

        edited_url = Url.query.get(int(edit_form.hidden_edit.data))

        edited_url.url = clean_url(urllib.parse.unquote(edit_form.url_edit.data))
        edited_url.old_url = clean_url(urllib.parse.unquote(edit_form.old_url_edit.data))
        edited_url.description = str(edit_form.description_edit.data)
        edited_url.date = human_to_datetime(edit_form.datetimepicker_edit.data)

        db.session.add(edited_url)
        db.session.commit()

        if ga_blueprint.session.authorized:

            # Delete stats for the url

            Stats.delete_url_stats(url_id=edited_url.id)

            db.session.commit()

            # Automatic update of the edited URL

            update_single_url(edited_url.id)

        flash('Url successfully updated!', 'success')

        return redirect(url_for('core.dashboard', project_id=session['project']))

    else:

        # Pass error flag to the template

        if edit_form.submit_edit.data:
            edit_form_error = True

    # Define sorting of links

    if not current_user.pref.sorting:

        urls = Url.query.filter_by(user_id=current_user.id,
                                   project_id=project_id).order_by(Url.pub_date.asc())

    else:

        urls = Url.query.filter_by(user_id=current_user.id,
                                   project_id=project_id).order_by(Url.pub_date.desc())

    # Retrieve periods

    dashboard_dict = {}

    if current_user.pref.periods:
        periods_list = [str(s) for s in json.loads(current_user.pref.periods)]
    else:
        periods_list = list()

    all_periods = list()
    for item in periods_list:
        all_periods.append(str(item))
        all_periods.append('-' + str(item))

    metrics = ('pageviews', 'pageviews_change', 'landing', 'landing_change', 'bounces',
               'transactions', 'transactions_change')

    for url in urls:
        dashboard_dict.setdefault(url.id, {})
        for period in all_periods:
            dashboard_dict[url.id].setdefault(period, {})
            for metric in metrics:
                dashboard_dict[url.id][period].setdefault(metric, 0)
                value = Stats.query.filter_by(url_id=url.id,
                                              period=period,
                                              metric=metric).first()
                try:
                    dashboard_dict[url.id][period][metric] = value.value
                except Exception:
                    # print(e)
                    dashboard_dict[url.id][period][metric] = None

    if 'bounces' in metrics:
        for url in urls:
            for period in periods_list:
                try:
                    dashboard_dict[url.id][str(period)]['bounce_rate'] = str(
                        (int(dashboard_dict[url.id][str(period)]['landing']) -
                        int(dashboard_dict[url.id][str(period)]['bounces'])) /
                        int(dashboard_dict[url.id][str(period)]['landing']))
                except ZeroDivisionError:
                    dashboard_dict[url.id][str(period)]['bounce_rate'] = str(0)
                except TypeError:
                    dashboard_dict[url.id][str(period)]['bounce_rate'] = None

                try:
                    dashboard_dict[url.id]['-' + str(period)]['bounce_rate'] = str(
                        (int(dashboard_dict[url.id]['-' + str(period)]['landing']) -
                        int(dashboard_dict[url.id]['-' + str(period)]['bounces'])) /
                        int(dashboard_dict[url.id]['-' + str(period)]['landing']))
                except ZeroDivisionError:
                    dashboard_dict[url.id]['-' + str(period)]['bounce_rate'] = str(0)
                except TypeError:
                    dashboard_dict[url.id]['-' + str(period)]['bounce_rate'] = None

                try:
                    dashboard_dict[url.id][str(period)]['bounce_rate_change'] = \
                        str((float((dashboard_dict[url.id][str(period)]['bounce_rate'])) - float(
                            dashboard_dict[url.id]['-' + str(period)][
                                'bounce_rate'])) / float(dashboard_dict[url.id]['-' + str(period)]['bounce_rate']))
                except ZeroDivisionError:
                    if float(dashboard_dict[url.id][str(period)]['bounce_rate']) == 0:
                        dashboard_dict[url.id][str(period)]['bounce_rate_change'] = str(0)
                    else:
                        dashboard_dict[url.id][str(period)]['bounce_rate_change'] = str(1)
                except TypeError:
                    dashboard_dict[url.id][str(period)]['bounce_rate_change'] = None

    # pprint(dashboard_dict)
    return render_template('dashboard.html', urls=urls, add_form=add_form, edit_form=edit_form,
                           add_form_error=add_form_error, edit_form_error=edit_form_error, stats=dashboard_dict,
                           periods_list=periods_list, ga_blueprint=ga_blueprint, project=project)


@core.route('/delete/<url_id>')
@login_required
def delete_url(url_id):

    Url.delete(int(url_id))

    db.session.commit()

    flash('URL and stats are successfully deleted!', 'success')

    return redirect(url_for('core.dashboard', project_id=session['project']))


@core.route('/delete-project/<int:project_id>')
@login_required
def delete_project(project_id):

    Projects.delete(project_id)

    db.session.commit()

    flash('Project successfully deleted!', 'success')

    return redirect(url_for('core.index'))


@core.route('/edit/<int:url_id>')
@login_required
def edit_url(url_id):
    url_edit = Url.query.get(int(url_id))

    return jsonify({
        'id': url_edit.id,
        'url': url_edit.url,
        'date': to_human_date(url_edit.date),
        'old_url': url_edit.old_url,
        'description': url_edit.description,
    })


@core.route('/edit-project/<int:project_id>')
@login_required
def edit_project(project_id):
    project_edit = Projects.query.get(int(project_id))
    project_notifications = 'on' if project_edit.notifications else 'off'
    return jsonify({
        'id': project_edit.id,
        'name': project_edit.name,
        'description': project_edit.description,
        'project_notifications': project_notifications,
    })


@core.route('/update/<int:url_id>')
@login_required
def update_single_url(url_id):
    url = Url.query.get(int(url_id))

    if ga_blueprint.session.authorized:
        try:
            ga_blueprint.session.get('https://analyticsadmin.googleapis.com/v1beta/accountSummaries')
        except (InvalidClientIdError, InvalidGrantError):
            flash('Your one hour Google session without refresh token has expired. Please submit the request again',
                  'danger')
            to_del = OAuth.query.filter_by(user_id=current_user.id,
                                           provider='ga-oauth').first()
            db.session.delete(to_del)
            db.session.commit()

            return redirect(url_for('ga-oauth.login'))

        current_user.launch_task('update_single_url', f'Updating single url: {url.url}...',
                                 user_id=current_user.id,
                                 access_token=ga_blueprint.session.token['access_token'],
                                 url_id=url_id)

        db.session.commit()

    else:
        flash("Cannot retrieve Google Analytics data. Please connect it!", 'danger')

    return redirect(url_for('core.dashboard', project_id=session['project']))


@core.route('/update-stats')
@login_required
def update_all_urls():
    if ga_blueprint.session.authorized:
        if current_user.get_task_in_progress('update_urls'):
            flash('Stats update is currently in progress', 'danger')
        else:
            try:
                ga_blueprint.session.get('https://analyticsadmin.googleapis.com/v1beta/accountSummaries')

            except (InvalidClientIdError, InvalidGrantError):

                flash('Your one hour Google session without refresh token has expired. Please submit the request again',
                      'danger')
                to_del = OAuth.query.filter_by(user_id=current_user.id,
                                               provider='ga-oauth').first()
                db.session.delete(to_del)
                db.session.commit()

                return redirect(url_for('ga-oauth.login'))

            current_user.launch_task('update_urls', 'Updating stats...',
                                     user_id=current_user.id,
                                     access_token=ga_blueprint.session.token['access_token'],
                                     project_id=session['project'])

            db.session.commit()

    else:
        flash("Cannot retrieve Google Analytics data. Please connect it!", 'danger')

    return redirect(url_for('core.dashboard', project_id=session['project']))


@core.route('/delete-all')
@login_required
def delete_all_links():

    Url.delete_all(user_id=current_user.id)

    return redirect(url_for('core.dashboard', project_id=session['project']))


@core.route('/info')
def info():
    return render_template('info.html')


@core.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@core.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    my_notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in my_notifications])
