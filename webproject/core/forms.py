from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, ValidationError, HiddenField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Optional
import urllib.parse
import validators
from datetime import datetime
from webproject.core.general import human_to_datetime


class AddProjectForm(FlaskForm):
    project_name = StringField('Project name', validators=[DataRequired()],
                               render_kw={"placeholder": 'Project name',
                                          'maxlength': 53})
    project_description = TextAreaField('Short project description', validators=[Optional()],
                                        render_kw={"placeholder": 'Optional',
                                                   'maxlength': 64})
    project_notifications = BooleanField('Email Notifications', render_kw={"data-toggle": 'toggle'})

    project_submit = SubmitField('Create project')

    def validate_project_name(self, project_name):
        if len(self.project_name.data.strip()) > 53:
            raise ValidationError('Project name is too long')

    def validate_project_description(self, project_description):
        if len(self.project_description.data.strip()) > 64:
            raise ValidationError('Project description is too long')


class EditProjectForm(FlaskForm):
    edit_project_name = StringField('Project name', validators=[DataRequired()],
                                    render_kw={"placeholder": 'Project name',
                                               'maxlength': 53})
    edit_project_description = TextAreaField('Short project description', validators=[Optional()],
                                             render_kw={"placeholder": 'Optional',
                                                        'maxlength': 64})
    edit_project_notifications = BooleanField('Email Notifications', render_kw={"data-toggle": 'toggle'})

    hidden_project_edit = HiddenField()

    edit_project_submit = SubmitField('Save changes')

    def validate_edit_project_name(self, edit_project_name):
        if len(self.edit_project_name.data.strip()) > 53:
            raise ValidationError('Project name is too long')

    def validate_edit_project_description(self, edit_project_description):
        if len(self.edit_project_description.data.strip()) > 64:
            raise ValidationError('Project description is too long')


class AddUrlForm(FlaskForm):
    url_add = StringField('URL of changed page', validators=[DataRequired()],
                          render_kw={"placeholder": 'http(s)://...'})
    old_url_add = StringField('Old name of URL', validators=[Optional()],
                              render_kw={"placeholder": '(Optional) http(s)://... '})
    datetimepicker = StringField('Date of change', validators=[DataRequired()],
                                 render_kw={"placeholder": 'DD.MM.YYYY', "data-toggle": "datetimepicker",
                                            "data-target": "#datetimepicker"})
    description_add = TextAreaField('Description of change', validators=[Optional()],
                                    render_kw={"placeholder": 'Optional',
                                               'maxlength': 400})
    submit_add = SubmitField('Add URL')

    def validate_url_add(self, url_add):
        url = urllib.parse.unquote(self.url_add.data)
        url = url.lower().strip()
        url_parsed = urllib.parse.urlparse(url)
        # if not all([url_parsed.scheme, url_parsed.netloc, url_parsed.path]):
        if not validators.url(url):
            if not url_parsed.scheme:
                raise ValidationError('URL not valid: missing http:// or https://!')
            else:
                raise ValidationError('This URL is not valid')

    def validate_old_url_add(self, old_url_add):
        if self.old_url_add.data:
            url = urllib.parse.unquote(self.old_url_add.data)
            url = url.lower().strip()
            url_parsed = urllib.parse.urlparse(url)

            if not validators.url(url):
                if not url_parsed.scheme:
                    raise ValidationError('URL not valid: missing http:// or https://!')
                else:
                    raise ValidationError('This URL is not valid')

    def validate_datetimepicker(self, datetimepicker):
        input_date = human_to_datetime(self.datetimepicker.data)

        if input_date > datetime.now():
            raise ValidationError('Date of change cannot be in the future')

        if input_date < human_to_datetime('01.01.1990'):
            raise ValidationError('Date may be wrong')

        try:
            datetime.strptime(self.datetimepicker.data, '%d.%m.%Y')
        except ValueError:
            raise ValidationError("Incorrect data format, should be DD-MM-YYYY")

    def validate_description_add(self, description_add):
        if self.description_add.data:
            description = self.description_add.data.strip()
            if len(description) > 400:
                raise ValidationError('The description is longer than 400 characters')


class EditUrlForm(FlaskForm):
    url_edit = StringField('URL of changed page', validators=[DataRequired()],
                           render_kw={"placeholder": 'http(s)://...'})
    old_url_edit = StringField('Old name of URL', validators=[Optional()],
                               render_kw={"placeholder": '(Optional) http(s)://... '})
    datetimepicker_edit = StringField('Date of change', validators=[DataRequired()],
                                      render_kw={"placeholder": 'DD.MM.YYYY', "data-toggle": "datetimepicker",
                                                 "data-target": "#datetimepicker_edit"})

    description_edit = TextAreaField('Description of change', validators=[Optional()],
                                     render_kw={"placeholder": 'Optional',
                                                'maxlength': 400})
    hidden_edit = HiddenField()

    submit_edit = SubmitField('Edit URL')

    def validate_url_edit(self, url_edit):
        url = urllib.parse.unquote(self.url_edit.data)
        url = url.lower().strip()
        url_parsed = urllib.parse.urlparse(url)
        # if not all([url_parsed.scheme, url_parsed.netloc, url_parsed.path]):
        if not validators.url(url):
            if not url_parsed.scheme:
                raise ValidationError('URL not valid: missing http:// or https://!')
            else:
                raise ValidationError('This URL is not valid')

    def validate_old_url_edit(self, old_url_edit):
        if self.old_url_edit.data:
            url = urllib.parse.unquote(self.old_url_edit.data)
            url = url.lower().strip()
            url_parsed = urllib.parse.urlparse(url)

            if not validators.url(url):
                if not url_parsed.scheme:
                    raise ValidationError('URL not valid: missing http:// or https://!')
                else:
                    raise ValidationError('This URL is not valid')

    def validate_datetimepicker_edit(self, datetimepicker_edit):

        input_date = human_to_datetime(self.datetimepicker_edit.data)

        if input_date > datetime.now():
            raise ValidationError('Date of change cannot be in the future')

        if input_date < human_to_datetime('01.01.1990'):
            raise ValidationError('Date may be wrong')

        try:
            datetime.strptime(self.datetimepicker_edit.data, '%d.%m.%Y')
        except ValueError:
            raise ValidationError("Incorrect data format, should be DD-MM-YYYY")

    def validate_description_edit(self, description_edit):
        if self.description_edit.data:
            description = self.description_edit.data.strip()
            if len(description) > 400:
                raise ValidationError('The description is longer than 400 characters')


class RemoveUrlForm(FlaskForm):
    url_del = StringField('Remove URL', validators=[DataRequired()], render_kw={"placeholder": 'Remove URL'})
    date_del = DateField('Date of change', validators=[Optional()])
    submit_del = SubmitField('Remove URL')
