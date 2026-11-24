
from services.component_engine import (
    get_all_components,
    compare_components
)

# Display available records
components = get_all_components()

print("Total components:", len(components))

# Compare two Door Panel records
result = compare_components("CB001", "CB002")

print("\n===== COMPONENT COMPARISON =====")
print("Component:", result["component_name"])

print("\nComponent A:", result["component_a"])
print("Component B:", result["component_b"])

print("\n===== ENGINEERING ANALYSIS =====")

for key, value in result["analysis"].items():
    print(f"{key}: {value}")
