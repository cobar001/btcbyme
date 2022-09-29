from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length


class NewMessageForm(FlaskForm):
    content = TextAreaField('Content', validators=[DataRequired(), Length(max=140)])
    submit = SubmitField('Send Message')
