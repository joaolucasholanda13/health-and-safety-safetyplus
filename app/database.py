from __future__ import annotations
import os
from datetime import datetime
from sqlalchemy import create_engine, String, Integer, Boolean, DateTime, Text, ForeignKey, event, insert, select, delete
from .audit_context import metadata as audit_metadata
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./storage/checklist_serena.db')
if DATABASE_URL.startswith('sqlite:///') and ':memory:' not in DATABASE_URL:
    # Instalação limpa (ex.: zip sem a pasta storage): cria a pasta do banco SQLite.
    from pathlib import Path as _P
    _P(DATABASE_URL.replace('sqlite:///', '', 1)).expanduser().parent.mkdir(parents=True, exist_ok=True)
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
_pool_args = {} if DATABASE_URL.startswith('sqlite') else {'pool_size': int(os.getenv('DB_POOL_SIZE', '20')), 'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')), 'pool_recycle': 1800}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=connect_args, **_pool_args)


def configure_sqlite_foreign_keys(target_engine) -> None:
    """Ativa a integridade referencial em cada conexão SQLite do engine."""
    if target_engine.dialect.name != 'sqlite':
        return

    def enable_foreign_keys(dbapi_connection, _connection_record):
        # Python 3.12 também permite conexões com autocommit=False, nas quais
        # PRAGMA foreign_keys só tem efeito fora de uma transação.
        has_autocommit = hasattr(dbapi_connection, 'autocommit')
        if has_autocommit:
            previous_autocommit = dbapi_connection.autocommit
            dbapi_connection.autocommit = True
        try:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute('PRAGMA foreign_keys=ON')
            finally:
                cursor.close()
        finally:
            if has_autocommit:
                dbapi_connection.autocommit = previous_autocommit

    event.listen(target_engine, 'connect', enable_foreign_keys)


configure_sqlite_foreign_keys(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), default='')
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default='Usuário')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    photo_path: Mapped[str] = mapped_column(String(300), default='', server_default='')


class UserScope(Base):
    __tablename__ = 'user_scopes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    cluster: Mapped[str] = mapped_column(String(120), default='', index=True)
    site: Mapped[str] = mapped_column(String(160), default='', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Company(Base):
    __tablename__ = 'companies'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Participant(Base):
    __tablename__ = 'participants'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180), index=True)
    job_title: Mapped[str] = mapped_column(String(140), default='')
    cluster: Mapped[str] = mapped_column(String(120), default='', server_default='')
    site: Mapped[str] = mapped_column(String(160), default='', server_default='')
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default='Rascunho', index=True)
    cluster: Mapped[str] = mapped_column(String(120), default='')
    site: Mapped[str] = mapped_column(String(160), default='')
    activity: Mapped[str] = mapped_column(Text, default='')
    data_json: Mapped[str] = mapped_column(Text, default='{}')
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id'), index=True)
    kind: Mapped[str] = mapped_column(String(60), default='apr_approval', index=True)
    message: Mapped[str] = mapped_column(Text, default='')
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PushSubscription(Base):
    __tablename__ = 'push_subscriptions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, default='')
    auth: Mapped[str] = mapped_column(Text, default='')
    user_agent: Mapped[str] = mapped_column(Text, default='')
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default='')

class CloudConnection(Base):
    __tablename__ = 'cloud_connections'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), unique=True, index=True, default='onedrive')
    tenant: Mapped[str] = mapped_column(String(120), default='common')
    client_id: Mapped[str] = mapped_column(String(200), default='')
    client_secret_enc: Mapped[str] = mapped_column(Text, default='')
    access_token_enc: Mapped[str] = mapped_column(Text, default='')
    refresh_token_enc: Mapped[str] = mapped_column(Text, default='')
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    folder_path: Mapped[str] = mapped_column(String(300), default='Checklist Serena')
    account_name: Mapped[str] = mapped_column(String(200), default='')
    account_email: Mapped[str] = mapped_column(String(200), default='')
    drive_id: Mapped[str] = mapped_column(String(200), default='')
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default='')


class SnowflakeSyncState(Base):
    __tablename__ = 'snowflake_sync_states'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default='Pendente', index=True)
    remote_path: Mapped[str] = mapped_column(String(700), default='')
    snapshot_code: Mapped[str] = mapped_column(String(100), default='')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    document_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    ip_address: Mapped[str] = mapped_column(String(45), default=lambda: audit_metadata()['ip_address'], server_default='')
    user_agent: Mapped[str] = mapped_column(String(400), default=lambda: audit_metadata()['user_agent'], server_default='')
    http_method: Mapped[str] = mapped_column(String(10), default=lambda: audit_metadata()['http_method'], server_default='')
    request_path: Mapped[str] = mapped_column(String(250), default=lambda: audit_metadata()['request_path'], server_default='')
    request_id: Mapped[str] = mapped_column(String(32), default=lambda: audit_metadata()['request_id'], server_default='')
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DocumentVersion(Base):
    """Foto do documento antes de cada alteração (histórico para o DEV desfazer)."""
    __tablename__ = 'document_versions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(30), default='')
    title: Mapped[str] = mapped_column(String(120), default='')
    cluster: Mapped[str] = mapped_column(String(120), default='')
    site: Mapped[str] = mapped_column(String(160), default='')
    activity: Mapped[str] = mapped_column(Text, default='')
    data_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

DOCUMENT_VERSION_LIMIT = 30
_VERSIONED = ('status', 'title', 'cluster', 'site', 'activity', 'data_json')

@event.listens_for(Document, 'before_update')
def _snapshot_document(mapper, connection, target):
    from sqlalchemy import inspect as _inspect
    state = _inspect(target)
    changed = False
    old = {}
    for name in _VERSIONED:
        hist = getattr(state.attrs, name).history
        if hist.has_changes() and hist.deleted:
            changed = True
            old[name] = hist.deleted[0]
        else:
            old[name] = getattr(target, name)
    if not changed:
        return
    vt = DocumentVersion.__table__
    connection.execute(insert(vt).values(document_id=target.id, created_at=datetime.utcnow(), **{k: (v or '') for k, v in old.items()}))
    keep = connection.execute(select(vt.c.id).where(vt.c.document_id == target.id).order_by(vt.c.id.desc()).limit(DOCUMENT_VERSION_LIMIT)).fetchall()
    if len(keep) >= DOCUMENT_VERSION_LIMIT:
        connection.execute(delete(vt).where(vt.c.document_id == target.id, vt.c.id < keep[-1][0]))


def ensure_audit_columns(target_engine):
    """Migração aditiva e idempotente para SQLite e PostgreSQL existentes."""
    from sqlalchemy import inspect, text
    columns = {c['name'] for c in inspect(target_engine).get_columns('audit_logs')}
    with target_engine.begin() as conn:
        for name, size in [('ip_address',45),('user_agent',400),('http_method',10),('request_path',250),('request_id',32)]:
            if name not in columns:
                conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {name} VARCHAR({size}) NOT NULL DEFAULT ''"))
