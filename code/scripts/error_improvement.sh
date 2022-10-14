# loop over all sites and find the error between the two rasters
for d in ../data/test_sites/*/; 
do
echo "calculating error improvement for $(basename $d)"
# gdal_calc.py 
# gdalinfo "$d/kalman_error.tif"
# gdalinfo "$d/gebco_error.tif"

gdal_calc.py --calc "abs(A)-abs(B)" -A "$d/gebco_error.tif" -B "$d/kalman_error.tif" \
--type=Float32 \
--overwrite \
--extent=intersect \
--co COMPRESS=LZW \
--co TILED=YES \
--outfile="$d/error_improvement_meter.tif" \
--NoDataValue -999999 
done
