#%%
from netCDF4 import Dataset as ncdf_ds
import xarray as xr
import glob
import numpy as np

filepath = '../data/ATLAS_test_subset/177187253/processed_ATL12_20181014092931_02410101_003_01.nc'

filelist = glob.glob('../data/ATLAS_test_subset/*/*.nc',recursive=True)

file = filelist[0]

def read_atl13(file):
    ds = ncdf_ds(file)
    
    beamgroups = [beam_name for beam_name in ds.groups if beam_name.startswith('gt')]


    # for beam in beamgroups:
    #     grouppath = 'beam/ssh_segments/heights' 
    #     array = xr.open_dataarray(heightgroup)
    return beamgroups

print(read_atl13(filepath))
# %%
