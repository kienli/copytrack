import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from logging.handlers import SMTPHandler, RotatingFileHandler
from config import Config
from redis import Redis
import rq
import rq_dashboard
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from webproject import commands

basedir = os.path.abspath(os.path.dirname(__file__))

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
mail = Mail()


def create_app(config_class=Config):
    app = Flask(__name__.split('.')[0])
    app.config.from_object(config_class)
    register_extensions(app)
    register_blueprints(app)
    register_shellcontext(app)
    register_commands(app)

    # if not app.debug and not app.testing:
    #     if app.config['MAIL_SERVER']:
    #         auth = None
    #         if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
    #             auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
    #         secure = None
    #         if app.config['MAIL_USE_TLS']:
    #             secure = ()
    #         mail_handler = SMTPHandler(
    #             mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
    #             fromaddr='no-reply@' + app.config['MAIL_SERVER'],
    #             toaddrs=app.config['ADMINS'], subject='CopyTrack Webapp Failure',
    #             credentials=auth, secure=secure)
    #         mail_handler.setLevel(logging.ERROR)
    #         app.logger.addHandler(mail_handler)
    #
    #     if app.config['LOG_TO_STDOUT']:
    #         stream_handler = logging.StreamHandler()
    #         stream_handler.setLevel(logging.INFO)
    #         app.logger.addHandler(stream_handler)
    #
    #     else:
    #
    #         if not os.path.exists('logs'):
    #             os.mkdir('logs')
    #         file_handler = RotatingFileHandler('logs/track-changes.log', maxBytes=10000000,
    #                                            backupCount=10)
    #         file_handler.setFormatter(logging.Formatter(
    #             '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    #         file_handler.setLevel(logging.INFO)
    #         app.logger.addHandler(file_handler)
    #
    #     app.logger.setLevel(logging.INFO)
    #     app.logger.info('Track Changes startup')

    return app


def register_extensions(app):
    """Register Flask extensions."""
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    app.redis = Redis.from_url(app.config['RQ_DASHBOARD_REDIS_URL'])
    app.task_queue = rq.Queue('copytrack-tasks', connection=app.redis)
    sentry_sdk.init(
        dsn="SENTRY_URL",
        integrations=[FlaskIntegration()]
    )

    return None


def register_blueprints(app):
    """Register Flask blueprints."""
    with app.app_context():
        from webproject.core.views import core
        app.register_blueprint(core)

        from webproject.users.views import users
        app.register_blueprint(users)

        from webproject.error_pages.handlers import error_pages
        app.register_blueprint(error_pages)

        from webproject.users.ga_oauth import ga_blueprint
        app.register_blueprint(ga_blueprint)

        from webproject.users.oauth import google_blueprint
        app.register_blueprint(google_blueprint, url_prefix="/login")

        app.config.from_object(rq_dashboard.default_settings)
        app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")

    return None


def register_shellcontext(app):
    """Register shell context objects."""
    from webproject.models import User, Stats, Url, Prefs, GaView, Task, Notification

    def shell_context():
        """Shell context objects."""
        return {'db': db, 'User': User, 'Url': Url, 'Stats': Stats, 'Prefs': Prefs,
                'GaView': GaView, 'Task': Task, 'Notification': Notification}

    app.shell_context_processor(shell_context)


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.test)
    app.cli.add_command(commands.lint)
    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.urls)
    app.cli.add_command(commands.resetdb)
