"""add credits indexes

Revision ID: 000002_credits_indexes
Revises: 000001_init
Create Date: 2025-09-11
"""

from alembic import op
import sqlalchemy as sa


revision = '000002_credits_indexes'
down_revision = '000001_init'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_credits_tenant_created_at', 'credits', ['tenant_id', 'created_at'])
    op.create_index('ix_credits_job', 'credits', ['job_id'])


def downgrade() -> None:
    op.drop_index('ix_credits_job', table_name='credits')
    op.drop_index('ix_credits_tenant_created_at', table_name='credits')

