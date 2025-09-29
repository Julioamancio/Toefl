from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, after_this_request
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
from config import config
from sqlalchemy import inspect, text
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
            try:
                promoted_total = promote_a1_levels_to_a2()
                if promoted_total:
                    print(f"Ajustados {promoted_total} campos CEFR de A1 para A2")
            except Exception as promote_error:
                print(f"Aviso: nao foi possivel ajustar niveis A1 -> A2 automaticamente: {promote_error}")

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
            
            # Distribuição por nível CEFR (excluindo valores None)
            cefr_distribution = db.session.query(
                Student.cefr_geral, 
                db.func.count(Student.id)
            ).filter(Student.cefr_geral.isnot(None)).group_by(Student.cefr_geral).all()
            
            # Converter para dicionário
            cefr_dict = {level: count for level, count in cefr_distribution if level is not None}
            
            # Garantir que todos os níveis estejam presentes
            all_levels = ['A1', 'A2', 'A2+', 'B1', 'B2']
            for level in all_levels:
                if level not in cefr_dict:
                    cefr_dict[level] = 0
            
            # Converter de volta para lista de tuplas para o template
            cefr_distribution_list = [(level, cefr_dict[level]) for level in all_levels]
            
            # Calcular nível predominante
            predominant_level = 'N/A'
            if cefr_dict:
                # Encontrar o nível com maior contagem
                max_level = max(cefr_dict.items(), key=lambda x: x[1])
                if max_level[1] > 0:  # Se há pelo menos um aluno
                    predominant_level = max_level[0]
            
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
                                 top_students_9th=top_students_9th)

        @app.route('/upload', methods=['GET', 'POST'])
        @login_required
        def upload():
            form = UploadForm()
            
            if form.validate_on_submit():
                try:
                    file = form.file.data
                    class_id = form.class_id.data if form.class_id.data != 0 else None
                    
                    # Salvar arquivo temporariamente
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), filename)
                    
                    # Criar diretório se não existir
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    file.save(filepath)
                    
                    # Processar arquivo
                    importer = ExcelImporter(filepath, class_id)
                    result = importer.import_data()
                    
                    # Remover arquivo temporário
                    os.remove(filepath)
                    
                    if result['success']:
                        flash(f'Upload realizado com sucesso! {result["imported"]} estudantes importados.', 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        flash(f'Erro no upload: {result["error"]}', 'error')
                        
                except Exception as e:
                    flash(f'Erro inesperado: {str(e)}', 'error')
            
            return render_template('upload/index.html', form=form)

        @app.route('/students')
        @login_required
        def students():
            page = request.args.get('page', 1, type=int)
            per_page = 20
            
            # Filtros
            class_filter = request.args.get('class_filter', type=int)
            teacher_filter = request.args.get('teacher_filter', type=int)
            cefr_filter = request.args.get('cefr_filter', '')
            search = request.args.get('search', '')
            sort = request.args.get('sort', 'name')
            
            # Query base - incluir ComputedLevel para filtro CEFR consistente
            query = Student.query.join(ComputedLevel, Student.id == ComputedLevel.student_id, isouter=True)
            
            # Aplicar filtros
            if class_filter:
                query = query.filter(Student.class_id == class_filter)
            if teacher_filter:
                query = query.filter(Student.teacher_id == teacher_filter)
            if cefr_filter:
                # Usar ComputedLevel.overall_level para consistência com a API
                query = query.filter(ComputedLevel.overall_level == cefr_filter.strip())
            if search:
                # Busca por múltiplos nomes separados por vírgula ou quebra de linha
                search_terms = [term.strip() for term in search.replace('\n', ',').split(',') if term.strip()]
                if search_terms:
                    search_conditions = []
                    for term in search_terms:
                        search_conditions.append(Student.name.contains(term))
                    query = query.filter(db.or_(*search_conditions))
            
            # Aplicar ordenação
            if sort == 'name':
                query = query.order_by(Student.name.asc())
            elif sort == 'name_desc':
                query = query.order_by(Student.name.desc())
            elif sort == 'class':
                query = query.join(Class).order_by(Class.name.asc())
            elif sort == 'class_desc':
                query = query.join(Class).order_by(Class.name.desc())
            elif sort == 'total_desc':
                query = query.order_by(Student.total.desc())
            elif sort == 'total':
                query = query.order_by(Student.total.asc())
            elif sort == 'cefr':
                query = query.order_by(Student.cefr_geral.asc())
            
            students = query.paginate(page=page, per_page=per_page, error_out=False)
            classes = Class.query.all()
            teachers = Teacher.query.all()
            
            # Calcular estatísticas gerais (sem filtros)
            total_students_general = Student.query.count()
            avg_total_general = db.session.query(db.func.avg(Student.total)).scalar() or 0
            
            # Calcular nível predominante geral (sem filtros)
            cefr_distribution_general = db.session.query(
                ComputedLevel.overall_level,
                db.func.count(ComputedLevel.id)
            ).filter(ComputedLevel.overall_level.isnot(None)).group_by(ComputedLevel.overall_level).all()
            
            predominant_cefr_general = 'N/A'
            if cefr_distribution_general:
                max_count = max(cefr_distribution_general, key=lambda x: x[1])
                if max_count[1] > 0:
                    predominant_cefr_general = max_count[0]
            
            # Calcular estatísticas filtradas (baseadas na query atual)
            # Criar uma query similar para estatísticas filtradas
            filtered_query = Student.query.join(ComputedLevel, Student.id == ComputedLevel.student_id, isouter=True)
            
            # Aplicar os mesmos filtros
            if class_filter:
                filtered_query = filtered_query.filter(Student.class_id == class_filter)
            if teacher_filter:
                filtered_query = filtered_query.filter(Student.teacher_id == teacher_filter)
            if cefr_filter:
                filtered_query = filtered_query.filter(ComputedLevel.overall_level == cefr_filter.strip())
            if search:
                search_terms = [term.strip() for term in search.replace('\n', ',').split(',') if term.strip()]
                if search_terms:
                    search_conditions = []
                    for term in search_terms:
                        search_conditions.append(Student.name.contains(term))
                    filtered_query = filtered_query.filter(db.or_(*search_conditions))
            
            # Contar alunos filtrados
            total_students_filtered = filtered_query.count()
            
            # Calcular média filtrada
            avg_total_filtered = filtered_query.with_entities(db.func.avg(Student.total)).scalar() or 0
            
            # Calcular nível predominante filtrado
            cefr_distribution_filtered = filtered_query.with_entities(
                ComputedLevel.overall_level,
                db.func.count(ComputedLevel.id)
            ).filter(ComputedLevel.overall_level.isnot(None)).group_by(ComputedLevel.overall_level).all()
            
            predominant_cefr_filtered = 'N/A'
            if cefr_distribution_filtered:
                max_count = max(cefr_distribution_filtered, key=lambda x: x[1])
                if max_count[1] > 0:
                    predominant_cefr_filtered = max_count[0]
            
            # Verificar se há filtros ativos
            has_filters = bool(class_filter or teacher_filter or cefr_filter or search)
            
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
            
            return render_template('students/index.html', 
                                 students=students, 
                                 classes=classes, 
                                 teachers=teachers,
                                 stats=stats,
                                 class_filter=class_filter,
                                 teacher_filter=teacher_filter,
                                 cefr_filter=cefr_filter,
                                 search=search,
                                 sort=sort)

        @app.route('/student/<int:id>')
        @login_required
        def student_detail(id):
            student = Student.query.get_or_404(id)
            return render_template('students/detail.html', student=student)

        @app.route('/student/<int:id>/edit-class', methods=['GET', 'POST'])
        @login_required
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

        @app.route('/student/<int:student_id>/report')
        @login_required
        def student_report(student_id):
            student = Student.query.get_or_404(student_id)
            return render_template('reports/student_report.html', student=student)

        @app.route('/classes')
        @login_required
        def classes():
            classes = Class.query.all()
            form = ClassForm()
            return render_template('classes/index.html', classes=classes, form=form)

        @app.route('/classes/create', methods=['POST'])
        @login_required
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
        def teachers():
            teachers = Teacher.query.all()
            form = TeacherForm()
            return render_template('teachers/index.html', teachers=teachers, form=form)

        @app.route('/teachers/create', methods=['POST'])
        @login_required
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
        def delete_multiple_teachers():
            teacher_ids = request.form.getlist('teacher_ids')
            if teacher_ids:
                Teacher.query.filter(Teacher.id.in_(teacher_ids)).delete(synchronize_session=False)
                db.session.commit()
                flash(f'{len(teacher_ids)} professores deletados com sucesso!', 'success')
            return redirect(url_for('teachers'))

        @app.route('/admin')
        @login_required
        def admin():
            users = User.query.all()
            form = UserForm()
            return render_template('admin/index.html', users=users, form=form)

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
            # Implementação básica de exportação
            students = Student.query.all()
            # Por enquanto, apenas redireciona de volta
            flash('Funcionalidade de exportação em desenvolvimento.', 'info')
            return redirect(url_for('students'))

        @app.route('/upload-preview', methods=['POST'])
        @login_required
        def upload_preview():
            # Implementação básica de preview
            return jsonify({'success': True, 'message': 'Preview em desenvolvimento'})

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
                default_layout_path = os.path.join('static', 'default_certificate_layout.json')
                
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

        @app.route('/api/alunos/deletar-multiplos', methods=['POST'])
        @login_required
        def deletar_multiplos_alunos():
            try:
                data = request.get_json()
                student_ids = data.get('student_ids', [])
                
                if not student_ids:
                    return jsonify({'error': 'Nenhum aluno selecionado'}), 400
                
                students = Student.query.filter(Student.id.in_(student_ids)).all()
                for student in students:
                    db.session.delete(student)
                
                db.session.commit()
                
                return jsonify({'success': True, 'message': f'{len(students)} alunos deletados com sucesso'})
            except Exception as e:
                return jsonify({'error': f'Erro ao deletar alunos: {str(e)}'}), 500

        @app.route('/update_student_teacher', methods=['POST'])
        @login_required
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
                data = request.get_json()
                print(f"🔍 Dados recebidos: {data}")
                
                student_id = data.get('student_id')
                positions = data.get('positions')
                colors = data.get('colors', {})
                certificate_date = data.get('certificate_date')  # Nova data personalizada
                
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
                    student_layout.positions = json.dumps(positions)
                    student_layout.colors = json.dumps(colors)
                    if certificate_date:
                        student_layout.certificate_date = certificate_date
                    student_layout.updated_at = datetime.utcnow()
                else:
                    # Criar novo layout
                    student_layout = StudentCertificateLayout(
                        student_id=student_id,
                        positions=json.dumps(positions),
                        colors=json.dumps(colors),
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
                data = request.get_json()
                student_id = data.get('student_id')
                colors = data.get('colors')
                
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
                
                default_layout_path = os.path.join('static', 'default_certificate_layout.json')
                
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
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Servidor iniciando na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
