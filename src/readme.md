# To run WebRTC server manually
cd ~/webrtc-drone
source /home/pi4/drone_env/bin/activate
python server.py

# To run MQTT bridge manually
cd ~
source /home/pi4/drone_env/bin/activate
python mqtt_bridge.py





MQTT


sudo systemctl restart webrtc-camera.service
sudo systemctl restart mqtt-bridge.service
sudo systemctl restart zerotier-one.service