# YAT Geo DB

An elegantly simple Geo Reference manager with managed database of US, Canada and Mexico. 
Quickly perform auto-complete style fuzzy search, fetch record details and search
a mile radius around a specific place.

Geo DB file lists available at `https://yat-geo-db.sfo3.digitaloceanspaces.com/`


## Install 

With Python 3.7 or greater install the package with simple pip command.

```
pip install yat-geo-db
```

## Usage

The manager utilizes two flat files maintained by YAT available at `<location>`.
On initial load those files will be downloaded to local machined and stored on 
machine as a form of cache.  You can specify a specific version denoted by date 
or utilize the current version.


Import and load data
```python
from yat_geo_db import GeoManager as GeoManagerImport

GeoManager = GeoManagerImport()

GeoManager.load_data(
    force_db_fetch= False, cache_local=True, compressed=True
)
```

Refresh local data (current version)

```python
from yat_geo_db import GeoManager as GeoManagerImport

GeoManager = GeoManagerImport()

GeoManager.load_data(force_db_fetch=True)
```

Perform Auto-complete style search
```python
search_param = "Nashvil"
filters = {"ref_data.state_prov": "TN", "ref_data.country": "US"}
fuzzy_res = GeoManager.fuzzy_search(
    search_param, num_results=2, filters=filters
)
print([(value["value"], value["id"]) for value in fuzzy_res])
>>> [('Nashville, TN', 'us__tn__nashville'), ('Nashville Metro Area, TN', 'nashville_tn_us_metro')]
```

Apply filters for any element in shape object including `geo_type` and `ref_data`,
latter allowing to refine search to specific country or state.

```python
search_param = "Nashvil"
filters = {"geo_type": "ZipCode", "ref_data.country": "US"}
fuzzy_res = GeoManager.fuzzy_search(
    search_param, num_results=2, filters=filters
)
print([(value["value"], value["id"]) for value in fuzzy_res])
>>> []
```

Fetch a shape object by the reference code.  All reference codes follow a hierarchical
structure, for below example `<country>__<state>__<name with _ seperator>`.

```python
reference_code = 'us__tn__nashville'

res = GeoManager.get_shape_by_ref_code(reference_code=reference_code)

print(res)

>>> {'value': 'Nashville, TN',
>>>  'clean_value': 'nashville tn',
>>>  'id': 6818,
>>>  'area': 0.0,
>>>  'bbox': {'ll_latitude': '36.165890',
>>>   'ur_latitude': '36.165890',
>>>   'll_longitude': '-86.784440',
>>>   'ur_longitude': '-86.784440'},
>>>  'geo_type': 'City',
>>>  'latitude': 36.16589,
>>>  'ref_data': {'city': 'Nashville',
>>>   'country': 'US',
>>>   'zip_code': '37222',
>>>   'state_prov': 'TN'},
>>>  'longitude': -86.78444,
>>>  'population': 530852,
>>>  'is_zip_code': False,
>>>  'is_aggregate': False,
>>>  'long_display': 'Nashville, TN 37222',
>>>  'short_display': 'Nashville, TN',
>>>  'primary_source': None,
>>>  'reference_code': 'us__tn__nashville',
>>>  'primary_timezone': 'America/Chicago',
>>>  'related_shape_id': 6718,
>>>  'primary_source_id': None,
>>>  'is_three_digit_zip_code': False}
```

Perform radius search around a Geo Object, utilizing a reference code, radius in
miles and indicator to return results within the same country.  Results returned 
are a list of Geo Shape IDs or with `full_results=True` a full list of Geo Objects 
returned.

```python
reference_code = 'us__tn__nashville'

res = GeoManager.radius_search(
    reference_code=reference_code, radius=10, country_exact=True
)

print(res)
>>> [6702, 6831, 142898, 142897, 142895, 142901, 142903, 142904, 142905, 142910, 142893, 119979, 104924, 258833, 259091, 118948, 
>>> 118950, 119199, 119208, 119565, 119569, 119570, 119978, 259331, 239701, 242429, 6764, 98, 6609, 6818, 242049, 6612, 6621, 
>>> 142899, 142900, 241027, 119206, 119572, 133787, 119196, 119567, 119977, 6622, 134214, 134217, 143024, 179468, 133797, 133808, 
>>> 119980, 119201, 119204, 119205, 119210, 142902, 142906, 142907, 142908, 142909]
```

### Example 

For an example microservice implementation with Flask check out this [repository](https://github.com/yat-co/yat_geo_db_api).

Of try out the free API with documentation here [YAT Demo](https://demo.yat.ai).