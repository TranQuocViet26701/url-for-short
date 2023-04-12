from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class GeneratorForm(FlaskForm):
    url = StringField('', validators=[DataRequired()])
    submit = SubmitField("Shorten")

