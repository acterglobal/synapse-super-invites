"""Add error logs to acceptance

Revision ID: 8c8c90d89eac
Revises: 25e4ec3cea32
Create Date: 2024-05-28 17:39:39.516462

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c8c90d89eac"
down_revision: Union[str, None] = "25e4ec3cea32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "accepted", sa.Column("errors", sa.String(length=1024), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("accepted", "errors")
    # ### end Alembic commands ###
