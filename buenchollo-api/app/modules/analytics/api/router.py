from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import require_admin
from app.modules.analytics.api.schemas import (
    AnalyticsOverviewResponse,
    TrackPageViewRequest,
    TrackPageViewResponse,
)
from app.modules.analytics.application.service import AnalyticsService, TrackPageViewCommand
from app.modules.analytics.infrastructure.repository import AnalyticsRepository


router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AnalyticsService:
    return AnalyticsService(
        AnalyticsRepository(db),
        hash_secret=settings.effective_analytics_hash_secret,
        retention_months=settings.analytics_retention_months,
    )


@router.post(
    "/events",
    response_model=TrackPageViewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("60/minute")
async def track_page_view(
    request: Request,
    payload: TrackPageViewRequest,
    service: AnalyticsService = Depends(get_analytics_service),
):
    result = await service.track_page_view(
        TrackPageViewCommand(
            visitor_id=str(payload.visitor_id),
            session_id=str(payload.session_id),
            path=payload.path,
            source=payload.source,
            source_detail=payload.source_detail,
            medium=payload.medium,
            campaign=payload.campaign,
            referrer_host=payload.referrer_host,
            user_agent=request.headers.get("user-agent", ""),
        )
    )
    return TrackPageViewResponse(
        accepted=result.accepted,
        blog_view_count=result.blog_view_count,
    )


@router.get("/admin/overview", response_model=AnalyticsOverviewResponse)
async def get_admin_overview(
    days: int = Query(default=30, ge=1, le=90),
    service: AnalyticsService = Depends(get_analytics_service),
    _admin=Depends(require_admin),
):
    return await service.get_overview(days)
