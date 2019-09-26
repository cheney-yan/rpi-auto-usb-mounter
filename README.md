#TODO:

[x] basic function works
[x] Change the function, mount using disk label rather than config?
[ ] Add memory queue and thread
[ ] use external yaml to config
[ ] Make it a service
[ ] refine code in python3
[ ] Auto build and publish
[ ] Add something for auto-sync before hot plug out

# install as a service
On pi:

sudo mkdir /opt/rpi-auto-usb-mounter/

sudo mv * /opt/rpi-auto-usb-mounter/
sudo mv /opt/rpi-auto-usb-mounter/usb-mounter.service /lib/systemd/system/
sudo chmod 644 /lib/systemd/system/usb-mounter.service
sudo systemctl daemon-reload
sudo systemctl enable usb-mounter.service
sudo systemctl start usb-mounter.service
