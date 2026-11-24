
import pandas as pd
from pathlib import Path

# Create 10 automotive components
components = [
    ("Door Panel", "Interior", 3.5, 850),
    ("Dashboard Frame", "Interior", 5.2, 1200),
    ("Brake Pedal", "Braking", 1.4, 450),
    ("Control Arm", "Suspension", 4.8, 1500),
    ("Battery Bracket", "Electrical", 2.1, 650),
    ("Seat Frame", "Seating", 8.0, 1800),
    ("Engine Mount", "Powertrain", 2.8, 900),
    ("Bumper Support", "Exterior", 3.9, 1100),
    ("Steering Bracket", "Steering", 1.8, 700),
    ("Motor Housing", "Electrical", 4.5, 1600),
]

# Material weight and cost multipliers
materials = {
    "Steel": (1.0, 1.0),
    "Aluminum": (0.65, 1.25),
    "Plastic": (0.45, 0.65),
    "Magnesium": (0.55, 1.5),
    "Cast Iron": (1.15, 0.9),
}

vehicles = [
    ("Model A", "OEM A"),
    ("Model B", "OEM B"),
    ("Model C", "OEM C"),
    ("Model D", "OEM D"),
    ("Model E", "OEM E"),
]

processes = [
    "Stamping",
    "Casting",
    "Injection Molding",
    "Forging",
]

rows = []

# Generate 50 synthetic component records
for index, (part, subsystem, base_weight, base_cost) in enumerate(components):

    for material_index, (material, factors) in enumerate(materials.items()):

        weight_factor, cost_factor = factors
        vehicle, oem = vehicles[material_index]

        rows.append({
            "Part_ID": f"CB{index * 5 + material_index + 1:03d}",
            "Vehicle_Model": vehicle,
            "OEM": oem,
            "Subsystem": subsystem,
            "Part_Name": part,
            "Material": material,
            "Manufacturing_Process": processes[
                (index + material_index) % len(processes)
            ],
            "Weight_kg": round(base_weight * weight_factor, 2),
            "Total_Cost_USD": round(base_cost * cost_factor, 2),
            "Design_Complexity": [
                "Low", "Medium", "High"
            ][(index + material_index) % 3],
            "Data_Type": "Synthetic"
        })

# Save dataset
output_folder = Path("data")
output_folder.mkdir(exist_ok=True)

df = pd.DataFrame(rows)

df.to_csv(output_folder / "components.csv", index=False)

print("\n===== COMPBENCH AI DATASET =====")
print("Dataset generated successfully!")
print("Total records:", len(df))
print("\nAvailable columns:")
print(df.columns.tolist())
print("\nFirst 5 records:")
print(df.head().to_string(index=False))
