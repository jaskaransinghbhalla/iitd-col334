# ryu run ryu.app.simple_switch &
sudo rm -rf logs
sudo mn -c
sudo rm .xyz_*
sudo rm *.csv
sudo rm xyz_downloaded_file.txt
sudo python3 p1_exp.py custom
# sudo python3 p1_exp.py loss
# sudo python3 p1_exp.py delay