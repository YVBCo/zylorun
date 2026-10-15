"""add command runner and targets tables

Revision ID: f7b8c9d0e1f2
Revises: e4f5a6b7c8d9
Create Date: 2026-10-15 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add role to users table if not exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    if 'role' not in user_columns:
        op.add_column('users', sa.Column('role', sa.String(), server_default='Analyst', nullable=False))

    # 2. Create targets table
    tables = inspector.get_table_names()
    if 'targets' not in tables:
        op.create_table(
            'targets',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('host', sa.String(), nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_targets_id'), 'targets', ['id'], unique=False)
        op.create_index(op.f('ix_targets_name'), 'targets', ['name'], unique=False)
        op.create_index(op.f('ix_targets_user_id'), 'targets', ['user_id'], unique=False)

    # 3. Create command_configs table
    if 'command_configs' not in tables:
        op.create_table(
            'command_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('executable', sa.String(), nullable=False),
            sa.Column('allowed_args', sa.Text(), server_default='[]', nullable=False),
            sa.Column('timeout_seconds', sa.Integer(), server_default='60', nullable=False),
            sa.Column('regex_rules', sa.Text(), server_default='{}', nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index(op.f('ix_command_configs_id'), 'command_configs', ['id'], unique=False)
        op.create_index(op.f('ix_command_configs_name'), 'command_configs', ['name'], unique=True)

    # 4. Create run_history table
    if 'run_history' not in tables:
        op.create_table(
            'run_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('command_id', sa.Integer(), nullable=False),
            sa.Column('target_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(), server_default='Pending', nullable=False),
            sa.Column('start_time', sa.DateTime(), nullable=True),
            sa.Column('end_time', sa.DateTime(), nullable=True),
            sa.Column('raw_output', sa.Text(), nullable=True),
            sa.Column('findings', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['command_id'], ['command_configs.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['target_id'], ['targets.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_run_history_id'), 'run_history', ['id'], unique=False)
        op.create_index(op.f('ix_run_history_command_id'), 'run_history', ['command_id'], unique=False)
        op.create_index(op.f('ix_run_history_target_id'), 'run_history', ['target_id'], unique=False)
        op.create_index(op.f('ix_run_history_user_id'), 'run_history', ['user_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'run_history' in tables:
        op.drop_index(op.f('ix_run_history_user_id'), table_name='run_history')
        op.drop_index(op.f('ix_run_history_target_id'), table_name='run_history')
        op.drop_index(op.f('ix_run_history_command_id'), table_name='run_history')
        op.drop_index(op.f('ix_run_history_id'), table_name='run_history')
        op.drop_table('run_history')

    if 'command_configs' in tables:
        op.drop_index(op.f('ix_command_configs_name'), table_name='command_configs')
        op.drop_index(op.f('ix_command_configs_id'), table_name='command_configs')
        op.drop_table('command_configs')

    if 'targets' in tables:
        op.drop_index(op.f('ix_targets_user_id'), table_name='targets')
        op.drop_index(op.f('ix_targets_name'), table_name='targets')
        op.drop_index(op.f('ix_targets_id'), table_name='targets')
        op.drop_table('targets')

    if 'users' in tables:
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        if 'role' in user_columns:
            op.drop_column('users', 'role')
