"""Service for expense analytics and insights."""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from calendar import monthrange

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text

from app.db.models.data import Expense, Budget
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExpenseAnalyticsService:
    """
    Service for expense analytics and insights.
    
    Responsibilities:
    - Expense analytics calculations
    - Trend analysis
    - Anomaly detection
    - Future predictions
    - Spending insights
    
    This service focuses purely on analytics and reporting,
    not on data modification.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize ExpenseAnalyticsService with database session.
        
        Args:
            db: AsyncSession for database operations
        """
        self.db = db
    
    async def get_monthly_analytics(
        self,
        user_id: UUID,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """
        Get comprehensive monthly budget vs spending analytics.
        
        Provides detailed breakdown of budgets, spending, and utilization
        for each category in the specified month.
        
        Args:
            user_id: UUID of the user
            year: Year (e.g., 2024)
            month: Month (1-12)
        
        Returns:
            Dict with:
                - month: "YYYY-MM" format
                - summary: total_budgeted, total_spent, total_remaining, utilization %
                - budget_analysis: list of per-category analysis
                - unbudgeted_spending: categories with spending but no budget
                - pie_chart_data: formatted for pie chart display
        """
        # Get month boundaries
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        try:
            # Get all budgets for the month
            budgets_result = await self.db.execute(
                select(Budget).where(
                    and_(
                        Budget.user_id == user_id,
                        Budget.month == start_date
                    )
                )
            )
            budgets = budgets_result.scalars().all()
            
            # Get expenses by category for the month
            expenses_result = await self.db.execute(
                select(
                    Expense.category,
                    func.sum(Expense.amount).label('total_spent'),
                    func.count(Expense.id).label('expense_count')
                ).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= start_date,
                        Expense.date <= end_date
                    )
                ).group_by(Expense.category)
            )
            expense_data = {
                row.category: {"spent": row.total_spent, "count": row.expense_count}
                for row in expenses_result.all()
            }
            
            # Calculate analytics
            total_budgeted = sum(b.allocated_amount or 0 for b in budgets)
            total_spent = sum(data["spent"] for data in expense_data.values())
            
            budget_analysis = []
            for budget in budgets:
                category = budget.category
                spent = expense_data.get(category, {"spent": 0, "count": 0})["spent"]
                
                utilization = 0
                if budget.allocated_amount and budget.allocated_amount > 0:
                    utilization = float((spent / budget.allocated_amount) * 100)
                
                status = "UNDER"
                if utilization >= 100:
                    status = "OVER"
                elif utilization >= 90:
                    status = "WARNING"
                
                budget_analysis.append({
                    "category": category,
                    "budgeted": float(budget.allocated_amount or 0),
                    "spent": float(spent),
                    "remaining": float((budget.allocated_amount or 0) - spent),
                    "utilization_percent": utilization,
                    "status": status,
                    "expense_count": expense_data.get(category, {"count": 0})["count"]
                })
            
            # Categories with spending but no budget
            unbudgeted_categories = []
            for category, data in expense_data.items():
                if not any(b.category == category for b in budgets):
                    unbudgeted_categories.append({
                        "category": category,
                        "spent": float(data["spent"]),
                        "expense_count": data["count"]
                    })
            
            return {
                "month": f"{year}-{month:02d}",
                "summary": {
                    "total_budgeted": float(total_budgeted),
                    "total_spent": float(total_spent),
                    "total_remaining": float(total_budgeted - total_spent),
                    "budget_utilization_percent": float(
                        (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0
                    )
                },
                "budget_analysis": budget_analysis,
                "unbudgeted_spending": unbudgeted_categories,
                "pie_chart_data": [
                    {"category": item["category"], "amount": item["spent"]}
                    for item in budget_analysis + unbudgeted_categories
                ]
            }
        except Exception as e:
            logger.error(f"Error getting monthly analytics: {str(e)}")
            raise
    
    async def calculate_expense_analytics(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive expense analytics for a date range.
        
        Args:
            user_id: UUID of the user
            start_date: Start date for analysis (inclusive)
            end_date: End date for analysis (inclusive)
        
        Returns:
            Dict with:
                - total_amount: Sum of all expenses
                - total_expenses: Count of expenses
                - average_amount: Average per expense
                - category_breakdown: Dict of category -> amount
                - spending_trend: "increasing" | "decreasing" | "stable"
        """
        try:
            # Get expenses for date range
            result = await self.db.execute(
                select(Expense).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= start_date.date() if isinstance(start_date, datetime) else start_date,
                        Expense.date <= end_date.date() if isinstance(end_date, datetime) else end_date
                    )
                )
            )
            expenses = result.scalars().all()
            
            if not expenses:
                return {
                    "total_amount": Decimal('0'),
                    "total_expenses": 0,
                    "average_amount": Decimal('0'),
                    "category_breakdown": {},
                    "spending_trend": "no_data"
                }
            
            # Calculate totals
            total = sum(float(expense.amount) for expense in expenses)
            average = total / len(expenses)
            
            # Category breakdown
            category_breakdown = {}
            for expense in expenses:
                category = expense.category
                if category not in category_breakdown:
                    category_breakdown[category] = Decimal('0')
                category_breakdown[category] += expense.amount
            
            return {
                "total_amount": Decimal(str(total)),
                "total_expenses": len(expenses),
                "average_amount": Decimal(str(round(average, 2))),
                "category_breakdown": category_breakdown,
                "spending_trend": "stable"
            }
        except Exception as e:
            logger.error(f"Error calculating expense analytics: {str(e)}")
            raise
    
    async def calculate_monthly_spending_trend(
        self,
        user_id: UUID,
        months: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Calculate monthly spending trend over the last N months.
        
        Args:
            user_id: UUID of the user
            months: Number of months to analyze (default 6)
        
        Returns:
            List of dicts with month and total_amount for each month
        """
        try:
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=30 * months)
            
            # Query for monthly totals using date_trunc with text literal
            month_trunc = func.date_trunc(text("'month'"), Expense.date)
            
            result = await self.db.execute(
                select(
                    month_trunc.label('month'),
                    func.sum(Expense.amount).label('total')
                ).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= start_date,
                        Expense.date <= end_date
                    )
                ).group_by(month_trunc)
                .order_by(month_trunc)
            )
            
            trend = []
            for row in result.all():
                trend.append({
                    "month": row.month.strftime("%Y-%m") if row.month else "Unknown",
                    "total_amount": float(row.total) if row.total else 0
                })
            
            return trend
        except Exception as e:
            logger.error(f"Error calculating spending trend: {str(e)}")
            raise
    
    async def detect_spending_anomalies(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Detect spending anomalies based on historical patterns.
        
        Identifies expenses that deviate significantly from the user's
        average spending pattern.
        
        Args:
            user_id: UUID of the user
        
        Returns:
            List of anomalies with details
        """
        try:
            # Get historical average from last 3 months
            three_months_ago = date.today() - timedelta(days=90)
            
            avg_result = await self.db.execute(
                select(func.avg(Expense.amount)).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= three_months_ago
                    )
                )
            )
            historical_avg = avg_result.scalar() or Decimal("0")
            
            if historical_avg == 0:
                return []
            
            # Get recent expenses from last month
            one_month_ago = date.today() - timedelta(days=30)
            
            expenses_result = await self.db.execute(
                select(Expense).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= one_month_ago
                    )
                ).order_by(Expense.date.desc())
            )
            expenses = expenses_result.scalars().all()
            
            # Detect anomalies (> 2.5x historical average)
            anomalies = []
            threshold = float(historical_avg) * 2.5
            
            for expense in expenses:
                if float(expense.amount) > threshold:
                    anomalies.append({
                        "type": "high_spending",
                        "expense_id": str(expense.id),
                        "amount": float(expense.amount),
                        "category": expense.category,
                        "date": expense.date,
                        "threshold": float(threshold),
                        "reason": f"Amount {expense.amount} exceeds threshold {threshold:.2f}"
                    })
            
            return anomalies
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            raise
    
    async def calculate_category_wise_trends(
        self,
        user_id: UUID,
        months: int = 6
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate spending trends by category over time.
        
        Args:
            user_id: UUID of the user
            months: Number of months to analyze (default 6)
        
        Returns:
            Dict mapping category -> list of monthly data
        """
        try:
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=30 * months)
            
            # Query for category-wise monthly data using text literal for date_trunc
            month_trunc = func.date_trunc(text("'month'"), Expense.date)
            
            result = await self.db.execute(
                select(
                    month_trunc.label('month'),
                    Expense.category,
                    func.sum(Expense.amount).label('total')
                ).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= start_date,
                        Expense.date <= end_date
                    )
                ).group_by(
                    month_trunc,
                    Expense.category
                ).order_by(
                    month_trunc,
                    Expense.category
                )
            )
            
            # Process the data into trends by category
            trends = {}
            for row in result.all():
                category = row.category
                if category not in trends:
                    trends[category] = []
                
                trends[category].append({
                    "month": row.month.strftime("%Y-%m") if row.month else "Unknown",
                    "amount": float(row.total) if row.total else 0,
                    "category": category
                })
            
            return trends
        except Exception as e:
            logger.error(f"Error calculating category trends: {str(e)}")
            raise
    
    async def generate_spending_insights(self, user_id: UUID) -> Dict[str, Any]:
        """
        Generate spending insights for the current month.
        
        Compares current month's spending against historical averages
        and identifies categories with significant changes.
        
        Args:
            user_id: UUID of the user
        
        Returns:
            Dict with insights and recommendations
        """
        try:
            current_date = datetime.now()
            start_of_month = current_date.replace(day=1).date()
            
            # Get current month expenses
            current_result = await self.db.execute(
                select(Expense).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= start_of_month,
                        Expense.date <= current_date.date()
                    )
                )
            )
            current_expenses = current_result.scalars().all()
            
            # Get historical averages for comparison (last 6 months)
            six_months_ago = start_of_month - timedelta(days=180)
            
            historical_result = await self.db.execute(
                select(
                    Expense.category,
                    func.avg(Expense.amount).label('avg_amount')
                ).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= six_months_ago,
                        Expense.date < start_of_month
                    )
                ).group_by(Expense.category)
            )
            historical_averages = historical_result.mappings().all()
            
            # Convert to dict for easier lookup
            historical_dict = {
                row['category']: row['avg_amount']
                for row in historical_averages
            }
            
            # Calculate current month spending by category
            current_spending = {}
            for expense in current_expenses:
                category = expense.category
                if category not in current_spending:
                    current_spending[category] = Decimal('0')
                current_spending[category] += expense.amount
            
            # Identify overspending categories
            overspending_categories = []
            for category, current_amount in current_spending.items():
                historical_avg = historical_dict.get(category, Decimal('0'))
                if historical_avg > 0 and current_amount > historical_avg * Decimal('1.5'):
                    overspent_amount = current_amount - historical_avg
                    overspending_categories.append({
                        "category": category,
                        "current_spending": float(current_amount),
                        "historical_average": float(historical_avg),
                        "overspent_amount": float(overspent_amount),
                        "overspend_percentage": float(
                            (current_amount - historical_avg) / historical_avg * 100
                        )
                    })
            
            insights = {
                "overspending_categories": overspending_categories,
                "total_categories": len(current_spending),
                "insights": []
            }
            
            # Add basic insights
            if current_spending:
                highest_category = max(current_spending.items(), key=lambda x: x[1])
                insights["insights"].append({
                    "message": f"Your highest spending category is {highest_category[0]} with ₹{highest_category[1]}",
                    "type": "info"
                })
            
            return insights
        except Exception as e:
            logger.error(f"Error generating spending insights: {str(e)}")
            raise
    
    async def calculate_payment_method_analytics(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> Dict[str, float]:
        """
        Calculate analytics by payment method.
        
        Args:
            user_id: UUID of the user
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            Dict mapping payment method -> total amount
        """
        try:
            result = await self.db.execute(
                select(Expense).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= start_date,
                        Expense.date <= end_date
                    )
                )
            )
            expenses = result.scalars().all()
            
            analytics = {}
            for expense in expenses:
                method = expense.payment_method or "unknown"
                if method not in analytics:
                    analytics[method] = Decimal("0")
                analytics[method] += expense.amount
            
            # Convert to float for JSON serialization
            return {method: float(amount) for method, amount in analytics.items()}
        except Exception as e:
            logger.error(f"Error calculating payment method analytics: {str(e)}")
            raise
    
    async def calculate_weekly_spending_pattern(
        self,
        user_id: UUID,
        weeks: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Calculate weekly spending patterns.
        
        Args:
            user_id: UUID of the user
            weeks: Number of weeks to analyze (default 4)
        
        Returns:
            List of weekly spending data
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=7 * weeks)
            
            # Use text literal for date_trunc function name
            week_trunc = func.date_trunc(text("'week'"), Expense.date)
            
            result = await self.db.execute(
                select(
                    week_trunc.label('week_start'),
                    func.sum(Expense.amount).label('total_amount'),
                    func.count(Expense.id).label('transaction_count')
                ).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= start_date,
                        Expense.date <= end_date
                    )
                ).group_by(week_trunc)
                .order_by(week_trunc)
            )
            
            weekly_data = []
            for row in result.all():
                weekly_data.append({
                    "week_start": row.week_start.isoformat() if row.week_start else None,
                    "total_amount": float(row.total_amount) if row.total_amount else 0,
                    "transaction_count": row.transaction_count or 0
                })
            
            return weekly_data
        except Exception as e:
            logger.error(f"Error calculating weekly spending: {str(e)}")
            raise
