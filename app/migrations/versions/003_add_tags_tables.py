"""Add tags and ruc_tags tables

Revision ID: 003
Revises: 002
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('color', sa.String(7), nullable=False, server_default='#C5A059'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_user_id'), 'tags', ['user_id'], unique=False)
    
    # Create ruc_tags table
    op.create_table(
        'ruc_tags',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('tag_id', sa.String(36), nullable=False),
        sa.Column('ruc', sa.String(11), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ruc_tags_tag_id'), 'ruc_tags', ['tag_id'], unique=False)
    op.create_index(op.f('ix_ruc_tags_user_id'), 'ruc_tags', ['user_id'], unique=False)
    op.create_index(op.f('ix_ruc_tags_ruc'), 'ruc_tags', ['ruc'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_ruc_tags_ruc'), table_name='ruc_tags')
    op.drop_index(op.f('ix_ruc_tags_user_id'), table_name='ruc_tags')
    op.drop_index(op.f('ix_ruc_tags_tag_id'), table_name='ruc_tags')
    op.drop_table('ruc_tags')
    op.drop_index(op.f('ix_tags_user_id'), table_name='tags')
    op.drop_table('tags')
