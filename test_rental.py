"""Run with:  python -m unittest -v"""
import unittest
from datetime import date, timedelta

from app import app
from models import (CarInUseError, CarUnavailableError, FleetFullError, InvalidDataError,
                    LuxuryCar, RentalAgency, SUV, EconomyCar, Car)

CAR = dict(brand="Test", model="Car", year=2022, price_per_day=50, seats=5,
           transmission="automatic", fuel="petrol", color="#112233")


def day(offset):
    return date.today() + timedelta(days=offset)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.agency = RentalAgency()

    def test_fleet_limit_is_20(self):
        for _ in range(20):
            self.agency.add_car("economy", **CAR)
        with self.assertRaises(FleetFullError):
            self.agency.add_car("suv", **CAR)
        self.assertEqual(self.agency.car_count, 20)

    def test_removing_a_car_frees_a_slot(self):
        for _ in range(20):
            self.agency.add_car("economy", **CAR)
        self.agency.remove_car(1)
        self.agency.add_car("luxury", **CAR)
        self.assertEqual(self.agency.car_count, 20)

    def test_car_is_abstract(self):
        with self.assertRaises(TypeError):
            Car(1, **CAR)

    def test_polymorphic_discounts(self):
        self.assertEqual(EconomyCar(1, **CAR).rental_cost(7), 315.0)   # 10 % off
        self.assertEqual(SUV(2, **CAR).rental_cost(7), 332.5)          # 5 % off
        self.assertEqual(LuxuryCar(3, **CAR).rental_cost(7), 350.0)    # none
        self.assertEqual(EconomyCar(4, **CAR).rental_cost(3), 150.0)

    def test_invalid_car_data(self):
        for field, bad in [("price_per_day", -5), ("seats", 20), ("year", 1800),
                           ("fuel", "water"), ("color", "red"), ("brand", "")]:
            with self.assertRaises(InvalidDataError, msg=field):
                self.agency.add_car("suv", **{**CAR, field: bad})

    def test_overlapping_booking_rejected_but_back_to_back_allowed(self):
        car = self.agency.add_car("economy", **CAR)
        self.agency.create_booking(car.id, "Ali", "07501234567", day(1), day(4))
        with self.assertRaises(CarUnavailableError):
            self.agency.create_booking(car.id, "Sara", "07509876543", day(3), day(6))
        self.agency.create_booking(car.id, "Sara", "07509876543", day(4), day(6))

    def test_cancel_needs_matching_phone_and_frees_car(self):
        car = self.agency.add_car("economy", **CAR)
        booking = self.agency.create_booking(car.id, "Ali", "0750 123 4567", day(1), day(3))
        with self.assertRaises(Exception):
            self.agency.cancel_booking(booking.id, phone="07700000000")
        self.agency.cancel_booking(booking.id, phone="٠٧٥٠١٢٣٤٥٦٧")  # Kurdish digits work
        self.assertTrue(car.is_free(day(1), day(3)))

    def test_cannot_delete_car_with_active_booking(self):
        car = self.agency.add_car("economy", **CAR)
        booking = self.agency.create_booking(car.id, "Ali", "07501234567", day(1), day(3))
        with self.assertRaises(CarInUseError):
            self.agency.remove_car(car.id)
        self.agency.return_car(booking.id)
        self.agency.remove_car(car.id)

    def test_bad_dates_and_phone(self):
        car = self.agency.add_car("economy", **CAR)
        for start, end in [(day(-1), day(2)), (day(2), day(2)), (day(3), day(1)), (day(1), day(90))]:
            with self.assertRaises(InvalidDataError):
                self.agency.create_booking(car.id, "Ali", "07501234567", start, end)
        with self.assertRaises(InvalidDataError):
            self.agency.create_booking(car.id, "Ali", "abc", day(1), day(2))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.admin = {"X-Admin-Pin": "1234"}

    def test_cars_listing_and_filters(self):
        data = self.client.get("/api/cars").get_json()
        self.assertEqual(data["max"], 20)
        self.assertGreaterEqual(len(data["cars"]), 12)
        suvs = self.client.get("/api/cars?category=suv").get_json()["cars"]
        self.assertTrue(suvs and all(c["category"] == "suv" for c in suvs))
        hits = self.client.get("/api/cars?q=corolla").get_json()["cars"]
        self.assertEqual(len(hits), 1)

    def test_admin_endpoints_need_pin(self):
        self.assertEqual(self.client.post("/api/cars", json=CAR).status_code, 401)
        self.assertEqual(self.client.delete("/api/cars/1").status_code, 401)
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 401)
        self.assertEqual(self.client.post("/api/admin/login", json={"pin": "nope"}).status_code, 401)
        self.assertEqual(self.client.post("/api/admin/login", json={"pin": "1234"}).status_code, 200)

    def test_booking_flow(self):
        quote = self.client.get(f"/api/quote?car_id=1&start={day(10)}&end={day(17)}").get_json()
        self.assertEqual(quote["days"], 7)
        self.assertEqual(quote["total"], 220.5)  # 35 * 7 less 10 %
        made = self.client.post("/api/bookings", json={
            "car_id": 1, "name": "Test User", "phone": "0770 111 2222",
            "start": str(day(10)), "end": str(day(17))})
        self.assertEqual(made.status_code, 201)
        booking_id = made.get_json()["id"]
        mine = self.client.get("/api/bookings?phone=07701112222").get_json()["bookings"]
        self.assertEqual([b["id"] for b in mine], [booking_id])
        self.assertEqual(self.client.get("/api/bookings").get_json()["bookings"], [])
        bad = self.client.post(f"/api/bookings/{booking_id}/cancel", json={"phone": "0000000"})
        self.assertEqual(bad.status_code, 403)
        ok = self.client.post(f"/api/bookings/{booking_id}/cancel", json={"phone": "07701112222"})
        self.assertEqual(ok.get_json()["status"], "cancelled")

    def test_errors_are_json_codes(self):
        resp = self.client.post("/api/bookings", json={
            "car_id": 999, "name": "Ali", "phone": "07501234567",
            "start": str(day(1)), "end": str(day(2))})
        self.assertEqual((resp.status_code, resp.get_json()["error"]), (404, "car_not_found"))
        resp = self.client.post("/api/bookings", json={"car_id": 1, "name": "A", "phone": "1",
                                                       "start": "garbage", "end": "x"})
        self.assertEqual(resp.get_json()["error"], "invalid_dates")


if __name__ == "__main__":
    unittest.main()
