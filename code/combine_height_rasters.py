"""
Combines the various national-level rasters from Global Mangrove Distribution, Aboveground Biomass, and Canopy Height dataset by Simard et al.

Takes
"""

__author__ = "Your Name"
__version__ = "0.1.0"
__license__ = "MIT"

from os import listdir
import os
import argparse
from osgeo import gdal


def main(args):
    """ Main entry point of the program """
    # get the normalized path where the rasters live
    raster_directory = os.path.normpath(args.filepath)
    # go to that directory
    os.chdir(raster_directory)

    # list the files and select the ones of interest
    all_files = listdir()
    max_canopy_height_files = [name for name in all_files if name.startswith('Mangrove_hmax95') and name.endswith('.tif')] 
    basal_ar_w_height_files = [name for name in all_files if name.startswith('Mangrove_hba95') and name.endswith('.tif')] 
    abovegr_biomass_files= [name for name in all_files if name.startswith('Mangrove_agb') and name.endswith('.tif')] 

    for raster in max_canopy_height_files:
        print(f'Adding file {raster}')
        r = gdal.Warp('hmax95_combined.tif', ['hmax95_combined.tif',raster],multithread=True)
        r = None

if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()

    # Required positional argument
    parser.add_argument("filepath", help="directory where the country-level rasters are stored")

    args = parser.parse_args()
    main(args)
