from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, url


class GeneratorForm(FlaskForm):
    url = StringField('', validators=[DataRequired(), url()])
    submit = SubmitField("Shorten")

