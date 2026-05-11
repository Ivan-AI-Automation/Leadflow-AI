"""Add import preview metadata.

Revision ID: 20260509_0002
Revises: 20260509_0001
Create Date: 2026-05-09 00:00:01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260509_0002"
down_revision: str | None = "20260509_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("lead_imports") as batch_op:
        batch_op.add_column(sa.Column("columns_json", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("dtypes_json", sa.JSON(), nullable=False, server_default="{}"))

    with op.batch_alter_table("lead_imports") as batch_op:
        batch_op.alter_column("columns_json", server_default=None)
        batch_op.alter_column("dtypes_json", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("lead_imports") as batch_op:
        batch_op.drop_column("dtypes_json")
        batch_op.drop_column("columns_json")
