"""
Domain model of the car rental system.

Pure Python: no web code and no database. Everything lives in memory.

OOP concepts demonstrated
-------------------------
* Abstraction     - Vehicle is an abstract base class (calculate_cost is abstract).
* Inheritance     - EconomyCar, SUV and LuxuryCar extend Vehicle.
* Polymorphism    - every subclass prices a rental differently.
* Encapsulation   - private attributes + validated properties.
* Composition     - a Booking has a Car and a Customer; the agency has cars and bookings.
* Factory pattern - CarFactory builds the right subclass from a category name.
* Custom errors   - a small exception hierarchy (RentalError and children).
"""
from abc import ABC, abstractmethod
from datetime import date
from threading import RLock


# --------------------------------------------------------------------------- #
#  Exceptions
# --------------------------------------------------------------------------- #
class RentalError(Exception):
    """Base class for every business-rule error. `code` maps to a translation."""
    code = "error"

    def __init__(self, **params):
        super().__init__(self.code)
        self.params = params


class FleetFullError(RentalError):
    code = "fleet_full"


class CarNotFoundError(RentalError):
    code = "car_not_found"


class BookingNotFoundError(RentalError):
    code = "booking_not_found"


class CarUnavailableError(RentalError):
    code = "car_unavailable"


class CarHasBookingsError(RentalError):
    code = "car_has_bookings"


class InvalidDatesError(RentalError):
    code = "invalid_dates"


class InvalidInputError(RentalError):
    code = "invalid_input"


# --------------------------------------------------------------------------- #
#  Small validation helpers
# --------------------------------------------------------------------------- #
def _text(value, field, max_len=40):
    value = str(value or "").strip()
    if not value or len(value) > max_len:
        raise InvalidInputError(field=field)
    return value


def _number(value, field, low, high, cast=int):
    try:
        number = cast(value)
    except (TypeError, ValueError):
        raise InvalidInputError(field=field)
    if not (low <= number <= high):
        raise InvalidInputError(field=field)
    return number


# --------------------------------------------------------------------------- #
#  Vehicles
# --------------------------------------------------------------------------- #
class Vehicle(ABC):
    """Abstract vehicle. Subclasses must say how a rental is priced."""

    CATEGORY = "vehicle"          # translation key suffix: cat_<CATEGORY>
    TRANSMISSIONS = ("automatic", "manual")
    FUELS = ("petrol", "diesel", "hybrid", "electric")

    def __init__(self, car_id, brand, model, year, seats,
                 transmission, fuel, daily_rate, color="#2c3e50"):
        self._id = car_id
        self._brand = _text(brand, "brand")
        self._model = _text(model, "model")
        self._year = _number(year, "year", 1990, date.today().year + 1)
        self._seats = _number(seats, "seats", 2, 9)
        if transmission not in self.TRANSMISSIONS:
            raise InvalidInputError(field="transmission")
        if fuel not in self.FUELS:
            raise InvalidInputError(field="fuel")
        self._transmission = transmission
        self._fuel = fuel
        self._daily_rate = 0.0
        self.daily_rate = daily_rate      # goes through the validated setter
        self._color = color if _is_hex_color(color) else "#2c3e50"

    # ---- read-only data ---------------------------------------------------
    @property
    def id(self):
        return self._id

    @property
    def brand(self):
        return self._brand

    @property
    def model(self):
        return self._model

    @property
    def name(self):
        return f"{self._brand} {self._model}"

    @property
    def year(self):
        return self._year

    @property
    def seats(self):
        return self._seats

    @property
    def transmission(self):
        return self._transmission

    @property
    def fuel(self):
        return self._fuel

    @property
    def color(self):
        return self._color

    @property
    def category(self):
        return self.CATEGORY

    # ---- validated, writable data ----------------------------------------
    @property
    def daily_rate(self):
        return self._daily_rate

    @daily_rate.setter
    def daily_rate(self, value):
        self._daily_rate = _number(value, "daily_rate", 1, 5000, cast=float)

    # ---- behaviour --------------------------------------------------------
    @abstractmethod
    def calculate_cost(self, days):
        """Total price for renting this vehicle for `days` days."""

    def __str__(self):
        return f"#{self.id} {self.name} ({self.year}) - {self.CATEGORY}"


class EconomyCar(Vehicle):
    CATEGORY = "economy"

    def calculate_cost(self, days):
        return round(self.daily_rate * days, 2)

class portsCar(Vehicle):
    CATEGORY = "Sport"
    SERVICE_FEE = 30.0
    def calculate_cost(self, days):
        return round(self.daily_rate * days, 2)


class SUV(Vehicle):
    CATEGORY = "suv"
    LONG_RENTAL_DAYS = 7
    LONG_RENTAL_DISCOUNT = 0.10

    def calculate_cost(self, days):
        cost = self.daily_rate * days
        if days >= self.LONG_RENTAL_DAYS:
            cost *= 1 - self.LONG_RENTAL_DISCOUNT
        return round(cost, 2)


class LuxuryCar(Vehicle):
    CATEGORY = "luxury"
    SERVICE_FEE = 50.0

    def calculate_cost(self, days):
        return round(self.daily_rate * days + self.SERVICE_FEE, 2)


class CarFactory:
    """Creates the correct Vehicle subclass from a category string."""
    _registry = {cls.CATEGORY: cls for cls in (EconomyCar, SUV, LuxuryCar)}

    @classmethod
    def categories(cls):
        return tuple(cls._registry)

    @classmethod
    def create(cls, category, car_id, **details):
        try:
            vehicle_class = cls._registry[category]
        except KeyError:
            raise InvalidInputError(field="category")
        return vehicle_class(car_id, **details)


def _is_hex_color(value):
    return (isinstance(value, str) and len(value) == 7 and value[0] == "#"
            and all(c in "0123456789abcdefABCDEF" for c in value[1:]))


# --------------------------------------------------------------------------- #
#  Customer and Booking
# --------------------------------------------------------------------------- #
class Customer:
    def __init__(self, name, phone):
        self.name = _text(name, "full_name", 60)
        cleaned = "".join(ch for ch in str(phone or "") if ch.isdigit())
        if not (7 <= len(cleaned) <= 15):
            raise InvalidInputError(field="phone")
        self.phone = cleaned              # digits only, so lookups are reliable


class Booking:
    ACTIVE = "active"
    CANCELLED = "cancelled"

    def __init__(self, booking_id, car, customer, start, end):
        self.id = booking_id
        self.car = car
        self.customer = customer
        self.start = start
        self.end = end
        self.status = self.ACTIVE
        self.total = car.calculate_cost(self.days)   # polymorphic call

    @property
    def days(self):
        return (self.end - self.start).days

    @property
    def is_active(self):
        return self.status == self.ACTIVE

    def overlaps(self, start, end):
        """True if [start, end) intersects this booking's period."""
        return self.is_active and start < self.end and end > self.start

    def cancel(self):
        self.status = self.CANCELLED


# --------------------------------------------------------------------------- #
#  The agency: owns the fleet and the bookings (in memory, max 20 cars)
# --------------------------------------------------------------------------- #
class CarRentalAgency:
    MAX_CARS = 20

    def __init__(self):
        self._cars = {}
        self._bookings = {}
        self._next_car_id = 1
        self._next_booking_id = 1001
        self._lock = RLock()          # the web server may handle requests in parallel

    # ---- fleet ------------------------------------------------------------
    @property
    def car_count(self):
        return len(self._cars)

    @property
    def is_full(self):
        return self.car_count >= self.MAX_CARS

    def add_car(self, category, **details):
        with self._lock:
            if self.is_full:
                raise FleetFullError(max=self.MAX_CARS)
            car = CarFactory.create(category, self._next_car_id, **details)
            self._cars[car.id] = car
            self._next_car_id += 1
            return car

    def remove_car(self, car_id):
        with self._lock:
            car = self.get_car(car_id)
            if any(b.car.id == car.id and b.is_active and b.end >= date.today()
                   for b in self._bookings.values()):
                raise CarHasBookingsError()
            del self._cars[car.id]

    def get_car(self, car_id):
        try:
            return self._cars[int(car_id)]
        except (KeyError, TypeError, ValueError):
            raise CarNotFoundError()

    def list_cars(self):
        return sorted(self._cars.values(), key=lambda c: c.id)

    # ---- availability and search -----------------------------------------
    def is_available(self, car, start, end):
        return not any(b.car.id == car.id and b.overlaps(start, end)
                       for b in self._bookings.values())

    def is_available_today(self, car):
        today = date.today()
        return not any(b.car.id == car.id and b.is_active
                       and b.start <= today < b.end
                       for b in self._bookings.values())

    @staticmethod
    def validate_dates(start, end):
        if start is None or end is None or start < date.today() or end <= start:
            raise InvalidDatesError()

    def search(self, category=None, max_price=None, start=None, end=None):
        if start is not None and end is not None:
            self.validate_dates(start, end)
        result = []
        for car in self.list_cars():
            if category and car.category != category:
                continue
            if max_price is not None and car.daily_rate > max_price:
                continue
            if start and end and not self.is_available(car, start, end):
                continue
            result.append(car)
        return result

    # ---- bookings ---------------------------------------------------------
    def quote(self, car_id, start, end):
        """Price check without creating a booking."""
        car = self.get_car(car_id)
        self.validate_dates(start, end)
        if not self.is_available(car, start, end):
            raise CarUnavailableError()
        days = (end - start).days
        return {"days": days, "total": car.calculate_cost(days)}

    def create_booking(self, car_id, name, phone, start, end):
        with self._lock:
            car = self.get_car(car_id)
            customer = Customer(name, phone)
            self.validate_dates(start, end)
            if not self.is_available(car, start, end):
                raise CarUnavailableError()
            booking = Booking(self._next_booking_id, car, customer, start, end)
            self._bookings[booking.id] = booking
            self._next_booking_id += 1
            return booking

    def get_booking(self, booking_id):
        try:
            return self._bookings[int(booking_id)]
        except (KeyError, TypeError, ValueError):
            raise BookingNotFoundError()

    def cancel_booking(self, booking_id):
        with self._lock:
            booking = self.get_booking(booking_id)
            booking.cancel()
            return booking

    def bookings_for_phone(self, phone):
        digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
        if not digits:
            return []
        return sorted((b for b in self._bookings.values() if b.customer.phone == digits),
                      key=lambda b: b.id, reverse=True)

    def list_bookings(self):
        return sorted(self._bookings.values(), key=lambda b: b.id, reverse=True)
