"""
WTForms for HTPI Admin Portal
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    """Login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')


class OrganizationForm(FlaskForm):
    """Organization form"""
    name = StringField('Organization Name', validators=[DataRequired(), Length(min=2, max=100)])
    type = SelectField('Type', choices=[
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('private_practice', 'Private Practice'),
        ('urgent_care', 'Urgent Care'),
        ('specialty_center', 'Specialty Center'),
        ('billing_company', 'Billing Company'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    
    # Contact Information
    contact_name = StringField('Primary Contact Name', validators=[DataRequired(), Length(max=100)])
    contact_email = StringField('Primary Contact Email', validators=[DataRequired(), Email()])
    contact_phone = StringField('Primary Contact Phone', validators=[DataRequired(), Length(max=20)])
    
    # Address
    address_line1 = StringField('Address Line 1', validators=[DataRequired(), Length(max=100)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=100)])
    city = StringField('City', validators=[DataRequired(), Length(max=50)])
    state = StringField('State', validators=[DataRequired(), Length(min=2, max=2)])
    zip_code = StringField('ZIP Code', validators=[DataRequired(), Length(min=5, max=10)])


class UserForm(FlaskForm):
    """Admin user form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    role = SelectField('Role', choices=[
        ('super_admin', 'Super Admin'),
        ('org_admin', 'Organization Admin'),
        ('billing_admin', 'Billing Admin'),
        ('clinical_admin', 'Clinical Admin'),
        ('support_admin', 'Support Admin'),
        ('read_only', 'Read Only')
    ], validators=[DataRequired()])
    password = PasswordField('Password', validators=[Optional(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[Optional()])