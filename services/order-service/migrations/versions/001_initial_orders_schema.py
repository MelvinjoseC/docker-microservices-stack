"""Initial orders and idempotency schema

Revision ID: 001_initial_orders
Revises: 
Create Date: 2026-11-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_orders'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, server_default='PENDING'),
        sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('status_history', sa.JSON(), nullable=True)
    )
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)

    op.create_table(
        'idempotency_records',
        sa.Column('key', sa.String(length=128), nullable=False, primary_key=True),
        sa.Column('response_code', sa.Integer(), nullable=False),
        sa.Column('response_body', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False)
    )
    op.create_index(op.f('ix_idempotency_records_key'), 'idempotency_records', ['key'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_idempotency_records_key'), table_name='idempotency_records')
    op.drop_table('idempotency_records')
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    op.drop_table('orders')
