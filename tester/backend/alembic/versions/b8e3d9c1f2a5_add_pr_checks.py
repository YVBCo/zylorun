"""add pr checks table

Revision ID: b8e3d9c1f2a5
Revises: a7f2c8d9e1b4
Create Date: 2026-10-12 20:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8e3d9c1f2a5'
down_revision: Union[str, Sequence[str], None] = 'a7f2c8d9e1b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pull_request_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=True),
        sa.Column('base_sha', sa.String(), nullable=True),
        sa.Column('head_sha', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='QUEUED'),
        sa.Column('conclusion', sa.String(), nullable=True),
        sa.Column('policy_decision', sa.String(), nullable=True),
        sa.Column('coverage_status', sa.String(), nullable=True),
        sa.Column('newly_introduced_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('resolved_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('summary_markdown', sa.Text(), nullable=True),
        sa.Column('github_check_run_id', sa.String(), nullable=True),
        sa.Column('details_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pull_request_checks_id'), 'pull_request_checks', ['id'], unique=False)
    op.create_index(op.f('ix_pull_request_checks_repository_id'), 'pull_request_checks', ['repository_id'], unique=False)
    op.create_index(op.f('ix_pull_request_checks_head_sha'), 'pull_request_checks', ['head_sha'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pull_request_checks_head_sha'), table_name='pull_request_checks')
    op.drop_index(op.f('ix_pull_request_checks_repository_id'), table_name='pull_request_checks')
    op.drop_index(op.f('ix_pull_request_checks_id'), table_name='pull_request_checks')
    op.drop_table('pull_request_checks')
