from pydantic import BaseModel, ConfigDict, Field, model_validator


class MetricResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    working_capital: float = Field(..., description="Current assets minus current liabilities")
    current_ratio: float = Field(..., description="Current assets divided by current liabilities")
    debt_to_asset: float = Field(..., description="Total liabilities divided by total assets")
    equity_ratio: float = Field(..., description="Net worth divided by total assets")
    operating_margin: float = Field(..., description="Net farm income divided by gross revenue")
    net_farm_income: float = Field(..., description="Annual net farm income")
    dscr: float = Field(..., description="Debt service coverage ratio")
    operating_expense_ratio: float = Field(..., description="Operating costs divided by gross revenue")


class RiskResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mean_income: float = Field(..., description="Mean simulated income")
    p10_income: float = Field(..., description="10th percentile simulated income")
    p50_income: float = Field(..., description="50th percentile simulated income")
    p90_income: float = Field(..., description="90th percentile simulated income")
    mean_dscr: float = Field(..., description="Mean simulated debt service coverage ratio")
    p10_dscr: float = Field(..., description="10th percentile simulated debt service coverage ratio")
    default_probability: float = Field(..., ge=0, le=1, description="Probability that DSCR falls below 1.0")
    worst_case_shortfall: float = Field(..., description="Worst simulated shortfall relative to debt service")
    simulation_runs: int = Field(..., gt=0, description="Number of Monte Carlo simulations")

    @model_validator(mode="after")
    def validate_percentile_ordering(self) -> "RiskResults":
        if not self.p10_income <= self.p50_income <= self.p90_income:
            raise ValueError("Income percentiles must satisfy p10 <= p50 <= p90")

        if self.p10_dscr - self.mean_dscr > 1e-9:
            raise ValueError("p10_dscr cannot exceed mean_dscr")

        return self


__all__ = ["MetricResults", "RiskResults"]
