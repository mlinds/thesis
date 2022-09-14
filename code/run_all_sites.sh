for d in ../data/test_sites/*/; 
do
echo "starting $(basename $d)"
python -m atl_module "$(basename $d)" -tr -b -lrmse
done