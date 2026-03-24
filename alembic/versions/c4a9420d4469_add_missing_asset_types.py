"""Add missing asset types

Revision ID: c4a9420d4469
Revises: 4b8bc8eadc04
Create Date: 2026-03-23 11:26:37.078630

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4a9420d4469'
down_revision: Union[str, Sequence[str], None] = '4b8bc8eadc04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Since PostgreSQL doesn't allow ALTER TYPE ... ADD VALUE inside a transaction block 
    # in some versions, we use a raw execution that handles it.
    op.execute("COMMIT")
    op.execute("ALTER TYPE assettype ADD VALUE 'CHANGELOG'")
    op.execute("ALTER TYPE assettype ADD VALUE 'SUPPORT_SNIPPET'")


def downgrade() -> None:
    """Downgrade schema."""
    # Downgrading enums in PostgreSQL is complex, usually involves recreating the type.
    # For dev, we can leave them.
    pass
