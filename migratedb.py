from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'xxxx'
down_revision = 'xxxx'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns
    op.add_column('tool_log', sa.Column('tool_name', sa.String(length=100), nullable=False, server_default=''))
    op.add_column('tool_log', sa.Column('username', sa.String(length=100), nullable=False, server_default=''))
    
    # Populate new columns with existing data
    connection = op.get_bind()
    logs = connection.execute(sa.text("SELECT id, tool_id, user_id FROM tool_log")).fetchall()
    for log in logs:
        tool_name = connection.execute(sa.text("SELECT name FROM tool WHERE id = :tool_id"), {'tool_id': log['tool_id']}).scalar()
        username = connection.execute(sa.text("SELECT username FROM user WHERE id = :user_id"), {'user_id': log['user_id']}).scalar()
        connection.execute(sa.text("UPDATE tool_log SET tool_name = :tool_name, username = :username WHERE id = :id"),
                           {'tool_name': tool_name, 'username': username, 'id': log['id']})
    
    # Drop foreign key columns
    op.drop_constraint('tool_log_tool_id_fkey', 'tool_log', type_='foreignkey')
    op.drop_constraint('tool_log_user_id_fkey', 'tool_log', type_='foreignkey')
    op.drop_column('tool_log', 'tool_id')
    op.drop_column('tool_log', 'user_id')

def downgrade():
    # Reverse the above operations
    op.add_column('tool_log', sa.Column('tool_id', sa.Integer(), nullable=False))
    op.add_column('tool_log', sa.Column('user_id', sa.Integer(), nullable=False))
    op.create_foreign_key('tool_log_tool_id_fkey', 'tool_log', 'tool', ['tool_id'], ['id'])
    op.create_foreign_key('tool_log_user_id_fkey', 'tool_log', 'user', ['user_id'], ['id'])
    op.drop_column('tool_log', 'tool_name')
    op.drop_column('tool_log', 'username')


'''
alembic init alembic


# example alembic.ini section
[alembic]
script_location = alembic

# example alembic.ini sqlalchemy.url
sqlalchemy.url = sqlite:///your_database.db

alembic revision --autogenerate -m "Add username and tool_name to ToolLog"


alembic upgrade head

'''