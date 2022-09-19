for d in ../data/test_sites/*/; 
# for d in oahu7 oahu8 stcroix; 
do
echo "starting $(basename $d)"
# python -m atl_module "$(basename $d)" -lrmse -g 50 -kr -ka 1.5 -rmse
python -m atl_module "$(basename $d)" -ka 3 -rmse
# python -m atl_module "$(basename $d)" -b -lrmse
done