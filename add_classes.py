#!/usr/bin/env python3
"""
Script para adicionar turmas 6° ano A-H e 9° ano A-G ao sistema TOEFL
"""

from app import app
from models import db, Class

def add_classes():
    """Adiciona as turmas necessárias ao banco de dados"""
    
    # Lista de turmas para adicionar
    classes_to_add = []
    
    # 6° ano A até H (8 turmas)
    for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
        class_name = f"6° ano {letter}"
        classes_to_add.append({
            'name': class_name,
            'description': f'Turma do {class_name}',
            'is_active': True
        })
    
    # 9° ano A até G (7 turmas)
    for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        class_name = f"9° ano {letter}"
        classes_to_add.append({
            'name': class_name,
            'description': f'Turma do {class_name}',
            'is_active': True
        })
    
    with app.app_context():
        added_count = 0
        skipped_count = 0
        
        for class_data in classes_to_add:
            # Verificar se a turma já existe
            existing_class = Class.query.filter_by(name=class_data['name']).first()
            
            if existing_class:
                print(f"Turma '{class_data['name']}' já existe. Pulando...")
                skipped_count += 1
                continue
            
            # Criar nova turma
            new_class = Class(
                name=class_data['name'],
                description=class_data['description'],
                is_active=class_data['is_active']
            )
            
            db.session.add(new_class)
            print(f"Adicionando turma: {class_data['name']}")
            added_count += 1
        
        try:
            db.session.commit()
            print(f"\n✅ Sucesso! {added_count} turmas adicionadas.")
            if skipped_count > 0:
                print(f"📝 {skipped_count} turmas já existiam e foram puladas.")
            
            # Listar todas as turmas criadas
            print("\n📋 Turmas adicionadas:")
            for class_data in classes_to_add:
                class_obj = Class.query.filter_by(name=class_data['name']).first()
                if class_obj:
                    status = "✅ Ativa" if class_obj.is_active else "❌ Inativa"
                    print(f"  - {class_obj.name} (ID: {class_obj.id}) - {status}")
                    
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar turmas: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("🏫 Adicionando turmas ao sistema TOEFL...")
    print("=" * 50)
    
    success = add_classes()
    
    if success:
        print("\n🎉 Processo concluído com sucesso!")
        print("Você pode agora acessar http://127.0.0.1:5000/turmas para ver as turmas.")
    else:
        print("\n❌ Processo falhou. Verifique os erros acima.")