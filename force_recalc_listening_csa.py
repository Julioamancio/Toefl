import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from models import db, Student
from listening_csa import compute_listening_csa
from app import create_app

def force_recalculate_all_listening_csa():
    """
    Força o recálculo de TODOS os valores de Listening CSA no banco de dados
    """
    print("=== FORÇANDO RECÁLCULO DE TODOS OS LISTENING CSA ===")
    
    # Buscar todos os estudantes com listening score
    students = Student.query.filter(Student.listening.isnot(None)).all()
    
    print(f"📊 Encontrados {len(students)} estudantes com listening score")
    
    updated_count = 0
    error_count = 0
    
    for student in students:
        try:
            # Calcular o CSA correto
            result = compute_listening_csa(student.turma_meta, student.listening)
            correct_csa = result.get('points', 0.0)
            
            # Verificar se precisa atualizar
            if student.listening_csa_points != correct_csa:
                old_value = student.listening_csa_points
                student.listening_csa_points = correct_csa
                
                print(f"🔄 {student.name}: {old_value} → {correct_csa} (Turma: {student.turma_meta}, Listening: {student.listening})")
                updated_count += 1
            
        except Exception as e:
            print(f"❌ ERRO ao processar {student.name}: {e}")
            error_count += 1
    
    # Salvar todas as mudanças
    try:
        db.session.commit()
        print(f"\n✅ RECÁLCULO CONCLUÍDO!")
        print(f"   📈 Estudantes atualizados: {updated_count}")
        print(f"   ❌ Erros encontrados: {error_count}")
        print(f"   📊 Total processados: {len(students)}")
        
        # Verificar alguns casos específicos
        print("\n=== VERIFICAÇÃO DOS CASOS DA TELA ===")
        test_names = [
            "Cheloni Alice T",
            "Cozzi Gabriela C", 
            "De Morais Santana E S",
            "De Souza Juan F",
            "De Souza Livia D",
            "Fernandes Henrique",
            "Junqueira Gabriel S",
            "Padua M Rafaela Daros",
            "Soares Marina O F"
        ]
        
        for name in test_names:
            student = Student.query.filter(Student.name.like(f"%{name}%")).first()
            if student:
                result = compute_listening_csa(student.turma_meta, student.listening)
                expected_csa = result.get('points', 0.0)
                print(f"✅ {student.name}: Listening={student.listening}, Turma={student.turma_meta}, CSA={student.listening_csa_points} (esperado: {expected_csa})")
            else:
                print(f"❌ Não encontrado: {name}")
                
    except Exception as e:
        db.session.rollback()
        print(f"❌ ERRO ao salvar no banco: {e}")

if __name__ == "__main__":
    # Criar a aplicação Flask
    app, csrf = create_app()
    
    with app.app_context():
        force_recalculate_all_listening_csa()