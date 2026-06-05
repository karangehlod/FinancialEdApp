"""API endpoints for data export functionality."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import date
import logging

from app.dependencies import get_current_user
from app.db.session import get_data_db
from app.services.export_service import ExportService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post(
    "/expenses/csv",
    summary="Export expenses to CSV",
    description="Export user expenses to CSV format",
)
async def export_expenses_csv(
    start_date: Optional[date] = Query(
        None, description="Start date for filtering (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date for filtering (YYYY-MM-DD)"
    ),
    current_user=Depends(get_current_user),
    session=Depends(get_data_db),
):
    """
    Export expenses to CSV format.

    **Query Parameters:**
    - `start_date`: Optional - Start date (YYYY-MM-DD)
    - `end_date`: Optional - End date (YYYY-MM-DD)

    **Response:**
    - CSV file with expense data

    **Example:**
    ```
    POST /api/v1/exports/expenses/csv?start_date=2024-01-01&end_date=2024-01-31
    ```

    **Headers:**
    - Content-Type: text/csv
    - Content-Disposition: attachment

    **CSV Format:**
    ```
    Date,Category,Subcategory,Amount,Merchant,Payment Method,Description
    2024-01-15,Food,Groceries,₹2,500.00,Supermarket,Debit Card,Weekly groceries
    ```
    """
    try:
        export_service = ExportService(session)

        csv_data = await export_service.export_expenses_csv(
            user_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date,
        )

        return StreamingResponse(
            iter([csv_data.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=expenses_{date.today().isoformat()}.csv"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting expenses to CSV: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to export expenses")


@router.post(
    "/budgets/csv",
    summary="Export budgets to CSV",
    description="Export user budgets to CSV format",
)
async def export_budgets_csv(
    month: Optional[date] = Query(
        None, description="Filter by month (YYYY-MM-01)"
    ),
    current_user=Depends(get_current_user),
    session=Depends(get_data_db),
):
    """
    Export budgets to CSV format.

    **Query Parameters:**
    - `month`: Optional - Filter by month (YYYY-MM-01)

    **Response:**
    - CSV file with budget data

    **Example:**
    ```
    POST /api/v1/exports/budgets/csv?month=2024-01-01
    ```

    **CSV Format:**
    ```
    Month,Category,Allocated Amount,Spent Amount,Remaining Amount,Utilization %
    2024-01-01,Food,₹10,000.00,₹8,500.00,₹1,500.00,85.0%
    ```
    """
    try:
        export_service = ExportService(session)

        csv_data = await export_service.export_budgets_csv(
            user_id=str(current_user.id),
            month=month,
        )

        return StreamingResponse(
            iter([csv_data.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=budgets_{date.today().isoformat()}.csv"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting budgets to CSV: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to export budgets")


@router.post(
    "/loans/csv",
    summary="Export loans to CSV",
    description="Export user loans to CSV format",
)
async def export_loans_csv(
    current_user=Depends(get_current_user),
    session=Depends(get_data_db),
):
    """
    Export loans to CSV format.

    **Response:**
    - CSV file with loan data

    **Example:**
    ```
    POST /api/v1/exports/loans/csv
    ```

    **CSV Format:**
    ```
    Loan Type,Lender,Principal Amount,Interest Rate %,EMI Amount,Outstanding Balance,Status
    Home Loan,HDFC Bank,₹50,00,000.00,7.50%,₹50,000.00,₹45,00,000.00,active
    ```
    """
    try:
        export_service = ExportService(session)

        csv_data = await export_service.export_loans_csv(
            user_id=str(current_user.id),
        )

        return StreamingResponse(
            iter([csv_data.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=loans_{date.today().isoformat()}.csv"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting loans to CSV: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to export loans")


@router.post(
    "/goals/csv",
    summary="Export goals to CSV",
    description="Export user goals to CSV format",
)
async def export_goals_csv(
    current_user=Depends(get_current_user),
    session=Depends(get_data_db),
):
    """
    Export goals to CSV format.

    **Response:**
    - CSV file with goal data

    **Example:**
    ```
    POST /api/v1/exports/goals/csv
    ```

    **CSV Format:**
    ```
    Goal Name,Type,Target Amount,Current Amount,Progress %,Target Date,Status,Priority
    Emergency Fund,emergency_fund,₹5,00,000.00,₹3,00,000.00,60.0%,2024-12-31,active,high
    ```
    """
    try:
        export_service = ExportService(session)

        csv_data = await export_service.export_goals_csv(
            user_id=str(current_user.id),
        )

        return StreamingResponse(
            iter([csv_data.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=goals_{date.today().isoformat()}.csv"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting goals to CSV: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to export goals")


@router.post(
    "/expenses/excel",
    summary="Export expenses to Excel",
    description="Export user expenses to Excel format",
)
async def export_expenses_excel(
    start_date: Optional[date] = Query(
        None, description="Start date for filtering (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date for filtering (YYYY-MM-DD)"
    ),
    current_user=Depends(get_current_user),
    session=Depends(get_data_db),
):
    """
    Export expenses to Excel format.

    **Query Parameters:**
    - `start_date`: Optional - Start date (YYYY-MM-DD)
    - `end_date`: Optional - End date (YYYY-MM-DD)

    **Response:**
    - Excel file with expense data (formatted)

    **Example:**
    ```
    POST /api/v1/exports/expenses/excel?start_date=2024-01-01&end_date=2024-01-31
    ```

    **Features:**
    - Formatted header row
    - Auto-sized columns
    - Proper currency formatting
    """
    try:
        export_service = ExportService(session)

        excel_data = await export_service.export_expenses_excel(
            user_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date,
        )

        return StreamingResponse(
            iter([excel_data.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=expenses_{date.today().isoformat()}.xlsx"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting expenses to Excel: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to export expenses")


@router.post(
    "/complete/excel",
    summary="Export all financial data to Excel",
    description="Export complete financial data (expenses, budgets, loans, goals) to a single Excel file",
)
async def export_complete_excel(
    current_user=Depends(get_current_user),
    session=Depends(get_data_db),
):
    """
    Export all financial data to a single Excel file.

    **Response:**
    - Excel file with multiple sheets (Expenses, Budgets, Loans, Goals)

    **Example:**
    ```
    POST /api/v1/exports/complete/excel
    ```

    **Features:**
    - Multiple sheets for different data types
    - Formatted headers
    - Auto-sized columns
    - Proper currency formatting
    - Professional styling

    **Sheets Included:**
    - Expenses: All transactions
    - Budgets: All budget allocations
    - Loans: All loans and EMIs
    - Goals: All financial goals
    """
    try:
        export_service = ExportService(session)

        excel_data = await export_service.export_complete_financial_data_excel(
            user_id=str(current_user.id),
        )

        return StreamingResponse(
            iter([excel_data.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=financial_data_{date.today().isoformat()}.xlsx"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting complete financial data to Excel: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to export financial data")
