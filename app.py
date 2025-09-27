from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import pandas as pd
from datetime import datetime, timedelta
import io
import csv
from config import config
from config_local import build_sqlalchemy_uri
# Removida dependência do CertificateGenerator - funcionalidade integrada diretamente
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache

def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""
    app = Flask(__name__)
    
    # Determinar o ambiente - usar production para Render
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
    
    print(f"Iniciando aplicação no ambiente: {config_name}")
    
    # Carregar configurações
    app.config.from_object(config[config_name])
    
    # Configurar banco de dados com a nova função
    db_uri = build_sqlalchemy_uri()
    print(f"Conectando ao banco: {db_uri.split('@')[0]}@***")  # Log sem senha
    
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_size": 3,  # Reduzido para Render
        "max_overflow": 2,  # Reduzido para evitar timeout
        "pool_recycle": 300,
        "pool_timeout": 20,  # Timeout mais baixo
        # Removido connect_timeout do connect_args para evitar TypeError
        # application_name já está configurado na URL via config_local.py
    }
    
    # Ensure upload folder exists
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        print(f"Pasta de upload configurada: {app.config['UPLOAD_FOLDER']}")
    except Exception as e:
        print(f"Erro ao criar pasta de upload: {e}")
    
    # Inicializar extensões
    from models import db
    db.init_app(app)  # REGISTRA a app na instância db
    
    # Configurar cache simples para melhor performance
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 ano para arquivos estáticos
    
    # Inicializar CSRF Protection
    csrf = CSRFProtect(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    
    # Importar modelos após inicialização do db
    from models import User, Student, Class, Teacher, ComputedLevel
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Não rodar nada de banco no BUILD
    if not os.getenv("RENDER_BUILD"):
        with app.app_context():
            # Criar tabelas (migração já foi executada no build)
            print("🔧 Criando tabelas do banco de dados...")
            db.create_all()
            print("✅ Tabelas criadas com sucesso!")
            
            # Verificar se as colunas necessárias existem (fallback de segurança)
            try:
                from sqlalchemy import inspect, text
                inspector = inspect(db.engine)
                
                # Verificar tabela users
                if inspector.has_table('users'):
                    columns = [col['name'] for col in inspector.get_columns('users')]
                    required_columns = ['is_teacher', 'is_active', 'created_at', 'last_login']
                    missing_columns = [col for col in required_columns if col not in columns]
                    
                    if missing_columns:
                        print(f"⚠️ Colunas faltando detectadas: {missing_columns}")
                        print("🔧 Adicionando colunas faltantes...")
                        
                        with db.engine.connect() as conn:
                            for col in missing_columns:
                                try:
                                    if col == 'is_teacher':
                                        conn.execute(text("ALTER TABLE users ADD COLUMN is_teacher BOOLEAN DEFAULT FALSE"))
                                    elif col == 'is_active':
                                        conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                                    elif col == 'created_at':
                                        conn.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP"))
                                    elif col == 'last_login':
                                        conn.execute(text("ALTER TABLE users ADD COLUMN last_login TIMESTAMP"))
                                    print(f"✅ Coluna '{col}' adicionada com sucesso")
                                except Exception as e:
                                    print(f"⚠️ Erro ao adicionar coluna '{col}': {e}")
                            conn.commit()
                        print("✅ Fallback de colunas executado com sucesso!")
                    else:
                        print("✅ Todas as colunas necessárias estão presentes!")
                
                # Verificar e adicionar coluna turma_meta na tabela students
                if inspector.has_table('students'):
                    student_columns = [col['name'] for col in inspector.get_columns('students')]
                    
                    if 'turma_meta' not in student_columns:
                        print("🔧 Adicionando coluna turma_meta à tabela students...")
                        try:
                            with db.engine.connect() as conn:
                                conn.execute(text("ALTER TABLE students ADD COLUMN turma_meta VARCHAR(10)"))
                                conn.commit()
                            print("✅ Coluna turma_meta adicionada com sucesso!")
                            
                            # Migrar dados existentes
                            print("🔄 Migrando dados para turma_meta...")
                            students_to_migrate = Student.query.filter(Student.turma_meta.is_(None)).all()
                            migrated_count = 0
                            
                            for student in students_to_migrate:
                                if student.class_info and student.class_info.meta_label:
                                    student.turma_meta = student.class_info.meta_label
                                    migrated_count += 1
                            
                            if migrated_count > 0:
                                db.session.commit()
                                print(f"✅ {migrated_count} alunos migrados para turma_meta!")
                            
                        except Exception as e:
                            print(f"⚠️ Erro ao adicionar/migrar turma_meta: {e}")
                    else:
                        print("✅ Coluna turma_meta já existe!")
                        
            except Exception as e:
                print(f"⚠️ Erro no fallback de verificação de colunas: {e}")
            
            # Opcional: seed de admin apenas se AUTO_CREATE_TABLES estiver habilitado
            if os.getenv("AUTO_CREATE_TABLES", "0") == "1":
                admin_user = os.getenv("ADMIN_USERNAME", "admin")
                try:
                    # Verificar se o usuário admin já existe (com tratamento de erro)
                    existing_user = None
                    try:
                        existing_user = User.query.filter_by(username=admin_user).first()
                    except Exception as query_error:
                        print(f"⚠️ Erro ao consultar usuário existente: {query_error}")
                        # Se a consulta falhar, assumir que o usuário não existe
                        existing_user = None
                    
                    if not existing_user:
                        print("👤 Criando usuário administrador...")
                        u = User(
                            username=admin_user,
                            email=os.getenv("ADMIN_EMAIL", "admin@example.com"),
                            is_admin=True,
                            is_active=True,
                            created_at=datetime.utcnow()
                        )
                        u.set_password(os.getenv("ADMIN_PASSWORD", "admin123"))
                        db.session.add(u)
                        db.session.commit()
                        print(f"✅ Usuário admin criado: {admin_user}")
                    else:
                        print(f"ℹ️ Usuário admin já existe: {admin_user}")
                except Exception as admin_error:
                    print(f"⚠️ Erro ao criar usuário admin: {admin_error}")
    
    # Importar e registrar blueprint da API
    from api_endpoints import api_bp
    app.register_blueprint(api_bp)
    
    # Retornar a instância csrf para uso global
    return app, csrf

app, csrf = create_app()

# Imports globais necessários para as rotas
from forms import LoginForm, UploadForm, ClassForm, EditStudentClassForm, UserForm, EditStudentTurmaMetaForm, TeacherForm, EditStudentTeacherForm
from services.importer import ExcelImporter
from models import User, Student, Class, Teacher, ComputedLevel, db

def calculate_cefr_level(total_score):
    """Calcula o nível CEFR baseado na pontuação total"""
    if total_score >= 800:
        return 'B2'
    elif total_score >= 700:
        return 'B1'
    elif total_score >= 650:
        return 'A2+'
    elif total_score >= 600:
        return 'A2'
    else:
        return 'A1'

def calculate_individual_cefr_levels(listening_score, reading_score, lfm_score):
    """
    Calcula os níveis CEFR individuais para cada habilidade
    
    Args:
        listening_score (int): Pontuação de Listening (200-300)
        reading_score (int): Pontuação de Reading (200-300)
        lfm_score (int): Pontuação de Language Form & Meaning (200-300)
        
    Returns:
        dict: Dicionário com os níveis CEFR para cada habilidade
    """
    def score_to_cefr(score):
        """Converte pontuação individual para nível CEFR"""
        if score is None or score < 200:
            return 'A1'
        
        score = float(score)
        
        if 200 <= score <= 245:
            return 'A2'
        elif 246 <= score <= 265:
            return 'A2+'
        elif 266 <= score <= 285:
            return 'B1'
        elif 286 <= score <= 300:
            return 'B2'
        elif score > 300:
            return 'B2+'
        else:
            return 'A1'
    
    return {
        'listening': score_to_cefr(listening_score),
        'reading': score_to_cefr(reading_score),
        'lfm': score_to_cefr(lfm_score)
    }

def hex_to_rgb(hex_color):
    """Converte cor hexadecimal para RGB"""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (0, 0, 0)  # Preto como fallback

def generate_certificate_with_editor_settings(student_data, positions, colors):
    """Gera certificado usando APENAS as configurações do editor - sem fallbacks"""
    try:
        template_path = os.path.join('static', 'templates', 'certificate_template.png')
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template não encontrado: {template_path}")
        
        # Verificar se posições e cores foram fornecidas
        if not positions:
            raise ValueError("Posições não fornecidas. Configure no editor primeiro.")
        
        if not colors:
            raise ValueError("Cores não fornecidas. Configure no editor primeiro.")
        
        # Abrir template
        template = Image.open(template_path)
        certificate = template.copy()
        draw = ImageDraw.Draw(certificate)
        
        # Log das dimensões da imagem template
        print(f"DEBUG BACKEND: Dimensões da imagem template: {template.size}")
        
        # Converter cores hex para RGB
        name_color = hex_to_rgb(colors.get('name_color', '#000000'))
        scores_color = hex_to_rgb(colors.get('scores_color', '#000000'))
        date_color = hex_to_rgb(colors.get('date_color', '#000000'))
        
        print(f"DEBUG BACKEND: Cores recebidas: {colors}")
        
    except Exception as e:
        print(f"Erro na função generate_certificate_with_editor_settings: {str(e)}")
        raise e
    
    # Mapear dados para os campos
    fields_data = {
        'studentName': student_data.get('name', 'N/A'),
        'listeningScore': str(student_data.get('listening', 'N/A')),
        'readingScore': str(student_data.get('reading', 'N/A')),
        'lfmScore': str(student_data.get('lfm', 'N/A')),
        'totalScore': str(student_data.get('total', 'N/A')),
        'testDate': student_data.get('test_date', datetime.now().strftime("%d/%m/%Y"))
    }
    
    # Definir cores por campo
    field_colors = {
        'studentName': name_color,
        'listeningScore': scores_color,
        'readingScore': scores_color,
        'lfmScore': scores_color,
        'totalScore': scores_color,
        'testDate': date_color
    }
    
    print(f"DEBUG BACKEND: Posições recebidas do frontend: {positions}")
    
    # Fator de conversão do editor (800x566) para imagem real (2000x1414)
    scale_factor_x = 2000 / 800  # 2.5
    scale_factor_y = 1414 / 566  # 2.5
    
    print(f"DEBUG BACKEND: Fatores de escala - X: {scale_factor_x}, Y: {scale_factor_y}")
    print(f"DEBUG BACKEND: Editor dimensions: 800x566, Template dimensions: 2000x1414")
    
    # Adicionar texto aos campos usando APENAS posições do editor
    for field_name, text in fields_data.items():
        # Verificar se o campo existe nas posições fornecidas
        if field_name not in positions:
            print(f"DEBUG BACKEND: Campo {field_name} não encontrado nas posições, pulando")
            continue
        
        pos = positions[field_name]
        
        # Converter coordenadas do editor para a escala da imagem real
        x = int(pos['x'] * scale_factor_x)
        y = int(pos['y'] * scale_factor_y)
        
        print(f"DEBUG BACKEND: Campo {field_name}:")
        print(f"  - Posição original (editor): x={pos['x']}, y={pos['y']}")
        print(f"  - Posição escalada (template): x={x}, y={y}")
        print(f"  - Texto: '{text}'")
        
        # Obter fonte apropriada - usar font_size das posições
        if 'font_size' in pos:
            # Usar tamanho de fonte das posições (já em pixels do editor) e escalar
            font_size = int(pos['font_size'] * 2.5)
            print(f"  - Font size das posições: {pos['font_size']}px -> {font_size}px (escalado)")
        else:
            raise ValueError(f"Font size não fornecido para o campo {field_name}")
            
        try:
            if field_name == 'studentName':
                font = ImageFont.truetype("arialbd.ttf", font_size)  # Bold para nome
            else:
                font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Desenhar texto
        draw.text(
            (x, y),
            text,
            fill=field_colors.get(field_name, (0, 0, 0)),
            font=font
        )
        print(f"  - Texto desenhado na posição final: ({x}, {y})")
    
    print("DEBUG BACKEND: Certificado gerado com sucesso")
    
    # Converter para bytes
    img_buffer = io.BytesIO()
    certificate.save(img_buffer, format='PNG', quality=95)
    img_buffer.seek(0)
    
    return img_buffer

def generate_certificate_preview_editor_scale(student_data, positions=None, colors=None):
    """
    Gera preview do certificado na mesma escala do editor (800x566) 
    para sincronização perfeita de posicionamento
    """
    # Carregar template base
    template_path = os.path.join('static', 'templates', 'certificate_template.png')
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template não encontrado: {template_path}")
    
    # Abrir e redimensionar template para escala do editor
    certificate = Image.open(template_path)
    certificate = certificate.resize((800, 566), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(certificate)
    
    # Processar cores - EXIGIR que sejam fornecidas
    if not colors:
        raise ValueError("Cores não fornecidas. Configure no editor primeiro.")
    
    name_color = tuple(int(colors.get('name_color', '#000000')[i:i+2], 16) for i in (1, 3, 5))
    scores_color = tuple(int(colors.get('scores_color', '#ff0000')[i:i+2], 16) for i in (1, 3, 5))
    date_color = tuple(int(colors.get('date_color', '#000000')[i:i+2], 16) for i in (1, 3, 5))
    
    # Dados dos campos
    fields_data = {
        'studentName': student_data.get('name', 'Nome do Estudante'),
        'listeningScore': str(student_data.get('listening', 'N/A')),
        'readingScore': str(student_data.get('reading', 'N/A')),
        'lfmScore': str(student_data.get('lfm', 'N/A')),
        'totalScore': str(student_data.get('total', 'N/A')),
        'testDate': student_data.get('test_date', datetime.now().strftime("%d/%m/%Y"))
    }
    
    # Cores por campo
    field_colors = {
        'studentName': name_color,
        'listeningScore': scores_color,
        'readingScore': scores_color,
        'lfmScore': scores_color,
        'totalScore': scores_color,
        'testDate': date_color
    }
    
    # EXIGIR que posições sejam fornecidas
    if not positions:
        raise ValueError("Posições não fornecidas. Configure no editor primeiro.")
    
    print(f"DEBUG PREVIEW: Posições recebidas (escala editor): {positions}")
    
    # Adicionar texto usando posições diretas (sem escala)
    for field_name, text in fields_data.items():
        if field_name not in positions:
            print(f"DEBUG PREVIEW: Campo {field_name} não encontrado nas posições, pulando")
            continue
        
        pos = positions[field_name]
        
        # Usar posições diretas (mesma escala do editor)
        x = int(pos['x'])
        y = int(pos['y'])
        
        print(f"DEBUG PREVIEW: Campo {field_name} - posição: x={x}, y={y}")
        
        # EXIGIR que tamanho da fonte seja fornecido
        if 'font_size' not in pos:
            raise ValueError(f"Tamanho da fonte não fornecido para o campo {field_name}. Configure no editor primeiro.")
        
        font_size = int(pos['font_size'])
        print(f"DEBUG PREVIEW: Font size: {font_size}px (direto do editor)")
        
        # Carregar fonte
        try:
            if field_name == 'studentName':
                font = ImageFont.truetype("arialbd.ttf", font_size)
            else:
                font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Desenhar texto
        draw.text(
            (x, y),
            text,
            fill=field_colors.get(field_name, (0, 0, 0)),
            font=font
        )
        print(f"DEBUG PREVIEW: Texto '{text}' desenhado em ({x}, {y})")
    
    print("DEBUG PREVIEW: Preview gerado na escala do editor (800x566)")
    
    # Converter para bytes
    img_buffer = io.BytesIO()
    certificate.save(img_buffer, format='PNG', quality=95)
    img_buffer.seek(0)
    
    return img_buffer

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        print(f"DEBUG: Tentativa de login com usuário: {form.username.data}")
        user = User.query.filter_by(username=form.username.data).first()
        print(f"DEBUG: Usuário encontrado: {user is not None}")
        
        if user:
            print(f"DEBUG: Usuário ativo: {user.is_active}")
            senha_correta = check_password_hash(user.password_hash, form.password.data)
            print(f"DEBUG: Senha correta: {senha_correta}")
            
            if senha_correta and user.is_active:
                user.update_last_login()
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                print(f"DEBUG: Login bem-sucedido, redirecionando para: {next_page or 'dashboard'}")
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            elif not user.is_active:
                flash('Sua conta está desativada. Entre em contato com o administrador.', 'warning')
            else:
                flash('Usuário ou senha inválidos.', 'danger')
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    else:
        if form.errors:
            print(f"DEBUG: Erros no formulário: {form.errors}")
    
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))

# Rota de health-check do DB
@app.route("/health/db")
def health_db():
    try:
        db.session.execute(db.text("SELECT 1"))
        return {"db": "ok"}, 200
    except Exception as e:
        return {"db": "error", "detail": str(e)}, 500

@app.route('/dash')
@login_required
def dashboard():
    # Cache das estatísticas básicas por 5 minutos
    @lru_cache(maxsize=1)
    def get_basic_stats():
        return {
            'total_students': Student.query.count(),
            'total_classes': Class.query.count()
        }
    
    # Cache das médias por 5 minutos
    @lru_cache(maxsize=1)
    def get_avg_scores():
        return db.session.query(
            db.func.avg(Student.listening),
            db.func.avg(Student.reading),
            db.func.avg(Student.lfm),
            db.func.avg(Student.total)
        ).first()
    
    # Obter estatísticas básicas do cache
    basic_stats = get_basic_stats()
    total_students = basic_stats['total_students']
    total_classes = basic_stats['total_classes']
    
    # Distribuição por nível CEFR usando o método correto do Student
    students = Student.query.all()
    cefr_counts = {}
    for student in students:
        cefr_level = student.get_cefr_level()
        if cefr_level and cefr_level != 'N/A':
            cefr_counts[cefr_level] = cefr_counts.get(cefr_level, 0) + 1
    
    # Converter para formato esperado pelo template
    cefr_distribution = [(level, count) for level, count in cefr_counts.items()]
    cefr_distribution.sort(key=lambda x: x[0])  # Ordenar por nível
    
    # Calcular nível predominante
    predominant_level = 'N/A'
    if cefr_distribution:
        # Encontrar o nível com maior contagem
        max_count = max(cefr_distribution, key=lambda x: x[1])
        predominant_level = max_count[0] if max_count[0] else 'N/A'
    
    # Médias por habilidade (usando cache)
    avg_scores = get_avg_scores()
    
    # Top 10 estudantes separados por ano escolar
    # 6° ano - baseado no meta_label das turmas (6.1, 6.2, 6.3)
    top_students_6th = Student.query.join(Class).filter(
        Student.total.isnot(None),
        Class.meta_label.like('6.%')
    ).order_by(Student.total.desc()).limit(10).all()
    
    # 9° ano - baseado no meta_label das turmas (9.1, 9.2, 9.3)
    top_students_9th = Student.query.join(Class).filter(
        Student.total.isnot(None),
        Class.meta_label.like('9.%')
    ).order_by(Student.total.desc()).limit(10).all()
    
    # Bottom 10 estudantes (valores NULL por último)
    bottom_students = Student.query.filter(Student.total.isnot(None)).order_by(Student.total.asc()).limit(10).all()
    
    # Novas estatísticas TOEFL Junior
    # Distribuição por CEFR Listening
    listening_cefr_distribution = db.session.query(
        Student.list_cefr,
        db.func.count(Student.id)
    ).group_by(Student.list_cefr).all()
    
    # CEFR Listening predominante
    predominant_listening_cefr = 'N/A'
    if listening_cefr_distribution:
        max_count = max(listening_cefr_distribution, key=lambda x: x[1])
        predominant_listening_cefr = max_count[0] if max_count[0] else 'N/A'
    
    # Distribuição por rótulo escolar (usando class meta_label)
    school_label_distribution = db.session.query(
        Class.meta_label,
        db.func.count(Student.id)
    ).join(Student, Class.id == Student.class_id).group_by(Class.meta_label).all()
    
    # Rótulo escolar predominante
    predominant_school_label = 'N/A'
    if school_label_distribution:
        max_count = max(school_label_distribution, key=lambda x: x[1])
        predominant_school_label = max_count[0] if max_count[0] else 'N/A'
    
    # Média das notas de Listening
    avg_listening_grade = db.session.query(
        db.func.avg(Student.listening)
    ).scalar()
    
    # Alunos que atingiram a meta (usando método do modelo)
    students_with_total = Student.query.filter(Student.total.isnot(None)).all()
    students_met_goal = sum(1 for student in students_with_total if student.atingiu_meta())
    
    return render_template('dashboard/index.html',
                         total_students=total_students,
                         total_classes=total_classes,
                         cefr_distribution=cefr_distribution,
                         predominant_level=predominant_level,
                         avg_scores=avg_scores,
                         top_students_6th=top_students_6th,
                         top_students_9th=top_students_9th,
                         top_students=top_students_6th + top_students_9th,
                         bottom_students=bottom_students,
                         # Novas estatísticas TOEFL Junior
                         listening_cefr_distribution=listening_cefr_distribution,
                         predominant_listening_cefr=predominant_listening_cefr,
                         school_label_distribution=school_label_distribution,
                         predominant_school_label=predominant_school_label,
                         avg_listening_grade=avg_listening_grade,
                         students_met_goal=students_met_goal)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm()
    
    if form.validate_on_submit():
        file = form.file.data
        class_id = form.class_id.data if form.class_id.data != 0 else None
        
        # Salvar arquivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Processar arquivo
        importer = ExcelImporter(file_path, class_id)
        result = importer.import_data()
        
        if result['success']:
            flash(f'Arquivo processado com sucesso! {result["processed"]} registros importados, '
                  f'{result["duplicates"]} duplicatas atualizadas, {result["errors"]} erros.', 'success')
        else:
            flash(f'Erro ao processar arquivo: {result["error"]}', 'danger')
        
        return redirect(url_for('students'))
    
    return render_template('upload/index.html', form=form)

@app.route('/upload/preview', methods=['POST'])
@login_required
@csrf.exempt
def upload_preview():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
    
    # Salvar arquivo temporário
    filename = secure_filename(file.filename)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_' + filename)
    file.save(temp_path)
    
    try:
        # Criar objeto de upload temporário
        importer = ExcelImporter(temp_path)
        result = importer.preview_data()
        
        # Remover arquivo temporário
        os.remove(temp_path)
        
        return jsonify(result)
    
    except Exception as e:
        # Remover arquivo temporário em caso de erro
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/alunos')
@login_required
def students():
    from forms import SearchForm
    from models import ComputedLevel
    
    form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Construir query base com join para ComputedLevel
    query = Student.query.outerjoin(ComputedLevel)
    
    # Aplicar filtros
    search = request.args.get('search', '')
    class_filter = request.args.get('class_filter', 0, type=int)
    teacher_filter = request.args.get('teacher_filter', 0, type=int)
    cefr_filter = request.args.get('cefr_filter', '')
    
    if search:
        # Busca inteligente com múltiplos nomes
        # Suporta separação por vírgula, quebra de linha ou ponto e vírgula
        search_lines = []
        
        # Primeiro, divide por quebras de linha
        for line in search.strip().split('\n'):
            line = line.strip()
            if line:
                # Depois divide por vírgula ou ponto e vírgula
                if ',' in line:
                    search_lines.extend([name.strip() for name in line.split(',') if name.strip()])
                elif ';' in line:
                    search_lines.extend([name.strip() for name in line.split(';') if name.strip()])
                else:
                    search_lines.append(line)
        
        # Se não há separadores, trata como busca normal
        if not search_lines:
            search_lines = [search.strip()]
        
        # Para cada nome na lista, cria condições de busca
        all_conditions = []
        
        for search_name in search_lines:
            if not search_name:
                continue
                
            # Divide cada nome em termos
            search_terms = search_name.strip().split()
            
            if len(search_terms) == 1:
                # Busca simples com um termo - considerando estrutura "Sobrenome Nome"
                term = search_terms[0]
                
                # REGRA PRINCIPAL: Priorizar APENAS o primeiro nome (segunda posição)
                # Estrutura: "Sobrenome PRIMEIRO_NOME"
                name_conditions = [
                    # APENAS primeiro nome (segunda posição): "Sobrenome TERMO"
                    Student.name.ilike(f'% {term}'),    # Termina com o termo (primeiro nome)
                ]
                
                # Condição para número do estudante (mantida para casos especiais)
                number_condition = Student.student_number.ilike(f'%{term}%')
                
                # Combina condições: APENAS primeiro nome OU número
                all_conditions.append(db.or_(*name_conditions, number_condition))
            else:
                # Busca com múltiplos termos - busca inteligente por posição
                search_conditions = []
                
                # Para cada termo, verifica se pode ser primeiro ou último nome
                for i, term in enumerate(search_terms):
                    term_conditions = []
                    
                    if i == 0:  # Primeiro termo da busca
                        # APENAS primeiro nome (segunda posição) - regra restritiva
                        term_conditions.extend([
                            Student.name.ilike(f'% {term}'),  # Primeiro nome (segunda posição)
                        ])
                    elif i == len(search_terms) - 1:  # Último termo da busca
                        # APENAS primeiro nome (segunda posição) - regra restritiva
                        term_conditions.extend([
                            Student.name.ilike(f'% {term}'),  # Primeiro nome (segunda posição)
                        ])
                    else:  # Termos do meio
                        # APENAS primeiro nome (segunda posição) - regra restritiva
                        term_conditions.append(Student.name.ilike(f'% {term}'))
                    
                    # Cada termo deve ser encontrado (AND entre termos)
                    search_conditions.append(db.or_(*term_conditions))
                
                # TODOS os termos devem ser encontrados (busca exata)
                name_and_condition = db.and_(*search_conditions)
                
                # Também permite busca no número do estudante
                number_condition = Student.student_number.ilike(f'%{search_name}%')
                
                # Combina: (busca inteligente no nome) OU (nome completo no número)
                exact_condition = db.or_(name_and_condition, number_condition)
                
                # Se a busca exata não encontrar resultados, tenta busca flexível
                # Primeiro testa se a busca exata retorna algo
                exact_results = Student.query.filter(exact_condition).all()
                
                if exact_results:
                    # Se encontrou com busca exata, usa ela
                    all_conditions.append(exact_condition)
                else:
                    # Se não encontrou, usa busca flexível RESTRITIVA (apenas primeiro nome)
                    flexible_conditions = []
                    for term in search_terms:
                        term_flexible = [
                            # APENAS primeiro nome (segunda posição) - regra restritiva
                            Student.name.ilike(f'% {term}'),  # Primeiro nome
                            Student.student_number.ilike(f'%{term}%')  # Número
                        ]
                        flexible_conditions.append(db.or_(*term_flexible))
                    
                    # Na busca flexível, pelo menos UM termo deve ser encontrado
                    all_conditions.append(db.or_(*flexible_conditions))
        
        # Combina todas as condições de todos os nomes com OR
        if all_conditions:
            query = query.filter(db.or_(*all_conditions))
    
    if class_filter:
        query = query.filter(Student.class_id == class_filter)
    
    if teacher_filter:
        query = query.filter(Student.teacher_id == teacher_filter)
    
    if cefr_filter:
        query = query.filter(ComputedLevel.overall_level == cefr_filter)
    
    # Ordenação
    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'asc')
    
    # Se há busca ativa, aplica ordenação por relevância
    if search and all_conditions:
        # Importa módulo de relevância
        from search_relevance import sort_students_by_relevance
        
        # Coleta todos os termos de busca de todas as linhas
        all_search_terms = []
        for search_name in search_lines:
            if search_name:
                all_search_terms.extend(search_name.strip().split())
        
        # Remove duplicatas mantendo ordem
        unique_terms = []
        for term in all_search_terms:
            if term not in unique_terms:
                unique_terms.append(term)
        
        # Aplica ordenação por relevância
        all_students = query.all()
        students_with_relevance = sort_students_by_relevance(all_students, unique_terms)
        
        # Extrai apenas os estudantes ordenados por relevância
        all_students = [student for student, relevance in students_with_relevance]
        
        # Cria uma nova query com os IDs ordenados por relevância
        if all_students:
            student_ids = [s.id for s in all_students]
            # Usa CASE WHEN para manter a ordem de relevância
            whens = [(Student.id == student_id, index) for index, student_id in enumerate(student_ids)]
            order_case = db.case(*whens, else_=len(student_ids))
            query = query.filter(Student.id.in_(student_ids)).order_by(order_case)
        else:
            # Se não há estudantes, cria query vazia
            query = query.filter(Student.id == -1)
    else:
        # Ordenação normal quando não há busca
        if sort_by == 'name':
            query = query.order_by(Student.name.asc() if sort_order == 'asc' else Student.name.desc())
        elif sort_by == 'student_number':
            query = query.order_by(Student.student_number.asc() if sort_order == 'asc' else Student.student_number.desc())
        elif sort_by == 'total':
            # Ordenar por total com valores NULL por último
            if sort_order == 'asc':
                query = query.order_by(Student.total.asc().nullslast())
            else:
                query = query.order_by(Student.total.desc().nullslast())
        elif sort_by == 'overall_level':
            query = query.order_by(ComputedLevel.overall_level.asc() if sort_order == 'asc' else ComputedLevel.overall_level.desc())
        elif sort_by == 'school_level':
            query = query.order_by(ComputedLevel.school_level.asc() if sort_order == 'asc' else ComputedLevel.school_level.desc())
        elif sort_by == 'teacher':
            query = query.join(Teacher, Student.teacher_id == Teacher.id, isouter=True).order_by(Teacher.name.asc(), Student.name.asc())
        
        # Calcular estatísticas antes da paginação
        all_students = query.all()
    
    stats = {
        'avg_total': None,
        'predominant_cefr': None,
        'total_students': len(all_students)
    }
    
    if all_students:
        # Calcular média total
        total_scores = [s.total for s in all_students if s.total is not None]
        if total_scores:
            stats['avg_total'] = sum(total_scores) / len(total_scores)
        
        # Encontrar CEFR predominante
        cefr_counts = {}
        for student in all_students:
            computed_level = ComputedLevel.query.filter_by(student_id=student.id).first()
            if computed_level and computed_level.overall_level:
                cefr_counts[computed_level.overall_level] = cefr_counts.get(computed_level.overall_level, 0) + 1
        
        if cefr_counts:
            stats['predominant_cefr'] = max(cefr_counts, key=cefr_counts.get)
    
    # Paginação
    students = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Buscar professores ativos para o dropdown
    teachers = Teacher.query.order_by(Teacher.name).all()
    
    # Buscar turmas ativas para o dropdown
    classes = Class.query.filter_by(is_active=True).order_by(Class.name).all()
    
    return render_template('students/index.html', 
                         students=students, 
                         form=form,
                         search=search,
                         class_filter=class_filter,
                         teacher_filter=teacher_filter,
                         cefr_filter=cefr_filter,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         stats=stats,
                         teachers=teachers,
                         classes=classes)

@app.route('/alunos/<int:id>')
@login_required
def student_detail(id):
    from models import ComputedLevel
    
    student = Student.query.get_or_404(id)
    computed_level = ComputedLevel.query.filter_by(student_id=student.id).first()
    
    # Buscar professor se existir
    teacher = None
    if student.teacher_id:
        teacher = Teacher.query.get(student.teacher_id)
    
    return render_template('students/detail.html', 
                         student=student, 
                         computed_level=computed_level,
                         teacher=teacher)

@app.route('/alunos/<int:id>/editar-turma', methods=['GET', 'POST'])
@login_required
def edit_student_class(id):
    student = Student.query.get_or_404(id)
    form = EditStudentClassForm()
    
    if form.validate_on_submit():
        if form.class_id.data == 0:
            flash('Por favor, selecione uma turma válida.', 'warning')
        else:
            old_class = student.class_info.name if student.class_info else 'Sem turma'
            new_class = Class.query.get(form.class_id.data)
            
            student.class_id = form.class_id.data
            student.updated_at = datetime.utcnow()
            
            try:
                db.session.commit()
                flash(f'Turma do aluno {student.name} alterada de "{old_class}" para "{new_class.name}" com sucesso!', 'success')
                return redirect(url_for('student_detail', id=student.id))
            except Exception as e:
                db.session.rollback()
                flash('Erro ao alterar a turma do aluno. Tente novamente.', 'danger')
    
    # Pré-selecionar a turma atual do aluno
    if student.class_id:
        form.class_id.data = student.class_id
    
    return render_template('students/edit_class.html', student=student, form=form)

@app.route('/alunos/<int:id>/editar-rotulo-escolar', methods=['GET', 'POST'])
@login_required
def edit_student_turma_meta(id):
    """Editar rótulo escolar (turma_meta) do aluno"""
    student = Student.query.get_or_404(id)
    form = EditStudentTurmaMetaForm(student=student)
    
    if form.validate_on_submit():
        old_turma_meta = student.turma_meta
        new_turma_meta = form.turma_meta.data
        
        # Atualizar turma_meta (o event listener cuidará do recálculo automático)
        student.turma_meta = new_turma_meta
        student.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash(f'Rótulo escolar do aluno {student.name} alterado de "{old_turma_meta}" para "{new_turma_meta}" com sucesso! A nota de Listening foi recalculada automaticamente.', 'success')
            return redirect(url_for('student_detail', id=student.id))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao alterar o rótulo escolar do aluno. Tente novamente.', 'danger')
    
    # Pré-selecionar o rótulo atual do aluno
    if student.turma_meta:
        form.turma_meta.data = student.turma_meta
    
    return render_template('students/edit_turma_meta.html', student=student, form=form)

@app.route('/api/alunos/<int:id>/alterar-turma', methods=['POST'])
@login_required
def api_change_student_class(id):
    """API endpoint para alterar turma do aluno via AJAX"""
    try:
        student = Student.query.get_or_404(id)
        data = request.get_json()
        
        if not data or 'class_id' not in data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        new_class_id = data['class_id']
        
        # Validar se a turma existe e está ativa
        if new_class_id != 0:  # 0 significa "sem turma"
            new_class = Class.query.filter_by(id=new_class_id, is_active=True).first()
            if not new_class:
                return jsonify({'success': False, 'error': 'Turma não encontrada ou inativa'}), 400
        
        # Salvar informações antigas para o log
        old_class_name = student.class_info.name if student.class_info else 'Sem turma'
        
        # Atualizar a turma do aluno
        student.class_id = new_class_id if new_class_id != 0 else None
        student.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Preparar resposta
        new_class_name = new_class.name if new_class_id != 0 else 'Sem turma'
        
        return jsonify({
            'success': True,
            'message': f'Turma alterada de "{old_class_name}" para "{new_class_name}"',
            'old_class': old_class_name,
            'new_class': new_class_name,
            'new_class_id': new_class_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/update_student_teacher', methods=['POST'])
@login_required
@csrf.exempt
def update_student_teacher():
    """API endpoint para alterar professor do aluno via AJAX"""
    try:
        data = request.get_json()
        
        if not data or 'student_id' not in data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        student_id = data['student_id']
        teacher_id = data.get('teacher_id')
        
        # Buscar o aluno
        student = Student.query.get_or_404(student_id)
        
        # Validar se o professor existe (se fornecido)
        teacher = None
        if teacher_id:
            teacher = Teacher.query.get(teacher_id)
            if not teacher:
                return jsonify({'success': False, 'error': 'Professor não encontrado'}), 400
        
        # Salvar informações antigas para o log
        old_teacher_name = student.teacher.name if student.teacher else 'Sem professor'
        
        # Atualizar o professor do aluno
        student.teacher_id = teacher_id
        student.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Preparar resposta
        new_teacher_name = teacher.name if teacher_id else 'Sem professor'
        
        return jsonify({
            'success': True,
            'message': f'Professor alterado de "{old_teacher_name}" para "{new_teacher_name}"',
            'old_teacher': old_teacher_name,
            'new_teacher': new_teacher_name,
            'teacher_id': teacher_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/student/<int:student_id>/report')
@login_required
def student_report(student_id):
    """Gera relatório individual do aluno com carta personalizada"""
    try:
        # Buscar o aluno
        student = Student.query.get_or_404(student_id)
        
        # Calcular níveis CEFR individuais
        cefr_levels = calculate_individual_cefr_levels(
            student.listening, 
            student.reading, 
            student.lfm
        )
        
        # Calcular nível CEFR geral
        overall_cefr = student.calculate_final_cefr() if student.total else 'N/A'
        
        # Preparar dados para o template
        report_data = {
            'student': student,
            'listening_cefr': cefr_levels['listening'],
            'reading_cefr': cefr_levels['reading'],
            'lfm_cefr': cefr_levels['lfm'],
            'overall_cefr': overall_cefr
        }
        
        return render_template('reports/student_report.html', **report_data)
        
    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/student/<int:student_id>/report/download')
@login_required
def download_student_report(student_id):
    """Gera e baixa o certificado do aluno em formato PNG com cores personalizáveis e posições personalizadas"""
    try:
        # Buscar o aluno
        student = Student.query.get_or_404(student_id)
        
        # Obter cores personalizadas dos parâmetros da URL
        header_color = request.args.get('header_color', '#007bff')
        background_color = request.args.get('background_color', '#ffffff')
        text_color = request.args.get('text_color', '#000000')
        accent_color = request.args.get('accent_color', '#28a745')
        
        # Preparar cores personalizadas para o certificado
        custom_colors = {
            'name_color': text_color,
            'scores_color': accent_color,
            'date_color': text_color
        }
        
        # Verificar se existem posições personalizadas salvas
        custom_positions = None
        try:
            # Primeiro, tentar carregar layout padrão do diretório static
            default_file = os.path.join('static', 'default_certificate_layout.json')
            if os.path.exists(default_file):
                import json
                with open(default_file, 'r') as f:
                    custom_positions = json.load(f)
            
            # Depois, verificar se há posições específicas para este estudante (sobrescreve o padrão)
            positions_file = f"custom_positions_{student_id}.json"
            if os.path.exists(positions_file):
                import json
                with open(positions_file, 'r') as f:
                    custom_positions = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar posições personalizadas: {e}")
            pass  # Se não conseguir carregar, usar posições padrão
        
        # Preparar dados do estudante
        student_data = {
            'name': student.name,
            'listening': student.listening,
            'reading': student.reading,
            'lfm': student.lfm,
            'total': student.total,
            'test_date': datetime.now().strftime("%d/%m/%Y")
        }
        
        # Gerar certificado PNG com as informações do estudante
        certificate_buffer = generate_certificate_with_editor_settings(student_data, custom_positions or {}, custom_colors)
        
        # Preparar nome do arquivo
        has_custom_colors = any([
            header_color != '#007bff',
            background_color != '#ffffff', 
            text_color != '#000000',
            accent_color != '#28a745'
        ])
        
        has_custom_positions = custom_positions is not None
        
        suffix = ""
        if has_custom_positions and has_custom_colors:
            suffix = "_personalizado_completo"
        elif has_custom_positions:
            suffix = "_layout_personalizado"
        elif has_custom_colors:
            suffix = "_cores_personalizadas"
        
        filename = f"Certificado_{student.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}{suffix}.png"
        
        return send_file(
            certificate_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='image/png'
        )
        
    except Exception as e:
        flash(f'Erro ao gerar download do relatório: {str(e)}', 'error')
        return redirect(url_for('student_report', student_id=student_id))

@app.route('/certificate/editor')
@login_required
def certificate_editor():
    """Editor visual de certificado com funcionalidade drag-and-drop"""
    return render_template('certificate/editor.html')

@app.route('/api/students/<int:student_id>', methods=['GET'])
@login_required
def get_student_data(student_id):
    """Retorna os dados de um estudante específico para o editor"""
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Estudante não encontrado'}), 404
        
        return jsonify({
            'id': student.id,
            'name': student.name,
            'listening': student.listening,
            'reading': student.reading,
            'lfm': student.lfm,
            'total': student.total,
            'test_date': student.created_at.strftime('%d/%m/%Y') if student.created_at else datetime.now().strftime('%d/%m/%Y')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/certificate/save-positions', methods=['POST'])
@login_required
@csrf.exempt
def save_certificate_positions():
    """Salva as posições personalizadas dos elementos do certificado e cores"""
    try:
        data = request.get_json()
        
        if not data or 'positions' not in data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        positions = data['positions']
        colors = data.get('colors', {})  # Incluir cores
        student_id = data.get('student_id')
        is_default = data.get('is_default', False)
        
        # Combinar posições e cores em um único objeto
        layout_data = {
            'positions': positions,
            'colors': colors
        }
        
        import json
        
        if is_default:
            # Salvar como layout padrão para todos os estudantes
            default_file = "static/default_certificate_layout.json"
            with open(default_file, 'w') as f:
                json.dump(layout_data, f, indent=2)
            
            return jsonify({
                'success': True, 
                'message': 'Layout padrão salvo com sucesso! Este layout será usado para todos os novos certificados.'
            })
        elif student_id:
            # Salvar posições específicas para este estudante
            positions_file = f"custom_positions_{student_id}.json"
            with open(positions_file, 'w') as f:
                json.dump(layout_data, f, indent=2)
            
            return jsonify({
                'success': True, 
                'message': 'Posições e cores personalizadas salvas com sucesso!'
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'Posições e cores salvas com sucesso',
                'positions': positions,
                'colors': colors
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/certificate/save-default-layout', methods=['POST'])
@login_required
@csrf.exempt
def save_default_certificate_layout():
    """Salva o layout padrão para todos os certificados"""
    try:
        data = request.get_json()
        
        if not data or 'positions' not in data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        positions = data['positions']
        colors = data.get('colors', {})
        
        # Combinar posições e cores em um único objeto
        layout_data = {
            'positions': positions,
            'colors': colors
        }
        
        import json
        
        # Salvar como layout padrão para todos os estudantes
        default_file = "static/default_certificate_layout.json"
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(default_file), exist_ok=True)
        
        with open(default_file, 'w', encoding='utf-8') as f:
            json.dump(layout_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True, 
            'message': 'Layout padrão salvo com sucesso! Este layout será usado para todos os novos certificados.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/certificate/save-colors', methods=['POST'])
@login_required
def save_certificate_colors():
    """Salva apenas as cores personalizadas dos elementos do certificado"""
    try:
        data = request.get_json()
        colors = data.get('colors', {})
        student_id = data.get('student_id')
        
        if student_id:
            # Salvar cores específicas do estudante
            positions_file = f'custom_positions_{student_id}.json'
            
            # Carregar dados existentes se houver
            layout_data = {}
            if os.path.exists(positions_file):
                import json
                with open(positions_file, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                    
                # Se for formato antigo (só posições), converter para novo formato
                if 'positions' not in layout_data:
                    layout_data = {'positions': layout_data, 'colors': {}}
            else:
                layout_data = {'positions': {}, 'colors': {}}
            
            # Atualizar apenas as cores
            layout_data['colors'] = colors
            
            # Salvar arquivo atualizado
            import json
            with open(positions_file, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, ensure_ascii=False, indent=2)
                
            return jsonify({
                'success': True, 
                'message': f'Cores salvas para o estudante {student_id}',
                'colors': colors
            })
        else:
            # Salvar cores como padrão
            default_layout_path = os.path.join('static', 'default_certificate_layout.json')
            
            # Carregar dados existentes se houver
            layout_data = {}
            if os.path.exists(default_layout_path):
                import json
                with open(default_layout_path, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                    
                # Se for formato antigo (só posições), converter para novo formato
                if 'positions' not in layout_data:
                    layout_data = {'positions': layout_data, 'colors': {}}
            else:
                layout_data = {'positions': {}, 'colors': {}}
            
            # Atualizar apenas as cores
            layout_data['colors'] = colors
            
            # Salvar arquivo atualizado
            import json
            with open(default_layout_path, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, ensure_ascii=False, indent=2)
                
            return jsonify({
                'success': True, 
                'message': 'Cores salvas como padrão',
                'colors': colors
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/certificate/colors', methods=['GET'])
@login_required
def load_certificate_colors():
    """Carrega as cores salvas do certificado"""
    try:
        student_id = request.args.get('student_id')
        
        if student_id:
            # Carregar cores específicas do estudante
            positions_file = f'custom_positions_{student_id}.json'
            
            if os.path.exists(positions_file):
                import json
                with open(positions_file, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                    
                # Se for formato antigo (só posições), retornar cores padrão
                if 'colors' not in layout_data:
                    return jsonify({
                        'success': False,
                        'message': 'Cores não configuradas para este estudante'
                    }), 404
                    
                return jsonify({
                    'success': True,
                    'colors': layout_data['colors']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Nenhuma configuração encontrada para este estudante'
                }), 404
        else:
            # Carregar cores padrão
            default_layout_path = os.path.join('static', 'default_certificate_layout.json')
            
            if os.path.exists(default_layout_path):
                import json
                with open(default_layout_path, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                    
                # Se for formato antigo (só posições), retornar cores padrão
                if 'colors' not in layout_data:
                    return jsonify({
                        'success': False,
                        'message': 'Cores padrão não configuradas'
                    }), 404
                    
                return jsonify({
                    'success': True,
                    'colors': layout_data['colors']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Configuração padrão não encontrada'
                }), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/certificate/load-positions', methods=['GET'])
@login_required
def load_certificate_positions():
    """Carrega as posições personalizadas dos elementos do certificado e cores"""
    try:
        student_id = request.args.get('student_id')
        
        if student_id:
            # Tentar carregar layout específico do estudante
            positions_file = f'custom_positions_{student_id}.json'
            if os.path.exists(positions_file):
                import json
                with open(positions_file, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                
                # Verificar se é o formato antigo (só posições) ou novo (posições + cores)
                if 'positions' in layout_data:
                    return jsonify({
                        'success': True,
                        'positions': layout_data.get('positions', {}),
                        'colors': layout_data.get('colors', {}),
                        'type': 'student_specific'
                    })
                else:
                    # Formato antigo - só posições
                    return jsonify({
                        'success': True,
                        'positions': layout_data,
                        'colors': {},
                        'type': 'student_specific'
                    })
        
        # Se não encontrou layout específico, tentar carregar padrão
        default_layout_path = os.path.join('static', 'default_certificate_layout.json')
        if os.path.exists(default_layout_path):
            import json
            with open(default_layout_path, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
            
            # Verificar se é o formato antigo (só posições) ou novo (posições + cores)
            if 'positions' in layout_data:
                return jsonify({
                    'success': True,
                    'positions': layout_data.get('positions', {}),
                    'colors': layout_data.get('colors', {}),
                    'type': 'default'
                })
            else:
                # Formato antigo - só posições
                return jsonify({
                    'success': True,
                    'positions': layout_data,
                    'colors': {},
                    'type': 'default'
                })
        
        # Se não encontrou nenhum layout
        return jsonify({
            'success': False,
            'message': 'Nenhum layout encontrado'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/certificate/preview', methods=['POST'])
@login_required
@csrf.exempt
def preview_certificate():
    """Gera preview do certificado com posições personalizadas"""
    try:
        data = request.get_json()
        
        student_id = data.get('student_id', 1)  # Usar ID padrão se não fornecido
        positions = data.get('positions', {})
        colors = data.get('colors', {})
        
        # Tentar buscar um estudante real, ou usar dados de exemplo
        student = Student.query.get(student_id)
        if not student:
            # Usar dados de exemplo para preview
            student_data = {
                'name': "Nome do Estudante",
                'listening': 85,
                'reading': 90,
                'lfm': 88,
                'total': 263,
                'test_date': datetime.now().strftime("%d/%m/%Y")
            }
        else:
            student_data = {
                'name': student.name,
                'listening': student.listening,
                'reading': student.reading,
                'lfm': student.lfm,
                'total': student.total,
                'test_date': datetime.now().strftime("%d/%m/%Y")
            }
        
        # IMPORTANTE: Sempre usar as posições enviadas pelo editor
        # Se não há posições fornecidas, retornar erro - DEVE vir do editor
        if not positions:
            return jsonify({
                'success': False, 
                'error': 'Posições não fornecidas. Configure no editor primeiro.'
            }), 400
        
        if not colors:
            return jsonify({
                'success': False, 
                'error': 'Cores não fornecidas. Configure no editor primeiro.'
            }), 400
        
        print(f"DEBUG PREVIEW: Posições recebidas (escala editor): {positions}")
        print(f"DEBUG PREVIEW: Cores recebidas: {colors}")
        
        # Gerar certificado na escala do editor para preview lateral
        certificate_buffer = generate_certificate_preview_editor_scale(student_data, positions, colors)
        
        # Converter para base64 para enviar via JSON
        import base64
        certificate_base64 = base64.b64encode(certificate_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'certificate': certificate_base64
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/certificate/download', methods=['POST'])
@login_required
@csrf.exempt
def download_certificate():
    """Gera e faz download do certificado com posições personalizadas"""
    try:
        data = request.get_json()
        
        print(f"[DOWNLOAD] Dados recebidos: {data}")
        
        # Usar dados do editor se fornecidos, senão usar dados padrão
        student_data = data.get('student_data')
        if not student_data:
            # Fallback para o método antigo
            student_id = data.get('student_id', 1)
            student = Student.query.get(student_id)
            if not student:
                # Criar objeto de exemplo para download
                student_data = {
                    'name': "Nome do Estudante",
                    'listening': 85,
                    'reading': 90,
                    'lfm': 88,
                    'total': 263,
                    'test_date': datetime.now().strftime("%d/%m/%Y")
                }
            else:
                student_data = {
                    'name': student.name,
                    'listening': student.listening,
                    'reading': student.reading,
                    'lfm': student.lfm,
                    'total': student.total,
                    'test_date': datetime.now().strftime("%d/%m/%Y")
                }
        
        positions = data.get('positions', {})
        colors = data.get('colors', {})
        
        print(f"[DOWNLOAD] Posições recebidas: {positions}")
        print(f"[DOWNLOAD] Cores recebidas: {colors}")
        
        # IMPORTANTE: Sempre usar as posições enviadas pelo editor
        # Se não há posições fornecidas, retornar erro - DEVE vir do editor
        if not positions:
            return jsonify({
                'success': False, 
                'error': 'Posições não fornecidas. Configure no editor primeiro.'
            }), 400
        
        if not colors:
            return jsonify({
                'success': False, 
                'error': 'Cores não fornecidas. Configure no editor primeiro.'
            }), 400
        
        # Gerar certificado diretamente
        certificate_buffer = generate_certificate_with_editor_settings(student_data, positions, colors)
        
        # Retornar o arquivo para download
        certificate_buffer.seek(0)
        return send_file(
            certificate_buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name='certificado_modelo.png'
        )
        
    except Exception as e:
        print(f"[DOWNLOAD] Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/alunos/deletar-multiplos', methods=['POST'])
@login_required
@csrf.exempt
def api_delete_multiple_students():
    """API endpoint para deletar múltiplos alunos via AJAX"""
    try:
        data = request.get_json()
        
        if not data or 'student_ids' not in data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        student_ids = data['student_ids']
        
        if not isinstance(student_ids, list) or len(student_ids) == 0:
            return jsonify({'success': False, 'error': 'Lista de IDs inválida'}), 400
        
        # Validar se todos os IDs são números inteiros
        try:
            student_ids = [int(id) for id in student_ids]
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'IDs de alunos inválidos'}), 400
        
        # Buscar os alunos que existem
        students_to_delete = Student.query.filter(Student.id.in_(student_ids)).all()
        
        if not students_to_delete:
            return jsonify({'success': False, 'error': 'Nenhum aluno encontrado para deletar'}), 404
        
        # Contar quantos alunos serão deletados
        deleted_count = len(students_to_delete)
        
        # Deletar os alunos e seus ComputedLevels relacionados
        for student in students_to_delete:
            # Primeiro, deletar explicitamente os ComputedLevels relacionados
            computed_levels = ComputedLevel.query.filter_by(student_id=student.id).all()
            for computed_level in computed_levels:
                db.session.delete(computed_level)
            
            # Depois deletar o aluno
            db.session.delete(student)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} aluno(s) deletado(s) com sucesso',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        # Log the actual error for debugging
        app.logger.error(f'Erro ao deletar alunos: {str(e)}')
        print(f'Erro ao deletar alunos: {str(e)}')  # Also print to console
        return jsonify({'success': False, 'error': f'Erro interno do servidor: {str(e)}'}), 500

@app.route('/api/alunos/<int:id>/alterar-rotulo-escolar', methods=['POST'])
@login_required
def api_change_student_school_label(id):
    """API endpoint para alterar o rótulo escolar de um aluno via AJAX"""
    try:
        student = Student.query.get_or_404(id)
        data = request.get_json()
        
        if not data or 'school_label' not in data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        new_label = data['school_label']
        
        # Validar se o rótulo é válido
        valid_labels = ['', '6.1', '6.2', '6.3', '9.1', '9.2', '9.3']
        if new_label not in valid_labels:
            return jsonify({'success': False, 'error': 'Rótulo escolar inválido'}), 400
        
        # CORREÇÃO: Atualizar o rótulo escolar INDIVIDUAL do aluno, não da turma
        old_label = student.turma_meta
        student.turma_meta = new_label if new_label else None
        student.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Recarregar o aluno para obter os dados atualizados
        db.session.refresh(student)
        
        # Mensagem de sucesso
        if new_label:
            message = f'Rótulo escolar alterado para {new_label}'
        else:
            message = 'Rótulo escolar removido'
        
        return jsonify({
            'success': True,
            'message': message,
            'old_label': old_label,
            'new_label': new_label,
            'updated_data': {
                'listening': student.listening,
                'list_cefr': student.list_cefr,
                'turma_meta': student.turma_meta
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/alunos/export')
@login_required
def export_students():
    # Aplicar os mesmos filtros da listagem
    query = Student.query
    
    search = request.args.get('search', '')
    class_filter = request.args.get('class_filter', 0, type=int)
    cefr_filter = request.args.get('cefr_filter', '')
    
    if search:
        # Busca inteligente com múltiplos nomes
        # Suporta separação por vírgula, quebra de linha ou ponto e vírgula
        search_lines = []
        
        # Primeiro, divide por quebras de linha
        for line in search.strip().split('\n'):
            line = line.strip()
            if line:
                # Depois divide por vírgula ou ponto e vírgula
                if ',' in line:
                    search_lines.extend([name.strip() for name in line.split(',') if name.strip()])
                elif ';' in line:
                    search_lines.extend([name.strip() for name in line.split(';') if name.strip()])
                else:
                    search_lines.append(line)
        
        # Se não há separadores, trata como busca normal
        if not search_lines:
            search_lines = [search.strip()]
        
        # Para cada nome na lista, cria condições de busca
        all_conditions = []
        
        for search_name in search_lines:
            if not search_name:
                continue
                
            # Divide cada nome em termos
            search_terms = search_name.strip().split()
            
            if len(search_terms) == 1:
                # Busca simples com um termo - prioriza primeiro e último nome
                term = search_terms[0]
                
                # Condições priorizadas: primeiro nome OU último nome
                priority_conditions = [
                    # Primeiro nome (início da string seguido de espaço ou fim)
                    Student.name.ilike(f'{term} %'),
                    Student.name.ilike(f'{term}'),
                    # Último nome (precedido de espaço ou início)
                    Student.name.ilike(f'% {term}'),
                ]
                
                # Condições secundárias: qualquer lugar no nome ou número
                secondary_conditions = [
                    Student.name.ilike(f'%{term}%'),
                    Student.student_number.ilike(f'%{term}%')
                ]
                
                # Combina prioridades com OR
                all_conditions.append(db.or_(*priority_conditions, *secondary_conditions))
            else:
                # Busca com múltiplos termos - busca inteligente por posição
                search_conditions = []
                
                # Para cada termo, verifica se pode ser primeiro ou último nome
                for i, term in enumerate(search_terms):
                    term_conditions = []
                    
                    if i == 0:  # Primeiro termo da busca
                        # Prioriza como primeiro nome no banco
                        term_conditions.extend([
                            Student.name.ilike(f'{term} %'),  # Primeiro nome
                            Student.name.ilike(f'% {term}'),  # Último nome
                            Student.name.ilike(f'%{term}%'),  # Qualquer posição
                        ])
                    elif i == len(search_terms) - 1:  # Último termo da busca
                        # Prioriza como último nome no banco
                        term_conditions.extend([
                            Student.name.ilike(f'% {term}'),  # Último nome
                            Student.name.ilike(f'{term} %'),  # Primeiro nome
                            Student.name.ilike(f'%{term}%'),  # Qualquer posição
                        ])
                    else:  # Termos do meio
                        # Busca em qualquer posição
                        term_conditions.append(Student.name.ilike(f'%{term}%'))
                    
                    # Cada termo deve ser encontrado (AND entre termos)
                    search_conditions.append(db.or_(*term_conditions))
                
                # TODOS os termos devem ser encontrados
                name_and_condition = db.and_(*search_conditions)
                
                # Também permite busca no número do estudante
                number_condition = Student.student_number.ilike(f'%{search_name}%')
                
                # Combina: (busca inteligente no nome) OU (nome completo no número)
                all_conditions.append(db.or_(name_and_condition, number_condition))
        
        # Combina todas as condições de todos os nomes com OR
        if all_conditions:
            query = query.filter(db.or_(*all_conditions))
    
    if class_filter:
        query = query.filter(Student.class_id == class_filter)
    
    if cefr_filter:
        query = query.filter(Student.cefr_geral == cefr_filter)
    
    students = query.all()
    
    # Criar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Cabeçalho atualizado com novo sistema TOEFL Junior
    writer.writerow([
        'Nome', 'Número do Estudante', 'Listening', 'Reading', 'LFM', 'Total',
        'Listening CEFR', 'Reading CEFR', 'LFM CEFR', 'CEFR Geral', 'Lexile', 'Turma'
    ])
    
    # Dados
    for student in students:
        writer.writerow([
            student.name,
            student.student_number,
            student.listening or '',
            student.reading or '',
            student.lfm or '',
            student.total or '',
            student.list_cefr or '',
            student.read_cefr or '',
            student.lfm_cefr or '',
            student.cefr_geral or '',
            student.lexile or '',
            student.class_info.name if student.class_info else ''
        ])
    
    # Preparar resposta
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'estudantes_toefl_junior_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/turmas')
@login_required
def classes():
    from forms import ClassForm
    
    form = ClassForm()
    classes = Class.query.all()
    
    # Calcular estatísticas
    total_students = Student.query.count()
    active_classes = Class.query.filter_by(is_active=True).count()
    
    # Calcular média de alunos por turma
    if len(classes) > 0:
        avg_students_per_class = total_students / len(classes)
    else:
        avg_students_per_class = 0
    
    # Calcular média geral das notas totais dos alunos
    avg_total_score = db.session.query(db.func.avg(Student.total)).filter(Student.total.isnot(None)).scalar()
    if avg_total_score is None:
        avg_total_score = 0
    
    return render_template('classes/index.html', 
                         classes=classes, 
                         form=form,
                         total_students=total_students,
                         active_classes=active_classes,
                         avg_students_per_class=avg_students_per_class,
                         avg_total_score=avg_total_score)

@app.route('/turmas/criar', methods=['POST'])
@login_required
def create_class():
    from forms import ClassForm
    
    form = ClassForm()
    if form.validate_on_submit():
        class_obj = Class(
            name=form.name.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        db.session.add(class_obj)
        db.session.commit()
        flash(f'Turma "{class_obj.name}" criada com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('classes'))

@app.route('/turmas/deletar/<int:class_id>', methods=['POST'])
@login_required
def delete_class(class_id):
    class_obj = Class.query.get_or_404(class_id)
    
    class_name = class_obj.name
    students_count = len(class_obj.students)
    
    # Primeiro, deletar explicitamente os ComputedLevels dos alunos da turma
    for student in class_obj.students:
        computed_levels = ComputedLevel.query.filter_by(student_id=student.id).all()
        for computed_level in computed_levels:
            db.session.delete(computed_level)
    
    # Depois deletar a turma (cascade irá deletar os alunos)
    db.session.delete(class_obj)
    db.session.commit()
    
    if students_count > 0:
        flash(f'Turma "{class_name}" e {students_count} aluno(s) deletados com sucesso!', 'success')
    else:
        flash(f'Turma "{class_name}" deletada com sucesso!', 'success')
    
    return redirect(url_for('classes'))

@app.route('/turmas/deletar-multiplas', methods=['POST'])
@login_required
def delete_multiple_classes():
    class_ids = request.form.getlist('class_ids')
    
    if not class_ids:
        flash('Nenhuma turma selecionada para exclusão.', 'warning')
        return redirect(url_for('classes'))
    
    deleted_count = 0
    total_students_deleted = 0
    errors = []
    
    for class_id in class_ids:
        try:
            class_obj = Class.query.get(int(class_id))
            if class_obj:
                class_name = class_obj.name
                students_count = len(class_obj.students)
                
                # Primeiro, deletar explicitamente os ComputedLevels dos alunos da turma
                for student in class_obj.students:
                    computed_levels = ComputedLevel.query.filter_by(student_id=student.id).all()
                    for computed_level in computed_levels:
                        db.session.delete(computed_level)
                
                # Depois deletar a turma (cascade irá deletar os alunos)
                db.session.delete(class_obj)
                deleted_count += 1
                total_students_deleted += students_count
            else:
                errors.append(f'Turma com ID {class_id} não encontrada')
        except Exception as e:
            errors.append(f'Erro ao deletar turma ID {class_id}: {str(e)}')
    
    # Commit all deletions
    if deleted_count > 0:
        try:
            db.session.commit()
            if deleted_count == 1:
                if total_students_deleted > 0:
                    flash(f'1 turma e {total_students_deleted} aluno(s) deletados com sucesso!', 'success')
                else:
                    flash(f'1 turma deletada com sucesso!', 'success')
            else:
                if total_students_deleted > 0:
                    flash(f'{deleted_count} turmas e {total_students_deleted} aluno(s) deletados com sucesso!', 'success')
                else:
                    flash(f'{deleted_count} turmas deletadas com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao deletar turmas: {str(e)}', 'error')
    
    # Show errors if any
    for error in errors:
        flash(error, 'warning')
    
    return redirect(url_for('classes'))

# ==================== ROTAS DE PROFESSORES ====================

@app.route('/professores')
@login_required
def teachers():
    teachers = Teacher.query.all()
    form = TeacherForm()
    return render_template('teachers/index.html', teachers=teachers, form=form)

@app.route('/professores/criar', methods=['POST'])
@login_required
def create_teacher():
    form = TeacherForm()
    if form.validate_on_submit():
        try:
            teacher = Teacher(
                name=form.name.data
            )
            db.session.add(teacher)
            db.session.commit()
            flash(f'Professor "{teacher.name}" criado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar professor: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{form[field].label.text}: {error}', 'error')
    
    return redirect(url_for('teachers'))

@app.route('/professores/<int:teacher_id>/editar', methods=['POST'])
@login_required
def edit_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    form = TeacherForm(teacher=teacher)
    
    if form.validate_on_submit():
        try:
            teacher.name = form.name.data
            teacher.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'Professor "{teacher.name}" atualizado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar professor: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{form[field].label.text}: {error}', 'error')
    
    return redirect(url_for('teachers'))

@app.route('/professores/<int:teacher_id>/deletar', methods=['POST'])
@login_required
def delete_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    
    try:
        # Verificar se há alunos associados
        students_count = Student.query.filter_by(teacher_id=teacher_id).count()
        if students_count > 0:
            flash(f'Não é possível deletar o professor "{teacher.name}" pois há {students_count} aluno(s) associado(s).', 'warning')
        else:
            teacher_name = teacher.name
            db.session.delete(teacher)
            db.session.commit()
            flash(f'Professor "{teacher_name}" deletado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar professor: {str(e)}', 'error')
    
    return redirect(url_for('teachers'))

@app.route('/professores/deletar-multiplos', methods=['POST'])
@login_required
def delete_multiple_teachers():
    print(f"Form data: {request.form}")
    print(f"CSRF token in form: {request.form.get('csrf_token')}")
    teacher_ids = request.form.getlist('teacher_ids')
    
    if not teacher_ids:
        flash('Nenhum professor selecionado para deletar.', 'warning')
        return redirect(url_for('teachers'))
    
    deleted_count = 0
    errors = []
    
    for teacher_id in teacher_ids:
        try:
            teacher = Teacher.query.get(teacher_id)
            if teacher:
                # Verificar se há alunos associados
                students_count = Student.query.filter_by(teacher_id=teacher_id).count()
                if students_count > 0:
                    errors.append(f'Professor "{teacher.name}" não pode ser deletado (tem {students_count} aluno(s) associado(s))')
                else:
                    db.session.delete(teacher)
                    deleted_count += 1
        except Exception as e:
            db.session.rollback()
            errors.append(f'Erro ao deletar professor ID {teacher_id}: {str(e)}')
    
    if deleted_count > 0:
        try:
            db.session.commit()
            flash(f'{deleted_count} professor(es) deletado(s) com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao deletar professores: {str(e)}', 'error')
    
    # Show errors if any
    for error in errors:
        flash(error, 'warning')
    
    return redirect(url_for('teachers'))

@app.route('/alunos/<int:id>/editar-professor', methods=['GET', 'POST'])
@login_required
def edit_student_teacher(id):
    student = Student.query.get_or_404(id)
    form = EditStudentTeacherForm()
    
    if form.validate_on_submit():
        try:
            old_teacher = student.teacher.name if student.teacher else 'Nenhum'
            student.teacher_id = form.teacher_id.data if form.teacher_id.data != 0 else None
            student.updated_at = datetime.utcnow()
            db.session.commit()
            
            new_teacher = student.teacher.name if student.teacher else 'Nenhum'
            flash(f'Professor do aluno "{student.name}" alterado de "{old_teacher}" para "{new_teacher}"!', 'success')
            return redirect(url_for('student_detail', id=student.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao alterar professor: {str(e)}', 'error')
    
    # Pre-populate form
    if student.teacher_id:
        form.teacher_id.data = student.teacher_id
    else:
        form.teacher_id.data = 0
    
    return render_template('students/edit_teacher.html', student=student, form=form)

# ==================== FIM ROTAS DE PROFESSORES ====================

@app.route('/admin')
@login_required
def admin():
    from forms import UserForm
    
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem acessar esta página.', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    form = UserForm()
    
    # Estatísticas para o dashboard admin
    active_users = User.query.filter_by(is_active=True).count()
    # total_uploads = Upload.query.count()  # Comentado pois Upload model não existe
    total_uploads = 0  # Valor padrão até implementar Upload model
    total_students = Student.query.count()
    
    return render_template('admin/index.html', 
                         users=users, 
                         form=form,
                         active_users=active_users,
                         total_uploads=total_uploads,
                         total_students=total_students)

@app.route('/admin/auto-fix', methods=['POST'])
@login_required
def admin_auto_fix():
    """Executa correções automáticas via interface administrativa"""
    if not current_user.is_admin:
        return jsonify({
            'success': False,
            'message': 'Acesso negado. Apenas administradores podem executar esta ação.'
        }), 403
    
    try:
        from render_auto_fix import run_auto_fix
        result = run_auto_fix()
        
        if result['overall_success']:
            flash(f'Correções executadas com sucesso! Total: {result["total_corrections"]} correções em {result["duration_seconds"]:.2f}s', 'success')
        else:
            flash(f'Correções executadas com alguns erros. Verifique os detalhes.', 'warning')
        
        return jsonify(result)
        
    except Exception as e:
        flash(f'Erro ao executar correções: {str(e)}', 'danger')
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/clear-cache', methods=['POST'])
@login_required
def clear_cache():
    """Endpoint para limpar cache das páginas - disponível para professores e administradores"""
    if not (current_user.is_admin or current_user.is_teacher):
        return jsonify({
            'success': False,
            'message': 'Acesso negado. Apenas professores e administradores podem limpar o cache.'
        }), 403
    
    try:
        # Limpar cache do Flask (se houver)
        if hasattr(app, 'cache'):
            app.cache.clear()
        
        # Limpar cache de funções com @lru_cache
        from functools import lru_cache
        # Encontrar e limpar todas as funções com cache
        for name in dir():
            obj = globals().get(name)
            if hasattr(obj, 'cache_clear'):
                obj.cache_clear()
        
        # Forçar recarregamento de dados estáticos se necessário
        # Aqui você pode adicionar lógica específica para limpar outros tipos de cache
        
        return jsonify({
            'success': True,
            'message': 'Cache limpo com sucesso!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao limpar cache: {str(e)}'
        }), 500

@app.route('/admin/cefr-fix', methods=['POST'])
@login_required
def admin_cefr_fix():
    """Executa correção de níveis CEFR via interface administrativa"""
    if not current_user.is_admin:
        return jsonify({
            'success': False,
            'message': 'Acesso negado. Apenas administradores podem executar esta ação.'
        }), 403
    
    try:
        from render_cefr_fix import run_cefr_fix
        result = run_cefr_fix()
        
        if result['success']:
            details = result['details']
            flash(f'Níveis CEFR corrigidos com sucesso! Atualizados: {details["updated_count"]}, Criados: {details["created_count"]} em {details["execution_time"]}s', 'success')
        else:
            flash(f'Erro na correção de níveis CEFR: {result["message"]}', 'danger')
        
        return jsonify(result)
        
    except Exception as e:
        flash(f'Erro ao executar correção de níveis CEFR: {str(e)}', 'danger')
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

@app.route('/admin/fix-asterisk-cefr', methods=['POST'])
@login_required
def admin_fix_asterisk_cefr():
    """Corrige todos os valores de asterisco (*) nos campos CEFR"""
    if not current_user.is_admin:
        return jsonify({
            'success': False,
            'message': 'Acesso negado. Apenas administradores podem executar esta ação.'
        }), 403
    
    try:
        from toefl_calculator import cefr_listening
        
        def cefr_reading(score):
            """Classifica uma pontuação de Reading (200-300) em nível CEFR"""
            if score is None or score < 200:
                return 'A1'
            
            score = float(score)
            
            if 200 <= score <= 245:
                return 'A2'
            elif 246 <= score <= 265:
                return 'A2+'
            elif 266 <= score <= 285:
                return 'B1'
            elif 286 <= score <= 300:
                return 'B2'
            elif score >= 301:
                return 'B2+'
            else:
                return 'A1'
        
        def cefr_lfm(score):
            """Classifica uma pontuação de LFM (200-300) em nível CEFR"""
            if score is None or score < 200:
                return 'A1'
            
            score = float(score)
            
            if 200 <= score <= 245:
                return 'A2'
            elif 246 <= score <= 265:
                return 'A2+'
            elif 266 <= score <= 285:
                return 'B1'
            elif 286 <= score <= 300:
                return 'B2'
            elif score >= 301:
                return 'B2+'
            else:
                return 'A1'
        
        corrections_made = 0
        total_checked = 0
        
        # Corrigir Read_CEFR com asterisco
        asterisk_read = Student.query.filter(Student.read_cefr == '*').all()
        for student in asterisk_read:
            total_checked += 1
            if student.reading is not None:
                correct_cefr = cefr_reading(student.reading)
                student.read_cefr = correct_cefr
                corrections_made += 1
        
        # Corrigir LFM_CEFR com asterisco
        asterisk_lfm = Student.query.filter(Student.lfm_cefr == '*').all()
        for student in asterisk_lfm:
            total_checked += 1
            if student.lfm is not None:
                correct_cefr = cefr_lfm(student.lfm)
                student.lfm_cefr = correct_cefr
                corrections_made += 1
        
        # Corrigir List_CEFR com asterisco
        asterisk_listening = Student.query.filter(Student.list_cefr == '*').all()
        for student in asterisk_listening:
            total_checked += 1
            if student.listening is not None:
                correct_cefr = cefr_listening(student.listening)
                student.list_cefr = correct_cefr
                corrections_made += 1
        
        # Salvar alterações
        db.session.commit()
        
        # Verificar asteriscos restantes
        remaining_asterisks = (
            Student.query.filter(Student.read_cefr == '*').count() +
            Student.query.filter(Student.lfm_cefr == '*').count() +
            Student.query.filter(Student.list_cefr == '*').count()
        )
        
        message = f'Correção de asteriscos concluída! {corrections_made} correções realizadas de {total_checked} registros verificados.'
        if remaining_asterisks > 0:
            message += f' Restam {remaining_asterisks} asteriscos (provavelmente estudantes sem pontuações).'
        
        flash(message, 'success')
        
        return jsonify({
            'success': True,
            'message': message,
            'corrections_made': corrections_made,
            'total_checked': total_checked,
            'remaining_asterisks': remaining_asterisks
        })
        
    except Exception as e:
        db.session.rollback()
        error_msg = f'Erro ao corrigir asteriscos: {str(e)}'
        flash(error_msg, 'danger')
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

@app.route('/import', methods=['POST'])
@login_required
def import_students():
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem importar dados.', 'error')
        return redirect(url_for('dashboard'))
    
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('admin'))
    
    if not file.filename.lower().endswith(('.xlsx', '.csv')):
        flash('Formato de arquivo não suportado. Use .xlsx ou .csv', 'error')
        return redirect(url_for('admin'))
    
    try:
        from models import ComputedLevel, calculate_student_levels
        import pandas as pd
        
        # Ler arquivo
        if file.filename.lower().endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)
        
        # Mapear colunas esperadas
        column_mapping = {
            'NAME': 'name',
            'StudentNumber': 'student_number',
            'Listening': 'listening',
            'ListCEFR': 'list_cefr',
            'LFM': 'lfm',
            'LFMCEFR': 'lfm_cefr',
            'Reading': 'reading',
            'ReadCEFR': 'read_cefr',
            'Lexile': 'lexile',
            'TOTAL': 'total',
            'CEFR GERAL': 'cefr_geral'
        }
        
        imported_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # Verificar se já existe
                existing = Student.query.filter_by(student_number=str(row.get('StudentNumber', ''))).first()
                if existing:
                    continue
                
                # Criar novo estudante
                student_data = {}
                for excel_col, db_col in column_mapping.items():
                    value = row.get(excel_col)
                    
                    # Tratar valores NULL/NaN
                    if pd.isna(value) or value == '':
                        value = None
                    elif db_col in ['listening', 'lfm', 'reading', 'total']:
                        # Validar tipos numéricos
                        try:
                            value = int(float(value)) if value is not None else None
                        except (ValueError, TypeError):
                            value = None
                    
                    student_data[db_col] = value
                
                # Criar estudante
                student = Student(**student_data)
                db.session.add(student)
                db.session.flush()  # Para obter o ID
                
                # Calcular níveis
                levels, applied_rules = calculate_student_levels(student)
                
                # Criar ComputedLevel
                computed_level = ComputedLevel(
                    student_id=student.id,
                    school_level=levels.get('school_level'),
                    listening_level=levels.get('listening_level'),
                    lfm_level=levels.get('lfm_level'),
                    reading_level=levels.get('reading_level'),
                    overall_level=levels.get('overall_level'),
                    applied_rules='; '.join(applied_rules)
                )
                db.session.add(computed_level)
                
                imported_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Erro ao importar linha {index}: {str(e)}")
                continue
        
        db.session.commit()
        
        flash(f'Importação concluída! {imported_count} estudantes importados, {error_count} erros.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro na importação: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/reset_db', methods=['POST'])
@login_required
def reset_database():
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem resetar o banco.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from models import ComputedLevel, seed_teachers
        
        # Dropar todas as tabelas
        db.drop_all()
        
        # Recriar todas as tabelas
        db.create_all()
        
        # Seed dos professores
        seed_teachers()
        
        flash('Banco de dados resetado com sucesso! Professores foram criados.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao resetar banco: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/init-db', methods=['POST'])
@login_required
def admin_init_db():
    """Rota protegida para inicializar o banco de dados manualmente"""
    if not current_user.is_admin:
        return jsonify({"error": "unauthorized"}), 401
    
    # Verificar token de segurança adicional (opcional)
    token = request.headers.get("X-Admin-Token")
    admin_token = os.getenv("ADMIN_INIT_TOKEN")
    if admin_token and token != admin_token:
        return jsonify({"error": "invalid token"}), 401
    
    try:
        from sqlalchemy import inspect
        
        with app.app_context():
            insp = inspect(db.engine)
            
            if not insp.has_table("classes"):
                db.create_all()
                
                # Criar usuário admin padrão se não existir
                admin_user = User.query.filter_by(username='admin').first()
                if not admin_user:
                    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
                    admin_user = User(
                        username='admin',
                        password_hash=generate_password_hash(admin_password),
                        is_active=True
                    )
                    db.session.add(admin_user)
                    db.session.commit()
                
                return jsonify({"status": "created", "message": "Tabelas criadas com sucesso"})
            else:
                return jsonify({"status": "exists", "message": "Tabelas já existem"})
                
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/create-user', methods=['POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    form = UserForm()
    if form.validate_on_submit():
        # Verificar se usuário já existe
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Nome de usuário já existe.', 'error')
            return redirect(url_for('admin'))
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=form.is_admin.data,
            is_active=form.is_active.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Usuário {user.username} criado com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    user = User.query.get_or_404(user_id)
    form = UserForm()
    
    if form.validate_on_submit():
        # Verificar se o novo username já existe (exceto para o próprio usuário)
        existing_user = User.query.filter(
            User.username == form.username.data,
            User.id != user_id
        ).first()
        
        if existing_user:
            flash('Nome de usuário já existe.', 'error')
            return redirect(url_for('admin'))
        
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        
        db.session.commit()
        flash(f'Usuário {user.username} atualizado com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Não permitir desativar o próprio usuário
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Não é possível alterar seu próprio status'}), 400
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'ativado' if user.is_active else 'desativado'
    return jsonify({'success': True, 'message': f'Usuário {status} com sucesso'})

@app.route('/admin/users/<int:user_id>/delete', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Não permitir excluir o próprio usuário
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Não é possível excluir seu próprio usuário'}), 400
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Usuário {username} excluído com sucesso'})

# ==================== ROTAS DE FERRAMENTAS ADMINISTRATIVAS ====================

@app.route('/admin/database/reset', methods=['POST'])
@login_required
def admin_database_reset():
    """Reset completo do banco de dados - ATENÇÃO: Remove todos os dados"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    try:
        # Log da ação
        print(f"🚨 RESET COMPLETO DO BANCO DE DADOS iniciado por: {current_user.username}")
        
        # Salvar informações do usuário atual antes do reset
        current_user_id = current_user.id
        current_username = current_user.username
        current_password_hash = current_user.password_hash
        current_email = current_user.email
        
        # Usar SQLAlchemy para remover todas as tabelas de forma segura
        # Isso evita problemas com PRAGMA foreign_keys
        db.drop_all()
        print("✅ Todas as tabelas removidas com sucesso")
        
        # Recriar todas as tabelas
        db.create_all()
        print("✅ Estrutura do banco recriada")
        
        # Recriar o usuário administrador atual
        from werkzeug.security import generate_password_hash
        admin_user = User(
            username=current_username,
            email=current_email,
            password_hash=current_password_hash,
            is_admin=True,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"✅ Usuário admin '{current_username}' recriado")
        print("🎉 Reset completo do banco de dados concluído com sucesso!")
        
        return jsonify({
            'success': True, 
            'message': 'Reset completo do banco de dados executado com sucesso! Todas as tabelas foram removidas e recriadas.'
        })
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro ao executar reset do banco de dados: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/admin/database/backup', methods=['POST'])
@login_required
def admin_database_backup():
    """Criar backup dos dados do banco de dados"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    try:
        import json
        import os
        from datetime import datetime
        
        # Criar diretório de backups se não existir
        backup_dir = os.path.join(os.getcwd(), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'toefl_backup_{timestamp}.json'
        filepath = os.path.join(backup_dir, filename)
        
        # Coletar dados de todas as tabelas
        backup_data = {
            'created_at': datetime.now().isoformat(),
            'created_by': current_user.username,
            'teachers': [],
            'classes': [],
            'students': [],
            'computed_levels': [],
            'users': []
        }
        
        # Backup de professores
        teachers = Teacher.query.all()
        for teacher in teachers:
            backup_data['teachers'].append({
                'id': teacher.id,
                'name': teacher.name,
                'created_at': teacher.created_at.isoformat() if teacher.created_at else None
            })
        
        # Backup de turmas
        classes = Class.query.all()
        for cls in classes:
            backup_data['classes'].append({
                'id': cls.id,
                'name': cls.name,
                'teacher_id': cls.teacher_id,
                'created_at': cls.created_at.isoformat() if cls.created_at else None
            })
        
        # Backup de estudantes
        students = Student.query.all()
        for student in students:
            backup_data['students'].append({
                'id': student.id,
                'name': student.name,
                'student_number': student.student_number,
                'listening': student.listening,
                'list_cefr': student.list_cefr,
                'lfm': student.lfm,
                'lfm_cefr': student.lfm_cefr,
                'reading': student.reading,
                'read_cefr': student.read_cefr,
                'lexile': student.lexile,
                'total': student.total,
                'class_id': student.class_id,
                'teacher_id': student.teacher_id,
                'created_at': student.created_at.isoformat() if student.created_at else None,
                'updated_at': student.updated_at.isoformat() if student.updated_at else None
            })
        
        # Backup de níveis computados
        computed_levels = ComputedLevel.query.all()
        for level in computed_levels:
            backup_data['computed_levels'].append({
                'id': level.id,
                'student_id': level.student_id,
                'general_cefr': level.general_cefr,
                'created_at': level.created_at.isoformat() if level.created_at else None,
                'updated_at': level.updated_at.isoformat() if level.updated_at else None
            })
        
        # Backup de usuários (sem senhas por segurança)
        users = User.query.all()
        for user in users:
            backup_data['users'].append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            })
        
        # Salvar arquivo JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Backup criado: {filename}")
        print(f"📊 Dados salvos: {len(backup_data['teachers'])} professores, {len(backup_data['classes'])} turmas, {len(backup_data['students'])} estudantes")
        
        return jsonify({
            'success': True,
            'message': f'Backup criado com sucesso!',
            'filename': filename,
            'stats': {
                'teachers': len(backup_data['teachers']),
                'classes': len(backup_data['classes']),
                'students': len(backup_data['students']),
                'computed_levels': len(backup_data['computed_levels']),
                'users': len(backup_data['users'])
            }
        })
        
    except Exception as e:
        error_msg = f"Erro ao criar backup: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

# ==================== FIM ROTAS DE FERRAMENTAS ADMINISTRATIVAS ====================

# Rotas de Backup
@app.route('/backup/download')
@login_required
def download_backup():
    """Gera e faz download de um backup JSON dos dados"""
    try:
        from database_backup import export_data_json
        import tempfile
        import os
        from datetime import datetime
        
        # Criar arquivo temporário
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'toefl_backup_{timestamp}.json'
        
        # Usar diretório temporário do sistema
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        
        # Exportar dados
        if export_data_json(temp_path):
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/json'
            )
        else:
            flash('Erro ao gerar backup', 'error')
            return redirect(url_for('dashboard'))
            
    except Exception as e:
        flash(f'Erro ao gerar backup: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/backup/upload', methods=['GET', 'POST'])
@login_required
def upload_backup():
    """Faz upload e restaura um backup JSON"""
    if request.method == 'GET':
        # Redirecionar requisições GET para o dashboard
        return redirect(url_for('dashboard'))
        
    try:
        if 'backup_file' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(url_for('dashboard'))
        
        file = request.files['backup_file']
        if file.filename == '' or file.filename is None:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(url_for('dashboard'))
        
        # Verificar se é um arquivo válido e tem extensão .json
        if file and hasattr(file, 'filename') and file.filename and file.filename.lower().endswith('.json'):
            from database_backup import import_data_json
            import tempfile
            import os
            from werkzeug.utils import secure_filename
            
            # Salvar arquivo temporariamente
            temp_dir = tempfile.gettempdir()
            secure_name = secure_filename(file.filename)
            temp_path = os.path.join(temp_dir, secure_name)
            
            print(f"DEBUG: Salvando arquivo em: {temp_path}")
            file.save(temp_path)
            
            # Verificar se o arquivo foi salvo
            if not os.path.exists(temp_path):
                flash('Erro ao salvar arquivo temporário', 'error')
                return redirect(url_for('dashboard'))
            
            print(f"DEBUG: Arquivo salvo com sucesso, tamanho: {os.path.getsize(temp_path)} bytes")
            
            # Importar dados
            if import_data_json(temp_path):
                flash('Backup restaurado com sucesso!', 'success')
                
                # Limpar arquivo temporário
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
                return redirect(url_for('dashboard'))
            else:
                flash('Erro ao restaurar backup', 'error')
                
                # Limpar arquivo temporário
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
                return redirect(url_for('dashboard'))
        else:
            flash('Formato de arquivo inválido. Use apenas arquivos .json', 'error')
            return redirect(url_for('dashboard'))
            
    except Exception as e:
        print(f"DEBUG: Erro na rota upload_backup: {str(e)}")
        flash(f'Erro ao restaurar backup: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Em desenvolvimento local, crie as tabelas se necessário
    with app.app_context():
        from sqlalchemy import inspect
        from models import db  # Importar db aqui
        insp = inspect(db.engine)
        if not insp.has_table("classes"):
            db.create_all()
    port = int(os.environ.get('PORT', 5000))
    # Desabilitado debug para melhor performance
    app.run(host='0.0.0.0', port=port, debug=False)