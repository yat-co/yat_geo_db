import numpy as np
from typing import Tuple

EARTH_RADIUS_MILES = 3958.756


def lat_lng_dist(lat_lng_1: Tuple[float, float],
                 lat_lng_2: Tuple[float, float]) -> float:
	"""
	Description
	-----------
		Distance as the crow flies, assuming the earther is a sphere.

	Parameters
	-----------
		lat_lng_1: Tuple (float,float)
			(<float: orig_lat>, <float: orig_lng>)
		lat_lng_2: Tuple (float,float)
			(<float: term_lat>, <float: term_lng>)

	Returns
	-----------
		Float
			Distance as the crow flies from origin lat/lng to destination lat/lng assuming the earth is a sphere or radius EARTH_RADIUS_MILES miles.
	"""
	lat1_rad = float(lat_lng_1[0]) * np.pi / 180
	lng1_rad = float(lat_lng_1[1]) * np.pi / 180
	lat2_rad = float(lat_lng_2[0]) * np.pi / 180
	lng2_rad = float(lat_lng_2[1]) * np.pi / 180
	dlat = lat2_rad - lat1_rad
	dlng = lng2_rad - lng1_rad
	a = np.sin(dlat/2) ** 2 + np.cos(lat1_rad) * \
            np.cos(lat2_rad) * np.sin(dlng/2) ** 2
	return 2 * EARTH_RADIUS_MILES * np.arctan(a ** .5 / (1-a) ** .5)


def latitude_delta_from_miles(miles):
	"""
	Description
	-----------
		Transforms North/South mileage deltas to latitude deltas.  Computes the latitude delta based on input miles, assuming the earth is a sphere.  Input miles are assumed to be purely North/South.

	Parameters
	-----------
		miles: Float/int
			Number of miles North/South to be converted to latitude delta

	Returns
	-----------
		Float
			The latitude delta necessarily to move the input number of miles
	"""
	return (miles / EARTH_RADIUS_MILES) * 180 / np.pi


def longitude_delta_from_miles(lat, miles):
	"""
	Description
	-----------
		Transforms East/West mileage deltas to longitude deltas.  Computes the longitude delta based on input miles, assuming the earth is a sphere.  Input miles are assumed to be purely East/West.  Note that latitude deltas depend on latitude reference location.

	Parameters
	-----------
		lat: Float/int
			Reference point latitude
		miles: Float/int
			Number of miles East/West to be converted to longitude delta

	Returns
	-----------
		Float
			The latitude delta necessarily to move the input number of miles
	"""
	r = EARTH_RADIUS_MILES * np.cos(lat * np.pi / 180)
	return (miles / r) * 180 / np.pi
