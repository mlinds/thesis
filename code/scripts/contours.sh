# loop over all sites and find the error between the two rasters
for d in ../data/test_sites/florida_keys/in-situ-DEM ../data/test_sites/stcroix/in-situ-DEM/ ../data/test_sites/charlotteamalie/in-situ-DEM/ ../data/oahu_dem/; 
do

gdal_contour -fl 0 -fl -10 -fl -20 -a elev "$d/truth.vrt" "$d/contours.shp" 
done
