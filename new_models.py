from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    
    # Relacionamento com estudantes
    students = db.relationship('Student', backref='teacher', lazy=True)
    
    def __repr__(self):
        return f'<Teacher {self.name}>'

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_number = db.Column(db.String(50), nullable=False)
    class_label = db.Column(db.String(10), nullable=True)  # "6.1", "6.2", "6.3", "9.1", "9.2", "9.3"
    
    # Scores TOEFL Junior (200-300 cada)
    listening = db.Column(db.Integer, nullable=True)
    list_cefr = db.Column(db.String(10), nullable=True)
    lfm = db.Column(db.Integer, nullable=True)  # Language Form and Meaning
    lfm_cefr = db.Column(db.String(10), nullable=True)
    reading = db.Column(db.Integer, nullable=True)
    read_cefr = db.Column(db.String(10), nullable=True)
    
    # Outros campos
    lexile = db.Column(db.Integer, nullable=True)
    total = db.Column(db.Integer, nullable=True)  # 600-900
    cefr_geral_raw = db.Column(db.String(10), nullable=True)  # CEFR GERAL da planilha
    
    # Foreign keys
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Student {self.name}>'

class ComputedLevel(db.Model):
    __tablename__ = 'computed_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    
    # Níveis calculados
    school_level = db.Column(db.String(20), nullable=True)  # A1 STARTER, A2, A2+, B1, B2, B2+
    listening_level = db.Column(db.String(10), nullable=True)  # A1, A2, B1, B2, B2+
    lfm_level = db.Column(db.String(10), nullable=True)  # A1, A2, B1, B2, B2+
    reading_level = db.Column(db.String(10), nullable=True)  # A1, A2, B1, B2, B2+
    overall_level = db.Column(db.String(10), nullable=True)  # A1, A2, B1, B2, B2+
    
    # Relacionamento com estudante
    student = db.relationship('Student', backref='computed_level', uselist=False)
    
    def __repr__(self):
        return f'<ComputedLevel Student:{self.student_id} Overall:{self.overall_level}>'

# Regras de mapeamento da escola
SCHOOL_LEVEL_MAP = {
    '6.1': 'A1 STARTER',
    '6.2': 'A2',
    '6.3': 'A2+',
    '9.1': 'B1',
    '9.2': 'B2',
    '9.3': 'B2+'
}

# Função para calcular nível por score numérico (fallback)
def calculate_level_by_score(score):
    """Calcula nível CEFR baseado no score numérico (200-300)"""
    if score is None or score < 200:
        return 'A1'
    elif score < 240:
        return 'A1'
    elif score < 265:
        return 'A2'
    elif score < 285:
        return 'B1'
    else:
        return 'B2'  # Cap em B2, exceto se TOTAL ≥ 900

# Função para aplicar guardrails TOEFL
def apply_toefl_guardrails(level, total_score, individual_scores):
    """Aplica guardrails TOEFL Junior"""
    # Hard guardrail A1
    if total_score is not None and total_score < 600:
        return 'A1'
    
    # Verificar se alguma habilidade < 200
    for score in individual_scores:
        if score is not None and score < 200:
            return 'A1'
    
    # Hard guardrail B2+
    if total_score is not None and total_score >= 900:
        return 'B2+'
    
    return level

# Função para calcular níveis de um estudante
def calculate_student_levels(student):
    """Calcula todos os níveis de um estudante"""
    computed = ComputedLevel.query.filter_by(student_id=student.id).first()
    if not computed:
        computed = ComputedLevel(student_id=student.id)
        db.session.add(computed)
    
    # 1. School level (baseado no class_label)
    if student.class_label and student.class_label in SCHOOL_LEVEL_MAP:
        computed.school_level = SCHOOL_LEVEL_MAP[student.class_label]
    
    # 2. Listening level
    if student.list_cefr and student.list_cefr.strip():
        computed.listening_level = student.list_cefr.strip().upper()
    else:
        computed.listening_level = calculate_level_by_score(student.listening)
    
    # 3. LFM level
    if student.lfm_cefr and student.lfm_cefr.strip():
        computed.lfm_level = student.lfm_cefr.strip().upper()
    else:
        computed.lfm_level = calculate_level_by_score(student.lfm)
    
    # 4. Reading level
    if student.read_cefr and student.read_cefr.strip():
        computed.reading_level = student.read_cefr.strip().upper()
    else:
        computed.reading_level = calculate_level_by_score(student.reading)
    
    # 5. Overall level
    if student.cefr_geral_raw and student.cefr_geral_raw.strip():
        computed.overall_level = student.cefr_geral_raw.strip().upper()
    else:
        # Inferir pelo maior nível entre as habilidades
        levels = [computed.listening_level, computed.lfm_level, computed.reading_level]
        level_order = ['A1', 'A2', 'B1', 'B2', 'B2+']
        max_level = 'A1'
        for level in levels:
            if level and level in level_order:
                if level_order.index(level) > level_order.index(max_level):
                    max_level = level
        computed.overall_level = max_level
    
    # Aplicar guardrails TOEFL
    individual_scores = [student.listening, student.lfm, student.reading]
    computed.listening_level = apply_toefl_guardrails(computed.listening_level, student.total, individual_scores)
    computed.lfm_level = apply_toefl_guardrails(computed.lfm_level, student.total, individual_scores)
    computed.reading_level = apply_toefl_guardrails(computed.reading_level, student.total, individual_scores)
    computed.overall_level = apply_toefl_guardrails(computed.overall_level, student.total, individual_scores)
    
    db.session.commit()
    return computed

# Lista de professores para seed
SEED_TEACHERS = [
    'Julio',
    'Renata', 
    'Ivana',
    'Carolina',
    'Fernanda Campos',
    'Fernanda Horta',
    'Natalia',
    'Caique'
]

def seed_teachers():
    """Popula a tabela de professores"""
    for teacher_name in SEED_TEACHERS:
        existing = Teacher.query.filter_by(name=teacher_name).first()
        if not existing:
            teacher = Teacher(name=teacher_name)
            db.session.add(teacher)
    
    db.session.commit()
    print(f"Professores criados: {len(SEED_TEACHERS)}")