"""add project hub core tables

Revision ID: e4f5a6b7c8d9
Revises: b8e3d9c1f2a5
Create Date: 2026-10-13 06:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'b8e3d9c1f2a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add ai_enabled flag to repositories
    op.add_column('repositories', sa.Column('ai_enabled', sa.Boolean(), server_default='1', nullable=False))

    # 2. repository_indexes
    op.create_table(
        'repository_indexes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('commit_sha', sa.String(), nullable=False),
        sa.Column('file_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('languages_json', sa.Text(), server_default='{}', nullable=True),
        sa.Column('frameworks_json', sa.Text(), server_default='[]', nullable=True),
        sa.Column('entry_points_json', sa.Text(), server_default='[]', nullable=True),
        sa.Column('module_map_json', sa.Text(), server_default='{}', nullable=True),
        sa.Column('routes_json', sa.Text(), server_default='[]', nullable=True),
        sa.Column('models_json', sa.Text(), server_default='[]', nullable=True),
        sa.Column('tests_json', sa.Text(), server_default='[]', nullable=True),
        sa.Column('dependencies_json', sa.Text(), server_default='[]', nullable=True),
        sa.Column('ci_cd_json', sa.Text(), server_default='[]', nullable=True),
        sa.Column('indexed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repository_indexes_id'), 'repository_indexes', ['id'], unique=False)
    op.create_index(op.f('ix_repository_indexes_repository_id'), 'repository_indexes', ['repository_id'], unique=False)
    op.create_index(op.f('ix_repository_indexes_commit_sha'), 'repository_indexes', ['commit_sha'], unique=False)

    # 3. analyzer_runs
    op.create_table(
        'analyzer_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('commit_sha', sa.String(), nullable=False),
        sa.Column('analyzer_name', sa.String(), nullable=False),
        sa.Column('analyzer_version', sa.String(), server_default='1.0.0', nullable=True),
        sa.Column('status', sa.String(), server_default='QUEUED', nullable=False),
        sa.Column('coverage_status', sa.String(), server_default='FULL', nullable=True),
        sa.Column('files_analyzed', sa.Integer(), server_default='0', nullable=True),
        sa.Column('duration_seconds', sa.Integer(), server_default='0', nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('findings_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('details_json', sa.Text(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analyzer_runs_id'), 'analyzer_runs', ['id'], unique=False)
    op.create_index(op.f('ix_analyzer_runs_repository_id'), 'analyzer_runs', ['repository_id'], unique=False)
    op.create_index(op.f('ix_analyzer_runs_commit_sha'), 'analyzer_runs', ['commit_sha'], unique=False)
    op.create_index(op.f('ix_analyzer_runs_analyzer_name'), 'analyzer_runs', ['analyzer_name'], unique=False)

    # 4. project_memories
    op.create_table(
        'project_memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(), server_default='NOTE', nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('reference_commit_sha', sa.String(), nullable=True),
        sa.Column('reference_file', sa.String(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_memories_id'), 'project_memories', ['id'], unique=False)
    op.create_index(op.f('ix_project_memories_repository_id'), 'project_memories', ['repository_id'], unique=False)

    # 5. repository_issues
    op.create_table(
        'repository_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('finding_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(), server_default='Medium', nullable=True),
        sa.Column('status', sa.String(), server_default='OPEN', nullable=True),
        sa.Column('github_issue_number', sa.Integer(), nullable=True),
        sa.Column('github_issue_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repository_issues_id'), 'repository_issues', ['id'], unique=False)
    op.create_index(op.f('ix_repository_issues_repository_id'), 'repository_issues', ['repository_id'], unique=False)

    # 6. release_records
    op.create_table(
        'release_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('version_tag', sa.String(), nullable=False),
        sa.Column('target_commit_sha', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='DRAFT', nullable=True),
        sa.Column('readiness_score', sa.Integer(), server_default='100', nullable=True),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('checklist_json', sa.Text(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_release_records_id'), 'release_records', ['id'], unique=False)
    op.create_index(op.f('ix_release_records_repository_id'), 'release_records', ['repository_id'], unique=False)

    # 7. cross_repo_dependencies
    op.create_table(
        'cross_repo_dependencies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('upstream_repo_id', sa.Integer(), nullable=False),
        sa.Column('downstream_repo_id', sa.Integer(), nullable=False),
        sa.Column('dependency_type', sa.String(), server_default='PACKAGE', nullable=True),
        sa.Column('details_json', sa.Text(), server_default='{}', nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['upstream_repo_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['downstream_repo_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cross_repo_dependencies_id'), 'cross_repo_dependencies', ['id'], unique=False)
    op.create_index(op.f('ix_cross_repo_dependencies_upstream_repo_id'), 'cross_repo_dependencies', ['upstream_repo_id'], unique=False)
    op.create_index(op.f('ix_cross_repo_dependencies_downstream_repo_id'), 'cross_repo_dependencies', ['downstream_repo_id'], unique=False)


def downgrade() -> None:
    op.drop_table('cross_repo_dependencies')
    op.drop_table('release_records')
    op.drop_table('repository_issues')
    op.drop_table('project_memories')
    op.drop_table('analyzer_runs')
    op.drop_table('repository_indexes')
    op.drop_column('repositories', 'ai_enabled')
