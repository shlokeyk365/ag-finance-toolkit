from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


CropName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CropMixItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop: CropName = Field(..., description="Name of the crop")
    acres: float = Field(..., gt=0, description="Acres allocated to this crop")
    expected_yield: float = Field(..., gt=0, description="Expected yield per acre")
    expected_price: float = Field(..., gt=0, description="Expected price per unit")


class FarmInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_acres: float = Field(..., gt=0, description="Total farm acreage")
    crop_mix: list[CropMixItem] = Field(
        ...,
        min_length=1,
        description="Crop acreage and revenue assumptions",
    )
    operating_costs: float = Field(..., ge=0, description="Annual operating costs")
    fixed_costs: float = Field(..., ge=0, description="Annual fixed costs")
    debt_obligations: float = Field(..., ge=0, description="Annual debt service")
    working_capital: float = Field(..., description="Current assets minus current liabilities")
    current_liabilities: float = Field(..., ge=0, description="Current liabilities")
    total_assets: float = Field(..., gt=0, description="Total assets")
    total_liabilities: float = Field(..., ge=0, description="Total liabilities")
    net_worth: float = Field(..., description="Total assets minus total liabilities")
    insurance_income: float = Field(default=0.0, ge=0, description="Insurance proceeds")
    govt_payments: float = Field(default=0.0, ge=0, description="Government support payments")
    interest_expense: float = Field(default=0.0, ge=0, description="Annual interest expense")
    depreciation: float = Field(default=0.0, ge=0, description="Annual depreciation expense")
    owner_draws: float = Field(default=0.0, ge=0, description="Owner withdrawals")

    @model_validator(mode="after")
    def validate_relationships(self) -> "FarmInputs":
        crop_acres = sum(item.acres for item in self.crop_mix)
        if crop_acres > self.total_acres:
            raise ValueError("Sum of crop acres cannot exceed total_acres")

        expected_net_worth = self.total_assets - self.total_liabilities
        if abs(self.net_worth - expected_net_worth) > 1e-6:
            raise ValueError("net_worth must equal total_assets minus total_liabilities")

        current_assets = self.working_capital + self.current_liabilities
        if current_assets < 0:
            raise ValueError(
                "working_capital and current_liabilities imply negative current_assets"
            )

        return self


__all__ = ["CropMixItem", "FarmInputs"]
