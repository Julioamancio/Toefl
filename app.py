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
from sqlalchemy import inspect
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache

def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""
    app = Flask(__name__)
    
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
            return redirect(url_for('login'))

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
                    if not next_page or not next_page.startswith('/'):
                        next_page = url_for('dashboard')
                    return redirect(next_page)
                flash('Nome de usuário ou senha inválidos', 'error')
            return render_template('login.html', form=form)

        @app.route('/logout')
        @login_required
        def logout():
            logout_user()
            return redirect(url_for('login'))

        @app.route("/health/db")
        def health_db():
            try:
                db.session.execute('SELECT 1')
                return {"status": "ok", "database": "connected"}, 200
            except Exception as e:
                return {"status": "error", "database": str(e)}, 500

        @app.route('/dash')
        @login_required
        def dashboard():
            # Estatísticas básicas
            total_students = Student.query.count()
            total_classes = Class.query.count()
            total_teachers = Teacher.query.count()
            
            # Distribuição por nível CEFR
            cefr_distribution = db.session.query(
                Student.cefr_level, 
                db.func.count(Student.id)
            ).group_by(Student.cefr_level).all()
            
            # Converter para dicionário
            cefr_dict = {level: count for level, count in cefr_distribution}
            
            # Garantir que todos os níveis estejam presentes
            all_levels = ['A1', 'A2', 'A2+', 'B1', 'B2']
            for level in all_levels:
                if level not in cefr_dict:
                    cefr_dict[level] = 0
            
            # Estatísticas por turma
            class_stats = db.session.query(
                Class.name,
                db.func.count(Student.id).label('student_count'),
                db.func.avg(Student.total_score).label('avg_score')
            ).outerjoin(Student).group_by(Class.id, Class.name).all()
            
            # Alunos recentes (últimos 10)
            recent_students = Student.query.order_by(Student.created_at.desc()).limit(10).all()
            
            # Top 10 alunos por pontuação
            top_students = Student.query.order_by(Student.total_score.desc()).limit(10).all()
            
            # Estatísticas por professor
            teacher_stats = db.session.query(
                Teacher.name,
                db.func.count(Student.id).label('student_count'),
                db.func.avg(Student.total_score).label('avg_score')
            ).outerjoin(Student).group_by(Teacher.id, Teacher.name).all()
            
            # Alunos sem turma_meta (rótulo escolar)
            students_without_turma_meta = Student.query.filter(
                (Student.turma_meta == None) | (Student.turma_meta == "")
            ).count()
            
            # Alunos sem professor
            students_without_teacher = Student.query.filter(Student.teacher_id == None).count()
            
            # Alunos sem turma
            students_without_class = Student.query.filter(Student.class_id == None).count()
            
            return render_template('dashboard.html', 
                                 total_students=total_students,
                                 total_classes=total_classes,
                                 total_teachers=total_teachers,
                                 cefr_distribution=cefr_dict,
                                 class_stats=class_stats,
                                 recent_students=recent_students,
                                 top_students=top_students,
                                 teacher_stats=teacher_stats,
                                 students_without_turma_meta=students_without_turma_meta,
                                 students_without_teacher=students_without_teacher,
                                 students_without_class=students_without_class)
    
    # Retornar a instância csrf para uso global
    return app, csrf

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

if __name__ == '__main__':
    # Criar app apenas para execução local
    app, csrf = create_app()
    
    # Criar tabelas se não existirem (apenas para desenvolvimento local)
    with app.app_context():
        from models import db  # Importar db aqui
        insp = inspect(db.engine)
        if not insp.has_table("classes"):
            db.create_all()
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Servidor iniciando na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)