"""
Combines the various national-level rasters from Global Mangrove Distribution, Aboveground Biomass, and Canopy Height dataset by Simard et al.

"""
#%%
from os import listdir
import os
import shutil


# def main(args):
""" Main entry point of the program """
# get the normalized path where the rasters live

raster_directory = os.path.abspath("../data/CMS_Global_Map_Mangrove_Canopy_1665/data")
# go to that directory
os.chdir(raster_directory)

os.mkdir("hmax95")
os.mkdir("agb")
os.mkdir("hba")

# list the files and select the ones of interest
all_files = listdir()
max_canopy_height_files = [
    name
    for name in all_files
    if name.startswith("Mangrove_hmax95") and name.endswith(".tif")
]
basal_ar_w_height_files = [
    name
    for name in all_files
    if name.startswith("Mangrove_hba95") and name.endswith(".tif")
]
abovegr_biomass_files = [
    name
    for name in all_files
    if name.startswith("Mangrove_agb") and name.endswith(".tif")
]

for file in max_canopy_height_files:
    shutil.move(file, f"hmax95/{file}")
for file in basal_ar_w_height_files:
    shutil.move(file, f"hba/{file}")
for file in abovegr_biomass_files:
    shutil.move(file, f"agb/{file}")


# %%
