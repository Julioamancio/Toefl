from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event

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

class Class(db.Model):
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    meta_label = db.Column(db.String(10))  # "6.1", "6.2", "6.3", "9.1", "9.2", "9.3"
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento com estudantes (com cascade delete)
    students = db.relationship('Student', backref='class_info', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Class {self.name}>'

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento com estudantes
    students = db.relationship('Student', backref='teacher', lazy=True)
    
    def __repr__(self):
        return f'<Teacher {self.name}>'

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # Campos importados da planilha
    listening = db.Column(db.Integer, nullable=True)
    list_cefr = db.Column(db.String(10), nullable=True)
    lfm = db.Column(db.Integer, nullable=True)
    lfm_cefr = db.Column(db.String(10), nullable=True)
    reading = db.Column(db.Integer, nullable=True)
    read_cefr = db.Column(db.String(10), nullable=True)
    lexile = db.Column(db.String(20), nullable=True)
    total = db.Column(db.Integer, nullable=True)
    cefr_geral = db.Column(db.String(10), nullable=True)
    
    # Campo para Listening CSA
    listening_csa_points = db.Column(db.Float, nullable=True)
    
    # Relacionamentos
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Student {self.name}>'
    
    def get_cefr_level(self):
        """Retorna o nível CEFR geral do estudante"""
        if self.cefr_geral:
            return self.cefr_geral
        elif self.list_cefr:
            return self.list_cefr
        elif self.read_cefr:
            return self.read_cefr
        elif self.lfm_cefr:
            return self.lfm_cefr
        else:
            return "N/A"
    
    def get_subfaixa(self):
        """Retorna a subfaixa do estudante baseada no total"""
        if not self.total:
            return None
        
        # Lógica simplificada de subfaixa baseada no total
        if self.total >= 280:
            return "Alta"
        elif self.total >= 250:
            return "Média"
        elif self.total >= 220:
            return "Baixa"
        else:
            return "Inicial"
    
    def atingiu_meta(self):
        """Verifica se o estudante atingiu a meta"""
        # Lógica simplificada - pode ser ajustada conforme necessário
        if not self.total:
            return False
        return self.total >= 250  # Meta padrão
    
    def gap_niveis(self):
        """Calcula a diferença entre o nível atual e a meta"""
        if not self.total:
            return 0
        meta_score = 250  # Meta padrão
        return max(0, meta_score - self.total)
    
    def calculate_final_cefr(self):
        """Calcula o nível CEFR final baseado na pontuação total"""
        if not self.total:
            return 'N/A'
        
        if self.total >= 800:
            return 'B2'
        elif self.total >= 700:
            return 'B1'
        elif self.total >= 650:
            return 'A2+'
        elif self.total >= 600:
            return 'A2'
        else:
            return 'A1'
    
    def calculate_cefr_level(self):
        """Alias para calculate_final_cefr para compatibilidade"""
        return self.calculate_final_cefr()
    
    def update_toefl_calculations(self):
        """Atualiza cálculos relacionados ao TOEFL"""
        # Atualizar listening_csa_points se temos os dados necessários
        if self.class_info and self.class_info.meta_label and self.listening is not None:
            from listening_csa import compute_listening_csa
            try:
                rotulo_escolar = float(self.class_info.meta_label)
                csa_result = compute_listening_csa(rotulo_escolar, self.listening)
                self.listening_csa_points = csa_result['points']
            except (ValueError, TypeError):
                self.listening_csa_points = None
        else:
            self.listening_csa_points = None
    
    def compute_listening_csa(self):
        """Computa e retorna dados do Listening CSA"""
        if self.class_info and self.class_info.meta_label and self.listening is not None:
            from listening_csa import compute_listening_csa
            try:
                rotulo_escolar = float(self.class_info.meta_label)
                return compute_listening_csa(rotulo_escolar, self.listening)
            except (ValueError, TypeError):
                return None
        return None
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class ComputedLevel(db.Model):
    __tablename__ = 'computed_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    
    # Níveis calculados
    school_level = db.Column(db.String(10), nullable=True)
    listening_level = db.Column(db.String(10), nullable=True)
    lfm_level = db.Column(db.String(10), nullable=True)
    reading_level = db.Column(db.String(10), nullable=True)
    overall_level = db.Column(db.String(10), nullable=True)
    
    # Regras aplicadas (para auditoria)
    applied_rules = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    student = db.relationship('Student', backref='computed_level', uselist=False, passive_deletes=True)
    
    def __repr__(self):
        return f'<ComputedLevel for Student {self.student_id}>'

# Mapeamento de níveis escolares
SCHOOL_LEVEL_MAP = {
    6.1: 'A1',
    6.2: 'A2',
    6.3: 'A2+',
    9.1: 'B1',
    9.2: 'B2',
    9.3: 'B2+'
}

def calculate_level_by_score(score, skill_type):
    """Calcula nível CEFR baseado na pontuação e tipo de habilidade"""
    if score is None:
        return None
    
    # Thresholds corretos para TOEFL Junior (200-300 range)
    if skill_type == 'listening':
        if score < 215:
            return 'A1'
        elif score < 245:
            return 'A2'
        elif score < 250:
            return 'A2+'
        elif score < 275:
            return 'B1'
        else:
            return 'B2'
    
    elif skill_type == 'lfm':
        if score < 215:
            return 'A1'
        elif score < 245:
            return 'A2'
        elif score < 250:
            return 'A2+'
        elif score < 275:
            return 'B1'
        else:
            return 'B2'
    
    elif skill_type == 'reading':
        if score < 215:
            return 'A1'
        elif score < 245:
            return 'A2'
        elif score < 250:
            return 'A2+'
        elif score < 275:
            return 'B1'
        else:
            return 'B2'
    
    return None

def apply_toefl_guardrails(level, score, individual_scores=None):
    """
    Aplica guardrails do TOEFL Junior
    
    Args:
        level: Nível calculado inicialmente
        score: Pontuação total ou individual
        individual_scores: Dict com pontuações individuais {'listening': x, 'lfm': y, 'reading': z}
    
    Returns:
        str: Nível após aplicação dos guardrails
    """
    if score is None:
        return level
    
    # Guardrail 1: TOTAL < 645 = A1 (215 * 3)
    if score < 645:
        return 'A1'
    
    # Guardrail 2: TOTAL >= 825 = B2 (275 * 3)
    if score >= 825:
        return 'B2'
    
    return level

def calculate_student_levels(student):
    """Calcula todos os níveis para um estudante"""
    levels = {}
    applied_rules = []
    
    # School level baseado no student_number
    if student.student_number:
        try:
            # Extrair série do student_number (assumindo formato como "6.1.001")
            parts = student.student_number.split('.')
            if len(parts) >= 2:
                serie = float(f"{parts[0]}.{parts[1]}")
                levels['school_level'] = SCHOOL_LEVEL_MAP.get(serie)
                if levels['school_level']:
                    applied_rules.append(f"School level: {serie} → {levels['school_level']}")
        except:
            pass
    
    # Preparar pontuações individuais para guardrails
    individual_scores = {
        'listening': student.listening,
        'lfm': student.lfm,
        'reading': student.reading
    }
    
    # Listening level
    if student.listening:
        levels['listening_level'] = calculate_level_by_score(student.listening, 'listening')
        applied_rules.append(f"Listening: {student.listening} → {levels['listening_level']}")
    
    # LFM level
    if student.lfm:
        levels['lfm_level'] = calculate_level_by_score(student.lfm, 'lfm')
        applied_rules.append(f"LFM: {student.lfm} → {levels['lfm_level']}")
    
    # Reading level
    if student.reading:
        levels['reading_level'] = calculate_level_by_score(student.reading, 'reading')
        applied_rules.append(f"Reading: {student.reading} → {levels['reading_level']}")
    
    # Overall level (maior nível entre as habilidades)
    skill_levels = [levels.get('listening_level'), levels.get('lfm_level'), levels.get('reading_level')]
    skill_levels = [l for l in skill_levels if l is not None]
    
    if skill_levels:
        # Converter para números para encontrar o maior
        level_values = {'A1': 1, 'A2': 2, 'A2+': 2.5, 'B1': 3, 'B2': 4, 'B2+': 4.5}
        value_levels = {v: k for k, v in level_values.items()}
        
        # Pegar o maior nível (não a média)
        max_value = max(level_values.get(l, 0) for l in skill_levels)
        levels['overall_level'] = value_levels[max_value]
        
        # Aplicar guardrails do TOEFL com pontuações individuais
        if student.total:
            levels['overall_level'] = apply_toefl_guardrails(
                levels['overall_level'], 
                student.total, 
                individual_scores
            )
            applied_rules.append(f"Overall: maior de {skill_levels} → {levels['overall_level']} (com guardrails)")
        else:
            applied_rules.append(f"Overall: maior de {skill_levels} → {levels['overall_level']}")
    
    return levels, applied_rules

def seed_teachers():
    """Popula a tabela de professores com dados iniciais"""
    teachers_data = [
        'Julio', 'Caique', 'Natalia', 'Ivana', 'Fernanda H.', 'Fernanda C.', 
        'Renata', 'Carolina', 'Mariana', 'Ricardo', 'Ana Paula', 'Carlos', 
        'Beatriz', 'Rafael', 'Camila'
    ]
    
    for teacher_name in teachers_data:
        existing = Teacher.query.filter_by(name=teacher_name).first()
        if not existing:
            teacher = Teacher(name=teacher_name)
            db.session.add(teacher)
    
    db.session.commit()
    print(f"Seeded {len(teachers_data)} teachers")

def seed_teacher_users():
    """Cria usuários para cada professor na administração"""
    teachers = Teacher.query.all()
    
    for teacher in teachers:
        # Criar username baseado no nome (sem espaços, minúsculo)
        username = teacher.name.lower().replace(' ', '_')
        
        # Verificar se o usuário já existe
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            # Criar usuário com senha padrão (nome em minúsculo)
            password = teacher.name.lower().replace(' ', '')
            user = User(
                username=username,
                email=f"{username}@toefl.com",
                is_admin=False,
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
    
    db.session.commit()
    print(f"Created user accounts for {len(teachers)} teachers")