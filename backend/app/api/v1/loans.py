"""Loan management API endpoints."""
from typing import List, Optional
from datetime import date
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
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

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    loan_data: LoanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Create a new loan."""
    try:
        loan_service = LoanService(db)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get all loans for the current user."""
    try:
        loan_service = LoanService(db)
        loans = await loan_service.get_user_loans(current_user.id, status_filter)
        return loans
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loans: {str(e)}"
        )


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get a specific loan by ID."""
    try:
        loan_service = LoanService(db)
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
async def update_loan(
    loan_id: UUID,
    loan_data: LoanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Update a specific loan."""
    try:
        loan_service = LoanService(db)
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
async def delete_loan(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Delete a specific loan."""
    try:
        loan_service = LoanService(db)
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
async def make_payment(
    loan_id: UUID,
    payment_data: LoanPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Make a payment towards a loan."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Get all payments for a specific loan."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Get repayment schedule for a specific loan."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Get comprehensive summary for a specific loan."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Get comprehensive loan analytics for the current user."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Get loan summary for a specific month."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Calculate the impact of EMI changes on loan tenure and interest savings."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Analyze the impact of prepayment on loan tenure and interest savings."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Configure loan parameters (principal, interest rate, EMI, prepayment)."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Get comprehensive loan analysis with optimization suggestions and budget integration."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Calculate EMI for given loan parameters."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Compare multiple loan options."""
    try:
        loan_service = LoanService(db)
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
    db: AsyncSession = Depends(get_data_db)
):
    """Analyze the impact of prepayment on a loan."""
    try:
        loan_service = LoanService(db)
        
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
