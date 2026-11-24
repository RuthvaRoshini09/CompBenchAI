import pandas as pd
from pathlib import Path

# Locate the dataset
DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "components.csv"
)


def load_components():
    """Load automotive component records."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    return pd.read_csv(DATA_PATH)


def get_all_components():
    """Return all available component records."""
    df = load_components()

    return df.to_dict(orient="records")


def compare_components(component_a_id, component_b_id):
    """Compare two versions of the same component."""

    df = load_components()

    if isinstance(component_a_id, str):
        component_a_id = component_a_id.strip()
    if isinstance(component_b_id, str):
        component_b_id = component_b_id.strip()

    component_a = df[df["Part_ID"] == component_a_id]
    component_b = df[df["Part_ID"] == component_b_id]

    if component_a.empty:
        raise ValueError(f"Component {component_a_id} not found")

    if component_b.empty:
        raise ValueError(f"Component {component_b_id} not found")

    a = component_a.iloc[0]
    b = component_b.iloc[0]

    if a["Part_Name"] != b["Part_Name"]:
        raise ValueError(
            "Please select two records with the same Part_Name."
        )

    # Python engineering calculations
    weight_difference = float(a["Weight_kg"] - b["Weight_kg"])
    cost_difference = float(b["Total_Cost_USD"] - a["Total_Cost_USD"])

    weight_reduction = (
        (weight_difference / float(a["Weight_kg"])) * 100
        if a["Weight_kg"] != 0
        else 0.0
    )

    cost_change = (
        (cost_difference / float(a["Total_Cost_USD"])) * 100
        if a["Total_Cost_USD"] != 0
        else 0.0
    )

    return {
        "component_name": str(a["Part_Name"]),

        "component_a": {
            "id": str(a["Part_ID"]),
            "vehicle": str(a["Vehicle_Model"]),
            "material": str(a["Material"]),
            "weight_kg": float(a["Weight_kg"]),
            "cost_usd": float(a["Total_Cost_USD"]),
            "manufacturing_process": str(a["Manufacturing_Process"])
        },

        "component_b": {
            "id": str(b["Part_ID"]),
            "vehicle": str(b["Vehicle_Model"]),
            "material": str(b["Material"]),
            "weight_kg": float(b["Weight_kg"]),
            "cost_usd": float(b["Total_Cost_USD"]),
            "manufacturing_process": str(b["Manufacturing_Process"])
        },

        "analysis": {
            "weight_difference_kg": round(weight_difference, 2),
            "weight_reduction_percent": round(weight_reduction, 2),
            "cost_difference_usd": round(cost_difference, 2),
            "cost_change_percent": round(cost_change, 2),
            "lighter_design": bool(
                b["Weight_kg"] < a["Weight_kg"]
            ),
            "lower_cost_design": bool(
                b["Total_Cost_USD"] < a["Total_Cost_USD"]
            ),
            "material_changed": bool(
                a["Material"] != b["Material"]
            ),
            "process_changed": bool(
                a["Manufacturing_Process"]
                != b["Manufacturing_Process"]
            )
        },

        "data_type": str(a.get("Data_Type", "Synthetic"))
    }
