"""add_user_suppliers_table

Revision ID: 88024a4663a8
Revises: 2f66a034fd23
Create Date: 2026-07-06 21:41:25.856883

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '88024a4663a8'
down_revision = '2f66a034fd23'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_suppliers table
    op.create_table(
        'user_suppliers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('ruc', sa.String(11), nullable=False, index=True),
        sa.Column('supplier_name', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('last_score', sa.Integer(), nullable=True),
        sa.Column('last_risk_level', sa.String(20), nullable=True),
        sa.Column('last_osce_sanciones', sa.Integer(), nullable=True),
        sa.Column('last_tce_sanciones', sa.Integer(), nullable=True),
    )
    
    # Create supplier_alerts table
    op.create_table(
        'supplier_alerts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('supplier_ruc', sa.String(11), nullable=False, index=True),
        sa.Column('supplier_name', sa.String(255), nullable=True),
        sa.Column('change_type', sa.String(50), nullable=False),
        sa.Column('previous_status', sa.String(255), nullable=True),
        sa.Column('new_status', sa.String(255), nullable=True),
        sa.Column('severity', sa.String(20), default='medium'),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('email_sent', sa.Boolean(), default=False),
        sa.Column('email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create index for user_suppliers unique constraint
    op.create_index('ix_user_suppliers_user_ruc', 'user_suppliers', ['user_id', 'ruc'], unique=True)
    
    # Create index for alerts by user + read status
    op.create_index('ix_supplier_alerts_user_read', 'supplier_alerts', ['user_id', 'is_read'])


def downgrade() -> None:
    op.drop_index('ix_supplier_alerts_user_read', table_name='supplier_alerts')
    op.drop_index('ix_user_suppliers_user_ruc', table_name='user_suppliers')
    op.drop_table('supplier_alerts')
    op.drop_table('user_suppliers')
