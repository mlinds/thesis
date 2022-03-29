#%%
from netCDF4 import Dataset as ncdf_ds
import xarray as xr
import glob
import numpy as np

filepath = '../data/ATLAS_test_subset/177187253/processed_ATL12_20181014092931_02410101_003_01.nc'

filelist = glob.glob('../data'+'/**/*.nc',recursive=True)

file = filelist[0]

def read_atl13(file):
    ds = ncdf_ds(file)

    beamgroups = [beam_name for beam_name in ds.groups if beam_name.startswith('gt')]

    all_hvals = np.ma.masked_array()
    all_lats = np.ma.masked_array()
    all_lons = np.ma.masked_array()

    for beam in beamgroups:
        pass
        # hvals = ds.groups[beam].groups['ssh_segments'].groups['heights'].variables['h'][:]
        # np.append(all_hvals,hvals)
        # lats = ds.groups[beam].groups['ssh_segments'].variables['latitude'][:]
        # np.append(all_lats,lats)
        # lons = ds.groups[beam].groups['ssh_segments'].variables['longitude'][:]
        # np.append(all_lons,lons)
        # hvals = ds.groups[beam].groups['ssh_segments'].groups['heights'].groups['h'][:]

    return ds

ds = read_atl13(file)
# %%
