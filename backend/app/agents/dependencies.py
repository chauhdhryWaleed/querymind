"""Typed dependency container passed to every LangGraph node."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.executors.sql_executor import SqlExecutor
from app.llm.base import LLMProvider
from app.validators.pipeline import ValidationPipeline


@dataclass(slots=True)
class AgentDeps:
    llm: LLMProvider
    executor: SqlExecutor
    validation_pipeline: ValidationPipeline
    ro_session: AsyncSession  # per-request user DB session
    settings: Settings
