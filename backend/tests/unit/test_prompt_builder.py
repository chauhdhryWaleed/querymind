from datetime import UTC

from app.prompts.builder import build_correction_prompt, build_system_prompt

SCHEMA_CTX = "TABLE orders (\n  id  uuid  PK\n)"


def test_system_prompt_contains_schema() -> None:
    prompt = build_system_prompt(schema_context=SCHEMA_CTX)
    assert "TABLE orders" in prompt


def test_system_prompt_contains_rules() -> None:
    prompt = build_system_prompt(schema_context=SCHEMA_CTX)
    assert "SELECT *" in prompt  # Rule about never using SELECT *


def test_system_prompt_injects_conversation_history() -> None:
    from datetime import datetime

    from app.schemas.history import ConversationTurn

    turns = [
        ConversationTurn(
            question="Show all orders",
            sql="SELECT id FROM orders LIMIT 10",
            result_summary="Returned 10 rows",
            timestamp=datetime.now(tz=UTC),
        )
    ]
    prompt = build_system_prompt(schema_context=SCHEMA_CTX, conversation_history=turns)
    assert "Show all orders" in prompt


def test_correction_prompt_contains_error() -> None:
    prompt = build_correction_prompt(
        question="Show revenue",
        failed_sql="SELECT revenue FROM orders",
        error_message="column 'revenue' does not exist",
        schema_context=SCHEMA_CTX,
    )
    assert "revenue" in prompt
    assert "does not exist" in prompt


def test_correction_prompt_classifies_syntax_error() -> None:
    prompt = build_correction_prompt(
        question="Show orders",
        failed_sql="SELCT id FROM orders",
        error_message="syntax error at or near 'SELCT'",
        schema_context=SCHEMA_CTX,
    )
    assert "syntax" in prompt.lower()


def test_correction_prompt_classifies_undefined_table() -> None:
    prompt = build_correction_prompt(
        question="Show invoices",
        failed_sql="SELECT id FROM invoices",
        error_message="undefined table 'invoices'",
        schema_context=SCHEMA_CTX,
    )
    assert "does not exist" in prompt.lower()
