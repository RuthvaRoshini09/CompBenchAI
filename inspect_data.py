
file_path = "data/components.csv"

print("Checking CSV file...\n")

with open(file_path, "r", encoding="utf-8-sig") as file:
    for number, line in enumerate(file, start=1):
        print(f"Line {number}: {line.rstrip()}")

        if number == 20:
            break
