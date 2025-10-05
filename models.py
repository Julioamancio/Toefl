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
    is_teacher = db.Column(db.Boolean, default=False)
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
    # Nome encontrado durante importação/normalização (para exibir diferenças)
    found_name = db.Column(db.String(120), nullable=True)
    
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
    
    # Campo individual para rótulo escolar (turma meta) - cada aluno tem seu próprio
    turma_meta = db.Column(db.String(10), nullable=True)  # "6.1", "6.2", "6.3", "9.1", "9.2", "9.3"

    # Origem da importação (nome da aba/planilha)
    import_sheet_name = db.Column(db.String(120), nullable=True)
    
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
        """Calcula o nível CEFR final baseado na pontuação total TOEFL Junior (600-900)
        Base única (TOEFL Junior → CEFR):
        - B2: 865–900
        - B1: 730–864
        - A2+: 650–729
        - A2: 600–649
        - Below A1: abaixo de 600
        """
        if not self.total:
            return 'N/A'
        
        total = self.total
        if total >= 865:
            return 'B2'
        elif total >= 730:
            return 'B1'
        elif total >= 650:
            return 'A2+'
        elif total >= 600:
            return 'A2'
        else:
            return 'Below A1'
    
    def calculate_cefr_level(self):
        """Alias para calculate_final_cefr para compatibilidade"""
        return self.calculate_final_cefr()
    
    def update_toefl_calculations(self):
        """Atualiza cálculos relacionados ao TOEFL"""
        # Atualizar listening_csa_points baseado em score_total e grupo (turma/nivel)
        from listening_csa import compute_listening_csa
        try:
            rotulo_escolar = None
            turma_name = None
            if self.class_info:
                turma_name = self.class_info.name
                if self.class_info.meta_label:
                    rotulo_escolar = str(self.class_info.meta_label).strip().replace(',', '.')
            elif self.turma_meta:
                rotulo_escolar = str(self.turma_meta).strip().replace(',', '.')

            if self.total is not None:
                result = compute_listening_csa(rotulo_escolar, self.total, turma_name=turma_name)
                self.listening_csa_points = result.get('points')
            else:
                self.listening_csa_points = None
        except Exception:
            self.listening_csa_points = None

    def compute_listening_csa(self):
        """Calcula o Listening CSA baseado em turma_meta/class_info e score_total"""
        try:
            rotulo_escolar = None
            turma_name = None
            if self.class_info:
                turma_name = self.class_info.name
                if self.class_info.meta_label:
                    rotulo_escolar = str(self.class_info.meta_label).strip().replace(',', '.')
            elif self.turma_meta:
                rotulo_escolar = str(self.turma_meta).strip().replace(',', '.')
            if self.total is not None:
                from listening_csa import compute_listening_csa
                return compute_listening_csa(rotulo_escolar, self.total, turma_name=turma_name)
        except Exception:
            return None
        return None

    def get_listening_csa_points(self):
        """Retorna apenas os pontos do Listening CSA (via score_total)."""
        try:
            rotulo_escolar = None
            turma_name = None
            if self.class_info:
                turma_name = self.class_info.name
                if self.class_info.meta_label:
                    rotulo_escolar = str(self.class_info.meta_label).strip().replace(',', '.')
            elif self.turma_meta:
                rotulo_escolar = str(self.turma_meta).strip().replace(',', '.')
            if self.total is not None:
                from listening_csa import compute_listening_csa
                result = compute_listening_csa(rotulo_escolar, self.total, turma_name=turma_name)
                return result.get('points') if result else None
        except Exception:
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
    student = db.relationship('Student', backref=db.backref('computed_level', uselist=False), uselist=False, passive_deletes=True)
    
    def __repr__(self):
        return f'<ComputedLevel for Student {self.student_id}>'

class CertificateLayout(db.Model):
    __tablename__ = 'certificate_layouts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='default')
    positions = db.Column(db.Text, nullable=False)  # JSON string com posições
    colors = db.Column(db.Text, nullable=True)  # JSON string com cores
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CertificateLayout {self.name}>'

class StudentCertificateLayout(db.Model):
    __tablename__ = 'student_certificate_layouts'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    positions = db.Column(db.Text, nullable=False)  # JSON string com posições
    colors = db.Column(db.Text, nullable=True)  # JSON string com cores
    certificate_date = db.Column(db.String(20), nullable=True)  # Data personalizada do certificado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    student = db.relationship('Student', backref=db.backref('certificate_layout', uselist=False), uselist=False, passive_deletes=True)
    
    def __repr__(self):
        return f'<StudentCertificateLayout for Student {self.student_id}>'

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
    
    # Ajuste conforme base única (priorizar classificação pelo total)
    if score is not None:
        if score >= 865:
            return 'B2'
        elif score >= 730:
            return 'B1'
        elif score >= 650:
            return 'A2+'
        elif score >= 600:
            return 'A2'
        else:
            return 'Below A1'
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
    
    # Overall level: priorizar classificação pelo total; se não houver total, usar maior das habilidades
    if student.total is not None:
        overall = apply_toefl_guardrails(None, student.total, individual_scores)
        levels['overall_level'] = overall
        applied_rules.append(f"Overall pelo total {student.total} → {overall}")
    else:
        skill_levels = [levels.get('listening_level'), levels.get('lfm_level'), levels.get('reading_level')]
        skill_levels = [l for l in skill_levels if l is not None]
        if skill_levels:
            level_values = {'Below A1': 0, 'A1': 1, 'A2': 2, 'A2+': 2.5, 'B1': 3, 'B2': 4, 'B2+': 4.5}
            value_levels = {v: k for k, v in level_values.items()}
            max_value = max(level_values.get(l, 0) for l in skill_levels)
            levels['overall_level'] = value_levels[max_value]
            applied_rules.append(f"Overall (sem total): maior de {skill_levels} → {levels['overall_level']}")
    
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