for d in ../data/test_sites/*/; 
# for d in oahu8 stcroix; 
do
echo "starting $(basename $d)"
# python -m atl_module "$(basename $d)"  -g 50 -kr -ka 1.5 -rmse
python -m atl_module "$(basename $d)" -geofig &
done
