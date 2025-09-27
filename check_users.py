from app import app
from models import User, db

with app.app_context():
    users = User.query.all()
    print(f'Total de usuários: {len(users)}')
    for u in users:
        print(f'- {u.username} (admin: {u.is_admin}, ativo: {u.is_active})')
    
    if len(users) == 0:
        print("Nenhum usuário encontrado. Criando usuário admin...")
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True,
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado com sucesso!")