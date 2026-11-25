import pandas as pd
from pathlib import Path
from services.material_engine import get_material_intelligence

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

    if str(a["Part_Name"]).strip() != str(b["Part_Name"]).strip():
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

    # Engineering Trade-off Analysis & Deterministic Decision Summary (Phase 2)
    tradeoff = compute_tradeoff_analysis(
        weight_a=float(a["Weight_kg"]),
        weight_b=float(b["Weight_kg"]),
        cost_a=float(a["Total_Cost_USD"]),
        cost_b=float(b["Total_Cost_USD"]),
        id_a=str(a["Part_ID"]),
        id_b=str(b["Part_ID"]),
    )

    # Material & Manufacturing Intelligence (Phase 3)
    material_intelligence = get_material_intelligence(
        material_a=str(a["Material"]),
        material_b=str(b["Material"]),
        process_a=str(a["Manufacturing_Process"]),
        process_b=str(b["Manufacturing_Process"]),
        component_a={
            "id": str(a["Part_ID"]),
            "weight_kg": float(a["Weight_kg"]),
            "cost_usd": float(a["Total_Cost_USD"]),
            "material": str(a["Material"]),
            "process": str(a["Manufacturing_Process"])
        },
        component_b={
            "id": str(b["Part_ID"]),
            "weight_kg": float(b["Weight_kg"]),
            "cost_usd": float(b["Total_Cost_USD"]),
            "material": str(b["Material"]),
            "process": str(b["Manufacturing_Process"])
        },
        query_rag=True
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
            ),
            "tradeoff_analysis": tradeoff,
            "material_intelligence": material_intelligence
        },

        "tradeoff_analysis": tradeoff,
        "material_intelligence": material_intelligence,
        "data_type": str(a.get("Data_Type", "Synthetic"))
    }


USD_TO_INR_RATE = 85.0


def compute_tradeoff_analysis(
    weight_a,
    weight_b,
    cost_a,
    cost_b,
    id_a="Component A",
    id_b="Component B",
    rate=USD_TO_INR_RATE,
):
    """
    Compute deterministic engineering trade-off analysis and decision summary.

    Formulas:
      Weight Difference = Baseline Weight - Candidate Weight (positive = weight saved, negative = weight gained)
      Weight Reduction Percentage = (Weight Difference / Baseline Weight) * 100
      Additional Cost = Candidate Cost - Baseline Cost (positive = more expensive, negative = cheaper)
      Cost Change Percentage = (Additional Cost / Baseline Cost) * 100
      Cost per kg Saved = Additional Cost / Weight Saved (applicable only if Weight Saved > 0)
    """
    # Safe float parsing
    try:
        w_a = float(weight_a) if weight_a is not None else 0.0
        w_b = float(weight_b) if weight_b is not None else 0.0
    except (ValueError, TypeError):
        w_a, w_b = 0.0, 0.0

    try:
        c_a = float(cost_a) if cost_a is not None else 0.0
        c_b = float(cost_b) if cost_b is not None else 0.0
    except (ValueError, TypeError):
        c_a, c_b = 0.0, 0.0

    EPSILON = 0.0001

    # Weight Calculations
    weight_difference = w_a - w_b  # Baseline - Candidate
    has_valid_baseline_weight = w_a > EPSILON

    if has_valid_baseline_weight:
        weight_reduction_pct = (weight_difference / w_a) * 100.0
    else:
        weight_reduction_pct = 0.0

    # Direction and status for Weight
    if weight_difference > EPSILON:
        is_lighter = True
        weight_status = "lighter"
        weight_direction_label = "Weight Saved (Lighter)"
    elif weight_difference < -EPSILON:
        is_lighter = False
        weight_status = "heavier"
        weight_direction_label = "Weight Increased (Heavier)"
    else:
        is_lighter = None
        weight_status = "equal"
        weight_direction_label = "Equal Weight (No Change)"

    # Cost Calculations
    additional_cost = c_b - c_a  # Candidate - Baseline
    has_valid_baseline_cost = c_a > EPSILON

    if has_valid_baseline_cost:
        cost_change_pct = (additional_cost / c_a) * 100.0
    else:
        cost_change_pct = 0.0

    # Direction and status for Cost
    if additional_cost > EPSILON:
        is_cheaper = False
        cost_status = "more_expensive"
        cost_direction_label = "Additional Cost (Investment)"
    elif additional_cost < -EPSILON:
        is_cheaper = True
        cost_status = "cheaper"
        cost_direction_label = "Cost Savings"
    else:
        is_cheaper = None
        cost_status = "equal"
        cost_direction_label = "Equal Cost (Neutral)"

    # Currency conversion
    additional_cost_inr = additional_cost * rate

    # Cost per kg Saved
    # Applicable ONLY when weight saved > 0
    weight_saved = weight_difference
    cost_per_kg_applicable = False
    cost_per_kg_usd = None
    cost_per_kg_inr = None
    cost_per_kg_type = "not_applicable"

    if weight_saved < -EPSILON:
        cost_per_kg_status = "not_applicable_heavier"
        cost_per_kg_reason = "Not applicable – candidate weight increased."
    elif abs(weight_saved) <= EPSILON:
        cost_per_kg_status = "not_applicable_equal"
        cost_per_kg_reason = "Not applicable – no weight reduction."
    else:
        # Candidate is lighter (weight_saved > 0)
        cost_per_kg_applicable = True
        if additional_cost > EPSILON:
            cost_per_kg_type = "investment"
            cost_per_kg_usd = round(additional_cost / weight_saved, 2)
            cost_per_kg_inr = round(cost_per_kg_usd * rate, 2)
            cost_per_kg_status = "additional_investment"
            cost_per_kg_reason = (
                f"${cost_per_kg_usd:,.2f}/kg (₹{cost_per_kg_inr:,.2f}/kg est.) "
                "additional investment required per kg of mass reduced."
            )
        elif additional_cost < -EPSILON:
            cost_per_kg_type = "savings"
            cost_per_kg_usd = round(abs(additional_cost) / weight_saved, 2)
            cost_per_kg_inr = round(cost_per_kg_usd * rate, 2)
            cost_per_kg_status = "cost_saving"
            cost_per_kg_reason = (
                f"Cost saving of ${cost_per_kg_usd:,.2f}/kg (₹{cost_per_kg_inr:,.2f}/kg est.) "
                "alongside mass reduction."
            )
        else:
            cost_per_kg_type = "neutral"
            cost_per_kg_usd = 0.0
            cost_per_kg_inr = 0.0
            cost_per_kg_status = "neutral_cost"
            cost_per_kg_reason = "$0.00/kg (Mass reduced at zero cost variance)."

    # Deterministic Engineering Decision Summary
    abs_wt_diff = abs(weight_difference)
    abs_wt_pct = abs(weight_reduction_pct)
    abs_cost_diff = abs(additional_cost)
    abs_cost_inr = abs(additional_cost_inr)
    abs_cost_pct = abs(cost_change_pct)

    if not has_valid_baseline_weight or not has_valid_baseline_cost:
        scenario_id = "E4"
        scenario_name = "Edge Case: Zero or Invalid Baseline Parameters"
        verdict = "Incomplete Baseline Data"
        recommendation_type = "warning"
        summary_text = (
            "Baseline component data contains non-positive weight or cost values. "
            "Reliable trade-off percentage metrics and decision summaries require verified non-zero baseline parameters."
        )
    elif weight_saved > EPSILON and additional_cost > EPSILON:
        # Scenario A: Lower Weight + Higher Cost
        scenario_id = "A"
        scenario_name = "Trade-off: Mass Reduction at Cost Premium"
        verdict = "Weight-Saving Trade-off"
        recommendation_type = "trade_off"
        summary_text = (
            f"Candidate [{id_b}] achieves a mass reduction of {abs_wt_diff:.2f} kg ({abs_wt_pct:.2f}%) "
            f"at an additional unit manufacturing cost of ${abs_cost_diff:,.2f} (est. ₹{abs_cost_inr:,.2f}, +{abs_cost_pct:.2f}%), "
            f"resulting in a lightweighting metric of ${cost_per_kg_usd:,.2f}/kg saved (est. ₹{cost_per_kg_inr:,.2f}/kg). "
            "This represents a classic automotive lightweighting trade-off rather than an unconditionally superior component. "
            "Adoption depends on platform weight-saving targets, EV range objectives, and target $/kg cost caps. "
            "Final selection requires structural, fatigue, and manufacturing validation."
        )
    elif weight_saved > EPSILON and additional_cost < -EPSILON:
        # Scenario B: Lower Weight + Lower Cost
        scenario_id = "B"
        scenario_name = "Dual Benefit: Mass Reduction and Cost Savings"
        verdict = "Favorable Dual Benefit"
        recommendation_type = "favorable"
        summary_text = (
            f"Candidate [{id_b}] achieves both a mass reduction of {abs_wt_diff:.2f} kg ({abs_wt_pct:.2f}%) "
            f"and a unit manufacturing cost savings of ${abs_cost_diff:,.2f} (est. ₹{abs_cost_inr:,.2f}, -{abs_cost_pct:.2f}%), "
            f"delivering a commercial saving of ${cost_per_kg_usd:,.2f}/kg saved. "
            f"Both mass and direct commercial metrics favor Candidate [{id_b}]. "
            "Component transition requires verifying that structural stiffness, crashworthiness, and tooling cycle times "
            "meet baseline engineering specifications."
        )
    elif weight_saved < -EPSILON and additional_cost < -EPSILON:
        # Scenario C: Higher Weight + Lower Cost
        scenario_id = "C"
        scenario_name = "Trade-off: Cost Reduction with Mass Penalty"
        verdict = "Economic Trade-off"
        recommendation_type = "trade_off"
        summary_text = (
            f"Candidate [{id_b}] delivers a unit manufacturing cost savings of ${abs_cost_diff:,.2f} (est. ₹{abs_cost_inr:,.2f}, -{abs_cost_pct:.2f}%), "
            f"but incurs a mass penalty of {abs_wt_diff:.2f} kg (+{abs_wt_pct:.2f}% heavier). "
            "This design is commercially advantageous for cost-sensitive vehicle architectures, provided the extra mass "
            "does not compromise dynamic handling, axle load limits, or fleet efficiency standards. "
            "Final engineering validation is required."
        )
    elif weight_saved < -EPSILON and additional_cost > EPSILON:
        # Scenario D: Higher Weight + Higher Cost
        scenario_id = "D"
        scenario_name = "Dual Penalty: Higher Weight and Higher Cost"
        verdict = "Unfavorable Benchmark Metrics"
        recommendation_type = "unfavorable"
        summary_text = (
            f"Candidate [{id_b}] incurs both a mass penalty of {abs_wt_diff:.2f} kg (+{abs_wt_pct:.2f}%) "
            f"and an additional unit cost of ${abs_cost_diff:,.2f} (est. ₹{abs_cost_inr:,.2f}, +{abs_cost_pct:.2f}%). "
            "Direct benchmarking metrics are unfavorable on mass and cost alone; however, Candidate [{id_b}] "
            "must not be declared technically inferior without evaluating functional criteria outside mass/cost scope "
            "(such as crash energy management, acoustic NVH attenuation, thermal performance, or high-volume tooling life)."
        )
    elif abs(weight_saved) <= EPSILON and abs(additional_cost) <= EPSILON:
        # Scenario E1: Equal Weight & Equal Cost
        scenario_id = "E1"
        scenario_name = "Neutral: Identical Weight and Cost"
        verdict = "Neutral Benchmark"
        recommendation_type = "neutral"
        summary_text = (
            f"Candidate [{id_b}] matches Baseline [{id_a}] in both mass ({w_a:.2f} kg) "
            f"and unit manufacturing cost (${c_a:,.2f}). Selection between these designs should be determined by "
            "manufacturing tooling availability, cycle time, material recyclability, or OEM platform commonality."
        )
    elif abs(weight_saved) <= EPSILON and abs(additional_cost) > EPSILON:
        # Scenario E2: Equal Weight, Cost Variance
        scenario_id = "E2"
        scenario_name = "Cost Variance at Equal Mass"
        verdict = "Pure Cost Trade-off"
        recommendation_type = "trade_off"
        cost_dir = "an additional cost of" if additional_cost > 0 else "a cost savings of"
        summary_text = (
            f"Both components have identical mass ({w_a:.2f} kg). The trade-off is purely economic: "
            f"Candidate [{id_b}] carries {cost_dir} ${abs_cost_diff:,.2f} (est. ₹{abs_cost_inr:,.2f}, {abs_cost_pct:.2f}%). "
            "Selection is governed by direct unit economics and tooling amortization."
        )
    elif weight_saved > EPSILON and abs(additional_cost) <= EPSILON:
        # Scenario E3a: Lighter at Equal Cost
        scenario_id = "E3a"
        scenario_name = "Mass Reduction at Cost Parity"
        verdict = "Favorable Mass Reduction"
        recommendation_type = "favorable"
        summary_text = (
            f"Both components carry identical manufacturing costs (${c_a:,.2f}). "
            f"Candidate [{id_b}] achieves a mass reduction of {abs_wt_diff:.2f} kg ({abs_wt_pct:.2f}%) "
            "at zero additional cost, delivering direct lightweighting benefits without economic penalty."
        )
    else:
        # Scenario E3b: Heavier at Equal Cost
        scenario_id = "E3b"
        scenario_name = "Mass Penalty at Cost Parity"
        verdict = "Unfavorable Mass Metric"
        recommendation_type = "trade_off"
        summary_text = (
            f"Both components carry identical manufacturing costs (${c_a:,.2f}). "
            f"Candidate [{id_b}] adds {abs_wt_diff:.2f} kg (+{abs_wt_pct:.2f}% heavier) "
            "with zero cost savings, resulting in a mass penalty without economic compensation."
        )

    return {
        "baseline_weight_kg": round(w_a, 2),
        "candidate_weight_kg": round(w_b, 2),
        "weight_difference_kg": round(weight_difference, 2),
        "weight_change_pct": round(weight_reduction_pct, 2) if has_valid_baseline_weight else None,
        "weight_status": weight_status,
        "weight_direction_label": weight_direction_label,
        "is_lighter": is_lighter,

        "baseline_cost_usd": round(c_a, 2),
        "candidate_cost_usd": round(c_b, 2),
        "additional_cost_usd": round(additional_cost, 2),
        "additional_cost_inr": round(additional_cost_inr, 2),
        "cost_change_pct": round(cost_change_pct, 2) if has_valid_baseline_cost else None,
        "cost_status": cost_status,
        "cost_direction_label": cost_direction_label,
        "is_cheaper": is_cheaper,

        "cost_per_kg_saved_applicable": cost_per_kg_applicable,
        "cost_per_kg_saved_usd": cost_per_kg_usd,
        "cost_per_kg_usd": cost_per_kg_usd,
        "cost_per_kg_saved_inr": cost_per_kg_inr,
        "cost_per_kg_inr": cost_per_kg_inr,
        "cost_per_kg_status": cost_per_kg_status,
        "cost_per_kg_type": cost_per_kg_type,
        "cost_per_kg_reason": cost_per_kg_reason,

        "decision": {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "verdict": verdict,
            "recommendation_type": recommendation_type,
            "summary_text": summary_text,
        },
        "currency_rate": rate,
        "disclaimer": "INR estimates use ₹85/USD illustrative rate. Calculations are deterministic Python ground truth."
    }
