"""Demo data: 12 cars (the limit is 20, so 8 slots stay free for the admin)."""
from models import CarRentalAgency

DEMO_CARS = [
    # category, brand, model, year, seats, transmission, fuel, daily_rate, color
    ("economy", "Toyota", "Corolla", 2022, 5, "automatic", "petrol", 35, "#c0392b"),
    ("economy", "Hyundai", "Elantra", 2021, 5, "automatic", "petrol", 32, "#2c3e50"),
    ("economy", "Kia", "Picanto", 2023, 4, "manual", "petrol", 22, "#f1c40f"),
    ("economy", "Nissan", "Sunny", 2020, 5, "automatic", "petrol", 28, "#7f8c8d"),
    ("economy", "Honda", "Civic", 2022, 5, "automatic", "petrol", 40, "#2980b9"),
    ("suv", "Toyota", "Land Cruiser", 2023, 7, "automatic", "diesel", 110, "#1a1a1a"),
    ("suv", "Hyundai", "Tucson", 2022, 5, "automatic", "petrol", 65, "#8e44ad"),
    ("suv", "Kia", "Sportage", 2023, 5, "automatic", "hybrid", 70, "#27ae60"),
    ("suv", "Nissan", "X-Trail", 2021, 7, "automatic", "petrol", 60, "#d35400"),
    ("luxury", "Mercedes-Benz", "E-Class", 2023, 5, "automatic", "petrol", 150, "#34495e"),
    ("luxury", "BMW", "5 Series", 2022, 5, "automatic", "hybrid", 160, "#ecf0f1"),
    ("luxury", "Tesla", "Model 3", 2023, 5, "automatic", "electric", 130, "#b71c1c"),
]


def build_demo_agency():
    agency = CarRentalAgency()
    for category, brand, model, year, seats, trans, fuel, rate, color in DEMO_CARS:
        agency.add_car(category, brand=brand, model=model, year=year, seats=seats,
                       transmission=trans, fuel=fuel, daily_rate=rate, color=color)
    return agency
