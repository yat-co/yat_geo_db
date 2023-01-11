import unittest

from yat_geo_db import GeoManager


class FuzzySearchTest(unittest.TestCase):
	def setUp(self):
		self.GeoManager = GeoManager()
		self.GeoManager.load_data()

	def tearDown(self):
		pass

	def test_results_returned(self):
		results = self.GeoManager.fuzzy_search(search_entity="Nashville, TN")
		self.assertGreater(len(results), 0, 'No results returned')


if __name__ == '__main__':
	unittest.main()
