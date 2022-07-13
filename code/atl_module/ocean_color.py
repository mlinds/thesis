import requests
import xarray as xr
from atl_module.secret_vars import COPERNICUS_USERNAME,COPERNICUS_PW

DAP_URL ='https://my.cmems-du.eu/thredds/dodsC/cmems_obs-oc_glo_bgc-transp_my_l4-gapfree-multi-4km_P1D'

# setup the session upon import
def setup_globcolor_api_session(COPERNICUS_USERNAME,COPERNICUS_PW,DAP_URL):
    session = requests.session()
    session.auth = (COPERNICUS_USERNAME,COPERNICUS_PW)
    store = xr.backends.PydapDataStore.open(DAP_URL,session=session)
    return xr.open_dataset(store)

ds = setup_globcolor_api_session(COPERNICUS_USERNAME,COPERNICUS_PW,DAP_URL)

def get_zsd_info(lat,lon,date):
    subset = ds.sel(lat=lat,lon=lon,method='nearest',tolerance=0.05).sel(time=date,method='nearest')
    secchi_depth_array = subset.ZSD.to_numpy()
    secchi_depth_uncertainty_array = subset.ZSD_uncertainty.to_numpy()
    return secchi_depth_array,secchi_depth_uncertainty_array

def get_color_dataframe(lat,lon,dates):
    subset = ds.sel(lat=lat,lon=lon,method='nearest',tolerance=0.05).sel(time=dates,method='nearest')
    return subset.to_dataframe()
