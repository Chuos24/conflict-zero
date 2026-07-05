"""add_is_approved_to_users

Revision ID: 2f66a034fd23
Revises: 5bf3fcd427a1
Create Date: 2026-07-06 01:23:40.469919

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f66a034fd23'
down_revision = '5bf3fcd427a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar columna is_approved a users (faltaba en DB SQLite local)
    op.add_column('users', sa.Column('is_approved', sa.Boolean(), nullable=True, default=False))


def downgrade() -> None:
    # Eliminar columna is_approved de users
    op.drop_column('users', 'is_approved')
