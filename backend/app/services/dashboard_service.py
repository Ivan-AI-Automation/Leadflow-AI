from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.email_draft import EmailDraft
from app.models.lead import Lead
from app.models.user import User
from app.schemas.dashboard import DashboardChartsResponse, DashboardSummaryResponse

STATUS_LABELS = ["New", "Contacted", "Follow-up", "Closed", "Lost"]
CATEGORY_LABELS = ["Hot", "Warm", "Nurture", "Low Priority"]


class DashboardService:
    @staticmethod
    def get_summary(db: Session, *, current_user: User) -> DashboardSummaryResponse:
        status_counts = DashboardService._count_leads_by_field(
            db,
            current_user=current_user,
            field=Lead.status,
            labels=STATUS_LABELS,
        )
        category_counts = DashboardService._count_leads_by_field(
            db,
            current_user=current_user,
            field=Lead.category,
            labels=CATEGORY_LABELS,
        )

        total_leads = DashboardService._count_leads(db, current_user=current_user)
        average_priority_score = DashboardService._average_priority_score(db, current_user=current_user)

        return DashboardSummaryResponse(
            total_leads=total_leads,
            new_leads=status_counts["New"],
            contacted_leads=status_counts["Contacted"],
            follow_up_leads=status_counts["Follow-up"],
            closed_leads=status_counts["Closed"],
            lost_leads=status_counts["Lost"],
            hot_leads=category_counts["Hot"],
            warm_leads=category_counts["Warm"],
            nurture_leads=category_counts["Nurture"],
            low_priority_leads=category_counts["Low Priority"],
            missing_email_count=DashboardService._count_missing_field(db, current_user=current_user, field=Lead.email),
            missing_phone_count=DashboardService._count_missing_field(db, current_user=current_user, field=Lead.phone),
            average_priority_score=average_priority_score,
            drafts_created=DashboardService._count_drafts(db, current_user=current_user),
            drafts_approved=DashboardService._count_drafts(db, current_user=current_user, status="Approved"),
        )

    @staticmethod
    def get_charts(db: Session, *, current_user: User) -> DashboardChartsResponse:
        status_counts = DashboardService._count_leads_by_field(
            db,
            current_user=current_user,
            field=Lead.status,
            labels=STATUS_LABELS,
        )
        category_counts = DashboardService._count_leads_by_field(
            db,
            current_user=current_user,
            field=Lead.category,
            labels=CATEGORY_LABELS,
        )

        return DashboardChartsResponse(
            charts=[
                {
                    "id": "leads_by_status",
                    "title": "Leads by Status",
                    "type": "bar",
                    "x": STATUS_LABELS,
                    "y": [status_counts[label] for label in STATUS_LABELS],
                },
                {
                    "id": "leads_by_category",
                    "title": "Leads by Category",
                    "type": "pie",
                    "labels": CATEGORY_LABELS,
                    "values": [category_counts[label] for label in CATEGORY_LABELS],
                },
            ]
        )

    @staticmethod
    def _count_leads(db: Session, *, current_user: User) -> int:
        statement = select(func.count()).select_from(Lead).where(Lead.user_id == current_user.id)
        return int(db.scalar(statement) or 0)

    @staticmethod
    def _average_priority_score(db: Session, *, current_user: User) -> float:
        statement = select(func.avg(Lead.priority_score)).where(Lead.user_id == current_user.id)
        average = db.scalar(statement)
        return round(float(average or 0), 2)

    @staticmethod
    def _count_missing_field(db: Session, *, current_user: User, field: Any) -> int:
        statement = (
            select(func.count())
            .select_from(Lead)
            .where(
                Lead.user_id == current_user.id,
                or_(field.is_(None), field == ""),
            )
        )
        return int(db.scalar(statement) or 0)

    @staticmethod
    def _count_drafts(db: Session, *, current_user: User, status: str | None = None) -> int:
        conditions = [EmailDraft.user_id == current_user.id]
        if status is not None:
            conditions.append(EmailDraft.status == status)

        statement = select(func.count()).select_from(EmailDraft).where(*conditions)
        return int(db.scalar(statement) or 0)

    @staticmethod
    def _count_leads_by_field(
        db: Session,
        *,
        current_user: User,
        field: Any,
        labels: list[str],
    ) -> dict[str, int]:
        statement = select(field, func.count()).select_from(Lead).where(Lead.user_id == current_user.id).group_by(field)
        counts = {label: 0 for label in labels}

        for label, count in db.execute(statement).all():
            if label in counts:
                counts[str(label)] = int(count)

        return counts
