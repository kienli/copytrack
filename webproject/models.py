import jwt
from time import time
import json
from datetime import datetime

import redis
import rq
import rq.exceptions

from flask import current_app, flash
from flask_login import UserMixin, current_user

from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage

from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm.exc import UnmappedInstanceError
from webproject import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    profile_image = db.Column(db.String(64), nullable=False, default='default_profile.png')
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))

    urls = db.relationship('Url', backref='user', lazy=True)
    pref = db.relationship('Prefs', backref='user', lazy=True, uselist=False)
    gaview = db.relationship('GaView', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')
    projects = db.relationship('Projects', backref='user', lazy=True)

    def __init__(self, email, username, password=None):
        self.email = email
        self.username = username
        if password is not None:
            self.password_hash = generate_password_hash(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"Username {self.username}"

    def get_reset_password_token(self, expires_in=3600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            user_id = jwt.decode(token, current_app.config['SECRET_KEY'],
                                 algorithms=['HS256'])['reset_password']
        except Exception:
            return

        return User.query.get(user_id)

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('webproject.core.tasks.' + name, self.id,
                                                *args, **kwargs, job_timeout=600)
        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self, complete=False).first()


class Prefs(db.Model):
    __tablename_ = 'prefs'
    users = db.relationship(User)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sorting = db.Column(db.Boolean, default=False)
    periods = db.Column(db.String(100), nullable=True)
    # TODO: Change the logic for user to select the timezone
    timezone = db.Column(db.String(60), nullable=False, default='Etc/UTC')


class Url(db.Model):
    __tablename__ = 'urls'
    users = db.relationship(User)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    url = db.Column(db.String(1000), nullable=False, index=True)
    old_url = db.Column(db.String(400), nullable=True, index=True)
    description = db.Column(db.String(400), nullable=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    pub_date = db.Column(db.DateTime, nullable=False, index=True, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)

    stats = db.relationship('Stats', backref='url', lazy=True)

    def __init__(self, url, old_url, description, date, user_id, project_id):
        self.url = url
        self.old_url = old_url
        self.description = description
        self.date = date
        self.user_id = user_id
        self.project_id = project_id

    def __repr__(self):
        return f"URL: {self.url} was changed on {self.date} by user: {self.user_id}"

    @staticmethod
    def delete(url_id):
        Stats.delete_url_stats(url_id=url_id)

        url_del = Url.query.get(url_id)

        try:
            db.session.delete(url_del)

        except UnmappedInstanceError:
            flash("Cannot find url to delete!", 'danger')

    @staticmethod
    def delete_all(user_id):

        del_urls = Url.query.filter_by(user_id=user_id).all()

        if len(del_urls) > 0:
            for url in del_urls:
                Url.delete(url.id)
            db.session.commit()

            flash('All URLs are successfully deleted!', 'success')

        else:

            flash('Nothing to be deleted!', 'danger')


class Projects(db.Model):
    __tablename__ = 'projects'

    users = db.relationship(User)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text)
    notifications = db.Column(db.Boolean, default=False)

    @staticmethod
    def delete(project_id):

        project_del_urls = Url.query.filter_by(project_id=project_id).all()

        project_del = Projects.query.get(int(project_id))

        # Delete stats for the url

        for url in project_del_urls:
            Stats.delete_url_stats(url_id=url.id)
            Url.delete(url_id=url.id)
        db.session.commit()

        db.session.delete(project_del)


class Stats(db.Model):
    __tablename__ = 'stats'

    urls = db.relationship(Url)
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('urls.id'), nullable=False)
    metric = db.Column(db.String(30), nullable=False, index=True)
    period = db.Column(db.String(10), nullable=False, index=True)
    value = db.Column(db.String(10), nullable=True, default=None)

    def __repr__(self):
        return f"URL: {self.url_id} has in the metric {self.metric} " \
            f"for the period {self.period} has value {self.value}"

    @staticmethod
    def delete_url_stats(url_id):
        del_stats = Stats.query.filter_by(url_id=url_id).all()

        try:
            for url_item in del_stats:
                db.session.delete(url_item)

        except Exception:
            flash(f'Could not delete stats for the url {url_item.url}!', 'danger')


class OAuth(OAuthConsumerMixin, db.Model):
    provider_user_id = db.Column(db.String(256), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship(User)

    @staticmethod
    # TODO: finish delete
    def delete():
        pass


class GaView(db.Model):
    __tablename__ = 'gaview'
    users = db.relationship(User)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(100), nullable=True)
    account_name = db.Column(db.String(100), nullable=True)
    account_id = db.Column(db.String(100), nullable=True)
    property_name = db.Column(db.String(100), nullable=True)
    property_id = db.Column(db.String(100), nullable=True)
    url = db.Column(db.String(100), nullable=True)
    profile_name = db.Column(db.String(100), nullable=True)
    profile_id = db.Column(db.String(100), nullable=True)
    timezone = db.Column(db.String(100), nullable=True)
    time_shift = db.Column(db.Integer, nullable=True)
    active = db.Column(db.Boolean, default=True)

    @staticmethod
    def delete_all(user_id):
        profiles_del = GaView.query.filter_by(user_id=user_id).all()

        for profile in profiles_del:
            db.session.delete(profile)


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(1000))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


from webproject.users.ga_oauth import ga_blueprint
from webproject.users.oauth import google_blueprint

ga_blueprint.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user)
google_blueprint.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user)
