"""Create initial database schema.

Revision ID: 20260509_0001
Revises:
Create Date: 2026-05-09 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260509_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "exported_email_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("lead_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_exported_email_batches_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exported_email_batches")),
    )
    op.create_index(op.f("ix_exported_email_batches_id"), "exported_email_batches", ["id"], unique=False)
    op.create_index(op.f("ix_exported_email_batches_user_id"), "exported_email_batches", ["user_id"], unique=False)

    op.create_table(
        "lead_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("rows_count", sa.Integer(), nullable=False),
        sa.Column("columns_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_lead_imports_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lead_imports")),
    )
    op.create_index(op.f("ix_lead_imports_id"), "lead_imports", ["id"], unique=False)
    op.create_index(op.f("ix_lead_imports_status"), "lead_imports", ["status"], unique=False)
    op.create_index(op.f("ix_lead_imports_user_id"), "lead_imports", ["user_id"], unique=False)

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("job_title", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("industry", sa.String(length=150), nullable=True),
        sa.Column("source", sa.String(length=150), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("deal_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("budget_range", sa.String(length=100), nullable=True),
        sa.Column("interest_level", sa.String(length=100), nullable=True),
        sa.Column("timeline", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("priority_score", sa.Integer(), nullable=False),
        sa.Column("missing_fields_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["import_id"], ["lead_imports.id"], name=op.f("fk_leads_import_id_lead_imports"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_leads_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leads")),
    )
    op.create_index(op.f("ix_leads_category"), "leads", ["category"], unique=False)
    op.create_index(op.f("ix_leads_company_name"), "leads", ["company_name"], unique=False)
    op.create_index(op.f("ix_leads_email"), "leads", ["email"], unique=False)
    op.create_index(op.f("ix_leads_id"), "leads", ["id"], unique=False)
    op.create_index(op.f("ix_leads_import_id"), "leads", ["import_id"], unique=False)
    op.create_index(op.f("ix_leads_industry"), "leads", ["industry"], unique=False)
    op.create_index(op.f("ix_leads_interest_level"), "leads", ["interest_level"], unique=False)
    op.create_index(op.f("ix_leads_priority_score"), "leads", ["priority_score"], unique=False)
    op.create_index(op.f("ix_leads_source"), "leads", ["source"], unique=False)
    op.create_index(op.f("ix_leads_status"), "leads", ["status"], unique=False)
    op.create_index(op.f("ix_leads_user_category"), "leads", ["user_id", "category"], unique=False)
    op.create_index(op.f("ix_leads_user_id"), "leads", ["user_id"], unique=False)
    op.create_index(op.f("ix_leads_user_priority_score"), "leads", ["user_id", "priority_score"], unique=False)
    op.create_index(op.f("ix_leads_user_status"), "leads", ["user_id", "status"], unique=False)

    op.create_table(
        "email_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("ai_provider", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name=op.f("fk_email_drafts_lead_id_leads"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_email_drafts_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_drafts")),
    )
    op.create_index(op.f("ix_email_drafts_id"), "email_drafts", ["id"], unique=False)
    op.create_index(op.f("ix_email_drafts_lead_id"), "email_drafts", ["lead_id"], unique=False)
    op.create_index(op.f("ix_email_drafts_status"), "email_drafts", ["status"], unique=False)
    op.create_index(op.f("ix_email_drafts_user_id"), "email_drafts", ["user_id"], unique=False)
    op.create_index(op.f("ix_email_drafts_user_status"), "email_drafts", ["user_id", "status"], unique=False)

    op.create_table(
        "lead_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name=op.f("fk_lead_activities_lead_id_leads"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_lead_activities_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lead_activities")),
    )
    op.create_index(op.f("ix_lead_activities_activity_type"), "lead_activities", ["activity_type"], unique=False)
    op.create_index(op.f("ix_lead_activities_id"), "lead_activities", ["id"], unique=False)
    op.create_index(
        op.f("ix_lead_activities_lead_created_at"), "lead_activities", ["lead_id", "created_at"], unique=False
    )
    op.create_index(op.f("ix_lead_activities_lead_id"), "lead_activities", ["lead_id"], unique=False)
    op.create_index(op.f("ix_lead_activities_user_id"), "lead_activities", ["user_id"], unique=False)

    op.create_table(
        "lead_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("score_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name=op.f("fk_lead_scores_lead_id_leads"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lead_scores")),
    )
    op.create_index(op.f("ix_lead_scores_category"), "lead_scores", ["category"], unique=False)
    op.create_index(op.f("ix_lead_scores_id"), "lead_scores", ["id"], unique=False)
    op.create_index(op.f("ix_lead_scores_lead_id"), "lead_scores", ["lead_id"], unique=True)
    op.create_index(op.f("ix_lead_scores_score"), "lead_scores", ["score"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_lead_scores_score"), table_name="lead_scores")
    op.drop_index(op.f("ix_lead_scores_lead_id"), table_name="lead_scores")
    op.drop_index(op.f("ix_lead_scores_id"), table_name="lead_scores")
    op.drop_index(op.f("ix_lead_scores_category"), table_name="lead_scores")
    op.drop_table("lead_scores")

    op.drop_index(op.f("ix_lead_activities_user_id"), table_name="lead_activities")
    op.drop_index(op.f("ix_lead_activities_lead_id"), table_name="lead_activities")
    op.drop_index(op.f("ix_lead_activities_lead_created_at"), table_name="lead_activities")
    op.drop_index(op.f("ix_lead_activities_id"), table_name="lead_activities")
    op.drop_index(op.f("ix_lead_activities_activity_type"), table_name="lead_activities")
    op.drop_table("lead_activities")

    op.drop_index(op.f("ix_email_drafts_user_status"), table_name="email_drafts")
    op.drop_index(op.f("ix_email_drafts_user_id"), table_name="email_drafts")
    op.drop_index(op.f("ix_email_drafts_status"), table_name="email_drafts")
    op.drop_index(op.f("ix_email_drafts_lead_id"), table_name="email_drafts")
    op.drop_index(op.f("ix_email_drafts_id"), table_name="email_drafts")
    op.drop_table("email_drafts")

    op.drop_index(op.f("ix_leads_user_status"), table_name="leads")
    op.drop_index(op.f("ix_leads_user_priority_score"), table_name="leads")
    op.drop_index(op.f("ix_leads_user_id"), table_name="leads")
    op.drop_index(op.f("ix_leads_user_category"), table_name="leads")
    op.drop_index(op.f("ix_leads_status"), table_name="leads")
    op.drop_index(op.f("ix_leads_source"), table_name="leads")
    op.drop_index(op.f("ix_leads_priority_score"), table_name="leads")
    op.drop_index(op.f("ix_leads_interest_level"), table_name="leads")
    op.drop_index(op.f("ix_leads_industry"), table_name="leads")
    op.drop_index(op.f("ix_leads_import_id"), table_name="leads")
    op.drop_index(op.f("ix_leads_id"), table_name="leads")
    op.drop_index(op.f("ix_leads_email"), table_name="leads")
    op.drop_index(op.f("ix_leads_company_name"), table_name="leads")
    op.drop_index(op.f("ix_leads_category"), table_name="leads")
    op.drop_table("leads")

    op.drop_index(op.f("ix_lead_imports_user_id"), table_name="lead_imports")
    op.drop_index(op.f("ix_lead_imports_status"), table_name="lead_imports")
    op.drop_index(op.f("ix_lead_imports_id"), table_name="lead_imports")
    op.drop_table("lead_imports")

    op.drop_index(op.f("ix_exported_email_batches_user_id"), table_name="exported_email_batches")
    op.drop_index(op.f("ix_exported_email_batches_id"), table_name="exported_email_batches")
    op.drop_table("exported_email_batches")

    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
