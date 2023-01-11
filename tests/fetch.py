import unittest

from yat_geo_db import GeoManager


class FetchTest(unittest.TestCase):
	def setUp(self):
		self.GeoManager = GeoManager()
		self.GeoManager.load_data()

	def tearDown(self):
		pass

	def test_results_returned(self):
		result = self.GeoManager.get_shape_by_ref_code(reference_code="us__60606")
		self.assertIsInstance(result, dict, 'Result is not of type `dict`')


if __name__ == '__main__':
	unittest.main()
