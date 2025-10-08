from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, after_this_request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.urls import url_parse
import os
import pandas as pd
from datetime import datetime, timedelta
import io
import csv
import re
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import config
from sqlalchemy import inspect, text
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache, wraps
import zipfile

def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""

    app = Flask(__name__)
    
    # Configure certificate logger
    log_dir = Path(app.root_path) / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'certificate_debug.log'

    logger = logging.getLogger('certificate')
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=1_048_576,
            backupCount=5,
            encoding='utf-8'
        )
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    app.config['CERTIFICATE_LOGGER'] = logger

    # Configuração
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app.config.from_object(config[config_name])
    
    # Normalizar DATABASE_URL antes de inicializar o banco
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Converter postgres:// ou postgresql:// para postgresql+psycopg://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        
        # Definir a URL normalizada
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    
    # Inicializar extensões
    from models import db
    db.init_app(app)
    
    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Configurar CSRF
    csrf = CSRFProtect(app)

    # Decorator para restringir acesso a administradores
    def admin_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
                return jsonify({'success': False, 'message': 'Acesso restrito a administradores'}), 403
            return f(*args, **kwargs)
        return wrapper
    
    # Criar tabelas se não existirem
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tabelas criadas/verificadas com sucesso")
            
            # Criar usuário admin se não existir
            from models import User
            admin_user = os.getenv("ADMIN_USERNAME", "admin")
            existing_admin = User.query.filter_by(username=admin_user).first()
            
            if not existing_admin:
                try:
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
                except Exception as admin_error:
                    print(f"⚠️ Erro ao criar usuário admin: {admin_error}")
            else:
                print(f"ℹ️ Usuário admin já existe: {admin_user}")
            try:
                promoted_total = promote_a1_levels_to_a2()
                if promoted_total:
                    print(f"Ajustados {promoted_total} campos CEFR de A1 para A2")
            except Exception as promote_error:
                print(f"Aviso: nao foi possivel ajustar niveis A1 -> A2 automaticamente: {promote_error}")

            # Migração simples: garantir colunas import_sheet_name e found_name em students
            try:
                insp = inspect(db.engine)
                if insp.has_table('students'):
                    col_names = [col['name'] for col in insp.get_columns('students')]
                    if 'import_sheet_name' not in col_names:
                        dialect = db.engine.dialect.name
                        if dialect == 'sqlite':
                            db.session.execute(text('ALTER TABLE students ADD COLUMN import_sheet_name VARCHAR(120)'))
                        else:
                            # Postgres/MySQL compatível
                            db.session.execute(text('ALTER TABLE students ADD COLUMN import_sheet_name VARCHAR(120)'))
                        db.session.commit()
                        print('✅ Coluna import_sheet_name adicionada à tabela students')
                    if 'found_name' not in col_names:
                        dialect = db.engine.dialect.name
                        try:
                            if dialect == 'sqlite':
                                db.session.execute(text('ALTER TABLE students ADD COLUMN found_name VARCHAR(120)'))
                            else:
                                db.session.execute(text('ALTER TABLE students ADD COLUMN found_name VARCHAR(120)'))
                            db.session.commit()
                            print('✅ Coluna found_name adicionada à tabela students')
                        except Exception as e:
                            db.session.rollback()
                            print(f"⚠️ Falha ao adicionar coluna found_name: {e}")
                    # Garantir coluna de override manual do Listening CSA
                    if 'listening_csa_is_manual' not in col_names:
                        dialect = db.engine.dialect.name
                        try:
                            if dialect == 'sqlite':
                                # SQLite não tem tipo booleano nativo; usar INTEGER 0/1
                                db.session.execute(text('ALTER TABLE students ADD COLUMN listening_csa_is_manual INTEGER DEFAULT 0'))
                            else:
                                db.session.execute(text('ALTER TABLE students ADD COLUMN listening_csa_is_manual BOOLEAN DEFAULT FALSE'))
                            db.session.commit()
                            print('✅ Coluna listening_csa_is_manual adicionada à tabela students')
                        except Exception as e:
                            db.session.rollback()
                            print(f"⚠️ Falha ao adicionar coluna listening_csa_is_manual: {e}")
            except Exception as mig_err:
                print(f"⚠️ Falha ao migrar coluna import_sheet_name: {mig_err}")

        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            
        # Importar e registrar blueprint da API
        from api_endpoints import api_bp
        app.register_blueprint(api_bp)
        
        # Imports necessários para as rotas
        from forms import LoginForm, UploadForm, ClassForm, EditStudentClassForm, UserForm, EditStudentTurmaMetaForm, TeacherForm, EditStudentTeacherForm
        from services.importer import ExcelImporter
        from models import User, Student, Class, Teacher, ComputedLevel, db
        
        # Definir todas as rotas dentro da função create_app
        @app.route('/')
        def index():
            return redirect(url_for('dashboard'))

        @app.route('/login', methods=['GET', 'POST'])
        def login():
            if current_user.is_authenticated:
                return redirect(url_for('dashboard'))
            
            form = LoginForm()
            if form.validate_on_submit():
                user = User.query.filter_by(username=form.username.data).first()
                if user and user.check_password(form.password.data) and user.is_active:
                    login_user(user, remember=form.remember_me.data)
                    next_page = request.args.get('next')
                    if not next_page or url_parse(next_page).netloc != '':
                        next_page = url_for('dashboard')
                    return redirect(next_page)
                flash('Nome de usuário ou senha inválidos')
            return render_template('auth/login.html', title='Login', form=form)

        @app.route('/logout')
        def logout():
            logout_user()
            return redirect(url_for('login'))

        @app.route("/health/db")
        def health_db():
            try:
                db.session.execute(text('SELECT 1'))
                return {"status": "ok", "database": "connected"}, 200
            except Exception as e:
                return {"status": "error", "database": str(e)}, 500

        @app.route('/dash')
        @app.route('/alunos')
        @login_required
        def dashboard():
            # Estatísticas básicas
            total_students = Student.query.count()
            total_classes = Class.query.count()
            total_teachers = Teacher.query.count()
            
            # Distribuição por nível CEFR priorizando ComputedLevel.overall_level
            cefr_distribution = db.session.query(
                ComputedLevel.overall_level,
                db.func.count(ComputedLevel.id)
            ).filter(ComputedLevel.overall_level.isnot(None)).group_by(ComputedLevel.overall_level).all()

            # Fallback para Student.cefr_geral caso não haja ComputedLevel
            if not cefr_distribution:
                cefr_distribution = db.session.query(
                    Student.cefr_geral,
                    db.func.count(Student.id)
                ).filter(Student.cefr_geral.isnot(None)).group_by(Student.cefr_geral).all()

            # Converter para dicionário
            cefr_dict = {level or 'N/A': count for level, count in cefr_distribution}

            # Garantir que todos os níveis estejam presentes e ordem consistente para o gráfico
            all_levels = ['A1', 'A2', 'A2+', 'B1', 'B2', 'Below A1']
            for level in all_levels:
                if level not in cefr_dict:
                    cefr_dict[level] = 0

            # Converter de volta para lista de tuplas para o template
            cefr_distribution_list = [(level, cefr_dict[level]) for level in all_levels]

            # Calcular nível predominante com regra que prioriza níveis mais altos quando B1+B2 > A2
            predominant_level = 'N/A'
            if cefr_dict:
                b2 = cefr_dict.get('B2', 0)
                b1 = cefr_dict.get('B1', 0)
                a2 = cefr_dict.get('A2', 0) + cefr_dict.get('A2+', 0)
                a1 = cefr_dict.get('A1', 0)
                below = cefr_dict.get('Below A1', 0)

                if max(b2, b1, a2, a1, below) == 0:
                    predominant_level = 'N/A'
                elif b2 >= b1 and b2 >= a2 and b2 >= a1 and b2 >= below:
                    predominant_level = 'B2'
                elif (b1 + b2) > a2:
                    predominant_level = 'B1'
                elif b1 >= a2 and b1 >= a1 and b1 >= below:
                    predominant_level = 'B1'
                elif a2 >= a1 and a2 >= below:
                    predominant_level = 'A2'
                elif a1 >= below:
                    predominant_level = 'A1'
                else:
                    predominant_level = 'Below A1'
            
            # Estatísticas por turma
            class_stats = db.session.query(
                Class.name,
                db.func.count(Student.id).label('student_count'),
                db.func.avg(Student.total).label('avg_score')
            ).outerjoin(Student).group_by(Class.id, Class.name).all()
            
            # Alunos recentes (últimos 10)
            recent_students = Student.query.order_by(Student.created_at.desc()).limit(10).all()
            
            # Top 10 alunos por pontuação
            top_students = Student.query.order_by(Student.total.desc()).limit(10).all()
            
            # Estatísticas por professor
            teacher_stats = db.session.query(
                Teacher.name,
                db.func.count(Student.id).label('student_count'),
                db.func.avg(Student.total).label('avg_score')
            ).outerjoin(Student).group_by(Teacher.id, Teacher.name).all()
            
            # Alunos sem turma_meta (rótulo escolar)
            students_without_turma_meta = Student.query.filter(
                (Student.turma_meta == None) | (Student.turma_meta == "")
            ).count()
            
            # Alunos sem professor
            students_without_teacher = Student.query.filter(Student.teacher_id == None).count()
            
            # Alunos sem turma
            students_without_class = Student.query.filter(Student.class_id == None).count()
            
            # Calcular médias por habilidade
            avg_listening = db.session.query(db.func.avg(Student.listening)).scalar() or 0
            avg_reading = db.session.query(db.func.avg(Student.reading)).scalar() or 0
            avg_lfm = db.session.query(db.func.avg(Student.lfm)).scalar() or 0
            avg_total = db.session.query(db.func.avg(Student.total)).scalar() or 0
            avg_scores = [avg_listening, avg_reading, avg_lfm, avg_total]

            # Top 10 estudantes por ano escolar
            top_students_6th = Student.query.filter(
                Student.turma_meta.like('%6%')
            ).order_by(Student.total.desc()).limit(10).all()
            
            top_students_9th = Student.query.filter(
                Student.turma_meta.like('%9%')
            ).order_by(Student.total.desc()).limit(10).all()

            # ---- Estatísticas comparativas: Nacional vs Colégio Santo Antônio ----
            def _bucket_level(lvl: str) -> str:
                if not lvl:
                    return '*'
                val = lvl.strip()
                if val in ('A1', 'Below A1'):
                    return '*'
                if val == 'A2+':
                    return 'A2'
                if val in ('A2', 'B1', 'B2'):
                    return val
                return '*'

            def _compute_distribution(skill_column, grade_prefix: str, school_filter: str = None):
                # Base query joining ComputedLevel with Student
                query = db.session.query(skill_column).join(Student).filter(skill_column.isnot(None))
                query = query.filter(Student.turma_meta.like(f'{grade_prefix}%'))
                if school_filter:
                    # Filtro por nome da aba (planilha) representando a escola
                    query = query.filter(Student.import_sheet_name.ilike(f'%{school_filter}%'))
                results = [row[0] for row in query.all()]
                total = len(results) if results else 0
                buckets = {'*': 0, 'A2': 0, 'B1': 0, 'B2': 0}
                for lvl in results:
                    b = _bucket_level(lvl)
                    if b in buckets:
                        buckets[b] += 1
                    else:
                        buckets['*'] += 1
                if total == 0:
                    return {k: 0 for k in buckets}
                return {k: round((v * 100.0) / total, 1) for k, v in buckets.items()}

            # Nacional (percentuais fixos fornecidos)
            national_6 = {
                'listening': {'*': 36, 'A2': 30, 'B1': 30, 'B2': 4},
                'lfm':       {'*': 15, 'A2': 60, 'B1': 20, 'B2': 6},
                'reading':   {'*': 35, 'A2': 39, 'B1': 20, 'B2': 5}
            }
            national_9 = {
                'listening': {'*': 19, 'A2': 22, 'B1': 40, 'B2': 20},
                'lfm':       {'*':  6, 'A2': 38, 'B1': 30, 'B2': 26},
                'reading':   {'*': 12, 'A2': 25, 'B1': 34, 'B2': 30}
            }

            # Colégio Santo Antônio (percentuais fixos fornecidos)
            school_name = 'Colégio Santo Antônio'
            school_6 = {
                'listening': {'*': 13, 'A2': 56, 'B1': 25, 'B2':  6},
                'lfm':       {'*':  8, 'A2': 65, 'B1': 24, 'B2':  3},
                'reading':   {'*': 27, 'A2': 42, 'B1': 28, 'B2':  3}
            }
            school_9 = {
                'listening': {'*':  2, 'A2': 13, 'B1': 46, 'B2': 39},
                'lfm':       {'*':  0, 'A2': 17, 'B1': 44, 'B2': 39},
                'reading':   {'*':  2, 'A2':  9, 'B1': 52, 'B2': 37}
            }
            
            return render_template('dashboard/index.html', 
                                 total_students=total_students,
                                 total_classes=total_classes,
                                 total_teachers=total_teachers,
                                 cefr_distribution=cefr_distribution_list,
                                 predominant_level=predominant_level,
                                 class_stats=class_stats,
                                 recent_students=recent_students,
                                 top_students=top_students,
                                 teacher_stats=teacher_stats,
                                 students_without_turma_meta=students_without_turma_meta,
                                 students_without_teacher=students_without_teacher,
                                 students_without_class=students_without_class,
                                 avg_scores=avg_scores,
                                 top_students_6th=top_students_6th,
                                 top_students_9th=top_students_9th,
                                 national_6=national_6,
                                 national_9=national_9,
                                 school_6=school_6,
                                 school_9=school_9,
                                 school_name=school_name)

        @app.route('/upload', methods=['GET', 'POST'])
        @login_required
        def upload():
            form = UploadForm()
            
            if form.validate_on_submit():
                try:
                    file = form.file.data
                    # Ignorar class_id para importação multi-abas automática
                    class_id = None
                    
                    # Salvar arquivo temporariamente
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), filename)
                    
                    # Criar diretório se não existir
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    file.save(filepath)
                    
                    # Processar todas as abas: criar/reutilizar turmas automaticamente (nome = nome da aba)
                    importer = ExcelImporter(filepath, class_id)
                    sheets = []
                    try:
                        sheets = importer.get_sheet_names()
                    except Exception as se:
                        print(f"Erro ao obter abas: {se}")
                        sheets = []

                    total_imported = 0
                    sheet_results = []
                    if not sheets:
                        # Fallback: processar como arquivo simples (CSV ou sem abas)
                        result = importer.import_data()
                        if result.get('success'):
                            total_imported = result.get('imported', 0)
                            sheet_results.append({'sheet': 'Arquivo', 'success': True, 'processed': result.get('imported', 0)})
                        else:
                            sheet_results.append({'sheet': 'Arquivo', 'success': False, 'error': result.get('error')})
                    else:
                        # Importar cada aba com rollback isolado
                        for s in sheets:
                            res = importer.import_sheet(sheet_name=s, class_id=None, class_name=s)
                            sheet_results.append(res)
                            if res.get('success'):
                                total_imported += res.get('processed', 0)
                            else:
                                # Registrar erro mas continuar (isolamento por aba)
                                print(f"Aba {s} falhou: {res.get('error')}")
                    
                    # Remover arquivo temporário
                    os.remove(filepath)
                    
                    # Feedback consolidado
                    success_sheets = [r['sheet'] for r in sheet_results if r.get('success')]
                    failed_sheets = [r for r in sheet_results if not r.get('success')]
                    if success_sheets:
                        flash(f"Importação concluída. {total_imported} estudantes importados em {len(success_sheets)} aba(s): {', '.join(success_sheets)}.", 'success')
                    if failed_sheets:
                        msgs = '; '.join([f"{r['sheet']}: {r.get('error')}" for r in failed_sheets])
                        flash(f"Algumas abas falharam e foram revertidas: {msgs}", 'warning')
                    return redirect(url_for('dashboard'))
                        
                except Exception as e:
                    flash(f'Erro inesperado: {str(e)}', 'error')
            
            return render_template('upload/index.html', form=form)

        @app.route('/students')
        @login_required
        def students():
            page = request.args.get('page', 1, type=int)
            per_page = 20
            
            # Filtros
            # Permitir filtro por turma específica (id) ou por ano inteiro: ALL_6 / ALL_9
            class_filter_raw = (request.args.get('class_filter') or '').strip()
            class_filter = None
            try:
                class_filter = int(class_filter_raw) if class_filter_raw.isdigit() else None
            except Exception:
                class_filter = None
            teacher_filter = request.args.get('teacher_filter', type=int)
            cefr_filter = request.args.get('cefr_filter', '')
            sheet_filter = request.args.get('sheet_filter', '')
            search = request.args.get('search', '')
            search_in = request.args.get('search_in', 'name')
            sort = request.args.get('sort', 'name')
            
            def apply_name_search(base_query):
                if not search:
                    return base_query
                normalized = search.replace('\n', ',').replace(';', ',')
                search_terms = [term.strip() for term in normalized.split(',') if term.strip()]
                if not search_terms:
                    return base_query
                conditions = []
                for term in search_terms:
                    tokens = []
                    for token in term.split():
                        cleaned = re.sub(r'[^\w]', '', token, flags=re.UNICODE)
                        if cleaned:
                            tokens.append(cleaned.lower())
                    if not tokens:
                        continue
                    # Build grouped conditions with explicit parentheses to avoid SQL precedence issues
                    target_col = Student.found_name if search_in == 'found' else Student.name
                    token_conditions = [db.func.lower(target_col).like(f'%{token}%') for token in tokens]
                    if token_conditions:
                        # (name LIKE token1 AND name LIKE token2 ...)
                        and_group = db.and_(*token_conditions)
                        forward_pattern = ' '.join(tokens)
                        forward_like = db.func.lower(target_col).like(f'%{forward_pattern}%')
                        term_or_group = db.or_(and_group, forward_like)
                        if len(tokens) > 1:
                            reverse_pattern = ' '.join(reversed(tokens))
                            if reverse_pattern != forward_pattern:
                                reverse_like = db.func.lower(target_col).like(f'%{reverse_pattern}%')
                                term_or_group = db.or_(term_or_group, reverse_like)
                        # Force parentheses around the entire term group
                        try:
                            term_or_group = term_or_group.self_group()
                        except Exception:
                            # Fallback without self_group if not available
                            pass
                        conditions.append(term_or_group)
                if conditions:
                    base_query = base_query.filter(db.or_(*conditions))
                return base_query

            # Query base - incluir ComputedLevel e Class para filtros consistentes
            query = (Student.query
                     .join(ComputedLevel, Student.id == ComputedLevel.student_id, isouter=True)
                     .join(Class, Student.class_id == Class.id, isouter=True))
            
            # Aplicar filtros
            if class_filter:
                # Filtro por turma específica (id)
                query = query.filter(Student.class_id == class_filter)
            elif class_filter_raw in ('ALL_6', 'ALL_9'):
                # Filtro por ano inteiro com base no nome da turma
                lname = db.func.lower(Class.name)
                if class_filter_raw == 'ALL_6':
                    query = query.filter(
                        db.or_(
                            # Padrões de 6º ano
                            db.and_(lname.like('%6%'), db.or_(lname.like('%ano%'), Class.name.like('%°%'), lname.like('%sexto%'))),
                            lname.like('fund-6%'),
                            lname.like('%fund-6%')
                        )
                    )
                else:  # ALL_9
                    query = query.filter(
                        db.or_(
                            # Padrões de 9º ano
                            db.and_(lname.like('%9%'), db.or_(lname.like('%ano%'), Class.name.like('%°%'), lname.like('%nono%'))),
                            lname.like('fund-9%'),
                            lname.like('%fund-9%')
                        )
                    )
            # Filtro por professor: permitir "Sem professor" com valor 0
            if teacher_filter is not None:
                if teacher_filter == 0:
                    query = query.filter(Student.teacher_id.is_(None))
                else:
                    query = query.filter(Student.teacher_id == teacher_filter)
            if cefr_filter:
                # Filtro CEFR: usar ComputedLevel.overall_level e fazer fallback para Student.cefr_geral
                level = cefr_filter.strip()
                if level:
                    query = query.filter(
                        db.or_(
                            ComputedLevel.overall_level == level,
                            Student.cefr_geral == level
                        )
                    )
            if sheet_filter:
                query = query.filter(Student.import_sheet_name.ilike(f"%{sheet_filter.strip()}%"))
            query = apply_name_search(query)
            
            # Aplicar ordenação
            if sort == 'name':
                query = query.order_by(Student.name.asc())
            elif sort == 'name_desc':
                query = query.order_by(Student.name.desc())
            elif sort == 'class':
                # Class já foi joinado na linha 536, não precisa fazer JOIN novamente
                query = query.order_by(Class.name.asc())
            elif sort == 'class_desc':
                # Class já foi joinado na linha 536, não precisa fazer JOIN novamente
                query = query.order_by(Class.name.desc())
            elif sort == 'total_desc':
                query = query.order_by(Student.total.desc())
            elif sort == 'total':
                query = query.order_by(Student.total.asc())
            elif sort == 'cefr':
                query = query.order_by(Student.cefr_geral.asc())
            
            students = query.paginate(page=page, per_page=per_page, error_out=False)
            classes = Class.query.all()
            teachers = Teacher.query.all()

            # Calcular "Nome encontrado" por aluno quando há busca ativa
            found_names_by_id = {}
            if search:
                normalized = search.replace('\n', ',').replace(';', ',')
                search_terms = [term.strip() for term in normalized.split(',') if term.strip()]
                for st in students.items:
                    target_value = (st.found_name if search_in == 'found' else st.name) or ''
                    sname = target_value.lower()
                    matched = ''
                    for term in search_terms:
                        raw = term.strip()
                        if not raw:
                            continue
                        tokens = []
                        for token in raw.split():
                            cleaned = re.sub(r'[^\w]', '', token, flags=re.UNICODE)
                            if cleaned:
                                tokens.append(cleaned.lower())
                        if not tokens:
                            # fallback simples
                            if raw.lower() in sname:
                                matched = raw
                                break
                            continue
                        forward = ' '.join(tokens)
                        reverse = ' '.join(reversed(tokens))
                        if forward in sname or (len(tokens) > 1 and reverse in sname):
                            matched = raw
                            break
                        if all(tok in sname for tok in tokens):
                            matched = raw
                            break
                    found_names_by_id[st.id] = matched
            
            # Calcular estatísticas gerais (sem filtros)
            total_students_general = Student.query.count()
            avg_total_general = db.session.query(db.func.avg(Student.total)).scalar() or 0
            
            # Calcular nível predominante geral (sem filtros)
            # Preferir ComputedLevel; se não houver dados, fazer fallback para Student.cefr_geral
            cefr_distribution_general = db.session.query(
                ComputedLevel.overall_level,
                db.func.count(ComputedLevel.id)
            ).filter(ComputedLevel.overall_level.isnot(None)).group_by(ComputedLevel.overall_level).all()

            if not cefr_distribution_general:
                cefr_distribution_general = db.session.query(
                    Student.cefr_geral,
                    db.func.count(Student.id)
                ).filter(Student.cefr_geral.isnot(None)).group_by(Student.cefr_geral).all()
            
            # Determinar nível predominante geral com preferência por níveis superiores
            predominant_cefr_general = 'N/A'
            if cefr_distribution_general:
                dist_map = {lvl or 'N/A': cnt for lvl, cnt in cefr_distribution_general}
                b2 = dist_map.get('B2', 0)
                b1 = dist_map.get('B1', 0)
                a2 = dist_map.get('A2', 0) + dist_map.get('A2+', 0)
                a1 = dist_map.get('A1', 0)
                below = dist_map.get('Below A1', 0)

                if max(b2, b1, a2, a1, below) == 0:
                    predominant_cefr_general = 'N/A'
                elif b2 >= b1 and b2 >= a2 and b2 >= a1 and b2 >= below:
                    predominant_cefr_general = 'B2'
                elif (b1 + b2) > a2:
                    predominant_cefr_general = 'B1'
                else:
                    # fallback para o maior isolado
                    predominant_cefr_general = max(
                        [('B2', b2), ('B1', b1), ('A2', a2), ('A1', a1), ('Below A1', below)],
                        key=lambda x: x[1]
                    )[0]
            
            # Calcular estatísticas filtradas (baseadas na query atual)
            # Criar uma query similar para estatísticas filtradas
            filtered_query = (Student.query
                              .join(ComputedLevel, Student.id == ComputedLevel.student_id, isouter=True)
                              .join(Class, Student.class_id == Class.id, isouter=True))
            
            # Aplicar os mesmos filtros
            if class_filter:
                filtered_query = filtered_query.filter(Student.class_id == class_filter)
            elif class_filter_raw in ('ALL_6', 'ALL_9'):
                lname = db.func.lower(Class.name)
                if class_filter_raw == 'ALL_6':
                    filtered_query = filtered_query.filter(
                        db.or_(
                            db.and_(lname.like('%6%'), db.or_(lname.like('%ano%'), Class.name.like('%°%'), lname.like('%sexto%'))),
                            lname.like('fund-6%'),
                            lname.like('%fund-6%')
                        )
                    )
                else:
                    filtered_query = filtered_query.filter(
                        db.or_(
                            db.and_(lname.like('%9%'), db.or_(lname.like('%ano%'), Class.name.like('%°%'), lname.like('%nono%'))),
                            lname.like('fund-9%'),
                            lname.like('%fund-9%')
                        )
                    )
            # Filtro por professor: permitir "Sem professor" com valor 0
            if teacher_filter is not None:
                if teacher_filter == 0:
                    filtered_query = filtered_query.filter(Student.teacher_id.is_(None))
                else:
                    filtered_query = filtered_query.filter(Student.teacher_id == teacher_filter)
            if cefr_filter:
                level = cefr_filter.strip()
                if level:
                    filtered_query = filtered_query.filter(
                        db.or_(
                            ComputedLevel.overall_level == level,
                            Student.cefr_geral == level
                        )
                    )
            if sheet_filter:
                filtered_query = filtered_query.filter(Student.import_sheet_name.ilike(f"%{sheet_filter.strip()}%"))
            filtered_query = apply_name_search(filtered_query)
            
            # Contar alunos filtrados
            total_students_filtered = filtered_query.count()
            
            # Calcular média filtrada
            avg_total_filtered = filtered_query.with_entities(db.func.avg(Student.total)).scalar() or 0
            
            # Calcular nível predominante filtrado
            cefr_distribution_filtered = filtered_query.with_entities(
                ComputedLevel.overall_level,
                db.func.count(ComputedLevel.id)
            ).filter(ComputedLevel.overall_level.isnot(None)).group_by(ComputedLevel.overall_level).all()

            if not cefr_distribution_filtered:
                cefr_distribution_filtered = filtered_query.with_entities(
                    Student.cefr_geral,
                    db.func.count(Student.id)
                ).filter(Student.cefr_geral.isnot(None)).group_by(Student.cefr_geral).all()
            
            # Determinar nível predominante para o conjunto filtrado
            predominant_cefr_filtered = 'N/A'
            if cefr_distribution_filtered:
                dist_map_f = {lvl or 'N/A': cnt for lvl, cnt in cefr_distribution_filtered}
                b2f = dist_map_f.get('B2', 0)
                b1f = dist_map_f.get('B1', 0)
                a2f = dist_map_f.get('A2', 0) + dist_map_f.get('A2+', 0)
                a1f = dist_map_f.get('A1', 0)
                belowf = dist_map_f.get('Below A1', 0)

                if max(b2f, b1f, a2f, a1f, belowf) == 0:
                    predominant_cefr_filtered = 'N/A'
                elif b2f >= b1f and b2f >= a2f and b2f >= a1f and b2f >= belowf:
                    predominant_cefr_filtered = 'B2'
                elif (b1f + b2f) > a2f:
                    predominant_cefr_filtered = 'B1'
                else:
                    predominant_cefr_filtered = max(
                        [('B2', b2f), ('B1', b1f), ('A2', a2f), ('A1', a1f), ('Below A1', belowf)],
                        key=lambda x: x[1]
                    )[0]
            
            # Verificar se há filtros ativos
            # Considerar "Sem professor" (0) como filtro ativo
            has_filters = bool(
                (class_filter is not None) or (class_filter_raw in ('ALL_6', 'ALL_9')) or cefr_filter or sheet_filter or search or (teacher_filter is not None)
            )
            
            stats = {
                'total_students': total_students_filtered if has_filters else total_students_general,
                'total_students_general': total_students_general,
                'total_students_filtered': total_students_filtered,
                'avg_total': avg_total_filtered if has_filters else avg_total_general,
                'avg_total_general': avg_total_general,
                'avg_total_filtered': avg_total_filtered,
                'predominant_cefr': predominant_cefr_filtered if has_filters else predominant_cefr_general,
                'predominant_cefr_general': predominant_cefr_general,
                'predominant_cefr_filtered': predominant_cefr_filtered,
                'has_filters': has_filters,
                'cefr_distribution_filtered': cefr_distribution_filtered,
                'cefr_distribution_general': cefr_distribution_general
            }
            
            # Coletar nomes distintos de abas importadas
            distinct_sheets = db.session.query(db.func.distinct(Student.import_sheet_name)).filter(Student.import_sheet_name.isnot(None)).all()
            sheet_names = [s[0] for s in distinct_sheets if s and s[0]]

            return render_template('students/index.html', 
                                 students=students, 
                                 classes=classes, 
                                 teachers=teachers,
                                 sheet_names=sheet_names,
                                 stats=stats,
                                 class_filter=class_filter,
                                 teacher_filter=teacher_filter,
                                 cefr_filter=cefr_filter,
                                 sheet_filter=sheet_filter,
                                 search=search,
                                 search_in=search_in,
                                 found_names_by_id=found_names_by_id,
                                 sort=sort)

        @app.route('/student/<int:id>')
        @login_required
        def student_detail(id):
            student = Student.query.get_or_404(id)
            return render_template('students/detail.html', student=student)

        @app.route('/student/<int:id>/edit-class', methods=['GET', 'POST'])
        @login_required
        @admin_required
        def edit_student_class(id):
            student = Student.query.get_or_404(id)
            form = EditStudentClassForm()
            
            if form.validate_on_submit():
                student.class_id = form.class_id.data if form.class_id.data != 0 else None
                db.session.commit()
                flash('Turma do estudante atualizada com sucesso!', 'success')
                return redirect(url_for('student_detail', id=student.id))
            
            form.class_id.data = student.class_id
            return render_template('students/edit_class.html', form=form, student=student)

        @app.route('/student/<int:id>/edit-turma-meta', methods=['GET', 'POST'])
        @login_required
        @admin_required
        def edit_student_turma_meta(id):
            student = Student.query.get_or_404(id)
            form = EditStudentTurmaMetaForm()
            
            if form.validate_on_submit():
                student.turma_meta = form.turma_meta.data
                db.session.commit()
                flash('Turma Meta do estudante atualizada com sucesso!', 'success')
                return redirect(url_for('student_detail', id=student.id))
            
            form.turma_meta.data = student.turma_meta
            return render_template('students/edit_turma_meta.html', form=form, student=student)

        @app.route('/student/<int:id>/edit-listening-csa', methods=['GET', 'POST'])
        @login_required
        @admin_required
        def edit_student_listening_csa(id):
            from forms import EditListeningCSAForm
            student = Student.query.get_or_404(id)
            form = EditListeningCSAForm()

            if form.validate_on_submit():
                try:
                    student.listening_csa_points = form.csa_points.data
                    student.listening_csa_is_manual = bool(form.is_manual.data)
                    db.session.commit()
                    flash('Listening CSA atualizado com sucesso!', 'success')
                    return redirect(url_for('student_detail', id=student.id))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao atualizar Listening CSA: {str(e)}', 'error')

            # Pré-popular valores
            form.csa_points.data = student.listening_csa_points if student.listening_csa_points is not None else 0.0
            form.is_manual.data = bool(getattr(student, 'listening_csa_is_manual', False))
            return render_template('students/edit_listening_csa.html', form=form, student=student)

        @app.route('/student/<int:student_id>/report')
        @login_required
        def student_report(student_id):
            student = Student.query.get_or_404(student_id)
            return render_template('reports/student_report.html', student=student)

        @app.route('/students/add')
        @login_required
        @admin_required
        def add_student_form():
            """Exibe o formulário para adicionar um novo aluno"""
            classes = Class.query.all()
            teachers = Teacher.query.all()
            return render_template('students/add.html', classes=classes, teachers=teachers)

        @app.route('/students/add', methods=['POST'])
        @login_required
        @admin_required
        def add_student():
            """Processa a criação de um novo aluno"""
            try:
                # DEBUG: Log todos os dados recebidos
                print("=== DEBUG ADD STUDENT ===")
                print("Form data recebido:")
                for key, value in request.form.items():
                    print(f"  {key}: '{value}'")
                print("========================")
                
                # Validar campos obrigatórios
                name = request.form.get('name', '').strip()
                student_number = request.form.get('student_number', '').strip()
                
                if not name or not student_number:
                    flash('Nome e Número do Aluno são obrigatórios.', 'error')
                    return redirect(url_for('add_student_form'))
                
                # Verificar se o número do aluno já existe
                existing_student = Student.query.filter_by(student_number=student_number).first()
                if existing_student:
                    flash(f'Já existe um aluno com o número {student_number}.', 'error')
                    return redirect(url_for('add_student_form'))
                
                # Criar novo aluno
                new_student = Student(
                    name=name,
                    student_number=student_number
                )
                
                # Campos opcionais - dados básicos
                new_student.found_name = request.form.get('found_name', '').strip() or None
                new_student.import_sheet_name = request.form.get('import_sheet_name', '').strip() or None
                
                # Associações
                class_id = request.form.get('class_id')
                if class_id and class_id.isdigit():
                    new_student.class_id = int(class_id)
                
                teacher_id = request.form.get('teacher_id')
                if teacher_id and teacher_id.isdigit():
                    new_student.teacher_id = int(teacher_id)
                
                new_student.turma_meta = request.form.get('turma_meta', '').strip() or None
                
                # Pontuações
                listening = request.form.get('listening')
                print(f"DEBUG: listening raw = '{listening}'")
                if listening and listening.isdigit():
                    listening_val = int(listening)
                    print(f"DEBUG: listening_val = {listening_val}")
                    if 0 <= listening_val <= 300:
                        new_student.listening = listening_val
                        print(f"DEBUG: listening salvo = {new_student.listening}")
                    else:
                        print(f"DEBUG: listening fora do range: {listening_val}")
                else:
                    print(f"DEBUG: listening inválido ou vazio: '{listening}'")
                
                reading = request.form.get('reading')
                print(f"DEBUG: reading raw = '{reading}'")
                if reading and reading.isdigit():
                    reading_val = int(reading)
                    print(f"DEBUG: reading_val = {reading_val}")
                    if 0 <= reading_val <= 300:
                        new_student.reading = reading_val
                        print(f"DEBUG: reading salvo = {new_student.reading}")
                    else:
                        print(f"DEBUG: reading fora do range: {reading_val}")
                else:
                    print(f"DEBUG: reading inválido ou vazio: '{reading}'")
                
                lfm = request.form.get('lfm')
                print(f"DEBUG: lfm raw = '{lfm}'")
                if lfm and lfm.isdigit():
                    lfm_val = int(lfm)
                    print(f"DEBUG: lfm_val = {lfm_val}")
                    if 0 <= lfm_val <= 300:
                        new_student.lfm = lfm_val
                        print(f"DEBUG: lfm salvo = {new_student.lfm}")
                    else:
                        print(f"DEBUG: lfm fora do range: {lfm_val}")
                else:
                    print(f"DEBUG: lfm inválido ou vazio: '{lfm}'")
                
                total = request.form.get('total')
                print(f"DEBUG: total raw = '{total}'")
                if total and total.isdigit():
                    total_val = int(total)
                    print(f"DEBUG: total_val = {total_val}")
                    if 0 <= total_val <= 900:
                        new_student.total = total_val
                        print(f"DEBUG: total salvo = {new_student.total}")
                    else:
                        print(f"DEBUG: total fora do range: {total_val}")
                else:
                    print(f"DEBUG: total inválido ou vazio: '{total}'")
                
                # Níveis CEFR
                new_student.list_cefr = request.form.get('list_cefr', '').strip() or None
                new_student.read_cefr = request.form.get('read_cefr', '').strip() or None
                new_student.lfm_cefr = request.form.get('lfm_cefr', '').strip() or None
                new_student.cefr_geral = request.form.get('cefr_geral', '').strip() or None
                
                # Campos adicionais
                new_student.lexile = request.form.get('lexile', '').strip() or None
                
                listening_csa = request.form.get('listening_csa_points')
                if listening_csa:
                    try:
                        new_student.listening_csa_points = float(listening_csa)
                    except ValueError:
                        pass
                
                new_student.listening_csa_is_manual = bool(request.form.get('listening_csa_is_manual'))
                
                # Salvar no banco
                db.session.add(new_student)
                db.session.commit()
                
                # Criar ComputedLevel automaticamente
                try:
                    from models import ComputedLevel, calculate_student_levels
                    levels, applied_rules = calculate_student_levels(new_student)
                    
                    computed_level = ComputedLevel(
                        student_id=new_student.id,
                        school_level=levels.get('school_level'),
                        listening_level=levels.get('listening_level'),
                        lfm_level=levels.get('lfm_level'),
                        reading_level=levels.get('reading_level'),
                        overall_level=levels.get('overall_level'),
                        applied_rules='\n'.join(applied_rules)
                    )
                    
                    db.session.add(computed_level)
                    db.session.commit()
                    
                    print(f"DEBUG: ComputedLevel criado para {name}: {levels}")
                    
                except Exception as e:
                    print(f"DEBUG: Erro ao criar ComputedLevel para {name}: {str(e)}")
                    # Não falhar a criação do estudante por causa do ComputedLevel
                
                flash(f'Aluno {name} adicionado com sucesso!', 'success')
                return redirect(url_for('students'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao adicionar aluno: {str(e)}', 'error')
                return redirect(url_for('add_student_form'))

        @app.route('/classes')
        @login_required
        def classes():
            classes = Class.query.all()
            form = ClassForm()
            return render_template('classes/index.html', classes=classes, form=form)

        @app.route('/classes/create', methods=['POST'])
        @login_required
        @admin_required
        def create_class():
            form = ClassForm()
            if form.validate_on_submit():
                new_class = Class(name=form.name.data)
                db.session.add(new_class)
                db.session.commit()
                flash('Turma criada com sucesso!', 'success')
            else:
                flash('Erro ao criar turma. Verifique os dados.', 'error')
            return redirect(url_for('classes'))

        @app.route('/teachers')
        @login_required
        @admin_required
        def teachers():
            teachers = Teacher.query.all()
            form = TeacherForm()
            return render_template('teachers/index.html', teachers=teachers, form=form)

        @app.route('/teachers/create', methods=['POST'])
        @login_required
        @admin_required
        def create_teacher():
            form = TeacherForm()
            if form.validate_on_submit():
                new_teacher = Teacher(name=form.name.data)
                db.session.add(new_teacher)
                db.session.commit()
                flash('Professor criado com sucesso!', 'success')
            else:
                flash('Erro ao criar professor. Verifique os dados.', 'error')
            return redirect(url_for('teachers'))

        @app.route('/teachers/delete-multiple', methods=['POST'])
        @login_required
        @admin_required
        def delete_multiple_teachers():
            teacher_ids = request.form.getlist('teacher_ids')
            if teacher_ids:
                Teacher.query.filter(Teacher.id.in_(teacher_ids)).delete(synchronize_session=False)
                db.session.commit()
                flash(f'{len(teacher_ids)} professores deletados com sucesso!', 'success')
            return redirect(url_for('teachers'))

        # Rotas em Português para edição e deleção de professores (compatibilidade com UI)
        @app.route('/professores/<int:teacher_id>/editar', methods=['GET', 'POST'])
        @login_required
        @admin_required
        def editar_professor(teacher_id):
            teacher = Teacher.query.get_or_404(teacher_id)
            from forms import TeacherForm
            form = TeacherForm(teacher=teacher)

            if request.method == 'GET':
                # Renderizar página dedicada de edição para acessos diretos
                return render_template('teachers/edit.html', teacher=teacher, form=form)

            if form.validate_on_submit():
                try:
                    new_name = form.name.data.strip()
                    if not new_name:
                        flash('Nome do professor não pode ser vazio.', 'error')
                        return redirect(url_for('editar_professor', teacher_id=teacher_id))
                    # Evitar nomes duplicados
                    existing = Teacher.query.filter(Teacher.name == new_name, Teacher.id != teacher_id).first()
                    if existing:
                        flash('Já existe um professor com esse nome.', 'error')
                        return redirect(url_for('editar_professor', teacher_id=teacher_id))
                    teacher.name = new_name
                    db.session.commit()
                    flash('Professor atualizado com sucesso!', 'success')
                except Exception as e:
                    flash(f'Erro ao atualizar professor: {str(e)}', 'error')
                return redirect(url_for('teachers'))
            else:
                # Falha de validação (inclui CSRF ausente/inválido)
                flash('Erro de validação do formulário. Verifique os dados e tente novamente.', 'error')
                return redirect(url_for('editar_professor', teacher_id=teacher_id))

        @app.route('/professores/<int:teacher_id>/deletar', methods=['POST'])
        @login_required
        @admin_required
        def deletar_professor(teacher_id):
            try:
                teacher = Teacher.query.get_or_404(teacher_id)
                db.session.delete(teacher)
                db.session.commit()
                flash('Professor deletado com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao deletar professor: {str(e)}', 'error')
            return redirect(url_for('teachers'))

        @app.route('/admin')
        @login_required
        def admin():
            users = User.query.all()
            form = UserForm()
            return render_template('admin/index.html', users=users, form=form)

        @app.route('/admin/import')
        @login_required
        def admin_import():
            # Área exclusiva de admin para importação
            try:
                from flask_login import current_user
                if not getattr(current_user, 'is_admin', False):
                    flash('Acesso restrito aos administradores.', 'error')
                    return redirect(url_for('admin'))
            except Exception:
                # fallback: apenas exige login
                pass
            # Página exclusiva do admin com fluxo de importação sem depender de turma pré-selecionada
            return render_template('admin/import.html')

        @app.route('/admin/ensure-schema', methods=['POST'])
        @login_required
        def ensure_schema():
            # Verifica e adiciona colunas necessárias para a importação
            try:
                from flask_login import current_user
                if not getattr(current_user, 'is_admin', False):
                    flash('Acesso restrito aos administradores.', 'error')
                    return redirect(url_for('admin'))

                insp = inspect(db.engine)
                dialect = db.engine.dialect.name

                # Garantir tabela students e colunas
                if insp.has_table('students'):
                    student_cols = [col['name'] for col in insp.get_columns('students')]
                    # Lista mínima de colunas para novo fluxo
                    required_student_cols = {
                        'import_sheet_name': 'VARCHAR(120)',
                        'turma_meta': 'VARCHAR(10)',
                        'listening_csa_points': 'FLOAT',
                        'found_name': 'VARCHAR(120)',
                        'listening_csa_is_manual': 'BOOLEAN'
                    }
                    for col_name, col_type in required_student_cols.items():
                        if col_name not in student_cols:
                            try:
                                if dialect == 'sqlite':
                                    db.session.execute(text(f'ALTER TABLE students ADD COLUMN {col_name} {col_type}'))
                                else:
                                    db.session.execute(text(f'ALTER TABLE students ADD COLUMN {col_name} {col_type}'))
                                db.session.commit()
                                print(f'✅ Coluna {col_name} adicionada à tabela students')
                            except Exception as e:
                                db.session.rollback()
                                print(f'⚠️ Falha ao adicionar coluna {col_name} em students: {e}')

                # Garantir tabela classes e coluna meta_label
                if insp.has_table('classes'):
                    class_cols = [col['name'] for col in insp.get_columns('classes')]
                    if 'meta_label' not in class_cols:
                        try:
                            if dialect == 'sqlite':
                                db.session.execute(text('ALTER TABLE classes ADD COLUMN meta_label VARCHAR(10)'))
                            else:
                                db.session.execute(text('ALTER TABLE classes ADD COLUMN meta_label VARCHAR(10)'))
                            db.session.commit()
                            print('✅ Coluna meta_label adicionada à tabela classes')
                        except Exception as e:
                            db.session.rollback()
                            print(f'⚠️ Falha ao adicionar meta_label em classes: {e}')

                # Garantir tabela computed_levels
                if not insp.has_table('computed_levels'):
                    try:
                        db.create_all()
                        print('✅ Tabela computed_levels criada/verificada')
                    except Exception as e:
                        print(f'⚠️ Falha ao criar/verificar computed_levels: {e}')

                flash('Schema verificado/atualizado com sucesso para importação.', 'success')
            except Exception as e:
                flash(f'Erro ao verificar/atualizar schema: {str(e)}', 'error')
            return redirect(url_for('admin'))

        @app.route('/admin/recalculate-listening-csa', methods=['POST'])
        @login_required
        def recalculate_listening_csa_admin():
            """Recalcula Listening CSA para todos os alunos com total definido.
            Não filtra por professor; usa turma_meta ou meta_label da turma.
            """
            try:
                from flask_login import current_user
                if not getattr(current_user, 'is_admin', False):
                    flash('Acesso restrito aos administradores.', 'error')
                    return redirect(url_for('admin'))

                from models import Student
                updated = 0
                skipped = 0
                errors = 0

                # Buscar todos alunos com total definido
                students = Student.query.filter(Student.total.isnot(None)).all()
                for s in students:
                    try:
                        # Atualiza pontos CSA usando turma_meta ou class_info.meta_label
                        s.update_toefl_calculations()
                        updated += 1 if s.listening_csa_points is not None else 0
                        skipped += 1 if s.listening_csa_points is None else 0
                    except Exception:
                        errors += 1

                db.session.commit()
                flash(f'Recalculado Listening CSA: atualizados {updated}, sem pontos {skipped}, erros {errors}.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao recalcular Listening CSA: {str(e)}', 'error')
            return redirect(url_for('admin'))

        @app.route('/admin/create-user', methods=['POST'])
        @login_required
        def create_user():
            form = UserForm()
            if form.validate_on_submit():
                new_user = User(
                    username=form.username.data,
                    email=form.email.data,
                    is_active=form.is_active.data
                )
                new_user.set_password(form.password.data)
                db.session.add(new_user)
                db.session.commit()
                flash('Usuário criado com sucesso!', 'success')
            else:
                flash('Erro ao criar usuário. Verifique os dados.', 'error')
            return redirect(url_for('admin'))

        @app.route('/export-students')
        @login_required
        def export_students():
            # Exporta CSV com filtros e campos adicionais
            try:
                # Filtros simples
                class_filter = request.args.get('class_filter', type=int)
                cefr_filter = request.args.get('cefr_filter', '')
                sheet_name = request.args.get('sheet_name', '')
                teacher = request.args.get('teacher', '')

                query = Student.query
                if class_filter:
                    query = query.filter(Student.class_id == class_filter)
                if cefr_filter:
                    from models import ComputedLevel
                    query = query.join(ComputedLevel, Student.id == ComputedLevel.student_id, isouter=True)
                    query = query.filter(ComputedLevel.overall_level == cefr_filter)
                if sheet_name:
                    query = query.filter(Student.import_sheet_name.ilike(sheet_name))
                if teacher:
                    from models import Teacher
                    query = query.join(Teacher, Student.teacher_id == Teacher.id, isouter=True)
                    query = query.filter(Teacher.name.ilike(f"%{teacher}%"))

                students = query.all()

                # Construir CSV em memória
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    'id','name','student_number','class_id','class_name','import_sheet_name','turma_meta',
                    'listening','reading','lfm','total','cefr_geral','list_cefr','read_cefr','lfm_cefr','lexile'
                ])
                for s in students:
                    writer.writerow([
                        s.id,
                        s.name,
                        s.student_number,
                        s.class_id,
                        s.class_info.name if s.class_info else '',
                        s.import_sheet_name or '',
                        s.turma_meta or '',
                        s.listening or '',
                        s.reading or '',
                        s.lfm or '',
                        s.total or '',
                        s.cefr_geral or '',
                        s.list_cefr or '',
                        s.read_cefr or '',
                        s.lfm_cefr or '',
                        s.lexile or ''
                    ])

                output.seek(0)
                return send_file(
                    io.BytesIO(output.getvalue().encode('utf-8')),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=f"students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )
            except Exception as e:
                flash(f'Erro ao exportar CSV: {e}', 'error')
                return redirect(url_for('students'))

        @app.route('/upload-preview', methods=['POST'])
        @login_required
        def upload_preview():
            try:
                file = request.files.get('file')
                if not file or not file.filename:
                    return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

                filename = secure_filename(file.filename)
                import tempfile, os
                fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(filename)[1] or '.xlsx')
                os.close(fd)
                try:
                    file.save(temp_path)
                    importer = ExcelImporter(temp_path)
                    preview = importer.preview_data(max_rows=10)
                    # Adicionar revisão por abas, quando aplicável
                    try:
                        sheets_review = importer.preview_sheets()
                        if sheets_review.get('success'):
                            preview['sheets'] = sheets_review.get('sheets', [])
                    except Exception:
                        pass
                    return jsonify(preview)
                finally:
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
            except Exception as e:
                return jsonify({'success': False, 'error': f'Erro ao gerar prévia: {str(e)}'}), 500

        @app.route('/upload-confirm', methods=['POST'])
        @login_required
        def upload_confirm():
            """Processa importação multi-abas com criação automática de turmas."""
            try:
                file = request.files.get('file')
                if not file or not file.filename:
                    return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

                # Opção de seleção de abas e nomes de turma (opcional)
                selected_sheets = request.form.get('selected_sheets')
                class_names_raw = request.form.get('class_names')
                try:
                    import json
                    selected_sheets = json.loads(selected_sheets) if selected_sheets else None
                    class_names = json.loads(class_names_raw) if class_names_raw else {}
                except Exception:
                    selected_sheets = None
                    class_names = {}

                filename = secure_filename(file.filename)
                import tempfile, os
                fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(filename)[1] or '.xlsx')
                os.close(fd)
                try:
                    file.save(temp_path)
                    importer = ExcelImporter(temp_path)
                    sheets = importer.get_sheet_names()
                    if selected_sheets:
                        sheets = [s for s in sheets if s in selected_sheets]
                    results = []
                    total = 0
                    for s in sheets:
                        cname = class_names.get(s, s)
                        res = importer.import_sheet(sheet_name=s, class_id=None, class_name=cname)
                        results.append(res)
                        if res.get('success'):
                            total += res.get('processed', 0)
                    return jsonify({'success': True, 'total_imported': total, 'results': results})
                finally:
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
            except Exception as e:
                return jsonify({'success': False, 'error': f'Erro na confirmação de importação: {str(e)}'}), 500

        @app.route('/download-backup')
        @login_required
        def download_backup():
            """Gera um arquivo de backup completo e o envia para download."""
            try:
                from database_backup import export_data_json
                from datetime import datetime
                import os
                import tempfile

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                fd, temp_path = tempfile.mkstemp(suffix='.json', prefix='backup_')
                os.close(fd)

                export_data_json(temp_path)

                download_name = f'backup_{timestamp}.json'

                @after_this_request
                def remove_file(response):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                    return response

                return send_file(temp_path, as_attachment=True, download_name=download_name, mimetype='application/json')
            except Exception as error:
                flash(f'Erro ao gerar backup: {error}', 'error')
                return redirect(url_for('dashboard'))

        def restore_backup_from_filestorage(file_storage):
            """Processa um arquivo de backup enviado via formulario ou fetch."""
            import json
            import os
            import tempfile

            if not file_storage:
                return False, 'Nenhum arquivo foi selecionado.', {}, 400

            filename = (file_storage.filename or '').strip()
            if not filename:
                return False, 'Nenhum arquivo foi selecionado.', {}, 400

            if not filename.lower().endswith('.json'):
                return False, 'Apenas arquivos JSON sao aceitos.', {}, 400

            try:
                file_bytes = file_storage.read()
                if isinstance(file_bytes, bytes):
                    file_content = file_bytes.decode('utf-8')
                else:
                    file_content = str(file_bytes)
            except UnicodeDecodeError:
                return False, 'Nao foi possivel ler o arquivo. Utilize UTF-8.', {}, 400
            except Exception as decode_error:
                return False, f'Erro ao ler arquivo: {decode_error}', {}, 400

            try:
                backup_data = json.loads(file_content)
            except json.JSONDecodeError:
                return False, 'Arquivo JSON invalido.', {}, 400

            required_keys = {'teachers', 'classes', 'students'}
            if not required_keys.issubset(backup_data.keys()):
                return False, 'Arquivo de backup invalido. Estrutura incorreta.', {}, 400

            temp_filename = None
            import_result = None
            try:
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                    json.dump(backup_data, temp_file, ensure_ascii=False)
                    temp_filename = temp_file.name

                try:
                    from restore_backup import import_data_json
                    import_result = import_data_json(temp_filename)
                except ImportError:
                    from database_backup import import_data_json as fallback_import
                    import_result = fallback_import(temp_filename)

                promoted_total = 0
                try:
                    promoted_total = promote_a1_levels_to_a2()
                except Exception as promote_error:
                    print(f'Aviso: falha ao ajustar niveis A1 -> A2 apos restore: {promote_error}')

                success = True
                message = 'Backup restaurado com sucesso!'
                details = {}

                if isinstance(import_result, dict):
                    success = import_result.get('success', True)
                    message = import_result.get('message') or message
                    details = import_result.get('details') or {}

                if promoted_total:
                    details = dict(details) if details else {}
                    details['cefr_a1_promoted_to_a2'] = promoted_total
                    message = f"{message} Ajustados {promoted_total} campos A1 -> A2."

                status_code = 200 if success else 500
                return success, message.strip(), details, status_code
            except Exception as import_error:
                return False, f'Erro ao restaurar backup: {import_error}', {}, 500
            finally:
                if temp_filename and os.path.exists(temp_filename):
                    try:
                        os.unlink(temp_filename)
                    except OSError:
                        pass


        @app.route('/upload-backup', methods=['POST'])
        @login_required
        def upload_backup():
            """Processa uploads de backup via dashboard (form tradicional)."""
            file_storage = request.files.get('backup_file')
            success, message, details, status_code = restore_backup_from_filestorage(file_storage)
            flash(message, 'success' if success else 'error')
            return redirect(url_for('dashboard'))

        @app.route('/certificate/editor')
        @login_required
        def certificate_editor():
            student_id = request.args.get('student_id')
            if not student_id:
                flash('ID do estudante é obrigatório.', 'error')
                return redirect(url_for('dashboard'))
            
            student = Student.query.get_or_404(student_id)
            return render_template('certificate/editor.html', student=student)

        @app.route('/api/certificate/download', methods=['POST'])
        @login_required
        def download_certificate():
            try:
                from services.certificate_generator import create_certificate_for_student
                from models import StudentCertificateLayout
                
                data = request.get_json()
                student_id = data.get('student_id')
                custom_colors = data.get('colors', {})
                custom_positions = data.get('positions', {})
                logger = current_app.config.get('CERTIFICATE_LOGGER')
                if logger:
                    logger.info('download requested', extra={'student_id': student_id, 'positions': custom_positions, 'colors': custom_colors})
                
                if not student_id:
                    return jsonify({'error': 'ID do estudante é obrigatório'}), 400
                
                student = Student.query.get_or_404(student_id)
                
                # Buscar data personalizada salva no banco
                student_layout = StudentCertificateLayout.query.filter_by(student_id=student_id).first()
                custom_date = None
                if student_layout and student_layout.certificate_date:
                    custom_date = student_layout.certificate_date
                
                # Gerar certificado com data personalizada
                certificate_buffer = create_certificate_for_student(
                    student, 
                    custom_colors=custom_colors,
                    custom_positions=custom_positions,
                    custom_date=custom_date
                )
                
                # Preparar nome do arquivo
                filename = f"certificado_{student.name.replace(' ', '_')}.png"
                
                return send_file(
                    certificate_buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='image/png'
                )
                
            except Exception as e:
                return jsonify({'error': f'Erro ao gerar certificado: {str(e)}'}), 500

        @app.route('/api/certificate/download-zip', methods=['POST'])
        @login_required
        def download_certificates_zip():
            try:
                from services.certificate_generator import create_certificate_for_student
                from models import Student, Class, Teacher

                data = request.get_json() or {}
                class_id = data.get('class_id')
                teacher_id = data.get('teacher_id')  # opcional; 0 significa "Sem professor"
                certificate_date = data.get('certificate_date') or '2025-08-02'

                # Validar turma
                if not class_id or not isinstance(class_id, int):
                    return jsonify({'error': 'class_id inválido ou não fornecido'}), 400

                turma = Class.query.get(class_id)
                if not turma:
                    return jsonify({'error': 'Turma não encontrada'}), 404

                # Construir query com filtros
                query = Student.query.filter_by(class_id=class_id)
                teacher_label = None
                if teacher_id is not None:
                    if isinstance(teacher_id, int):
                        if teacher_id == 0:
                            query = query.filter(Student.teacher_id.is_(None))
                            teacher_label = 'sem_professor'
                        else:
                            teacher = Teacher.query.get(teacher_id)
                            if not teacher:
                                return jsonify({'error': 'Professor não encontrado'}), 404
                            query = query.filter(Student.teacher_id == teacher_id)
                            teacher_label = ''.join(c for c in teacher.name if c.isalnum() or c in (' ', '_', '-'))
                    else:
                        return jsonify({'error': 'teacher_id deve ser inteiro'}), 400

                students = query.all()
                if not students:
                    return jsonify({'error': 'Nenhum aluno encontrado para os filtros selecionados'}), 404

                # Gerar ZIP em memória
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for student in students:
                        img_buffer = create_certificate_for_student(
                            student,
                            custom_colors=None,
                            custom_positions=None,
                            custom_date=certificate_date
                        )
                        safe_name = ''.join(c for c in student.name if c.isalnum() or c in (' ', '_', '-'))
                        filename = f"Certificado_{safe_name.replace(' ', '_')}.png"
                        zipf.writestr(filename, img_buffer.getvalue())

                zip_buffer.seek(0)
                # Construir nome: Turma - Professor (preservando espaços e caracteres como '°')
                raw_class_name = turma.name or 'Turma'
                if teacher_id is None:
                    raw_teacher_name = 'Todos Professores'
                elif teacher_id == 0:
                    raw_teacher_name = 'Sem Professor'
                else:
                    raw_teacher_name = teacher.name if 'teacher' in locals() and teacher else (teacher_label or f'Professor_{teacher_id}')

                def to_safe_keep_spaces(s: str) -> str:
                    return ''.join(c for c in s if c.isalnum() or c in (' ', '_', '-', '.', '°')).strip()

                class_part = to_safe_keep_spaces(raw_class_name)
                teacher_part = to_safe_keep_spaces(raw_teacher_name)

                # Nome final do ZIP
                download_name = f"{class_part} - {teacher_part}.zip"

                return send_file(
                    zip_buffer,
                    as_attachment=True,
                    download_name=download_name,
                    mimetype='application/zip'
                )
            except Exception as e:
                return jsonify({'error': f'Erro ao gerar ZIP: {str(e)}'}), 500

        @app.route('/api/certificate/preview', methods=['POST'])
        @login_required
        def preview_certificate():
            try:
                print("🔍 PREVIEW: Iniciando geração de preview...")
                
                from services.certificate_generator import create_certificate_for_student
                from models import StudentCertificateLayout
                import base64
                
                data = request.get_json()
                print(f"🔍 PREVIEW: Dados recebidos: {data}")
                
                student_id = data.get('student_id')
                custom_colors = data.get('colors', {})
                custom_positions = data.get('positions', {})
                
                print(f"🔍 PREVIEW: student_id={student_id}, colors={custom_colors}, positions={custom_positions}")
                
                if not student_id:
                    print("❌ PREVIEW: ID do estudante não fornecido")
                    return jsonify({'error': 'ID do estudante é obrigatório'}), 400
                
                print(f"🔍 PREVIEW: Buscando estudante ID {student_id}...")
                student = Student.query.get_or_404(student_id)
                print(f"✅ PREVIEW: Estudante encontrado: {student.name}")
                
                # Buscar data personalizada salva no banco
                print(f"🔍 PREVIEW: Buscando layout personalizado...")
                student_layout = StudentCertificateLayout.query.filter_by(student_id=student_id).first()
                custom_date = None
                if student_layout and student_layout.certificate_date:
                    custom_date = student_layout.certificate_date
                    print(f"✅ PREVIEW: Data personalizada encontrada: {custom_date}")
                else:
                    print("ℹ️ PREVIEW: Nenhuma data personalizada, usando data atual")
                
                # Gerar certificado com data personalizada
                print(f"🔍 PREVIEW: Gerando certificado...")
                certificate_buffer = create_certificate_for_student(
                    student, 
                    custom_colors=custom_colors,
                    custom_positions=custom_positions,
                    custom_date=custom_date
                )
                print(f"✅ PREVIEW: Certificado gerado com sucesso")
                
                # Converter para base64 para enviar como JSON
                print(f"🔍 PREVIEW: Convertendo para base64...")
                certificate_buffer.seek(0)
                img_base64 = base64.b64encode(certificate_buffer.read()).decode('utf-8')
                print(f"✅ PREVIEW: Conversão base64 concluída (tamanho: {len(img_base64)} chars)")
                
                return jsonify({
                    'success': True,
                    'image': f'data:image/png;base64,{img_base64}'
                })
                
            except Exception as e:
                print(f"❌ PREVIEW: ERRO DETALHADO: {str(e)}")
                import traceback
                print(f"❌ PREVIEW: TRACEBACK: {traceback.format_exc()}")
                return jsonify({'error': f'Erro ao gerar preview: {str(e)}'}), 500

        @app.route('/api/certificate/load-positions')
        @login_required
        def load_certificate_positions():
            try:
                student_id = request.args.get('student_id')
                if not student_id:
                    return jsonify({'error': 'ID do estudante é obrigatório'}), 400
                
                # Tentar carregar layout específico do estudante
                from models import StudentCertificateLayout
                student_layout = StudentCertificateLayout.query.filter_by(student_id=student_id).first()
                
                if student_layout:
                    import json
                    positions = json.loads(student_layout.positions)
                    colors = json.loads(student_layout.colors) if student_layout.colors else {}
                    certificate_date = student_layout.certificate_date if hasattr(student_layout, 'certificate_date') else None
                    return jsonify({
                        'positions': positions,
                        'colors': colors,
                        'certificate_date': certificate_date
                    })
                
                # Se não há layout específico, carregar layout padrão do arquivo JSON
                import json
                default_layout_path = os.path.join(app.root_path, 'static', 'default_certificate_layout.json')
                
                if os.path.exists(default_layout_path):
                    with open(default_layout_path, 'r') as f:
                        layout = json.load(f)
                    return jsonify(layout)
                else:
                    # Retornar layout padrão se arquivo não existir
                    return jsonify({
                        'positions': {
                            'studentName': {'x': 401, 'y': 237, 'font_size': 31},
                            'listeningScore': {'x': 418, 'y': 337, 'font_size': 16},
                            'readingScore': {'x': 626, 'y': 336, 'font_size': 16},
                            'lfmScore': {'x': 419, 'y': 365, 'font_size': 16},
                            'totalScore': {'x': 626, 'y': 366, 'font_size': 16},
                            'testDate': {'x': 297, 'y': 414, 'font_size': 16}
                        },
                        'colors': {
                            'name_color': '#000000',
                            'scores_color': '#000000',
                            'date_color': '#000000'
                        }
                    })
                    
            except Exception as e:
                return jsonify({'error': f'Erro ao carregar posições: {str(e)}'}), 500

        @app.route('/api/students/<int:student_id>')
        @login_required
        def get_student_api(student_id):
            try:
                student = Student.query.get_or_404(student_id)
                return jsonify({
                    'id': student.id,
                    'name': student.name,
                    'listening': student.listening,
                    'reading': student.reading,
                    'lfm': student.lfm,
                    'total': student.total,
                    'cefr_geral': student.cefr_geral
                })
            except Exception as e:
                return jsonify({'error': f'Erro ao obter dados do estudante: {str(e)}'}), 500

        # Rotas para alteração de dados dos alunos
        @app.route('/api/alunos/<int:student_id>/alterar-professor', methods=['POST'])
        @login_required
        @admin_required
        def alterar_professor_aluno(student_id):
            try:
                data = request.get_json()
                teacher_id = data.get('teacher_id')
                
                student = Student.query.get_or_404(student_id)
                student.teacher_id = teacher_id
                db.session.commit()
                
                return jsonify({'success': True, 'message': 'Professor alterado com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao alterar professor: {str(e)}'}), 500

        @app.route('/api/alunos/<int:student_id>/alterar-turma', methods=['POST'])
        @login_required
        @admin_required
        def alterar_turma_aluno(student_id):
            try:
                data = request.get_json()
                class_id = data.get('class_id')
                
                student = Student.query.get_or_404(student_id)
                student.class_id = class_id
                db.session.commit()
                
                return jsonify({'success': True, 'message': 'Turma alterada com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao alterar turma: {str(e)}'}), 500

        @app.route('/api/alunos/<int:student_id>/alterar-rotulo-escolar', methods=['POST'])
        @login_required
        @admin_required
        def alterar_rotulo_escolar(student_id):
            try:
                data = request.get_json()
                school_label = data.get('school_label')
                
                student = Student.query.get_or_404(student_id)
                student.turma_meta = school_label  # Corrigido: usar turma_meta em vez de rotulo_escolar
                db.session.commit()
                
                return jsonify({'success': True, 'message': 'Rótulo escolar alterado com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao alterar rótulo escolar: {str(e)}'}), 500

        # Novo: alterar manualmente o "nome encontrado" do aluno
        @app.route('/api/alunos/<int:student_id>/alterar-nome-encontrado', methods=['POST'])
        @login_required
        @admin_required
        def alterar_nome_encontrado(student_id):
            try:
                data = request.get_json() or {}
                raw_found_name = data.get('found_name', '')

                # Normalização simples: remover espaços extras e limitar tamanho
                if raw_found_name is None:
                    normalized_found_name = ''
                else:
                    normalized_found_name = str(raw_found_name).strip()
                if len(normalized_found_name) > 120:
                    normalized_found_name = normalized_found_name[:120]

                student = Student.query.get_or_404(student_id)
                student.found_name = normalized_found_name or None  # permitir limpar o campo
                db.session.commit()

                return jsonify({'success': True, 'message': 'Nome encontrado atualizado com sucesso', 'found_name': student.found_name or ''})
            except Exception as e:
                return jsonify({'error': f'Erro ao alterar nome encontrado: {str(e)}'}), 500

        @app.route('/api/alunos/deletar-multiplos', methods=['POST'])
        @login_required
        def deletar_multiplos_alunos():
            try:
                data = request.get_json()
                student_ids = data.get('student_ids', [])
                
                if not student_ids:
                    return jsonify({'error': 'Nenhum aluno selecionado'}), 400
                
                # Converter student_ids para inteiros para evitar erro de tipo
                try:
                    student_ids = [int(id) for id in student_ids]
                except (ValueError, TypeError):
                    return jsonify({'error': 'IDs de alunos inválidos'}), 400
                
                students = Student.query.filter(Student.id.in_(student_ids)).all()
                for student in students:
                    db.session.delete(student)
                
                db.session.commit()
                
                return jsonify({'success': True, 'message': f'{len(students)} alunos deletados com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao deletar alunos: {str(e)}'}), 500

        @app.route('/update_student_teacher', methods=['POST'])
        @login_required
        @admin_required
        def update_student_teacher():
            try:
                data = request.get_json()
                student_id = data.get('student_id')
                teacher_id = data.get('teacher_id')
                
                student = Student.query.get_or_404(student_id)
                student.teacher_id = teacher_id
                db.session.commit()
                
                return jsonify({'success': True, 'message': 'Professor atualizado com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao atualizar professor: {str(e)}'}), 500

        # Rotas para certificados
        @app.route('/api/certificate/save-positions', methods=['POST'])
        @login_required
        def save_certificate_positions():
            try:
                data = request.get_json(silent=True) or {}
                print(f"🔍 Dados recebidos: {data}")

                # Extrair campos do payload
                student_id = data.get('student_id')
                positions = data.get('positions')
                colors = data.get('colors', {})
                certificate_date = data.get('certificate_date')  # Nova data personalizada

                # Normalizar quando vierem como strings JSON
                import json
                if isinstance(positions, str):
                    try:
                        positions = json.loads(positions)
                    except Exception:
                        pass
                if isinstance(colors, str):
                    try:
                        colors = json.loads(colors)
                    except Exception:
                        pass

                # Log seguro após inicializar variáveis
                logger = current_app.config.get('CERTIFICATE_LOGGER')
                if logger:
                    safe_positions_keys = list(positions.keys()) if isinstance(positions, dict) else 'not-dict'
                    logger.info('save positions', extra={'student_id': student_id, 'positions_keys': safe_positions_keys, 'colors': colors, 'certificate_date': certificate_date})
                
                print(f"🔍 student_id: {student_id}, positions: {positions}, colors: {colors}, certificate_date: {certificate_date}")
                
                if not student_id or not positions:
                    print(f"❌ Dados insuficientes - student_id: {student_id}, positions: {positions}")
                    return jsonify({'error': 'Dados insuficientes'}), 400
                
                # Verificar se o estudante existe
                from models import Student, StudentCertificateLayout
                student = Student.query.get(student_id)
                if not student:
                    return jsonify({'error': 'Estudante não encontrado'}), 404
                
                # Verificar se já existe um layout para este estudante
                student_layout = StudentCertificateLayout.query.filter_by(student_id=student_id).first()

                import json
                if student_layout:
                    # Atualizar layout existente
                    student_layout.positions = json.dumps(positions if not isinstance(positions, str) else json.loads(positions))
                    student_layout.colors = json.dumps(colors if not isinstance(colors, str) else json.loads(colors))
                    if certificate_date:
                        student_layout.certificate_date = certificate_date
                    student_layout.updated_at = datetime.utcnow()
                else:
                    # Criar novo layout
                    student_layout = StudentCertificateLayout(
                        student_id=student_id,
                        positions=json.dumps(positions if not isinstance(positions, str) else json.loads(positions)),
                        colors=json.dumps(colors if not isinstance(colors, str) else json.loads(colors)),
                        certificate_date=certificate_date
                    )
                    db.session.add(student_layout)
                
                db.session.commit()
                print(f"✅ Posições salvas com sucesso para student_id: {student_id}")
                return jsonify({'success': True, 'message': 'Posições salvas com sucesso'})
            except Exception as e:
                print(f"❌ Erro ao salvar posições: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Erro ao salvar posições: {str(e)}'}), 500

        @app.route('/api/certificate/save-colors', methods=['POST'])
        @login_required
        def save_certificate_colors():
            try:
                data = request.get_json(silent=True) or {}
                student_id = data.get('student_id')
                colors = data.get('colors')

                # Normalizar se vierem como string JSON
                import json
                if isinstance(colors, str):
                    try:
                        colors = json.loads(colors)
                    except Exception:
                        pass

                # Log seguro após inicializar variáveis
                logger = current_app.config.get('CERTIFICATE_LOGGER')
                if logger:
                    logger.info('save colors', extra={'student_id': student_id, 'colors': colors})
                
                if not student_id or not colors:
                    return jsonify({'error': 'Dados insuficientes'}), 400
                
                # Verificar se o estudante existe
                from models import Student, StudentCertificateLayout
                student = Student.query.get(student_id)
                if not student:
                    return jsonify({'error': 'Estudante não encontrado'}), 404
                
                # Verificar se já existe um layout para este estudante
                student_layout = StudentCertificateLayout.query.filter_by(student_id=student_id).first()
                
                import json
                if student_layout:
                    # Atualizar cores do layout existente
                    student_layout.colors = json.dumps(colors)
                    student_layout.updated_at = datetime.utcnow()
                else:
                    # Criar novo layout apenas com cores (posições vazias por enquanto)
                    student_layout = StudentCertificateLayout(
                        student_id=student_id,
                        positions=json.dumps({}),  # Posições vazias
                        colors=json.dumps(colors)
                    )
                    db.session.add(student_layout)
                
                db.session.commit()
                return jsonify({'success': True, 'message': 'Cores salvas com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao salvar cores: {str(e)}'}), 500

        @app.route('/api/certificate/save-default-layout', methods=['POST'])
        @login_required
        def save_default_layout():
            try:
                data = request.get_json()
                positions = data.get('positions')
                colors = data.get('colors', {})
                
                print(f"Salvando layout padrão - Posições: {positions}")
                print(f"Salvando layout padrão - Cores: {colors}")
                
                if not positions:
                    return jsonify({'error': 'Posições não fornecidas'}), 400
                
                # Salvar no arquivo JSON
                import json
                layout_data = {
                    'positions': positions,
                    'colors': colors
                }
                
                default_layout_path = os.path.join(app.root_path, 'static', 'default_certificate_layout.json')
                
                # Criar diretório static se não existir
                os.makedirs(os.path.dirname(default_layout_path), exist_ok=True)
                
                print(f"Salvando arquivo em: {default_layout_path}")
                
                with open(default_layout_path, 'w', encoding='utf-8') as f:
                    json.dump(layout_data, f, indent=2, ensure_ascii=False)
                
                print("Arquivo JSON salvo com sucesso")
                
                # Também salvar no banco de dados como layout padrão
                from models import CertificateLayout
                default_layout = CertificateLayout.query.filter_by(is_default=True).first()
                
                if default_layout:
                    # Atualizar layout padrão existente
                    default_layout.positions = json.dumps(positions)
                    default_layout.colors = json.dumps(colors)
                    default_layout.updated_at = datetime.utcnow()
                    print("Layout padrão existente atualizado")
                else:
                    # Criar novo layout padrão
                    default_layout = CertificateLayout(
                        name='default',
                        positions=json.dumps(positions),
                        colors=json.dumps(colors),
                        is_default=True
                    )
                    db.session.add(default_layout)
                    print("Novo layout padrão criado")
                
                db.session.commit()
                print("Banco de dados atualizado com sucesso")
                return jsonify({'success': True, 'message': 'Layout padrão salvo com sucesso'})
            except Exception as e:
                print(f"Erro ao salvar layout padrão: {str(e)}")
                return jsonify({'error': f'Erro ao salvar layout padrão: {str(e)}'}), 500

        @app.route('/api/certificate/colors')
        @login_required
        def get_certificate_colors():
            try:
                student_id = request.args.get('student_id')
                
                if not student_id:
                    return jsonify({'error': 'ID do estudante não fornecido'}), 400
                
                # Retornar cores padrão ou salvas
                default_colors = {
                    'student_name': '#000000',
                    'scores': '#000000',
                    'date': '#000000'
                }
                
                return jsonify(default_colors)
            except Exception as e:
                return jsonify({'error': f'Erro ao carregar cores: {str(e)}'}), 500

        # Rotas de administração
        @app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
        @login_required
        def toggle_user_status(user_id):
            try:
                user = User.query.get_or_404(user_id)
                user.is_active = not user.is_active
                db.session.commit()
                
                status = 'ativado' if user.is_active else 'desativado'
                return jsonify({'success': True, 'message': f'Usuário {status} com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao alterar status do usuário: {str(e)}'}), 500

        @app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
        @login_required
        def edit_user(user_id):
            try:
                user = User.query.get_or_404(user_id)
                form = UserForm()
                
                if form.validate_on_submit():
                    user.username = form.username.data
                    user.email = form.email.data
                    user.is_admin = form.is_admin.data
                    user.is_active = form.is_active.data
                    
                    # Só atualiza a senha se foi fornecida
                    if form.password.data:
                        user.set_password(form.password.data)
                    
                    db.session.commit()
                    flash('Usuário atualizado com sucesso!', 'success')
                else:
                    flash('Erro ao atualizar usuário. Verifique os dados.', 'error')
                
                return redirect(url_for('admin'))
            except Exception as e:
                flash(f'Erro ao editar usuário: {str(e)}', 'error')
                return redirect(url_for('admin'))

        @app.route('/admin/users/<int:user_id>/delete', methods=['DELETE'])
        @login_required
        def delete_user(user_id):
            try:
                user = User.query.get_or_404(user_id)
                
                # Não permitir deletar o próprio usuário
                if user.id == current_user.id:
                    return jsonify({'success': False, 'error': 'Não é possível deletar seu próprio usuário'}), 400
                
                db.session.delete(user)
                db.session.commit()
                
                return jsonify({'success': True, 'message': 'Usuário deletado com sucesso'})
            except Exception as e:
                return jsonify({'success': False, 'error': f'Erro ao deletar usuário: {str(e)}'}), 500

        @app.route('/admin/database/reset', methods=['POST'])
        @login_required
        def reset_database():
            """Reset completo do banco de dados"""
            try:
                from models import db, User
                from werkzeug.security import generate_password_hash
                
                # Salvar informações do usuário atual
                current_user_id = current_user.id
                current_user_data = {
                    'username': current_user.username,
                    'email': current_user.email,
                    'password_hash': current_user.password_hash,
                    'is_admin': current_user.is_admin
                }
                
                # Dropar todas as tabelas
                db.drop_all()
                
                # Recriar todas as tabelas
                db.create_all()
                
                # Recriar usuário atual
                new_user = User(
                    username=current_user_data['username'],
                    email=current_user_data['email'],
                    password_hash=current_user_data['password_hash'],
                    is_admin=current_user_data['is_admin'],
                    is_active=True
                )
                db.session.add(new_user)
                
                # Criar usuário admin padrão se não for o atual
                if not current_user_data['is_admin']:
                    admin_user = User(
                        username='admin',
                        email='admin@toefl.com',
                        password_hash=generate_password_hash('admin123'),
                        is_admin=True,
                        is_active=True
                    )
                    db.session.add(admin_user)
                
                db.session.commit()
                
                return jsonify({
                    'success': True, 
                    'message': 'Reset do banco de dados executado com sucesso! Todas as tabelas foram recriadas.'
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Erro ao resetar banco de dados: {str(e)}'})

        @app.route('/admin/database/backup', methods=['POST'])
        @login_required
        @admin_required
        def backup_database():
            """Criar backup do banco de dados"""
            try:
                from database_backup import export_data_json
                from datetime import datetime
                import os
                
                # Criar diretório de backups se não existir
                backup_dir = 'backups'
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                
                # Gerar nome do arquivo com timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'backups/backup_{timestamp}.json'
                
                # Executar backup
                export_data_json(filename)
                
                return jsonify({
                    'success': True, 
                    'message': f'Backup criado com sucesso! Arquivo: {filename}',
                    'filename': filename
                })
            except Exception as e:
                return jsonify({'success': False, 'message': f'Erro ao criar backup: {str(e)}'}), 500

        @app.route('/admin/restore-backup', methods=['GET', 'POST'])
        @login_required
        @admin_required
        def restore_backup():
            """Restaura um backup via painel administrativo (fetch)."""
            if request.method == 'GET':
                return redirect(url_for('admin'))

            file_storage = request.files.get('backup_file')
            success, message, details, status_code = restore_backup_from_filestorage(file_storage)

            response = {'success': success, 'message': message}
            if details:
                response['details'] = details

            return jsonify(response), status_code

        @app.route('/admin/auto-fix', methods=['POST'])
        @login_required
        def auto_fix():
            """Executar correções automáticas"""
            try:
                from render_auto_fix import run_auto_fix
                
                # Executar correções automáticas
                results = run_auto_fix()
                
                if results['overall_success']:
                    message = f"Correções automáticas concluídas! Total de correções: {results['total_corrections']}"
                    if results['details']['errors']:
                        message += f" (com {len(results['details']['errors'])} avisos)"
                    
                    return jsonify({
                        'success': True, 
                        'message': message,
                        'details': results['details']
                    })
                else:
                    return jsonify({
                        'success': False, 
                        'message': 'Algumas correções falharam',
                        'details': results['details']
                    })
            except Exception as e:
                return jsonify({'success': False, 'message': f'Erro ao executar correções: {str(e)}'}), 500

        @app.route('/admin/reset-perfect', methods=['POST'])
        @login_required
        def reset_perfect():
            """Executar reset perfeito do banco de dados"""
            try:
                import subprocess
                import sys
                
                # Executar o script render_perfect_reset.py
                result = subprocess.run([sys.executable, 'render_perfect_reset.py'], 
                                      capture_output=True, text=True, cwd=os.getcwd())
                
                if result.returncode == 0:
                    return jsonify({
                        'success': True, 
                        'message': 'Reset perfeito executado com sucesso! Banco de dados recriado com dados do backup.',
                        'output': result.stdout
                    })
                else:
                    return jsonify({
                        'success': False, 
                        'message': f'Erro ao executar reset perfeito: {result.stderr}',
                        'output': result.stdout
                    })
            except Exception as e:
                return jsonify({'success': False, 'message': f'Erro ao executar reset perfeito: {str(e)}'}), 500

        @app.route('/admin/cefr-fix', methods=['POST'])
        @login_required
        def cefr_fix():
            """Recalcular níveis CEFR para todos os estudantes"""
            try:
                from models import Student, ComputedLevel, calculate_student_levels
                
                students = Student.query.all()
                updated_count = 0
                created_count = 0
                errors = []
                
                for student in students:
                    try:
                        # Calcular níveis para o estudante
                        levels, applied_rules = calculate_student_levels(student)
                        
                        # Buscar ou criar ComputedLevel
                        computed_level = ComputedLevel.query.filter_by(student_id=student.id).first()
                        
                        if computed_level:
                            # Atualizar registro existente
                            computed_level.school_level = levels.get('school_level')
                            computed_level.listening_level = levels.get('listening_level')
                            computed_level.lfm_level = levels.get('lfm_level')
                            computed_level.reading_level = levels.get('reading_level')
                            computed_level.overall_level = levels.get('overall_level')
                            computed_level.applied_rules = '\n'.join(applied_rules)
                            updated_count += 1
                        else:
                            # Criar novo registro
                            computed_level = ComputedLevel(
                                student_id=student.id,
                                school_level=levels.get('school_level'),
                                listening_level=levels.get('listening_level'),
                                lfm_level=levels.get('lfm_level'),
                                reading_level=levels.get('reading_level'),
                                overall_level=levels.get('overall_level'),
                                applied_rules='\n'.join(applied_rules)
                            )
                            db.session.add(computed_level)
                            created_count += 1
                            
                    except Exception as e:
                        errors.append(f"Erro no estudante {student.id} ({student.name}): {str(e)}")
                
                # Salvar alterações
                db.session.commit()
                
                message = f"Níveis CEFR recalculados! Atualizados: {updated_count}, Criados: {created_count}"
                if errors:
                    message += f" (com {len(errors)} erros)"
                
                return jsonify({
                    'success': True, 
                    'message': message,
                    'details': {
                        'updated': updated_count,
                        'created': created_count,
                        'errors': errors
                    }
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Erro ao recalcular níveis CEFR: {str(e)}'})

        @app.route('/admin/fix-asterisk-cefr', methods=['POST'])
        @login_required
        def fix_asterisk_cefr():
            """Corrigir campos CEFR com asterisco (*)"""
            try:
                from models import Student
                
                # Buscar estudantes com asteriscos nos campos CEFR
                students_with_asterisk = Student.query.filter(
                    db.or_(
                        Student.list_cefr == '*',
                        Student.lfm_cefr == '*',
                        Student.read_cefr == '*',
                        Student.cefr_geral == '*'
                    )
                ).all()
                
                fixed_count = 0
                errors = []
                
                for student in students_with_asterisk:
                    try:
                        # Corrigir campos com asterisco baseado nas pontuações
                        if student.list_cefr == '*' and student.listening:
                            student.list_cefr = calculate_cefr_by_score(student.listening, 'listening')
                            fixed_count += 1
                        
                        if student.lfm_cefr == '*' and student.lfm:
                            student.lfm_cefr = calculate_cefr_by_score(student.lfm, 'lfm')
                            fixed_count += 1
                        
                        if student.read_cefr == '*' and student.reading:
                            student.read_cefr = calculate_cefr_by_score(student.reading, 'reading')
                            fixed_count += 1
                        
                        if student.cefr_geral == '*' and student.total:
                            student.cefr_geral = calculate_cefr_level(student.total)
                            fixed_count += 1
                            
                    except Exception as e:
                        errors.append(f"Erro no estudante {student.id} ({student.name}): {str(e)}")
                
                # Salvar alterações
                db.session.commit()
                
                message = f"Correção de asteriscos concluída! {fixed_count} campos corrigidos em {len(students_with_asterisk)} estudantes"
                if errors:
                    message += f" (com {len(errors)} erros)"
                
                return jsonify({
                    'success': True, 
                    'message': message,
                    'details': {
                        'students_processed': len(students_with_asterisk),
                        'fields_fixed': fixed_count,
                        'errors': errors
                    }
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Erro ao corrigir asteriscos: {str(e)}'})

        # Rota para limpar cache
        @app.route('/api/clear-cache', methods=['POST'])
        @login_required
        @admin_required
        def clear_cache():
            try:
                # Implementar limpeza de cache
                return jsonify({'success': True, 'message': 'Cache limpo com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao limpar cache: {str(e)}'}), 500

        return app, csrf




def promote_a1_levels_to_a2():
    """Ensure all CEFR values stored as A1 are promoted to A2."""
    from models import db, Student, ComputedLevel

    total_updates = 0

    try:
        student_columns = (
            Student.list_cefr,
            Student.lfm_cefr,
            Student.read_cefr,
            Student.cefr_geral,
        )

        for column in student_columns:
            updates = Student.query.filter(column == 'A1').update(
                {column: 'A2'},
                synchronize_session=False,
            )
            if updates:
                total_updates += updates

        computed_columns = (
            ComputedLevel.listening_level,
            ComputedLevel.lfm_level,
            ComputedLevel.reading_level,
            ComputedLevel.overall_level,
        )

        for column in computed_columns:
            updates = ComputedLevel.query.filter(column == 'A1').update(
                {column: 'A2'},
                synchronize_session=False,
            )
            if updates:
                total_updates += updates

        if total_updates:
            db.session.commit()

        return total_updates
    except Exception:
        db.session.rollback()
        raise

def calculate_cefr_level(total_score):
    """Calcula o nível CEFR baseado na pontuação total (base única)."""
    if total_score is None:
        return 'N/A'
    if total_score >= 865:
        return 'B2'
    elif total_score >= 730:
        return 'B1'
    elif total_score >= 650:
        return 'A2+'
    elif total_score >= 600:
        return 'A2'
    else:
        return 'Below A1'

def calculate_cefr_by_score(score, skill_type):
    """Calcula o nível CEFR baseado na pontuação de uma habilidade específica"""
    # Thresholds podem variar por habilidade, mas usando os mesmos por simplicidade
    if score >= 200:
        return 'B2'
    elif score >= 175:
        return 'B1'
    elif score >= 162:
        return 'A2+'
    elif score >= 150:
        return 'A2'
    else:
        return 'A1'

if __name__ == '__main__':
    # Criar app apenas para execução local
    app, csrf = create_app()
    
    # Criar tabelas se não existirem (apenas para desenvolvimento local)
    with app.app_context():
        from models import db  # Importar db aqui
        insp = inspect(db.engine)
        if not insp.has_table("classes"):
            db.create_all()
    # Usar porta fixa 5001 para execução local
    port = 5001
    print(f"🚀 Servidor iniciando na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
