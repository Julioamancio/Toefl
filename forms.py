from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FloatField
from wtforms.validators import DataRequired, Length, Email, ValidationError
from models import User, Class, Teacher

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class UploadForm(FlaskForm):
    file = FileField('Arquivo Excel/CSV', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls', 'csv'], 'Apenas arquivos Excel (.xlsx, .xls) ou CSV são permitidos!')
    ])
    class_id = SelectField('Turma', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Fazer Upload')
    
    def __init__(self, *args, **kwargs):
        super(UploadForm, self).__init__(*args, **kwargs)
        # Cache das classes para melhor performance
        classes = Class.query.with_entities(Class.id, Class.name).all()
        self.class_id.choices = [(c.id, c.name) for c in classes]
        self.class_id.choices.insert(0, (0, 'Selecione uma turma...'))

class ClassForm(FlaskForm):
    name = StringField('Nome da Turma', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Descrição', validators=[Length(max=500)])
    is_active = BooleanField('Turma Ativa', default=True)
    submit = SubmitField('Criar Turma')
    
    def validate_name(self, name):
        class_obj = Class.query.filter_by(name=name.data).first()
        if class_obj:
            raise ValidationError('Já existe uma turma com este nome. Escolha um nome diferente.')

class UserForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    is_admin = BooleanField('Administrador')
    is_active = BooleanField('Usuário Ativo', default=True)
    submit = SubmitField('Criar Usuário')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nome de usuário já está em uso. Escolha um diferente.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email já está cadastrado. Escolha um diferente.')

class SearchForm(FlaskForm):
    search = StringField('Buscar por nome ou número do estudante')
    class_filter = SelectField('Filtrar por turma', coerce=int)
    cefr_filter = SelectField('Filtrar por nível CEFR')
    submit = SubmitField('Buscar')
    
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        
        # Opções de turma - otimizada para carregar apenas campos necessários
        self.class_filter.choices = [(0, 'Todas as turmas')]
        classes = Class.query.with_entities(Class.id, Class.name).all()
        self.class_filter.choices.extend([(c.id, c.name) for c in classes])
        
        # Opções de nível CEFR
        self.cefr_filter.choices = [
            ('', 'Todos os níveis'),
            ('B2', 'B2'),
            ('B1', 'B1'),
            ('A2', 'A2'),
            ('A1', 'A1'),
            ('Below A1', 'Below A1')
        ]

class TeacherForm(FlaskForm):
    name = StringField('Nome do Professor', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Salvar Professor')
    
    def __init__(self, teacher=None, *args, **kwargs):
        super(TeacherForm, self).__init__(*args, **kwargs)
        self.teacher = teacher

class EditStudentTeacherForm(FlaskForm):
    teacher_id = SelectField('Professor', coerce=int, validators=[])
    submit = SubmitField('Alterar Professor')
    
    def __init__(self, *args, **kwargs):
        super(EditStudentTeacherForm, self).__init__(*args, **kwargs)
        self.teacher_id.choices = [(0, 'Nenhum professor selecionado')]
        # Otimizada para carregar apenas campos necessários
        teachers = Teacher.query.with_entities(Teacher.id, Teacher.name).all()
        self.teacher_id.choices.extend([(t.id, t.name) for t in teachers])

class EditStudentClassForm(FlaskForm):
    class_id = SelectField('Nova Turma', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Alterar Turma')
    
    def __init__(self, *args, **kwargs):
        super(EditStudentClassForm, self).__init__(*args, **kwargs)
        # Otimizada para carregar apenas campos necessários de classes ativas
        active_classes = Class.query.filter_by(is_active=True).with_entities(Class.id, Class.name).all()
        self.class_id.choices = [(c.id, c.name) for c in active_classes]
        self.class_id.choices.insert(0, (0, 'Selecione uma turma...'))

class EditStudentTurmaMetaForm(FlaskForm):
    turma_meta = SelectField('Rótulo Escolar (Turma Meta)', validators=[DataRequired()])
    submit = SubmitField('Atualizar Rótulo')
    
    def __init__(self, student=None, *args, **kwargs):
        super(EditStudentTurmaMetaForm, self).__init__(*args, **kwargs)
        
        # Determinar o ano da turma baseado no nome da turma do aluno
        grade_year = self._get_grade_year(student)
        
        # Filtrar rótulos baseado no ano da turma
        if grade_year == 6:
            self.turma_meta.choices = [
                ('6.1', '6.1 - 6º Ano Básico'),
                ('6.2', '6.2 - 6º Ano Intermediário'),
                ('6.3', '6.3 - 6º Ano Avançado')
            ]
        elif grade_year == 9:
            self.turma_meta.choices = [
                ('9.1', '9.1 - 9º Ano Básico'),
                ('9.2', '9.2 - 9º Ano Intermediário'),
                ('9.3', '9.3 - 9º Ano Avançado')
            ]
        else:
            # Se não conseguir identificar, mostrar todos (fallback)
            self.turma_meta.choices = [
                ('6.1', '6.1 - 6º Ano Básico'),
                ('6.2', '6.2 - 6º Ano Intermediário'),
                ('6.3', '6.3 - 6º Ano Avançado'),
                ('9.1', '9.1 - 9º Ano Básico'),
                ('9.2', '9.2 - 9º Ano Intermediário'),
                ('9.3', '9.3 - 9º Ano Avançado')
            ]
    
    def _get_grade_year(self, student):
        """Determina o ano da turma (6 ou 9) baseado no nome da turma do aluno"""
        if not student or not student.class_info or not student.class_info.name:
            return None
        class_name = student.class_info.name.lower()
        # Verifica se é 6º ano - padrões: "6° ano", "6º ano", "6 ano"
        if ('6°' in class_name or '6º' in class_name or '6 ano' in class_name):
            return 6
        # Verifica se é 9º ano - padrões: "9° ano", "9º ano", "9 ano"
        if ('9°' in class_name or '9º' in class_name or '9 ano' in class_name):
            return 9
        return None

class EditListeningCSAForm(FlaskForm):
    csa_points = FloatField(
        'Pontos Listening CSA',
        validators=[DataRequired()],
        filters=[lambda x: x.replace(',', '.') if isinstance(x, str) else x]
    )
    is_manual = BooleanField('Manter valor manual (não recalcular automaticamente)')
    submit = SubmitField('Salvar Listening CSA')