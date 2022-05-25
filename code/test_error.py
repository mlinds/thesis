# %%
from atl_module import icesat_bathymetry
from atl_module.refraction_correction import refr_corrected_depth
from atl_module.error_calc import calc_rms_error
from atl_module.raster_interaction import query_raster
from atl_module.geospatial_functions import add_track_dist_meters
from glob import iglob

# %%
folderpath = '../data/test_sites/florida_keys'
# get_bathymetry
bathy_points = icesat_bathymetry.bathy_from_all_tracks_parallel(folderpath)
# %%


# %%
true_bathy = query_raster(bathy_points,src='../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt')

# %%
bathy_points = bathy_points.assign(fema_elev = true_bathy)
bathy_points.eval('sf_refr = sea_level_interp - 0.77*(sea_level_interp - z_kde)',inplace=True)
# %%
bathy_points.eval('error = sf_refr-fema_elev',inplace=True)
calc_rms_error(bathy_points, ['fema_elev'])
# %%

gdf = add_track_dist_meters(bathy_points.to_records(),geodataframe=True)
# %%
gdf.to_file('../data/test_sites/florida_keys/all_bathy_pts.gpkg',overwrite=True)

# %%
gdf.error.plot.hist(bins=50)

bathy_points.plot.scatter(y='z_kde',x='fema_elev',alpha=0.1,figsize=(20,20))