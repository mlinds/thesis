#%%
import rasterio
from rasterio.plot import show_hist,show
hmax = rasterio.open('../data/CMS_Global_Map_Mangrove_Canopy_1665/data/hmax95/height_vrt.vrt')

# right now I can easily open this and get the metadata but any processing of it requires loading the entire thing into memory which isn't possible
# need to look into 


# %%
