"""add pr gate policy fields

Revision ID: a7f2c8d9e1b4
Revises: f3a9b7c21d4e
Create Date: 2026-10-12 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7f2c8d9e1b4'
down_revision: Union[str, Sequence[str], None] = 'f3a9b7c21d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('repositories', sa.Column('pr_gate_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('repositories', sa.Column('pr_gate_block_critical', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('repositories', sa.Column('pr_gate_block_high', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('repositories', sa.Column('pr_gate_block_medium', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('repositories', sa.Column('pr_gate_block_incomplete', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade() -> None:
    op.drop_column('repositories', 'pr_gate_block_incomplete')
    op.drop_column('repositories', 'pr_gate_block_medium')
    op.drop_column('repositories', 'pr_gate_block_high')
    op.drop_column('repositories', 'pr_gate_block_critical')
    op.drop_column('repositories', 'pr_gate_enabled')
