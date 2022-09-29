from flask_wtf import FlaskForm
from btcbyme.models import User
from wtforms import StringField, PasswordField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Length, EqualTo, Regexp


class RegistrationForm(FlaskForm):
    username = StringField(
        'Username', validators=[DataRequired(), Length(min=5, max=20),
                                Regexp('^[a-zA-Z0-9_]*$')])
    password = PasswordField(
        'Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(
        'Username', validators=[DataRequired(), Length(min=5, max=20)])
    password = PasswordField(
        'Password', validators=[DataRequired()])
    submit = SubmitField('Log in')
