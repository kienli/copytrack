import json
from flask import redirect, url_for, flash
from sqlalchemy.orm.exc import NoResultFound
from webproject import db
from webproject.models import User, OAuth, Prefs, Projects
from flask_dance.contrib.google import make_google_blueprint
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_login import login_user

google_blueprint = make_google_blueprint(
    # client_id=current_app.config['GOOGLE_OAUTH_CLIENT_ID'],
    # client_secret=current_app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    offline=True,
    scope=["https://www.googleapis.com/auth/userinfo.email"]
)

google_blueprint.from_config["client_id"] = "GOOGLE_OAUTH_CLIENT_ID"
google_blueprint.from_config["client_secret"] = "GOOGLE_OAUTH_CLIENT_SECRET"


# create/login local user on successful OAuth login
@oauth_authorized.connect_via(google_blueprint)
def google_logged_in(blueprint, token):
    if not token:
        flash('Failed to log in with Google.', 'danger')
        return False

    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        msg = "Failed to fetch user info from Google."
        flash(msg, 'danger')
        return False

    google_info = resp.json()
    google_user_id = str(google_info["id"])

    # Find this OAuth token in the database, or create it
    query = OAuth.query.filter_by(
        provider=blueprint.name,
        provider_user_id=google_user_id,
    )
    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(
            provider=blueprint.name,
            provider_user_id=google_user_id,
            token=token,
        )

    if oauth.user:
        login_user(oauth.user, remember=True)
        flash('Successfully signed in with Google.', 'success')

    else:
        # Create a new local user account for this user

        existing_email = User.query.filter_by(email=google_info['email'].lower()).first()
        if existing_email is not None:
            flash('Failed to log in with Google. This email has been already registered!', 'danger')
            return redirect(url_for('users.login'))

        username = google_info['email'].lower()

        existing_username = User.query.filter_by(username=username).first()
        if existing_username is not None:
            username = google_info['email'].lower() + '_' + str(google_info["id"])

        user = User(
            email=google_info['email'].lower(),
            username=username,
        )
        # Associate the new local user account with the OAuth token
        oauth.user = user
        # Save and commit our database models
        db.session.add_all([user, oauth])
        db.session.commit()
        default_prefs = Prefs(user_id=user.id, periods=json.dumps([7, 14, 21]))
        default_project = Projects(name='Default project',
                                   user_id=user.id,
                                   description='My first project')
        db.session.add(default_project)
        db.session.add(default_prefs)
        db.session.commit()
        # Log in the new local user account
        login_user(user, remember=True)
        flash('Successfully signed in with Google.', 'success')

    return False


# notify on OAuth provider error
@oauth_error.connect_via(google_blueprint)
def google_error(blueprint, error, error_description=None, error_uri=None):
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
