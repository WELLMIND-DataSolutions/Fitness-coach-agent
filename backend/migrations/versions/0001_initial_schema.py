"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-24 12:56:22.462586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=32), nullable=False),
    sa.Column('password_hash', sa.String(length=100), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)

    op.create_table('chat_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('tool_calls', sa.JSON(), nullable=True),
    sa.Column('tool_call_id', sa.String(length=100), nullable=True),
    sa.Column('tool_name', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_chat_messages_user_id'), ['user_id'], unique=False)

    op.create_table('meal_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('logged_on', sa.Date(), nullable=False),
    sa.Column('food', sa.String(length=200), nullable=False),
    sa.Column('calories', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('meal_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_meal_logs_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_meal_user_date', ['user_id', 'logged_on'], unique=False)

    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('message', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notifications_user_id'), ['user_id'], unique=False)

    op.create_table('profiles',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('age', sa.Integer(), nullable=False),
    sa.Column('gender', sa.String(length=10), nullable=False),
    sa.Column('height_cm', sa.Float(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.Column('goal', sa.String(length=20), nullable=False),
    sa.Column('activity_level', sa.String(length=20), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('reminders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('time_hhmm', sa.String(length=5), nullable=False),
    sa.Column('message', sa.String(length=200), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('last_fired_on', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('reminders', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reminders_user_id'), ['user_id'], unique=False)

    op.create_table('weight_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('logged_on', sa.Date(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('weight_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_weight_logs_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_weight_user_date', ['user_id', 'logged_on'], unique=False)

    op.create_table('workout_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('logged_on', sa.Date(), nullable=False),
    sa.Column('exercise', sa.String(length=100), nullable=False),
    sa.Column('sets', sa.Integer(), nullable=False),
    sa.Column('reps', sa.Integer(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workout_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workout_logs_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_workout_user_date', ['user_id', 'logged_on'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('workout_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_workout_user_date')
        batch_op.drop_index(batch_op.f('ix_workout_logs_user_id'))
    op.drop_table('workout_logs')

    with op.batch_alter_table('weight_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_weight_user_date')
        batch_op.drop_index(batch_op.f('ix_weight_logs_user_id'))
    op.drop_table('weight_logs')

    with op.batch_alter_table('reminders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reminders_user_id'))
    op.drop_table('reminders')

    op.drop_table('profiles')

    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notifications_user_id'))
    op.drop_table('notifications')

    with op.batch_alter_table('meal_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_meal_user_date')
        batch_op.drop_index(batch_op.f('ix_meal_logs_user_id'))
    op.drop_table('meal_logs')

    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chat_messages_user_id'))
    op.drop_table('chat_messages')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_username'))
    op.drop_table('users')