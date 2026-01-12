from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import QueryFeedback
from app.models.history import QueryHistory
from app.schemas.stats import ProviderBreakdown, StatsResponse


class StatsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def summary(self, window_days: int = 7) -> StatsResponse:
        cutoff = datetime.now(tz=UTC) - timedelta(days=window_days)

        history_q = select(
            func.count(QueryHistory.id),
            func.coalesce(func.sum(QueryHistory.input_tokens), 0),
            func.coalesce(func.sum(QueryHistory.output_tokens), 0),
            func.coalesce(func.avg(QueryHistory.execution_time_ms), 0.0),
            func.coalesce(func.avg(QueryHistory.retry_count), 0.0),
            func.coalesce(func.sum(case((QueryHistory.error.is_(None), 1), else_=0)), 0),
            func.coalesce(func.sum(case((QueryHistory.error.is_not(None), 1), else_=0)), 0),
        ).where(QueryHistory.created_at >= cutoff)
        (
            total,
            input_tokens,
            output_tokens,
            avg_exec_ms,
            avg_retries,
            success,
            failed,
        ) = (await self._session.execute(history_q)).one()

        provider_q = (
            select(
                QueryHistory.llm_provider,
                func.count(QueryHistory.id),
                func.coalesce(func.sum(QueryHistory.input_tokens), 0),
                func.coalesce(func.sum(QueryHistory.output_tokens), 0),
            )
            .where(QueryHistory.created_at >= cutoff)
            .group_by(QueryHistory.llm_provider)
        )
        providers = [
            ProviderBreakdown(
                provider=p or "unknown",
                query_count=int(c),
                input_tokens=int(it),
                output_tokens=int(ot),
            )
            for p, c, it, ot in (await self._session.execute(provider_q)).all()
        ]

        feedback_q = select(
            func.coalesce(func.sum(case((QueryFeedback.rating == "up", 1), else_=0)), 0),
            func.coalesce(func.sum(case((QueryFeedback.rating == "down", 1), else_=0)), 0),
        ).where(QueryFeedback.created_at >= cutoff)
        up, down = (await self._session.execute(feedback_q)).one()

        return StatsResponse(
            window_days=window_days,
            query_count=int(total),
            successful_query_count=int(success),
            failed_query_count=int(failed),
            total_input_tokens=int(input_tokens),
            total_output_tokens=int(output_tokens),
            avg_execution_time_ms=round(float(avg_exec_ms), 2),
            avg_retry_count=round(float(avg_retries), 2),
            feedback_up=int(up),
            feedback_down=int(down),
            providers=providers,
        )
