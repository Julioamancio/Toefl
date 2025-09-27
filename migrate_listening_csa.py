"""
Script de migração para adicionar campo listening_csa_points e calcular valores existentes
"""

from app import app
from models import db, Student
from listening_csa import compute_listening_csa

def migrate_listening_csa():
    """
    Migra o banco de dados para incluir listening_csa_points e calcula valores para estudantes existentes
    """
    with app.app_context():
        print("Iniciando migração do Listening CSA...")
        
        # Criar as tabelas (incluindo a nova coluna)
        db.create_all()
        print("✓ Tabelas atualizadas")
        
        # Buscar todos os estudantes
        students = Student.query.all()
        print(f"Encontrados {len(students)} estudantes para processar")
        
        updated_count = 0
        error_count = 0
        
        for student in students:
            try:
                # Verificar se temos os dados necessários
                if student.class_info and student.class_info.meta_label and student.listening is not None:
                    rotulo_escolar = float(student.class_info.meta_label)
                    csa_result = compute_listening_csa(rotulo_escolar, student.listening)
                    student.listening_csa_points = csa_result['points']
                    updated_count += 1
                    
                    if updated_count % 50 == 0:
                        print(f"Processados {updated_count} estudantes...")
                        
                else:
                    # Estudante sem dados suficientes
                    student.listening_csa_points = None
                    
            except Exception as e:
                print(f"Erro ao processar estudante {student.name} (ID: {student.id}): {e}")
                student.listening_csa_points = None
                error_count += 1
        
        # Salvar todas as alterações
        try:
            db.session.commit()
            print(f"✓ Migração concluída com sucesso!")
            print(f"  - {updated_count} estudantes com listening_csa_points calculado")
            print(f"  - {len(students) - updated_count} estudantes sem dados suficientes")
            if error_count > 0:
                print(f"  - {error_count} erros encontrados")
                
        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao salvar alterações: {e}")
            return False
            
        return True

if __name__ == "__main__":
    success = migrate_listening_csa()
    if success:
        print("\n🎉 Migração do Listening CSA concluída com sucesso!")
    else:
        print("\n❌ Falha na migração do Listening CSA")