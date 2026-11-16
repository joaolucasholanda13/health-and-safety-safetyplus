from __future__ import annotations
import getpass
import os
import sys
from pathlib import Path
from .database import Base, engine, SessionLocal, User
from .security import hash_password, revoke_password_sessions

ROLE_DEV = 'DEV'

def main():
    """Cria ou atualiza o usuário externo de DEV (oculto nas listagens do sistema).

    Uso: python -m app.create_ti_user <login> [nome]
    A senha vem de TI_PASSWORD ou é pedida no terminal.
    """
    if len(sys.argv) < 2:
        raise SystemExit('Uso: python -m app.create_ti_user <login> [nome]')
    username = sys.argv[1].strip()
    name = sys.argv[2].strip() if len(sys.argv) > 2 else 'DEV'
    password = os.getenv('TI_PASSWORD') or getpass.getpass('Senha do usuário DEV: ')
    if len(password) < 8:
        raise SystemExit('A senha deve ter pelo menos 8 caracteres.')
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        u = db.query(User).filter(User.username == username).first()
        if u and u.role != ROLE_DEV:
            raise SystemExit('Já existe um usuário comum com esse login.')
        reset_existing = u is not None
        if not u:
            u = User(username=username)
            db.add(u)
        u.full_name = name
        u.password_hash = hash_password(password)
        u.role = ROLE_DEV
        u.active = True
        db.commit()
        user_id = u.id
    if reset_existing:
        storage = Path(os.getenv('STORAGE_DIR', str(Path(__file__).resolve().parent.parent / 'storage'))).resolve()
        storage.mkdir(parents=True, exist_ok=True)
        revoke_password_sessions(storage, user_id)
    print(f'Usuário DEV pronto: {username}')

if __name__ == '__main__':
    main()
