from .fuzzy import ngrams, tversky_index
from .geometry import (
    latitude_delta_from_miles, longitude_delta_from_miles, lat_lng_dist
)
from .settings import BASE_STORE_URL
from .utils import get_key

from jellyfish import damerau_levenshtein_distance

from datetime import datetime
from collections import Counter
import logging
from math import log
import os
import json
from pathlib import Path
import pytz
import re
import requests
from statistics import mean
from typing import Dict, List, Set, Union


logger = logging.getLogger(__name__)


def geo_damerau_levenshtein_distance(val1, val2):
    return min(
        damerau_levenshtein_distance(val1.split(',')[0], val2.split(',')[0]),
        damerau_levenshtein_distance(val1, val2)
    )


def geo_auto_complete_score(result: Dict) -> float:
    """
    Geo Auto Complete Scoring considering both tversky index rating and
    population
    """
    if result['population'] <= 0:
        return (result['rating'] * .9)
    return (result['rating'] * .9) + (log(result['population']) * .1)


def apply_shape_filters(value, filters):
    """Apply Filters to Geo Shape object payload"""
    # No Need to Filter if no filters applied
    if filters is None:
        return True

    if value is None or not isinstance(value, dict):
        return False

    # Apply Filters
    return all(
        filter_value == get_key(value, filter_key)
        for filter_key, filter_value in filters.items()
    )


class ShapeManager(object):
    """
    Manager for Get actions
    """
    def get_shape_ref_code(self, shape_id: int) -> str:
        """Get Shape Reference Code from Shape ID"""
        return self.id_reference_code_map.get(shape_id)
    
    def get_shape_geo_type(self, shape_id: int) -> str:
        """Get Shape Reference Code from Shape ID"""
        shape = self.get_shape_by_id(shape_id=shape_id)
        return (shape or {}).get('geo_type')

    def get_shape_id_by_ref_code(self, reference_code: str) -> int:
        """Get Shape ID from Shape Reference Code"""
        shape = self.get_shape_by_ref_code(reference_code=reference_code)
        return (shape or {}).get('id')

    def get_shape_geo_type_by_ref_code(self, reference_code: str) -> int:
        """Get Shape Geo Type from Shape Reference Code"""
        shape = self.get_shape_by_ref_code(reference_code=reference_code)
        return (shape or {}).get('geo_type')

    def get_shape_by_ref_code(self, reference_code):
        """
        Helper function to get Shape Object from Shape Reference Code
        """
        return self.geo_shape_dict.get(reference_code)

    def get_shape_by_id(self, shape_id):
        """
        Helper function to get Shape Object from Shape ID
        """
        reference_code = self.get_shape_ref_code(shape_id)
        return self.get_shape_by_ref_code(reference_code=reference_code)

    def get_quote_location_by_id(self, shape_id):
        shape = self.get_shape_by_id(shape_id=shape_id) or {}
        ref_data = shape.get('ref_data') or {}
        if shape.get('geo_type') == 'MetroArea':
            return {
                'namesake_city': ref_data.get('city'),
                'reference_code': shape.get('reference_code'),
                'metro_area_name': ref_data.get('metro'),
                'metro_area_size_rank': ref_data.get('metro_size'),
                'namesake_city_state_code': ref_data.get('state_prov'),
                'metro_area_primary_state_code': ref_data.get('state_prov'),
                'metro_area_primary_country_code': ref_data.get('country'),
            }
        else:
            return {
                'zip_code': ref_data.get('zip_code'),
                'city_name': ref_data.get('city'),
                'state_code': ref_data.get('state_prov'),
                'country_code': ref_data.get('country'),
            }

    def get_quote_location_by_reference_code(self, reference_code):
        shape = self.get_shape_by_ref_code(reference_code=reference_code)
        ref_data = shape.get('ref_data') or {}
        return {
            'zip_code': ref_data.get('zip_code'),
            'city_name': ref_data.get('city'),
            'state_code': ref_data.get('state_prov'),
            'country_code': ref_data.get('country'),
        }

    def get_shape_display_by_id(self, shape_id: int, long_desc: bool = True, user_friendly: bool = False):
        """
        Helper function to get Shape Display from Shape ID
        """
        reference_code = self.get_shape_ref_code(shape_id=shape_id)
        return self.get_shape_display_by_ref_code(
            reference_code=reference_code, long_desc=long_desc, user_friendly=user_friendly
        )

    def get_shape_display_by_ref_code(self, reference_code, long_desc: bool = True, user_friendly: bool = False):
        """
        Helper function to get Shape Object from Shape Reference Code
        """
        shape_obj = self.geo_shape_dict.get(reference_code)
        # For Zip Code & County -> Route Long Desc (Route to City/Zip)
        if user_friendly and (shape_obj or {}).get('geo_type', '') in ('County', 'ZipCode'):
            return (shape_obj or {}).get('long_display', None)
        if user_friendly and (shape_obj or {}).get('geo_type', '') in ('MetroArea',):
            return (shape_obj or {}).get('short_display', None)
        if long_desc:
            return (shape_obj or {}).get('long_display', None)
        return (shape_obj or {}).get('short_display', None)

    def get_shape_time_by_ref_code(self, reference_code):
        """
        Get Current Time for Shape by Reference Code
        """
        shape_obj = self.get_shape_by_ref_code(reference_code=reference_code)
        if shape_obj.get('primary_timezone') is None:
            return datetime.now()
        return datetime.now().astimezone(tz=pytz.timezone(shape_obj.get('primary_timezone')))

    def get_shape_time_by_id(self, shape_id):
        """
        Get Current Time for Shape by Shape ID
        """
        reference_code = self.get_shape_ref_code(shape_id=shape_id)
        return self.get_shape_time_by_ref_code(reference_code=reference_code)


class RadiusSearchShape(object):
    def __init__(self, shape_obj):
        self.pk = shape_obj['id']
        self.is_aggregate = shape_obj.get('is_aggregate', False)
        self.latitude = float(shape_obj['latitude'])
        self.longitude = float(shape_obj['longitude'])
        self.area = shape_obj['area']
        self.short_display = shape_obj['short_display']
        self.reference_code = shape_obj['reference_code']
        self.shape_extra = shape_obj

        # Set Bounding Box for Aggregates
        if self.is_aggregate:
            for key, value in shape_obj['bbox'].items():
                setattr(self, key, float(value or 0))

    def radius_match(self, latitude, longitude, lat_delta, lng_delta, country_filter: str = None):
        if self.is_aggregate:
            return self.radius_check_contains(latitude, longitude, lat_delta, lng_delta, country_filter)
        else:
            return self.radius_check_dist(latitude, longitude, lat_delta, lng_delta, country_filter)

    def radius_check_dist(self, latitude, longitude, lat_delta, lng_delta, country_filter: str = None):
        # This is approximate distance.  It performs well for small radii, but will not be accurate for larger radii.
        # We can use lat_lng_dist instead - more computation, but is more accurate.
        if country_filter is not None:
            if country_filter != self.shape_extra.get('ref_data', {}).get('country') != country_filter:
                return False

        return (((((latitude - self.latitude) / lat_delta)**2) +
                 (((longitude - self.longitude) / lng_delta)**2))
                < 1)

    def radius_check_contains(self, latitude, longitude, lat_delta, lng_delta, country_filter: str = None):
        try:
            if country_filter is not None:
                if country_filter != self.shape_extra.get('ref_data', {}).get('country') != country_filter:
                    return False

            return (
                (self.ur_latitude >= latitude >= self.ll_latitude) &
                (self.ur_longitude >= longitude >= self.ll_longitude)
            )
        except Exception:
            logger.error(
                f"Error with Radius check: shape_id={self.pk}", exc_info=True
            )
            return False


class RadiusSearchManager(object):

    def get_radius_shape_by_ref_code(self, reference_code):
        """
        Helper function specific to Radius Search to get Radius Shape Object via Reference Code
        different from the standard `get_shape_by_ref_code` as the object returned is 
        object specific for Radius Searches
        """
        return self.radius_search_map.get(reference_code)

    def get_radius_shape_by_id(self, shape_id):
        """
        Helper function specific to Radius Search to get Radius Shape Object via Shape ID
        different from the standard `get_shape_by_id` as the object returned is 
        object specific for Radius Searches
        """
        reference_code = self.get_shape_ref_code(shape_id)
        return self.radius_search_map.get(reference_code)

    def radius_search(self,
                      reference_code,
                      radius,
                      country_exact: bool = False,
                      full_results: bool = False):
        """
        Perform Radius Search by Reference Code
        
        Parameters
        -----------
            reference_code str
                Geo Reference Code, example `us__tn__nashville`
            radius int
                Radius around reference_code in miles to return results
            country_exact bool
                Country exact, default False to return only Geo Shapes within the 
                same country as the requested reference code
            full_results bool
                Full results, default False to return simply list of Shape IDs 
                or list of Shape Objects
        
        Returns 
        -----------
            results List[Union[int, Dict]]
                Results returned are either a list of Shape IDs or List of Shape 
                Objects 
        """
        shape_obj = self.get_shape_by_ref_code(reference_code=reference_code)
        if shape_obj is None:
            return []

        country_filter = None
        if country_exact:
            country_filter = shape_obj.get('ref_data', {}).get('country')

        shape_id_ls = self.get_radius_lat_lng_shape_ids(
            latitude=shape_obj['latitude'],
            longitude=shape_obj['longitude'],
            radius=radius, 
            country_filter=country_filter
        )

        # Return full results if parameter specified
        if full_results:
            shape_obj_ls = [
                self.get_shape_by_id(shape_id) for shape_id in shape_id_ls
            ]
            
            # Add Distance
            for shape_obj in shape_obj_ls:
                shape_obj.update({
                    "distance": self.get_shape_pair_distance(reference_code, shape_obj["reference_code"])
                })
            
            return shape_obj_ls

        return shape_id_ls

    def get_radius_lat_lng_shape_ids(self, latitude, longitude, radius, country_filter: str = None):
        lng_delta = longitude_delta_from_miles(lat=latitude, miles=radius)
        lat_delta = latitude_delta_from_miles(miles=radius)
        res = [
            radius_shape.pk for radius_shape in self.radius_search_map.values()
            if radius_shape.radius_match(
                latitude=latitude,
                longitude=longitude,
                lat_delta=lat_delta,
                lng_delta=lng_delta,
                country_filter=country_filter
            )
        ]
        return res

    def radius_lat_lng_search(self, latitude, longitude, radius, filters: Dict = None):
        lng_delta = longitude_delta_from_miles(lat=latitude, miles=radius)
        lat_delta = latitude_delta_from_miles(miles=radius)
        res = [
            radius_shape for radius_shape in self.radius_search_map.values()
            if radius_shape.radius_match(
                latitude = latitude,
                longitude = longitude,
                lat_delta = lat_delta,
                lng_delta = lng_delta
            ) 
            and not radius_shape.is_aggregate
            and apply_shape_filters(
                value=radius_shape.shape_extra, filters=filters
            )
        ]
        return res

    def get_shape_pair_distance(self, orig_shape_ref, dest_shape_ref) -> dict:
        """
        Get the distance between two Radius Shape object via `reference_code`
        """
        orig_shape = self.get_radius_shape_by_ref_code(reference_code=orig_shape_ref)
        dest_shape = self.get_radius_shape_by_ref_code(reference_code=dest_shape_ref)
        if orig_shape is None or dest_shape is None:
            logger.warning(
                f"[RadiusSearchManager] Unable to find orig/dest shape ref=`{orig_shape_ref}/{dest_shape_ref}"
            )
            return {'distance': 999, 'normalized_distance': 999, 'aggregate': False}

        distance = round(lat_lng_dist(
                lat_lng_1 = (orig_shape.latitude, orig_shape.longitude),
                lat_lng_2 = (dest_shape.latitude, dest_shape.longitude),
            ), 4)

        # Point to Point Distance
        if not orig_shape.is_aggregate and not dest_shape.is_aggregate:
            return {'distance': distance, 'normalized_distance': distance, 'aggregate': False}

        # Aggregate Location distance
        if orig_shape.is_aggregate:
            if orig_shape.area < 10:
                return {
                    'distance': distance,
                    'normalized_distance': distance,
                    'aggregate': True
                }
            return {
                'distance': distance,
                'normalized_distance': distance / log(max(orig_shape.area, 1)),
                'aggregate': True
            }
        elif dest_shape.is_aggregate:
            if dest_shape.area < 10:
                return {
                    'distance': distance,
                    'normalized_distance': distance,
                    'aggregate': True
                }
            return {
                'distance': distance,
                'normalized_distance': distance / log(max(dest_shape.area, 1)),
                'aggregate': True
            }
        else:
            # Both Areas Aggregates
            if orig_shape.area < 10 or dest_shape.area < 10:
                return {
                    'distance': distance,
                    'normalized_distance': distance,
                    'aggregate': True
                }
            return {
                'distance': distance,
                'normalized_distance': distance / log(max(mean(orig_shape.area, dest_shape.area), 1)),
                'aggregate': True
            }

    def get_shape_pair_distance_id(self, shape_ref, shape_id):
        """
        Wrapper function for `get_shape_pair_distance` where `id` over `reference_code`s
        is provided
        """
        shape_id_ref = self.get_shape_ref_code(shape_id)
        if shape_id_ref is None:
            logger.warning(f"[GeoManager] Unable to find `shape_id_ref` for id `{shape_id}`")
            return None, None
        return self.get_shape_pair_distance(shape_ref, shape_id_ref), shape_id_ref


class NgramSearchManager(object):
    def clean_ngram_cnt(self, word, n=3):
        word = re.sub('[^0-9a-zA-Z]+', '', word).lower()
        return dict(Counter([''.join(x) for x in zip(*[word[i:] for i in range(n)])]))

    def clean_entity(self, val):
        if self.lower_only:
            return re.sub('[^0-9a-zA-Z ]+', '', val).lower()
        else:
            return re.sub('[^0-9a-zA-Z ]+', '', val)

    def add_entity(self, entity, entity_id, partition=None, extra_entity=None):
        """
        Add Shape Entity to the Fuzzy Search Index
        """
        entity = self.clean_entity(entity)
        entity_ngram_ls = ngrams(entity, 3)
        
        # Converting Entity in dictionary to access
        entity = {'value': entity, 'clean_value': entity}
        if extra_entity is not None and isinstance(extra_entity, dict):
            entity.update(extra_entity)

        if self.partitioned:
            self.geo_shape_dict[partition].update({entity_id : entity})
        else:
            self.geo_shape_dict.update({entity_id : entity})

        for ngram in entity_ngram_ls:
            if self.partitioned:
                ngram_obs = self.search_dict[partition].get(ngram, []).copy()
                ngram_obs.append(entity_id)
                self.search_dict[partition].update({ngram : ngram_obs})
            else:
                ngram_obs = self.search_dict.get(ngram, []).copy()
                ngram_obs.append(entity_id)
                self.search_dict.update({ngram : ngram_obs})

    def _ngram_similarity(self, search_ngram_ls, source_str):
        source_ngram_ls = ngrams(source_str, 3)
        difference_num_ngrams = len(set(search_ngram_ls).symmetric_difference(set(source_ngram_ls)))
        num_search_ngrams = len(set(search_ngram_ls))
        return 1 - (difference_num_ngrams / num_search_ngrams)

    def entity_fuzzy_score(self, search_str: str, source_str: str) -> float:
        fuzzy_score = tversky_index(search_str, source_str, .85, .15)
        
        # Add to Fuzzy Score if starts with same substring
        fuzzy_score += (source_str.startswith(search_str) * (fuzzy_score * 0.15))
        return fuzzy_score

    def geo_search_score(self, search_str: str, source_str: str, population: int) -> float:
        # Postal Code
        if search_str.isnumeric():
            # Split to just base string
            fuzzy_score = self.entity_fuzzy_score(search_str, source_str.split(' ')[0])
        else:
            fuzzy_score = self.entity_fuzzy_score(search_str, source_str)

        if population <= 0 or fuzzy_score <= 0.65:
            return fuzzy_score * .9
        return (fuzzy_score * .9) + (log(population) * .1)

    def fuzzy_search(self, search_entity: str, partition=None, num_results=50, filters=None):
        """
        Sample values to compare against by passing the parameter `filters` to search
        {
            "value": "71330, US",
            "id": 140024,
            "reference_code": "us__71330",
            "geo_type": "ZipCode",
            "is_zip_code": true,
            "is_three_digit_zip_code": false
        }
        """
        search_entity = self.clean_entity(search_entity)
        search_ngram_ls = ngrams(search_entity, 3)

        if self.partitioned:
            ## Return Nothing if Partition Does not Exists
            if partition not in self.partitions:
                return []
            search_res = {
                ngram : self.search_dict[partition].get(ngram, '')
                for ngram in search_ngram_ls
            }
            # Larger Search Radius to Address Post Result Filtering
            top_search_res = dict(
                Counter([y for x in search_res.values() for y in x]).most_common(max(num_results, 500))
            )
            results = {
                self.geo_shape_dict[partition].get(key, {}).get('clean_value') : {
                    'value': self.geo_shape_dict.get(key, {}).get('value'),
                    'clean_value': self.geo_shape_dict[partition].get(key, {}).get('clean_value'),
                    'distance': geo_damerau_levenshtein_distance(
                        search_entity, self.geo_shape_dict[partition].get(key, {}).get('clean_value', '').lower()
                    ),
                    'ngram_similarity': self.entity_fuzzy_score(
                        search_entity,
                        self.geo_shape_dict[partition].get(key, {}).get('clean_value', '').lower()
                    ),
                    'score': self.geo_search_score(
                        search_entity,
                        self.geo_shape_dict[partition].get(key, {}).get('clean_value', '').lower(),
                        self.geo_shape_dict.get(key, {}).get('population', 0)
                    ),
                    'id': key,
                    'extra': self.geo_shape_dict[partition].get(key, None)
                }
                for key in top_search_res.keys()
                if apply_shape_filters(
                    value=self.geo_shape_dict[partition].get(key, {}),
                    filters=filters
                )
            }
        else:
            search_res = {ngram : self.search_dict.get(ngram, '') for ngram in search_ngram_ls}
            # Larger Search Radius to Address Post Result Filtering
            top_search_res = dict(
                Counter([y for x in search_res.values() for y in x]).most_common(max(num_results, 500))
            )
            results = {
                self.geo_shape_dict.get(key, {}).get('clean_value') : {
                    'value': self.geo_shape_dict.get(key, {}).get('value'),
                    'clean_value': self.geo_shape_dict.get(key, {}).get('clean_value'),
                    'distance': geo_damerau_levenshtein_distance(
                        search_entity,
                        self.geo_shape_dict.get(key, {}).get('clean_value', '').lower()
                    ),
                    'ngram_similarity': self.entity_fuzzy_score(
                        search_entity,
                        self.geo_shape_dict.get(key, {}).get('clean_value', '').lower(),
                    ),
                    'score': self.geo_search_score(
                        search_entity,
                        self.geo_shape_dict.get(key, {}).get('clean_value', '').lower(),
                        self.geo_shape_dict.get(key, {}).get('population', 0)
                    ),
                    'id': key,
                    'extra': self.geo_shape_dict.get(key, None)
                }
                for key in top_search_res.keys()
                if apply_shape_filters(
                    value=self.geo_shape_dict.get(key, {}),
                    filters=filters
                )
            }

        return [
            result for result in
            sorted(
                results.values(), key=lambda result: result['score'],
                reverse=True
            )][0:num_results]


class GeoManager(ShapeManager, RadiusSearchManager, NgramSearchManager):
    def __init__(self, partitions: Union[List, Set] = None, lower_only: bool = True):
        self.lower_only = lower_only # Indication if all stored items are lower case
        self.partitions = set(partitions) if partitions is not None else None
        self.partitioned = self.partitions is not None

        assert self.lower_only, "Currently only supports lower_only=True"
        assert not self.partitioned, "Currently only supports unpartitioned data"

        if self.partitioned:
            self.geo_shape_dict = {}
            self.search_dict = {}
            for partition in self.partitions:
                self.geo_shape_dict[partition] = {}
                self.search_dict[partition] = {}
        else:
            self.geo_shape_dict = {}
            self.search_dict = {}
        
        # Radius Search
        self._generate_maps()

    def _generate_maps(self):
        # Map Between IDs and Refence
        self.id_reference_code_map = {
            record['id']: record['reference_code'] for record in self.geo_shape_dict.values()
        }
        for value in self.geo_shape_dict.values():
            try:
                value.update({
                    'latitude': float(value['latitude']),
                    'longitude': float(value['longitude'])
                })
            except KeyError:
                logger.error(f'[GeoManager] `_generate_maps` key error', exc_info=True)

        self.radius_search_map = {
            ref_code: RadiusSearchShape(record) for ref_code, record in self.geo_shape_dict.items()
        }

    @property
    def num_shapes(self):
        return len(list(self.geo_shape_dict.keys()))

    def get_base_url(self, version: str = None):
        version_path = ''
        if version is not None:
            version_path = f"v/{version}/"
        return f"{BASE_STORE_URL}/{version_path}"

    def load_data(self, version: str = None, force_db_fetch: bool = False, cache_local: bool = True):
        search_file_name = 'geo_manager_ngram_search.json'
        geo_shape_file_name = 'geo_manager_shape.json'
        
        # Load Local
        local_path = os.path.join("temp", "data", "geo_db", version or "current")
        if os.path.exists(local_path) and not force_db_fetch:
            with open(os.path.join(local_path, search_file_name), 'r') as f:
                self.search_dict = json.load(f)

            with open(os.path.join(local_path, geo_shape_file_name), 'r') as f:
                self.geo_shape_dict = json.load(f)
            
            # Radius Search
            self._generate_maps()
            return
        
        # Load Search File
        response = requests.get(f'{self.get_base_url(version=version)}{search_file_name}')
        if response.status_code == 200: 
            self.search_dict = response.json()
        else:
            raise ValueError(f"Unable to load search file reason={response.text}")

        # Load Shape File
        response = requests.get(f'{self.get_base_url(version=version)}{geo_shape_file_name}')
        if response.status_code == 200: 
            self.geo_shape_dict = response.json()
        else:
            raise ValueError(f"Unable to load shape file reason={response.text}")

        # Cache Files to Local Disk
        if cache_local:
            Path(local_path).mkdir(parents=True, exist_ok=True)
            # Write to local
            with open(os.path.join(local_path, search_file_name), 'w') as f:
                json.dump(self.search_dict, f)

            with open(os.path.join(local_path, geo_shape_file_name), 'w') as f:
                json.dump(self.geo_shape_dict, f)
            
        # Radius Search
        self._generate_maps()
