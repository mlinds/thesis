# loop over the DEMs and generate contours of the 0,-10,-20 levels
for d in ../data/test_sites/florida_keys/in-situ-DEM ../data/test_sites/stcroix/in-situ-DEM/ ../data/test_sites/charlotteamalie/in-situ-DEM/ ../data/oahu_dem/; 
do
gdal_contour -fl -5 -10 -a elev "$d/truth.vrt" "$d/contours.shp" 
done
