from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import current_user

from webproject import db
from webproject.models import OAuth

from oauthlib.oauth2.rfc6749.errors import InvalidClientIdError

error_pages = Blueprint('error_pages', __name__)


@error_pages.app_errorhandler(404)
def error_404(error):
    return render_template('error_pages/404.html'), 404


@error_pages.app_errorhandler(403)
def error_403(error):
    return render_template('error_pages/403.html'), 403


@error_pages.app_errorhandler(500)
def error_500(error):
    db.session.rollback()
    return render_template('error_pages/500.html'), 500


@error_pages.errorhandler(InvalidClientIdError)
def token_expired():
    """
    """
    # del ga_blueprint.session.token
    # TODO: Add better solution for expired token, this doesn't work
    flash('Your session had expired. Please submit the request again',
          'danger')
    to_del = OAuth.query.filter_by(user_id=current_user.id).filter_by(provider='ga-oauth').first()
    db.session.delete(to_del)
    db.session.commit()

    return redirect(url_for('ga-oauth.login'))
    # return redirect(url_for('core.index'))
