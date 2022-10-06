for d in ../data/test_sites/oahu*/; 
# for d in oahu1 oahu2 oahu3 oahu4 oahu5 oahu8;
do
echo "starting $(basename $d)"
python -m atl_module "$(basename $d)" -g 50 -kr -ka 1.5 -rmse
# python -m atl_module "$(basename $d)" -geofig &
done
