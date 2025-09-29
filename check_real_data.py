import sqlite3
import os

# Verificar se o banco existe
db_path = 'toefl_dashboard.db'
if not os.path.exists(db_path):
    print(f"❌ Banco de dados não encontrado: {db_path}")
    exit(1)

print(f"✅ Banco encontrado: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Listar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"📋 Tabelas encontradas: {tables}")
    
    if not tables:
        print("❌ Nenhuma tabela encontrada no banco!")
        conn.close()
        exit(1)
    
    # Verificar tabela de estudantes (pode ser 'student' ou 'students')
    student_table = None
    for table in tables:
        if 'student' in table.lower():
            student_table = table
            break
    
    if not student_table:
        print("❌ Tabela de estudantes não encontrada!")
        conn.close()
        exit(1)
    
    print(f"👥 Tabela de estudantes: {student_table}")
    
    # Contar estudantes
    cursor.execute(f"SELECT COUNT(*) FROM {student_table}")
    count = cursor.fetchone()[0]
    print(f"📊 Total de estudantes: {count}")
    
    if count > 0:
        # Mostrar alguns estudantes
        cursor.execute(f"SELECT id, name FROM {student_table} LIMIT 5")
        students = cursor.fetchall()
        print("👤 Primeiros estudantes:")
        for student in students:
            print(f"  ID: {student[0]}, Nome: {student[1]}")
    else:
        print("❌ Nenhum estudante encontrado no banco!")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Erro ao acessar banco: {e}")