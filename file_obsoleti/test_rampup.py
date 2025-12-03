"""Test ramp-up functionality."""
from peptide_manager.models.cycle import Cycle
from datetime import date, timedelta

# Test 1: Ramp schedule calculation
print("=== TEST 1: Ramp Schedule Calculation ===\n")

ramp_schedule = [
    {"week": 1, "percentage": 50},
    {"week": 2, "percentage": 75},
    {"week": 3, "percentage": 100}
]

start_date = date.today() - timedelta(days=10)  # 10 giorni fa (settimana 2)

cycle = Cycle(
    name="Test Ramp",
    start_date=start_date,
    ramp_schedule=ramp_schedule
)

# Testa settimana corrente
current_week = cycle.get_current_week()
print(f"Start date: {start_date}")
print(f"Today: {date.today()}")
print(f"Current week: {current_week}")
print()

# Testa percentuale per diverse date
test_dates = [
    (start_date, "Day 1 (Week 1)"),
    (start_date + timedelta(days=5), "Day 6 (Week 1)"),
    (start_date + timedelta(days=7), "Day 8 (Week 2)"),
    (start_date + timedelta(days=14), "Day 15 (Week 3)"),
    (start_date + timedelta(days=21), "Day 22 (Week 4+)"),
]

for test_date, label in test_dates:
    pct = cycle.get_ramp_percentage(test_date)
    week = cycle.get_current_week(test_date)
    print(f"{label}: Week {week} → {pct*100:.0f}%")

print("\n=== TEST 2: Dose Calculation ===\n")

target_dose = 500  # mcg
for test_date, label in test_dates:
    pct = cycle.get_ramp_percentage(test_date)
    ramped_dose = target_dose * pct
    print(f"{label}: {target_dose} mcg × {pct*100:.0f}% = {ramped_dose:.0f} mcg")

print("\n✅ All tests completed!")
