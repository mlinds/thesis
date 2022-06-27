import ee
from ee_plugin import Map

ee.Initialize()

image = ee.ImageCollection("LANDSAT/MANGROVE_FORESTS")

Map.addLayer(image, {"min": 0, "max": 1}, "Mangroves", True)
