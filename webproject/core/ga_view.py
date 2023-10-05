from webproject.users.ga_oauth import ga_blueprint
from webproject.models import GaView
from flask_login import current_user
from webproject import db
import pendulum

# from pprint import pprint


def get_account_summaries():
    account_response = ga_blueprint.session.get('https://analyticsadmin.googleapis.com/v1beta/accountSummaries')
    account_summaries = account_response.json()
    return account_summaries


def save_views(account_summary):
    for account in account_summary.get('accountSummaries', []):
        if account:
            for property_item in account.get('propertySummaries', []):
                if property_item:
                    is_activ = 0  # Only one active profile for each property is allowed
                    new_profile = GaView(
                        user_id=current_user.id,
                        username=account.get('name'),
                        account_name=account.get('displayName'),
                        account_id=account.get('account').replace('account/', ''),
                        property_name=property_item.get('displayName'),
                        property_id=property_item.get('property'),
                        url=('https://' + property_item.get('displayName')).replace(' - GA4', ''),
                        profile_name=property_item.get('displayName'),
                        profile_id=property_item.get('property').replace('properties/', ''),
                        active=True if is_activ < 1 else False
                    )
                db.session.add(new_profile)
                is_activ += 1

    db.session.commit()


def tz_diff(user_tz, ga_tz):
    now = pendulum.now()
    user_tz_dt = pendulum.datetime(now.year, now.month, now.day, tz=user_tz)
    ga_tz_dt = pendulum.datetime(now.year, now.month, now.day, tz=ga_tz)
    # TODO: Compare with Google timezones and handle the exceptions
    diff = user_tz_dt.diff(ga_tz_dt, False).in_hours()

    return diff


def get_timezones():

    # TODO: Schedule it for once a day

    for profile in GaView.query.filter_by(user_id=current_user.id).all():
        view_url = f"https://analyticsadmin.googleapis.com/v1beta/" \
            f"{profile.property_id}"

        view_response = ga_blueprint.session.get(view_url)
        view_summary = view_response.json()
        profile.timezone = str(view_summary.get('timeZone'))

        user_tz = current_user.pref.timezone
        ga_tz = str(view_summary.get('timeZone'))

        profile.time_shift = tz_diff(user_tz=user_tz, ga_tz=ga_tz)

        db.session.add(profile)
    db.session.commit()


def get_views():
    account_summaries = get_account_summaries()
    save_views(account_summaries)
    get_timezones()
