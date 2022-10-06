import os.path
import sys
from glob import glob

import pandas as pd
from atl_module.ATL03_preprocessing.atl03_netcdf_loading import (
    get_beams,
    load_beam_array_ncds,
)
from atl_module.bathymetry_extraction.icesat_bathymetry import (
    _filter_points,
    add_rolling_kde,
)
from atl_module.utility_functions.error_calc import add_true_elevation
from atl_module.utility_functions.plotting import plot_transect_results


def run_kde(filename, beam):
    beamarray = load_beam_array_ncds(filename=filename, beam=beam)
    point_df = pd.DataFrame(beamarray)

    subsurface_return_pts = _filter_points(
        point_df,
        low_limit=-40,
        high_limit=1,
        rolling_window=200,
        max_sea_surf_elev=2,
        filter_below_z=-40,
        filter_below_depth=-40,
        n=3,
        max_geoid_high_z=5,
    )
    # find the bathymetry points using the KDE function
    bathy_pts = add_rolling_kde(
        subsurface_return_pts,
        window=100,
        min_photons=None,
        window_meters=None,
    )

    return subsurface_return_pts, bathy_pts


def main():
    site = sys.argv[1]
    print("starting site:", site)
    for file in glob(f"../data/test_sites/{site}/ATL03/*.nc"):
        print("starting file: ", file)
        outfilename = os.path.basename(file).strip("005_01.nc").strip("processed_ATL03_")
        print(outfilename)

        beamlist = get_beams(file)
        for beam in beamlist:
            print("starting beam", beam)
            subsurfpts, bathy_pts = run_kde(file, beam)
            bathy_pts = add_true_elevation(
                bathy_pts, f"../data/test_sites/{site}/in-situ-DEM/truth.vrt", crs="EPSG:32620"
            )
            bathy_pts[bathy_pts.kde_val > 0.15]
            if len(subsurfpts) == 0 or len(bathy_pts) == 0:
                continue
            plot_transect_results(
                subsurfpts, bathy_pts, f"../data/temp_figs/{site}_{outfilename}-{beam}.jpg"
            )


if __name__ == "__main__":
    main()
