from flask_wtf import FlaskForm
# from flask_wtf.file import FileAllowed, FileField
from wtforms import (BooleanField, PasswordField, RadioField, StringField,
                     SubmitField, ValidationError, HiddenField, SelectField)
from wtforms.validators import DataRequired, Email, EqualTo

from webproject.models import User


class LoginForm(FlaskForm):
    email = StringField('Email address', validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "Email address"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Password"})
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    email = StringField('Email address', validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "Email address"})
    username = StringField('Username', validators=[DataRequired()],
                           render_kw={"placeholder": "Username"})
    password = PasswordField('Password',
                             validators=[DataRequired()], render_kw={"placeholder": "Password"})
    pass_confirm = PasswordField('Confirm Password',
                                 validators=[DataRequired(),
                                             EqualTo('password', message='Passwords must match!')],
                                 render_kw={"placeholder": "Confirm Password"})
    timezone_hidden = HiddenField()

    submit = SubmitField('Register')

    def validate_email(self, email):
        email = User.query.filter_by(email=email.data.lower()).first()
        if email is not None:
            raise ValidationError('This email has been already registered!')

    def validate_username(self, username):
        username = User.query.filter_by(username=username.data).first()
        if username is not None:
            raise ValidationError('This username has been already registered!')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email address', validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "Email address"})
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Password"})
    pass_confirm = PasswordField('Confirm Password',
                                 validators=[DataRequired(), EqualTo('password', message='Passwords must match!')],
                                 render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField('Request Password Reset')


class DashboardSettingsForm(FlaskForm):
    periods = StringField('Periods (in days)', validators=[DataRequired()])
    sorting = RadioField('New links go', choices=[('0', 'to bottom'), ('1', 'on top')], default='0')
    dash_submit = SubmitField('Save changes')

    def validate_periods(self, periods):
        period_list_row = self.periods.data.strip(',')
        period_list_digits = period_list_row.split(',')
        period_list_digits = [s.strip() for s in period_list_digits]
        for item in period_list_digits:
            if not item.isdigit() or item == '0':
                raise ValidationError('Please use only numbers, commas and spaces')


class UnsafeSelectField(SelectField):
    def pre_validate(self, form):
        return True


class UpdateUserForm(FlaskForm):
    timezone = UnsafeSelectField('Timezone', choices=[], coerce=str, validators=[DataRequired()],
                                 render_kw={"data-live-search": "true"})
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired()])
    # picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    timezone_hidden = HiddenField()
    profile_submit = SubmitField('Save changes')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(UpdateUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('This username is taken. Please use a different username.')

    def validate_email(self, email):
        if email.data != self.original_email:
            email = User.query.filter_by(email=self.email.data).first()
            if email is not None:
                raise ValidationError('This email is taken. Please use a different email.')
