from app import create_app
from app.models import db, Role, User

app = create_app()

with app.app_context():
    # Create roles
    roles = ['Admin', 'Editor', 'User']
    for role_name in roles:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name)
            db.session.add(role)

    # Create admin user
    admin_user = User.query.filter_by(email='admin@example.com').first()
    if not admin_user:
        admin_user = User(username='admin', email='admin@example.com')
        admin_user.set_password('adminpassword') 
        admin_role = Role.query.filter_by(name='Admin').first()
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)

    db.session.commit()
    print("Roles and admin user initialized.")
