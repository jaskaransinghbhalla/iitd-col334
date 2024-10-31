# ryu run ryu.app.simple_switch &
sudo rm -rf p2_logs
sudo mn -c
# sudo rm .xyz_*
# sudo rm *.csv

# silently try to remove the files

sudo rm -f *.txt
sudo rm -f *.bin

# sudo rm xyz_downloaded_file.txt
sudo python3 p2_exp_fairness.py --log 1
# sudo python3 p1_exp.py loss
# sudo python3 p1_exp.py delay