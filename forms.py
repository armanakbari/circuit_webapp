from flask_wtf import FlaskForm
from wtforms import TextAreaField, FileField, SelectField, StringField
from wtforms.validators import DataRequired, Length, Optional

class SampleForm(FlaskForm):
    question = TextAreaField('Question Text', validators=[
        DataRequired(),
        Length(min=10, max=1000, message='Question must be between 10 and 1000 characters')
    ])
    
    source_book = StringField('Source Book/Material', validators=[
        DataRequired(),
        Length(min=1, max=200, message='Source book must be between 1 and 200 characters')
    ])
    
    source_page = StringField('Page/Section Reference', validators=[
        Optional(),
        Length(max=50, message='Page reference must be less than 50 characters')
    ])
    
    source_problem = StringField('Problem/Example Reference', validators=[
        Optional(),
        Length(max=100, message='Problem reference must be less than 100 characters')
    ])
    
    source = TextAreaField('Additional Source Information', validators=[
        Optional(),
        Length(max=500, message='Additional source info must be less than 500 characters')
    ])
    
    text_answer = TextAreaField('Text Answer', validators=[
        Optional(),
        Length(max=1000, message='Text answer must be less than 1000 characters')
    ])
    
    derivation = TextAreaField('Derivation/Solution', validators=[
        Optional(),
        Length(max=5000, message='Derivation must be less than 5000 characters')
    ])
    
    image = FileField('Circuit Image', validators=[DataRequired()])
    
    difficultiness = SelectField(
        'Difficulty Level',
        choices=[
            ('0', '0 (pure resistance)'),
            ('0.5', '0.5 (RCL)'),
            ('1', '1 (RCL + ideal amp)'),
            ('2', '2 (transistor-included)')
        ],
        validators=[DataRequired()]
    )
    
    mc_choices = TextAreaField('Multiple Choice Options (one per line)', validators=[Optional(), Length(max=1000)])
    correct_choice = SelectField(
        'Correct Choice',
        choices=[('', 'Select the correct answer (optional)'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')],
        validators=[Optional()]
    ) 