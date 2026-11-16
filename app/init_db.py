from __future__ import annotations
import os
from .database import Base, engine, SessionLocal, User
from .security import hash_password

def main():
    Base.metadata.create_all(engine)
    from .database import ensure_audit_columns
    ensure_audit_columns(engine)
    from sqlalchemy import text, inspect as _inspect
    try:
        if 'photo_path' not in {c['name'] for c in _inspect(engine).get_columns('users')}:
            with engine.begin() as _c: _c.execute(text("ALTER TABLE users ADD COLUMN photo_path VARCHAR(300) DEFAULT ''"))
    except Exception as e: print(f'[init_db] photo_path: {e}')
    # Índices para listagens/históricos com muitos documentos e usuários (idempotente).
    with engine.begin() as conn:
        for stmt in (
            'CREATE INDEX IF NOT EXISTS ix_documents_created_by_updated ON documents (created_by, updated_at)',
            'CREATE INDEX IF NOT EXISTS ix_documents_kind_status ON documents (kind, status)',
            'CREATE INDEX IF NOT EXISTS ix_documents_updated_at ON documents (updated_at)',
        ):
            try: conn.execute(text(stmt))
            except Exception as e: print(f'[init_db] índice ignorado: {e}')
    admin_user = os.getenv('ADMIN_USER', 'admin').strip() or 'admin'
    admin_pass = (os.getenv('ADMIN_PASSWORD') or '').strip()
    admin_name = os.getenv('ADMIN_NAME', 'Administrador')
    with SessionLocal() as db:
        if db.query(User).count() == 0:
            if not admin_pass or len(admin_pass) < 8:
                raise RuntimeError('ADMIN_PASSWORD é obrigatório e deve ter pelo menos 8 caracteres na primeira inicialização.')
            if os.getenv('SECURE_COOKIES','false').lower()=='true' and admin_pass.lower() in {'admin123','password','12345678'}:
                raise RuntimeError('ADMIN_PASSWORD insegura detectada. Defina uma senha inicial forte no .env.')
            db.add(User(username=admin_user, full_name=admin_name, password_hash=hash_password(admin_pass), role='Super Administrador', active=True))
            db.commit()
            print(f'[Checklist Serena] Super Administrador inicial criado: {admin_user}')

if __name__ == '__main__':
    main()
