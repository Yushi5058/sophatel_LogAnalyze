"""
Migration manuelle — ajoute log_path, password, ssh_key à vps_servers

Si vous utilisez Alembic :
  1. Copiez ce fichier dans backend/alembic/versions/
  2. alembic upgrade head

Si vous n'utilisez pas Alembic, exécutez ces commandes SQL directement :
  ALTER TABLE vps_servers ADD COLUMN IF NOT EXISTS log_path VARCHAR(500) DEFAULT '/var/log/nginx/access.log';
  ALTER TABLE vps_servers ADD COLUMN IF NOT EXISTS password VARCHAR(500);
  ALTER TABLE vps_servers ADD COLUMN IF NOT EXISTS ssh_key TEXT;
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_vps_auth_logpath'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('vps_servers',
        sa.Column('log_path', sa.String(500), nullable=True,
                  server_default='/var/log/nginx/access.log'))
    op.add_column('vps_servers',
        sa.Column('password', sa.String(500), nullable=True))
    op.add_column('vps_servers',
        sa.Column('ssh_key', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('vps_servers', 'ssh_key')
    op.drop_column('vps_servers', 'password')
    op.drop_column('vps_servers', 'log_path')