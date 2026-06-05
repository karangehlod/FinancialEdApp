"""Loan management API endpoints."""
from typing import List, Optional
from datetime import date
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.db.session import get_data_db
from app.db.models.auth import User
from app.schemas.loan import (
    LoanCreate, LoanUpdate, LoanResponse, LoanPaymentCreate,
    LoanPaymentResponse, LoanAnalytics, RepaymentScheduleItem,
    LoanSummary, MonthlyLoanSummary, EMICalculationRequest,
    EMIImpactAnalysis, PrepaymentAnalysis, LoanConfiguration,
    ComprehensiveLoanAnalysis, LoanComparisonRequest, 
    LoanComparisonResponse, PrepaymentAnalysisRequest,
    PrepaymentAnalysisResponse
)
from app.services.loan_service import LoanService
from app.core.validation_decorators import validate_loan_input
from app.core.error_handling_decorators import (
    log_operation,
    audit_log,
    handle_db_errors,
)
from app.core.rate_limiting_decorators import rate_limit, apply_preset_limit
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/loans", tags=["loans"])


def get_loan_service(
    db: AsyncSession = Depends(get_data_db),
) -> LoanService:
    """Dependency factory — builds a LoanService per request."""
    return LoanService(db)


@router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
@apply_preset_limit("create")
@validate_loan_input
@log_operation("create_loan", include_args=False, include_result=False)
@audit_log(action="create", resource_type="loan")
@handle_db_errors(rollback_on_error=True)
async def create_loan(
    loan_data: LoanCreate,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service),
    request: Request = None,
    response: Response = None,
):
    """Create a new loan."""
    try:
        loan = await loan_service.create_loan(current_user.id, loan_data)
        return loan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create loan: {str(e)}"
        )


@router.get("", response_model=List[LoanResponse])
async def get_loans(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return (hard cap: 500)"),
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Get all loans for the current user."""
    try:
        loans = await loan_service.get_user_loans(current_user.id, status_filter)
        # Apply pagination at the service layer result (service doesn't yet support offset/limit)
        return loans[skip : skip + limit]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loans: {str(e)}"
        )


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Get a specific loan by ID."""
    try:
        loan = await loan_service.get_loan(current_user.id, loan_id)
        
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        return loan
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loan: {str(e)}"
        )


@router.put("/{loan_id}", response_model=LoanResponse)
@apply_preset_limit("update")
@validate_loan_input
@log_operation("update_loan", include_args=False, include_result=False)
@audit_log(action="update", resource_type="loan")
@handle_db_errors(rollback_on_error=True)
async def update_loan(
    loan_id: UUID,
    loan_data: LoanUpdate,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service),
    request: Request = None,
    response: Response = None,
):
    """Update a specific loan."""
    try:
        loan = await loan_service.update_loan(current_user.id, loan_id, loan_data)
        
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        return loan
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update loan: {str(e)}"
        )


@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
@apply_preset_limit("delete")
@log_operation("delete_loan")
@audit_log(action="delete", resource_type="loan")
@handle_db_errors(rollback_on_error=True)
async def delete_loan(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service),
    request: Request = None,
    response: Response = None,
):
    """Delete a specific loan."""
    try:
        success = await loan_service.delete_loan(current_user.id, loan_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete loan: {str(e)}"
        )


@router.post("/{loan_id}/payments", response_model=LoanPaymentResponse, status_code=status.HTTP_201_CREATED)
@apply_preset_limit("payment")
@log_operation("make_loan_payment", include_args=False, include_result=False)
@audit_log(action="create", resource_type="loan_payment")
@handle_db_errors(rollback_on_error=True)
async def make_payment(
    loan_id: UUID,
    payment_data: LoanPaymentCreate,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service),
    request: Request = None,
    response: Response = None,
):
    """Make a payment towards a loan."""
    try:
        payment = await loan_service.make_payment(current_user.id, loan_id, payment_data)
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found or inactive"
            )
        
        return payment
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to make payment: {str(e)}"
        )


@router.get("/{loan_id}/payments", response_model=List[LoanPaymentResponse])
async def get_loan_payments(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Get all payments for a specific loan."""
    try:
        # First check if loan exists
        loan = await loan_service.get_loan(current_user.id, loan_id)
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        payments = await loan_service.get_loan_payments(current_user.id, loan_id)
        return payments
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payments: {str(e)}"
        )


@router.get("/{loan_id}/schedule", response_model=List[RepaymentScheduleItem])
async def get_repayment_schedule(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Get repayment schedule for a specific loan."""
    try:
        # First check if loan exists
        loan = await loan_service.get_loan(current_user.id, loan_id)
        if not loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        schedule = await loan_service.generate_repayment_schedule(current_user.id, loan_id)
        return schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate repayment schedule: {str(e)}"
        )


@router.get("/{loan_id}/summary", response_model=LoanSummary)
async def get_loan_summary(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Get comprehensive summary for a specific loan."""
    try:
        summary = await loan_service.get_loan_summary(current_user.id, loan_id)
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get loan summary: {str(e)}"
        )


# Analytics endpoints
@router.get("/analytics/overview", response_model=LoanAnalytics)
async def get_loan_analytics(
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Get comprehensive loan analytics for the current user."""
    try:
        analytics = await loan_service.get_loan_analytics(current_user.id)
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loan analytics: {str(e)}"
        )


@router.get("/analytics/monthly", response_model=MonthlyLoanSummary)
async def get_monthly_loan_summary(
    year: int = Query(..., description="Year (e.g., 2024)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Get loan summary for a specific month."""
    try:
        summary = await loan_service.get_monthly_loan_summary(current_user.id, year, month)
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve monthly loan summary: {str(e)}"
        )


# NEW: Advanced loan calculation endpoints
@router.post("/calculate-emi-impact", response_model=EMIImpactAnalysis)
async def calculate_emi_impact(
    calculation_request: EMICalculationRequest,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Calculate the impact of EMI changes on loan tenure and interest savings."""
    try:
        impact_analysis = await loan_service.calculate_emi_impact(calculation_request)
        return impact_analysis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate EMI impact: {str(e)}"
        )


@router.post("/{loan_id}/analyze-prepayment", response_model=PrepaymentAnalysis)
async def analyze_prepayment(
    loan_id: UUID,
    prepayment_request: PrepaymentAnalysisRequest,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Analyze the impact of prepayment on loan tenure and interest savings."""
    try:
        analysis = await loan_service.analyze_prepayment(
            current_user.id, 
            loan_id, 
            prepayment_request.prepayment_amount
        )
        return analysis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze prepayment: {str(e)}"
        )


@router.put("/configure", response_model=LoanResponse)
async def configure_loan(
    loan_config: LoanConfiguration,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Configure loan parameters (principal, interest rate, EMI, prepayment)."""
    try:
        configured_loan = await loan_service.configure_loan(current_user.id, loan_config)
        
        if not configured_loan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found"
            )
        
        return configured_loan
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to configure loan: {str(e)}"
        )


@router.get("/analytics/comprehensive", response_model=ComprehensiveLoanAnalysis)
async def get_comprehensive_loan_analysis(
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Get comprehensive loan analysis with optimization suggestions and budget integration."""
    try:
        analysis = await loan_service.get_comprehensive_loan_analysis(current_user.id)
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comprehensive loan analysis: {str(e)}"
        )

# EMI calculation endpoint
@router.post("/calculate-emi")
async def calculate_emi(
    calculation_request: EMICalculationRequest,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Calculate EMI for given loan parameters."""
    try:
        emi_amount = loan_service._calculate_emi(
            calculation_request.principal_amount,
            calculation_request.interest_rate,
            calculation_request.loan_term_months
        )
        
        # Calculate total amount payable
        total_amount = emi_amount * calculation_request.loan_term_months
        total_interest = total_amount - calculation_request.principal_amount
        
        return {
            "emi_amount": emi_amount,
            "principal_amount": calculation_request.principal_amount,
            "interest_rate": calculation_request.interest_rate,
            "loan_term_months": calculation_request.loan_term_months,
            "total_amount": total_amount,
            "total_interest": total_interest
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to calculate EMI: {str(e)}"
        )


@router.post("/compare", response_model=LoanComparisonResponse)
async def compare_loans(
    comparison_request: LoanComparisonRequest,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Compare multiple loan options."""
    try:
        comparison_results = []
        
        for loan_option in comparison_request.loan_options:
            emi_amount = loan_service._calculate_emi(
                loan_option.principal_amount,
                loan_option.interest_rate,
                loan_option.loan_term_months
            )
            
            total_amount_payable = emi_amount * loan_option.loan_term_months
            total_interest = total_amount_payable - loan_option.principal_amount
            
            comparison_results.append({
                "lender_name": loan_option.lender_name,
                "loan_type": loan_option.loan_type,
                "principal_amount": loan_option.principal_amount,
                "interest_rate": loan_option.interest_rate,
                "loan_term_months": loan_option.loan_term_months,
                "emi_amount": emi_amount,
                "total_amount_payable": total_amount_payable,
                "total_interest": total_interest
            })
        
        # Find best option (lowest total interest)
        best_option = min(comparison_results, key=lambda x: x["total_interest"])
        worst_option = max(comparison_results, key=lambda x: x["total_interest"])
        savings_vs_worst = worst_option["total_interest"] - best_option["total_interest"]
        
        return LoanComparisonResponse(
            comparison_results=comparison_results,
            best_option=best_option,
            savings_vs_worst=savings_vs_worst
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to compare loans: {str(e)}"
        )


@router.post("/prepayment-analysis", response_model=PrepaymentAnalysisResponse)
async def analyze_prepayment(
    prepayment_request: PrepaymentAnalysisRequest,
    current_user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service)
):
    """Analyze the impact of prepayment on a loan."""
    try:
        # Calculate original EMI
        original_emi = loan_service._calculate_emi(
            prepayment_request.principal_amount,
            prepayment_request.interest_rate,
            prepayment_request.loan_term_months
        )
        
        # Calculate new loan details after prepayment
        remaining_principal = prepayment_request.principal_amount - prepayment_request.prepayment_amount
        remaining_months = prepayment_request.loan_term_months - prepayment_request.prepayment_month
        
        # Calculate new EMI with reduced principal
        new_emi = loan_service._calculate_emi(
            remaining_principal,
            prepayment_request.interest_rate,
            remaining_months
        ) if remaining_months > 0 else Decimal('0')
        
        # Calculate original total payment
        original_total = original_emi * prepayment_request.loan_term_months
        
        # Calculate new total payment (payments made so far + remaining payments + prepayment)
        payments_made = original_emi * prepayment_request.prepayment_month
        remaining_payments = new_emi * remaining_months if remaining_months > 0 else Decimal('0')
        new_total = payments_made + prepayment_request.prepayment_amount + remaining_payments
        
        # Calculate savings
        total_savings = original_total - new_total
        interest_savings = total_savings  # Simplified calculation
        
        # Calculate tenure reduction
        original_months = prepayment_request.loan_term_months
        new_months = prepayment_request.prepayment_month + remaining_months
        tenure_reduction = original_months - new_months
        
        return PrepaymentAnalysisResponse(
            original_emi=original_emi,
            new_emi=new_emi if remaining_months > 0 else None,
            tenure_reduction_months=tenure_reduction,
            new_loan_term_months=new_months,
            interest_savings=interest_savings,
            total_savings=total_savings,
            savings=total_savings  # For compatibility with tests
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to analyze prepayment: {str(e)}"
        )
