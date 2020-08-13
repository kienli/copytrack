from flask import render_template, current_app
from webproject.email import send_email
from flask_dance.contrib.google import google


def send_password_reset_email(user):

    token = user.get_reset_password_token()

    send_email('[CopyTrack] Reset Your Password',
               sender=current_app.config['MAIL_USERNAME'],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt', user=user, token=token),
               html_body=render_template('email/reset_password.html', user=user, token=token)
               )


def send_google_oauth_reminder(user):
    send_email('[CopyTrack] Reset Your Password',
               sender=current_app.config['MAIL_USERNAME'],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt', user=user, google=google),
               html_body=render_template('email/google_oauth_reminder.html', user=user, google=google)
               )
