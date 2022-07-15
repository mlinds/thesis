from atl_module.core import GebcoUpscaler
import sys

sitename = sys.argv[1]

site = GebcoUpscaler(
    f"/mnt/c/Users/XCB/OneDrive - Van Oord/Documents/thesis/data/test_sites/{sitename}/",
    f"/mnt/c/Users/XCB/OneDrive - Van Oord/Documents/thesis/data/test_sites/{sitename}/in-situ-DEM/truth.vrt",
)

# site.find_bathy_from_icesat(window=100,threshold_val=0.0,req_perc_hconf=0,window_meters=None,min_photons=None)
# site.subset_gebco()
# site.kriging(npts=1000)
site.kalman(1)
# site.rmse_error()
