import unittest
import numpy as np
from utils import round_max_value, round_min_value, calculate_step, grid_boundaries_from_centers

class TestRoundMaxValue(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(round_max_value(0), 0.0)

    def test_positive_numbers(self):
        self.assertEqual(round_max_value(123), 200)
        self.assertEqual(round_max_value(0.0456), 0.05)
        self.assertEqual(round_max_value(9), 9)

    def test_negative_numbers(self):
        self.assertEqual(round_max_value(-123), -200)
        self.assertEqual(round_max_value(-0.0456), -0.05)
        self.assertEqual(round_max_value(-9), -9)

    def test_edge_cases(self):
        self.assertEqual(round_max_value(1), 1)
        self.assertEqual(round_max_value(-1), -1)
        self.assertEqual(round_max_value(0.1), 0.1)
        self.assertEqual(round_max_value(-0.1), -0.1)

class TestRoundMinValue(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(round_min_value(0), 0.0)

    def test_positive_numbers(self):
        self.assertEqual(round_min_value(123), 100)
        self.assertEqual(round_min_value(0.0456), 0.04)
        self.assertEqual(round_min_value(9), 9)

    def test_negative_numbers(self):
        self.assertEqual(round_min_value(-123), -100)
        self.assertEqual(round_min_value(-0.0456), -0.04)
        self.assertEqual(round_min_value(-9), -9)

    def test_edge_cases(self):
        self.assertEqual(round_min_value(1), 1)
        self.assertEqual(round_min_value(-1), -1)
        self.assertEqual(round_min_value(0.1), 0.1)
        self.assertEqual(round_min_value(-0.1), -0.1)

class TestCalculateStep(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(calculate_step(0, 2), 1)
        self.assertEqual(calculate_step(-2, 0), 1)

    def test_positive_numbers(self):
        self.assertEqual(calculate_step(0.05, 0.1), 0.01)  # min_value is more precise
        self.assertEqual(calculate_step(3, 10), 1)  # min_value is more precise
        self.assertEqual(calculate_step(0.9, 1.5), 0.1)  # min_value is more precise

    def test_negative_numbers(self):
        self.assertEqual(calculate_step(-0.05, -0.1), 0.01)  # min_value is more precise
        self.assertEqual(calculate_step(-3, -10), 1)  # min_value is more precise
        self.assertEqual(calculate_step(-0.9, -1.5), 0.1)  # min_value is more precise

    def test_edge_cases(self):
        self.assertEqual(calculate_step(1, 10), 1)  # min_value is more precise
        self.assertEqual(calculate_step(-1, -10), 1)  # min_value is more precise
        self.assertEqual(calculate_step(0.1, 0.5), 0.1)  # min_value is more precise
        self.assertEqual(calculate_step(-0.1, -0.5), 0.1)  # min_value is more precise

class TestGridBoundariesFromCenters(unittest.TestCase):

    def test_regular_case(self):
        x_centers = [1, 2, 3, 4]
        y_centers = [10, 20, 30, 40]
        x_bounds, y_bounds = grid_boundaries_from_centers(x_centers, y_centers)

        np.testing.assert_array_almost_equal(x_bounds, [0.5, 1.5, 2.5, 3.5, 4.5])
        np.testing.assert_array_almost_equal(y_bounds, [5, 15, 25, 35, 45])

    def test_single_center(self):
        x_centers = [5]
        y_centers = [50]
        x_bounds, y_bounds = grid_boundaries_from_centers(x_centers, y_centers)

        np.testing.assert_array_almost_equal(x_bounds, [5])
        np.testing.assert_array_almost_equal(y_bounds, [50])

    def test_empty_centers(self):
        x_centers = []
        y_centers = []
        x_bounds, y_bounds = grid_boundaries_from_centers(x_centers, y_centers)

        self.assertEqual(len(x_bounds), 0)
        self.assertEqual(len(y_bounds), 0)


if __name__ == "__main__":
    unittest.main()
