"""init

Revision ID: 000001_init
Revises: 
Create Date: 2025-09-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '000001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('case_ref', sa.String(), nullable=True),
        sa.Column('orig_filename', sa.String(), nullable=False),
        sa.Column('mime', sa.String(), nullable=False),
        sa.Column('bytes_sha256', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_documents_bytes_sha256', 'documents', ['bytes_sha256'])

    op.create_table(
        'document_versions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('storage_uri', sa.String(), nullable=False),
        sa.Column('ocr_text_uri', sa.String(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'processing_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('status', sa.Enum('queued', 'running', 'succeeded', 'failed', name='processingstatus'), nullable=False),
        sa.Column('steps', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'credits',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('delta', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('processing_jobs.id'), nullable=True),
        sa.Column('is_estimate', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('credits')
    op.drop_table('processing_jobs')
    op.drop_table('document_versions')
    op.drop_index('ix_documents_bytes_sha256', table_name='documents')
    op.drop_table('documents')
    op.drop_table('users')
    op.drop_table('tenants')
    op.execute('DROP TYPE IF EXISTS processingstatus;')

