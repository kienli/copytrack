from flask import flash, redirect, url_for, session
from flask_login import current_user
from flask_dance.consumer import OAuth2ConsumerBlueprint
from flask_dance.consumer import oauth_authorized, oauth_error
from sqlalchemy.orm.exc import NoResultFound

from webproject import db


ga_blueprint = OAuth2ConsumerBlueprint(
    "ga-oauth", __name__,
    base_url="https://www.googleapis.com/",
    token_url="https://accounts.google.com/o/oauth2/token",
    authorization_url="https://accounts.google.com/o/oauth2/auth",
    authorization_url_params={"access_type": "offline"},
    auto_refresh_url="https://accounts.google.com/o/oauth2/token",
    scope="https://www.googleapis.com/auth/analytics.readonly",
    redirect_url="/account#api"
)

ga_blueprint.from_config["client_id"] = "GOOGLE_OAUTH_CLIENT_ID"
ga_blueprint.from_config["client_secret"] = "GOOGLE_OAUTH_CLIENT_SECRET"


from webproject.models import OAuth, GaView
from webproject.core.ga_view import get_views


@oauth_authorized.connect_via(ga_blueprint)
def ga_logged_in(blueprint, token):
    if not token:
        flash('Failed to connect to Google Analytics.', 'danger')
        return False

    # Find this OAuth token in the database, or create it
    query = OAuth.query.filter_by(
        provider=blueprint.name,
        user_id=current_user.id,
    )

    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(
            provider=blueprint.name,
            user_id=current_user.id,
            token=token,
        )

    db.session.add(oauth)
    db.session.commit()

    if len(GaView.query.filter_by(user_id=current_user.id).all()) == 0:
        get_views()
        if len(GaView.query.filter_by(user_id=current_user.id).all()) == 0:
            flash("You don't have any Google Analytics properties to search in. Connect another account", 'danger')
            return redirect(url_for('core.dashboard', project_id=session['project']))

    flash('Your Google Analytics account is successfully connected!', 'success')

    return False


# notify on OAuth provider error
@oauth_error.connect_via(ga_blueprint)
def ga_error(blueprint, error, error_description=None, error_uri=None):
    msg = (
        "OAuth error! "
        "error={error} description={description} uri={uri}"
    ).format(
        name=blueprint.name,
        error=error,
        description=error_description,
        uri=error_uri,
    )
    flash(msg, 'danger')
