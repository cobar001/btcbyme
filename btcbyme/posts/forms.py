from flask_wtf import FlaskForm
from wtforms import FloatField, StringField, SubmitField, SelectField
from wtforms.fields.html5 import IntegerRangeField
from wtforms.validators import DataRequired, NumberRange, Length
from btcbyme.utilities import utilities


class NewPostForm(FlaskForm):
    markup = FloatField('Markup', validators=[DataRequired(), NumberRange(min=0.0)])
    min_tx = FloatField('Minimum Transaction', validators=[DataRequired(), NumberRange(min=1.0)])
    max_tx = FloatField('Maximum Transaction', validators=[DataRequired(), NumberRange(min=1.0)])
    city = StringField('City', validators=[DataRequired(), Length(max=60)])
    region = StringField('Region or State (Optional)', validators=[Length(max=60)])
    country = StringField('Country', validators=[DataRequired(), Length(max=60)])
    currency = SelectField('Currency', choices=utilities.SUPPORTED_CURRENCIES, coerce=str)
    submit = SubmitField('Create Post')


class NewPostConfirmationForm(FlaskForm):
    submit = SubmitField('Confirm New Post')


class SearchPostForm(FlaskForm):
    max_markup = FloatField('Max Markup', validators=[NumberRange(min=0.0)])
    desired_tx_amount = FloatField('Desired Transaction Amount', validators=[NumberRange(min=1.0)])
    city = StringField('City', validators=[Length(max=60)])
    region = StringField('Region or State', validators=[Length(max=60)])
    country = StringField('Country', validators=[Length(max=60)])
    currency = SelectField('Currency', choices=utilities.SUPPORTED_CURRENCIES, coerce=str)
    search_distance = IntegerRangeField('Search Distance', validators=[NumberRange(min=0, max=50)])
    sort_by = SelectField('Sort By', choices=utilities.SEARCH_SORTING_OPTIONS, coerce=str)
    submit = SubmitField('Refresh post results')
