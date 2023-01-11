import unittest

from yat_geo_db import GeoManager


class RadiusSearchTest(unittest.TestCase):
	def setUp(self):
		self.GeoManager = GeoManager()
		self.GeoManager.load_data()

	def tearDown(self):
		pass

	def test_results_returned(self):
		results = self.GeoManager.radius_search(
            reference_code="us__60606", radius=50, country_exact=True
        )
		self.assertGreater(len(results), 0, 'No results returned')


if __name__ == '__main__':
	unittest.main()
