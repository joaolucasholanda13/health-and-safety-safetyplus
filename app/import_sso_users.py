"""Importa usuários em massa para o login único (SSO).

Uso (dentro do container web):
    python -m app.import_sso_users arquivo.csv            # simulação, não grava nada
    python -m app.import_sso_users arquivo.csv --apply    # grava

Arquivo .csv (UTF-8, separador ; ou ,) ou .xlsx, com cabeçalho:
    email   (obrigatório; vira o username, em minúsculas)
    nome    (obrigatório)
    perfil  (opcional: Usuário, Administrador ou Super Administrador; padrão Usuário)
    escopos (obrigatório para Administrador: "Cluster|Site;Cluster|Site")

Cada usuário recebe uma senha aleatória que ninguém conhece: entra só pelo SSO
(o administrador pode redefinir a senha depois, se necessário).
Usuários já existentes nunca são alterados; ficam no relatório.
"""
from __future__ import annotations

import argparse
import csv
import re
import secrets
import sys
from pathlib import Path

from .database import Base, engine, SessionLocal, User, UserScope, AuditLog
from .module_configs import SEPARATE_CLUSTER_SITES
from .security import hash_password

ROLE_USER = 'Usuário'
ROLE_ADMIN = 'Administrador'
ROLE_SUPER_ADMIN = 'Super Administrador'
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
ALIASES = {
    'email': {'email', 'e-mail', 'mail', 'username', 'usuario', 'usuário', 'upn'},
    'nome': {'nome', 'name', 'nome completo', 'full_name', 'displayname'},
    'perfil': {'perfil', 'role', 'papel'},
    'escopos': {'escopos', 'escopo', 'cluster/site', 'scopes'},
}


def _norm(text) -> str:
    return str(text or '').strip()


def read_rows(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == '.xlsx':
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True, data_only=True).active
        matrix = [[_norm(c) for c in row] for row in ws.iter_rows(values_only=True)]
    else:
        text = path.read_text(encoding='utf-8-sig')
        dialect = csv.excel_tab if '\t' in text.splitlines()[0] else (
            csv.excel if text.splitlines()[0].count(',') > text.splitlines()[0].count(';') else None)
        reader = csv.reader(text.splitlines(), dialect) if dialect else csv.reader(text.splitlines(), delimiter=';')
        matrix = [[_norm(c) for c in row] for row in reader]
    matrix = [r for r in matrix if any(r)]
    if not matrix:
        return []
    header = {}
    for i, col in enumerate(matrix[0]):
        for key, names in ALIASES.items():
            if col.lower() in names and key not in header:
                header[key] = i
    missing = [k for k in ('email', 'nome') if k not in header]
    if missing:
        raise SystemExit(f'Colunas obrigatórias ausentes no cabeçalho: {", ".join(missing)}')
    rows = []
    for n, r in enumerate(matrix[1:], start=2):
        rows.append({'_linha': str(n), **{k: (r[i] if i < len(r) else '') for k, i in header.items()}})
    return rows


def parse_scopes(raw: str) -> tuple[list[tuple[str, str]], list[str]]:
    pairs, bad = [], []
    for item in filter(None, (s.strip() for s in raw.split(';'))):
        cluster, _, site = item.partition('|')
        cluster, site = cluster.strip(), site.strip()
        if cluster in SEPARATE_CLUSTER_SITES and site in SEPARATE_CLUSTER_SITES[cluster]:
            if (cluster, site) not in pairs:
                pairs.append((cluster, site))
        else:
            bad.append(item)
    return pairs, bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('arquivo')
    ap.add_argument('--apply', action='store_true', help='grava no banco (sem isso, só simula)')
    args = ap.parse_args()

    rows = read_rows(Path(args.arquivo))
    Base.metadata.create_all(engine)
    to_create, skipped, errors, same_name = [], [], [], []
    seen: set[str] = set()

    with SessionLocal() as db:
        existing = {u.username.lower(): u for u in db.query(User).all()}
        by_name: dict[str, list[User]] = {}
        for u in existing.values():
            by_name.setdefault(u.full_name.strip().lower(), []).append(u)

        for r in rows:
            ln, email, nome = r['_linha'], r['email'].lower(), r['nome']
            role = r.get('perfil') or ROLE_USER
            if not EMAIL_RE.match(email):
                errors.append((ln, email or '(vazio)', 'e-mail inválido')); continue
            if not nome:
                errors.append((ln, email, 'nome vazio')); continue
            if role not in {ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN}:
                errors.append((ln, email, f'perfil inválido: {role}')); continue
            pairs, bad = parse_scopes(r.get('escopos', ''))
            if bad:
                errors.append((ln, email, f'escopo inexistente: {"; ".join(bad)}')); continue
            if role == ROLE_ADMIN and not pairs:
                errors.append((ln, email, 'Administrador exige escopos (Cluster|Site)')); continue
            if email in seen:
                errors.append((ln, email, 'e-mail repetido no arquivo')); continue
            seen.add(email)
            if email in existing:
                skipped.append((ln, email)); continue
            for other in by_name.get(nome.lower(), []):
                same_name.append((ln, email, other.username))
            to_create.append((email, nome, role, pairs))

        if args.apply:
            for email, nome, role, pairs in to_create:
                u = User(username=email, full_name=nome, role=role, active=True,
                         password_hash=hash_password(secrets.token_urlsafe(32)))
                db.add(u)
                db.flush()
                if role == ROLE_ADMIN:
                    for cluster, site in pairs:
                        db.add(UserScope(user_id=u.id, cluster=cluster, site=site))
                db.add(AuditLog(user_id=None, action='criar_usuario',
                                detail=f'{email} | perfil={role} | escopos={len(pairs)} | importação SSO em massa'))
            db.commit()

    modo = 'GRAVADO' if args.apply else 'SIMULAÇÃO (nada foi gravado; use --apply)'
    print(f'== {modo} ==')
    print(f'Linhas lidas: {len(rows)} | a criar: {len(to_create)} | já existem: {len(skipped)} | com erro: {len(errors)}')
    for ln, email in skipped:
        print(f'  [já existe] linha {ln}: {email}')
    for ln, email, other in same_name:
        print(f'  [ATENÇÃO] linha {ln}: {email} tem o mesmo nome do usuário "{other}" (possível duplicidade; '
              f'se for a mesma pessoa, troque o username dele para o e-mail em vez de criar outro)')
    for ln, email, msg in errors:
        print(f'  [erro] linha {ln}: {email}: {msg}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
