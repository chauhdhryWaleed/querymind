"""Curated example questions, grouped by category, served by /examples."""

from __future__ import annotations

from pydantic import BaseModel


class ExampleQuery(BaseModel):
    text: str
    icon: str


class ExampleCategory(BaseModel):
    id: str
    label: str
    queries: list[ExampleQuery]


class ExamplesResponse(BaseModel):
    categories: list[ExampleCategory]


_CATEGORIES: list[ExampleCategory] = [
    ExampleCategory(
        id="trends",
        label="Trends and time series",
        queries=[
            ExampleQuery(text="Monthly revenue trend for 2025", icon="trending"),
            ExampleQuery(
                text="Compare this quarter to the previous one by revenue", icon="compare"
            ),
            ExampleQuery(text="Show monthly revenue with a 3-month moving average", icon="wave"),
            ExampleQuery(text="Month-over-month growth rate of completed orders", icon="growth"),
        ],
    ),
    ExampleCategory(
        id="leaderboards",
        label="Leaderboards",
        queries=[
            ExampleQuery(text="Top 10 customers by lifetime value", icon="trophy"),
            ExampleQuery(text="Top 5 product categories by revenue this year", icon="medal"),
            ExampleQuery(text="Top 3 countries by completed order count", icon="globe"),
            ExampleQuery(
                text="Rank customers by total spend using a window function", icon="ranking"
            ),
        ],
    ),
    ExampleCategory(
        id="distribution",
        label="Distribution and segments",
        queries=[
            ExampleQuery(text="Revenue breakdown by region", icon="pie"),
            ExampleQuery(text="Order status breakdown with counts", icon="status"),
            ExampleQuery(text="Average order value by customer segment", icon="segment"),
            ExampleQuery(text="Customer count by country", icon="users"),
        ],
    ),
    ExampleCategory(
        id="analytics",
        label="Advanced analytics",
        queries=[
            ExampleQuery(
                text="Percentage of completed vs cancelled orders by region", icon="ratio"
            ),
            ExampleQuery(text="Cohort retention by customer signup month", icon="cohort"),
            ExampleQuery(text="Top products with year-over-year revenue change", icon="delta"),
            ExampleQuery(text="Customers whose latest order was over 60 days ago", icon="clock"),
        ],
    ),
]


def get_examples() -> ExamplesResponse:
    return ExamplesResponse(categories=_CATEGORIES)
