"""
LangChain tools that give the AI agent access to the user's financial data.

Each tool is a plain async function decorated with @tool.  The agent decides
which tool(s) to invoke based on the user's question.  All tools receive the
user_id from the graph state (injected at runtime, never exposed to the LLM).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: get a data-DB session (ad-hoc, short-lived)
# ---------------------------------------------------------------------------
async def _get_data_session() -> AsyncSession:
    """Create a short-lived async session against the data database."""
    from app.db.session import DataSessionLocal
    return DataSessionLocal()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
async def get_expense_summary(user_id: str, months: int = 3) -> str:
    """
    Return a summary of the user's expenses over the last N months,
    grouped by category.  Useful when the user asks about spending
    habits, category breakdowns, or where their money is going.
    """
    from app.models.expense import Expense

    session = await _get_data_session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=months * 30)
        uid = UUID(user_id)

        result = await session.execute(
            select(
                Expense.category,
                func.count(Expense.id).label("count"),
                func.sum(Expense.amount).label("total"),
            )
            .where(Expense.user_id == uid, Expense.date >= cutoff)
            .group_by(Expense.category)
            .order_by(func.sum(Expense.amount).desc())
        )
        rows = result.all()

        if not rows:
            return f"No expenses found in the last {months} months."

        grand_total = sum(float(r.total) for r in rows)
        lines = [f"Expense summary (last {months} months) — total: ${grand_total:,.2f}"]
        for r in rows:
            pct = (float(r.total) / grand_total * 100) if grand_total else 0
            lines.append(f"  • {r.category or 'Uncategorised'}: ${float(r.total):,.2f} ({r.count} txns, {pct:.0f}%)")
        return "\n".join(lines)
    finally:
        await session.close()


@tool
async def get_budget_status(user_id: str) -> str:
    """
    Return the user's active budgets with current spending vs limits.
    Useful when the user asks about budgets, overspending, or remaining
    budget for a category.
    """
    from app.models.budget import Budget
    from datetime import date

    session = await _get_data_session()
    try:
        uid = UUID(user_id)
        # Get budgets for the current month (most relevant)
        today = date.today()
        current_month = today.replace(day=1)
        result = await session.execute(
            select(Budget).where(
                Budget.user_id == uid,
                Budget.month == current_month,
            )
        )
        budgets = result.scalars().all()

        # Fallback: get the latest month if none for current
        if not budgets:
            result = await session.execute(
                select(Budget)
                .where(Budget.user_id == uid)
                .order_by(Budget.month.desc())
                .limit(10)
            )
            budgets = result.scalars().all()

        if not budgets:
            return "No active budgets found. Consider creating a budget to track spending."

        lines = ["Active budgets:"]
        for b in budgets:
            spent = float(b.spent_amount or 0)
            limit_amt = float(b.allocated_amount or 0)
            remaining = limit_amt - spent
            pct = (spent / limit_amt * 100) if limit_amt else 0
            status = "⚠️ OVER" if pct > 100 else ("🟡 Caution" if pct > 80 else "✅ On track")
            lines.append(
                f"  • {b.category}: ${spent:,.2f} / ${limit_amt:,.2f} "
                f"({pct:.0f}%) — remaining ${remaining:,.2f} {status}"
            )
        return "\n".join(lines)
    finally:
        await session.close()


@tool
async def get_goals_progress(user_id: str) -> str:
    """
    Return the user's savings goals and progress toward each.
    Useful when the user asks about savings goals, progress, or
    how close they are to reaching a target.
    """
    from app.db.models.data import Goal

    session = await _get_data_session()
    try:
        uid = UUID(user_id)
        result = await session.execute(
            select(Goal).where(Goal.user_id == uid)
        )
        goals = result.scalars().all()

        if not goals:
            return "No savings goals set. Setting a goal helps track financial milestones!"

        lines = ["Savings goals:"]
        for g in goals:
            current = float(g.current_amount or 0)
            target = float(g.target_amount or 0)
            pct = (current / target * 100) if target else 0
            lines.append(
                f"  • {g.goal_name}: ${current:,.2f} / ${target:,.2f} ({pct:.0f}%)"
            )
        return "\n".join(lines)
    finally:
        await session.close()


@tool
async def get_loan_overview(user_id: str) -> str:
    """
    Return the user's active loans with outstanding balance and EMI.
    Useful when the user asks about debts, EMI payments, or loan status.
    """
    from app.db.models.data import Loan

    session = await _get_data_session()
    try:
        uid = UUID(user_id)
        result = await session.execute(
            select(Loan).where(Loan.user_id == uid)
        )
        loans = result.scalars().all()

        if not loans:
            return "No active loans found."

        lines = ["Loan overview:"]
        total_emi = 0.0
        for ln in loans:
            emi = float(ln.emi_amount or 0)
            total_emi += emi
            lines.append(
                f"  • {ln.loan_type} ({ln.lender_name or 'N/A'}): principal ${float(ln.principal_amount or 0):,.2f}, "
                f"rate {float(ln.interest_rate or 0):.1f}%, EMI ${emi:,.2f}/mo, "
                f"status={ln.status}"
            )
        lines.append(f"  Total monthly EMI: ${total_emi:,.2f}")
        return "\n".join(lines)
    finally:
        await session.close()


@tool
async def get_financial_profile(user_id: str) -> str:
    """
    Return the user's financial profile: monthly salary, rent,
    insurance, subscriptions. Useful for overall financial health checks.
    """
    from app.models.budget import FinancialProfile

    session = await _get_data_session()
    try:
        uid = UUID(user_id)
        result = await session.execute(
            select(FinancialProfile).where(FinancialProfile.user_id == uid)
        )
        profile = result.scalars().first()

        if not profile:
            return "Financial profile not set. Update your income and fixed expenses in Settings."

        salary = float(profile.monthly_salary or 0)
        rent = float(profile.rent or 0)
        insurance = float(profile.insurance or 0)
        subs = float(profile.subscriptions or 0)
        fixed = rent + insurance + subs
        disposable = salary - fixed

        return (
            f"Financial profile:\n"
            f"  Monthly salary: ${salary:,.2f}\n"
            f"  Fixed expenses: ${fixed:,.2f} (rent ${rent:,.2f}, "
            f"insurance ${insurance:,.2f}, subscriptions ${subs:,.2f})\n"
            f"  Disposable income: ${disposable:,.2f}"
        )
    finally:
        await session.close()


@tool
async def get_recent_transactions(user_id: str, limit: int = 10) -> str:
    """
    Return the user's most recent transactions.
    Useful when the user asks about recent spending or latest purchases.
    """
    from app.models.expense import Expense

    session = await _get_data_session()
    try:
        uid = UUID(user_id)
        result = await session.execute(
            select(Expense)
            .where(Expense.user_id == uid)
            .order_by(Expense.date.desc())
            .limit(limit)
        )
        expenses = result.scalars().all()

        if not expenses:
            return "No recent transactions found."

        lines = [f"Last {len(expenses)} transactions:"]
        for e in expenses:
            date_str = e.date.strftime("%Y-%m-%d") if e.date else "N/A"
            lines.append(
                f"  • {date_str}: {e.description or 'N/A'} — "
                f"${float(e.amount):,.2f} [{e.category or 'N/A'}]"
            )
        return "\n".join(lines)
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Tool registry — used by the agent graph
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    get_expense_summary,
    get_budget_status,
    get_goals_progress,
    get_loan_overview,
    get_financial_profile,
    get_recent_transactions,
]
