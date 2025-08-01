"""
Flask-WTF Forms
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    """Login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class OrganizationForm(FlaskForm):
    """Organization form"""
    name = StringField('Organization Name', validators=[
        DataRequired(), 
        Length(min=3, max=200)
    ])
    type = SelectField('Type', choices=[
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('practice', 'Private Practice'),
        ('lab', 'Laboratory'),
        ('pharmacy', 'Pharmacy'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    contact_email = StringField('Contact Email', validators=[
        DataRequired(), 
        Email()
    ])
    contact_phone = StringField('Contact Phone', validators=[
        Length(max=20)
    ])
    address = TextAreaField('Address', validators=[
        Length(max=500)
    ])