import csv

references_csv = '/Users/apgupta/WORK/migrations/Customer/Kepler/Convert1105/results/conversions/conversion-2025-11-05-10-24-01/Reports/SnowConvert/ObjectReferences.20251105.102401.csv'
target_proc = '[DSS_EquityFactor].[FinRatio].[pFinancialRatioUpdate_ConsolidateRatio](NVARCHAR,DATETIME,NVARCHAR)'

dependencies = set()
dependents = set()

with open(references_csv, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        caller = row.get('Caller_CodeUnit_FullName', '').strip()
        referenced = row.get('Referenced_Element_FullName', '').strip()
        
        if caller == target_proc and referenced != target_proc:
            dependencies.add(referenced)
        
        if referenced == target_proc and caller != target_proc:
            dependents.add(caller)

print(f"Object: {target_proc}")
print(f"\nDirect Dependencies: {len(dependencies)}")
print("-" * 80)
for i, dep in enumerate(sorted(dependencies), 1):
    print(f"{i}. {dep}")

print(f"\nDirect Dependents: {len(dependents)}")
print("-" * 80)
for i, dep in enumerate(sorted(dependents), 1):
    print(f"{i}. {dep}")
