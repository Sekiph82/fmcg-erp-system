"""two_factor_auth

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    twofamethod = postgresql.ENUM('totp', 'sms', 'email', name='twofamethod')
    twofamethod.create(op.get_bind(), checkfirst=True)

    twofasessionstatus = postgresql.ENUM(
        'pending', 'verified', 'expired', 'failed',
        name='twofasessionstatus',
    )
    twofasessionstatus.create(op.get_bind(), checkfirst=True)

    # ── user_2fa_settings ─────────────────────────────────────────────────────
    op.create_table(
        'user_2fa_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('method', sa.Enum('totp', 'sms', 'email', name='twofamethod'), nullable=False, server_default='totp'),
        sa.Column('secret_key', sa.String(64), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_user_2fa_settings_user_id', 'user_2fa_settings', ['user_id'])

    # ── two_fa_sessions ───────────────────────────────────────────────────────
    op.create_table(
        'two_fa_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('settings_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_2fa_settings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('challenge_code', sa.String(10), nullable=True),
        sa.Column('method', sa.Enum('totp', 'sms', 'email', name='twofamethod'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Enum('pending', 'verified', 'expired', 'failed', name='twofasessionstatus'), nullable=False, server_default='pending'),
        sa.Column('attempt_count', sa.String(3), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_two_fa_sessions_user_id', 'two_fa_sessions', ['user_id'])

    # ── recovery_codes ────────────────────────────────────────────────────────
    op.create_table(
        'recovery_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('settings_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_2fa_settings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code_hash', sa.String(255), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_recovery_codes_user_id', 'recovery_codes', ['user_id'])


def downgrade() -> None:
    op.drop_table('recovery_codes')
    op.drop_table('two_fa_sessions')
    op.drop_table('user_2fa_settings')

    op.execute("DROP TYPE IF EXISTS twofasessionstatus")
    op.execute("DROP TYPE IF EXISTS twofamethod")
