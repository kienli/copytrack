from flask import Blueprint, flash, redirect, render_template, request, url_for, session
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.urls import url_parse

from webproject import db
from webproject.models import Prefs, User, OAuth, GaView, Task, Notification, Url, Stats, Projects

from webproject.users.forms import (LoginForm, RegistrationForm, UpdateUserForm,
                                    DashboardSettingsForm, ResetPasswordRequestForm, ResetPasswordForm)
#  from webproject.users.picture_handler import add_profile_pic
import json

from webproject.users.ga_oauth import ga_blueprint
from webproject.users.reset_email import send_password_reset_email, send_google_oauth_reminder

from webproject.core.views import update_all_urls

# from webproject.core.general import to_datetime

from webproject.core.ga_view import tz_diff

from flask_dance.contrib.google import google

users = Blueprint('users', __name__)


@users.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(email=form.email.data.lower(),
                    username=form.username.data,
                    password=form.password.data)

        db.session.add(user)
        db.session.commit()

        default_prefs = Prefs(user_id=user.id,
                              periods=json.dumps([7, 14, 21]),
                              timezone=str(
                                  form.timezone_hidden.data) if form.timezone_hidden.data else 'Asia/Yekaterinburg')

        default_project = Projects(name='Default project',
                                   user_id=user.id,
                                   description='My first project')

        db.session.add(default_prefs)
        db.session.add(default_project)
        db.session.commit()

        login_user(user, remember=True)

        flash('Thanks for registration!', 'info')

        return redirect(url_for('core.index'))

        #  return redirect(url_for('users.login'))

    return render_template('register.html', form=form, google=google)


@users.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')

            return redirect(url_for('users.login'))

        login_user(user, remember=form.remember_me.data)

        next_page = request.args.get('next')

        if not next_page or not next_page[0] == '/' or url_parse(next_page).netloc != '':
            next_page = url_for('core.index')

        return redirect(next_page)

    return render_template('login.html', form=form, google=google)


@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("core.index"))


def get_profiles():
    prof_dict = {}
    for profile in current_user.gaview:
        prof_dict.setdefault(profile.username, {})
        prof_dict[profile.username].setdefault(profile.account_id, {})
        prof_dict[profile.username][profile.account_id]['account_name'] = profile.account_name
        prof_dict[profile.username][profile.account_id].setdefault('properties', {})
        prof_dict[profile.username][profile.account_id]['properties'].setdefault(profile.property_id, {})
        prof_dict[profile.username][profile.account_id]['properties'][profile.property_id][
            'property_name'] = profile.property_name
        prof_dict[profile.username][profile.account_id]['properties'][profile.property_id][
            'property_url'] = profile.url
        prof_dict[profile.username][profile.account_id]['properties'][profile.property_id].setdefault('profiles',
                                                                                                      {})
        prof_dict[profile.username][profile.account_id]['properties'][profile.property_id]['profiles'].setdefault(
            profile.profile_id, {})
        prof_dict[profile.username][profile.account_id]['properties'][profile.property_id]['profiles'][
            profile.profile_id]['profile_name'] = profile.profile_name
        prof_dict[profile.username][profile.account_id]['properties'][profile.property_id]['profiles'][
            profile.profile_id]['active'] = profile.active
    return prof_dict


@users.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    prof_dict = get_profiles()
    profile_form = UpdateUserForm(current_user.username, current_user.email)
    dash_sett_form = DashboardSettingsForm()

    if dash_sett_form.dash_submit.data and dash_sett_form.validate():
        user_pref = Prefs.query.filter_by(user_id=current_user.id).first()
        user_pref.sorting = bool(int(dash_sett_form.sorting.data))

        period_list_row = dash_sett_form.periods.data.strip(',')
        period_list = list(int(s) for s in period_list_row.split(','))
        period_list_sorted = list(set(period_list))
        period_list_sorted = sorted(period_list_sorted)
        user_pref.periods = json.dumps(period_list_sorted)

        db.session.add(user_pref)
        db.session.commit()
        flash('Dashboard Settings Updated!', 'success')
        return redirect(url_for('users.account', _anchor='dashboard'))

    elif dash_sett_form.dash_submit.data and not dash_sett_form.validate():
        profile_form.username.data = current_user.username
        profile_form.email.data = current_user.email
        profile_form.timezone_hidden.data = current_user.pref.timezone

    elif request.method == "GET":
        dash_sett_form.periods.data = ', '.join(str(x) for x in json.loads(current_user.pref.periods))
        dash_sett_form.sorting.data = str(int(current_user.pref.sorting is True))

    if profile_form.profile_submit.data and profile_form.validate():

        # if profile_form.picture.data:
        #     username = current_user.username
        #     pic = add_profile_pic(profile_form.picture.data, username)
        #     current_user.profile_image = pic

        original_timezone = current_user.pref.timezone

        current_user.username = profile_form.username.data
        current_user.email = profile_form.email.data

        user_pref = Prefs.query.filter_by(user_id=current_user.id).first()
        user_pref.timezone = str(profile_form.timezone.data)

        db.session.add(user_pref)

        if str(profile_form.timezone.data) != original_timezone:
            if ga_blueprint.session.authorized:
                ga_views = GaView.query.filter_by(user_id=current_user.id).all()
                for view in ga_views:
                    view.time_shift = tz_diff(user_tz=str(profile_form.timezone.data), ga_tz=view.timezone)
                    db.session.add(view)
        db.session.commit()
        flash('User Account Updated!', 'success')
        return redirect(url_for('users.account', _anchor='profile'))

    elif profile_form.profile_submit.data and not profile_form.validate():
        dash_sett_form.periods.data = ', '.join(str(x) for x in json.loads(current_user.pref.periods))
        dash_sett_form.sorting.data = str(int(current_user.pref.sorting is True))
        # return redirect(url_for('users.account', _anchor='profile'))

    elif request.method == "GET":
        profile_form.username.data = current_user.username
        profile_form.email.data = current_user.email
        profile_form.timezone_hidden.data = current_user.pref.timezone

    if request.method == 'POST' and request.form.get('ga-profiles') == 'ga-profiles':
        data = request.form.to_dict()

        # Reset all active column

        reset = GaView.query.filter_by(user_id=current_user.id).all()

        for profile_entry in reset:
            profile_entry.active = False
            db.session.add(profile_entry)
        db.session.commit()

        # Delete stats from previous profiles

        del_urls = Url.query.filter_by(user_id=current_user.id).all()

        if len(del_urls) > 0:
            for url in del_urls:
                Stats.delete_url_stats(url_id=url.id)
            db.session.commit()

        # Save new active state

        for property_id, profile_id in data.items():
            if property_id != 'ga-profiles':
                entry = GaView.query.filter_by(user_id=current_user.id,
                                               property_id=property_id,
                                               profile_id=profile_id).first()
                entry.active = True
                db.session.add(entry)
        db.session.commit()

        update_all_urls()

        return redirect(url_for('users.account', _anchor='api'))

    elif request.method == 'GET':

        prof_dict = get_profiles()

    # profile_image = url_for('static', filename='profile_pics/' + current_user.profile_image)
    return render_template('account.html', profile_form=profile_form, dash_sett_form=dash_sett_form,
                           ga_blueprint=ga_blueprint, prof_dict=prof_dict)


@users.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))

    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:

            # Check if user has previously authorized with Google OAuth

            if OAuth.query.filter_by(user_id=user.id, provider='google').first():
                send_google_oauth_reminder(user)
            else:
                send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_password_request.html', form=form)


@users.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))

    user = User.verify_reset_password_token(token)

    if not user:
        return redirect(url_for('core.index'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.', 'success')
        return redirect(url_for('users.login'))

    return render_template('reset_password.html', form=form)


@users.route("/ga-login")
@login_required
def ga_login():
    if not ga_blueprint.session.authorized:
        return redirect(url_for('ga-oauth.login'))
    else:
        flash('Your Google Analytics account is already connected!', 'info')
        return redirect(url_for('core.dashboard', project_id=session['project']))


@users.route("/ga-revoke")
@login_required
def ga_revoke():
    if ga_blueprint.session.authorized:

        # Revoke Google access token

        token = ga_blueprint.session.token["access_token"]

        try:
            resp = ga_blueprint.session.post(
                "https://accounts.google.com/o/oauth2/revoke",
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        except:
            pass

        # Delete DB entry

        to_del = OAuth.query.filter_by(user_id=current_user.id,
                                       provider='ga-oauth').first()
        db.session.delete(to_del)

        # Delete GA profiles

        profiles_del = GaView.query.filter_by(user_id=current_user.id).all()

        for profile in profiles_del:
            db.session.delete(profile)

        db.session.commit()
        flash("You have successfully revoked the access", 'success')
        return redirect(url_for('users.account', _anchor='api'))
    else:
        flash("You cannot revoke the access, because you were not authorized", 'info')
        return redirect(url_for('users.account', _anchor='api'))


@users.route("/force-revoke")
@login_required
def force_revoke():
    if ga_blueprint.session.authorized:

        to_del = OAuth.query.filter_by(user_id=current_user.id,
                                       provider='ga-oauth').first()
        db.session.delete(to_del)

        # Delete GA profiles

        GaView.delete_all(user_id=current_user.id)

        db.session.commit()
        flash("You have successfully revoked the access", 'success')

        return redirect(url_for('users.account', _anchor='api'))
    else:
        flash("You cannot revoke the access, because you were not authorized", 'info')
        return redirect(url_for('users.account', _anchor='api'))


@users.route("/upgrade")
def upgrade():
    try:
        # for user in User.query.all():
        # project = Projects(name='Default',
        #                    user_id=user.id,
        #                    description='My first project')
        # db.session.add(project)
        # db.session.commit()
        #
        # for url in Url.query.filter_by(user_id=user.id).all():
        #     url.project_id = project.id
        #
        #     db.session.add(url)
        #
        # db.session.commit()

        #  del_urls = Url.query.filter_by(user_id=user.id).all()
        #
        # if del_urls:
        #     for url in del_urls:
        #         del_stats = Stats.query.filter_by(url_id=url.id).all()
        #
        #         try:
        #             for stats_item in del_stats:
        #                 db.session.delete(stats_item)
        #             db.session.commit()
        #         except Exception:
        #             flash(f'Could not delete stats for the url {url.url}!', 'danger')

        for task in Task.query.all():
            db.session.delete(task)

        for notification in Notification.query.all():
            db.session.delete(notification)

        db.session.commit()
        flash('Upgrade successful!', 'success')

    except Exception as e:
        flash(f'Upgrade failed! Reason: {e}', 'danger')

    return redirect(url_for('core.index'))


@users.route("/privacy-policy")
def privacy_policy():
    return render_template('privacy-policy.html')
