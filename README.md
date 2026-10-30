# AutoRent - Car Rental System (Python / Flask, OOP, no database)

Bilingual website: **English** and **Kurdish (Sorani, right-to-left)**.
All data lives in memory (Python objects) - there is no database. The fleet is limited to **20 cars**.
Restarting the server resets the data to the 12 demo cars.

## Run (Windows)
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 - use the button in the top bar to switch language.
Admin page: `/admin`, password `admin123` (change it with the `ADMIN_PASSWORD` environment variable).

## Car photos
Photos are not included (no internet access when this was built). Add them either way:
- **Admin page:** log in at `/admin`, choose a picture next to each car and click *Upload photo* (also possible when adding a new car).
- **By file name:** copy pictures into `static/cars/` named after the car, e.g. `toyota-corolla.jpg`
  (see `static/cars/README.txt` for all 12 names).

Use pictures you are allowed to use (for example from Wikimedia Commons, with credit). Cars without a photo show an illustration.

## Files
| File | Purpose |
|------|---------|
| `models.py` | All OOP classes (see below) |
| `seed.py` | 12 demo cars |
| `translations.py` | English/Kurdish texts + `Translator` class |
| `app.py` | Flask routes (web layer only) |
| `templates/`, `static/` | HTML, CSS and JavaScript front end |

## OOP concepts in `models.py`
- **Abstraction** - `Vehicle` is an abstract class with the abstract method `calculate_cost()`
- **Inheritance** - `EconomyCar`, `SUV`, `LuxuryCar` extend `Vehicle`
- **Polymorphism** - each subclass prices a rental differently (SUV: 10% off from 7 days; Luxury: +$50 service fee)
- **Encapsulation** - private attributes (`_daily_rate`...) with validated properties
- **Composition** - `Booking` has a `Car` and a `Customer`; `CarRentalAgency` owns the cars and bookings
- **Factory pattern** - `CarFactory.create(category, ...)`
- **Custom exceptions** - `RentalError` and its children (`FleetFullError`, `CarUnavailableError`, ...)

## Features
- Browse and filter cars (category, max price, available between two dates)
- Booking with live price (JavaScript calls `/api/quote`, which uses the Python classes)
- Double-booking prevention by date overlap
- Look up / cancel bookings by phone number
- Admin: add/remove cars (blocked at 20 cars), see all bookings
