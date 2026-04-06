import os

from agfin.connectors import get_crop_price, get_crop_yield, get_production_data


def main() -> None:
    api_key = os.getenv("USDA_NASS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set USDA_NASS_API_KEY before running this script, for example:\n"
            'export USDA_NASS_API_KEY="your-key-here"'
        )

    crop = "corn"
    state = "IA"
    year = 2022

    print(f"Testing USDA NASS Quick Stats for {crop} in {state} for {year}")
    print("-" * 60)
    print("yield:", get_crop_yield(crop, state, year))
    print("price:", get_crop_price(crop, state, year))
    print("production:", get_production_data(crop, state, year))


if __name__ == "__main__":
    main()
