#!/usr/bin/python3
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymavlink import mavutil
from threading import Thread
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

class PixhawkConnection:
    def __init__(self):
        self.connection = None
        self.connected = False
        self.lat = 0
        self.lon = 0
        self.alt = 0
        self.relative_alt = 0
        self.heading = 0
        self.groundspeed = 0
        self.battery_percentage = 0
        self.mode = "UNKNOWN"
        self.battery_voltage = 0
        self.battery_current = 0
        self.battery_consumed = 0
        self.logs = []
        self.armed = False

    def connect(self):
        try:
            print("Connecting to Pixhawk...")
            self.connection = mavutil.mavlink_connection('/dev/serial0', baud=921600)
            print("Waiting for heartbeat...")
            self.connection.wait_heartbeat()
            self.connected = True
            print(f"Connected to system: {self.connection.target_system} component: {self.connection.target_component}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def request_data_streams(self):
        print("Requesting data streams...")
        self.connection.mav.request_data_stream_send(
            self.connection.target_system,
            self.connection.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            4,  # 4 Hz update rate
            1
        )

    def update_telemetry(self):
        while True:
            if not self.connected:
                time.sleep(1)
                continue
            try:
                msg = self.connection.recv_match(blocking=True)
                if msg is None:
                    continue
                msg_type = msg.get_type()
                if msg_type == 'GLOBAL_POSITION_INT':
                    self.lat = msg.lat / 1e7
                    self.lon = msg.lon / 1e7
                    self.alt = msg.alt / 1000
                    self.relative_alt = msg.relative_alt / 1000
                    self.heading = msg.hdg / 100.0
                elif msg_type == 'VFR_HUD':
                    self.groundspeed = msg.groundspeed
                elif msg_type == 'HEARTBEAT':
                    self.mode = mavutil.mode_string_v10(msg)
                    self.armed = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                elif msg_type == 'SYS_STATUS':
                    self.battery_percentage = msg.battery_remaining
                    self.battery_voltage = msg.voltage_battery / 1000
                    self.battery_current = msg.current_battery / 100
                    self.battery_consumed = msg.battery_remaining
            except Exception as e:
                print(f"Telemetry update error: {e}")
                time.sleep(1)

    def set_mode(self, mode):
        if not self.connected:
            return False
        try:
            mode_id = self.connection.mode_mapping()[mode]
            self.connection.mav.set_mode_send(
                self.connection.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_id
            )
            return True
        except Exception as e:
            print(f"Failed to set mode: {e}")
            return False

    def arm(self, arm=True):
        if not self.connected:
            return False
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1 if arm else 0, 0, 0, 0, 0, 0, 0
            )
            return True
        except Exception as e:
            print(f"Failed to arm/disarm: {e}")
            return False

pixhawk = PixhawkConnection()

@app.route('/connect', methods=['POST'])
def connect():
    success = pixhawk.connect()
    if success:
        pixhawk.request_data_streams()
        Thread(target=pixhawk.update_telemetry, daemon=True).start()
    return jsonify({'success': success})

@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    return jsonify({
        'connected': pixhawk.connected,
        'lat': pixhawk.lat,
        'lon': pixhawk.lon,
        'alt': pixhawk.alt,
        'relative_alt': pixhawk.relative_alt,
        'heading': pixhawk.heading,
        'groundspeed': pixhawk.groundspeed,
        'battery_percentage': pixhawk.battery_percentage,
        'mode': pixhawk.mode,
        'battery_voltage': pixhawk.battery_voltage,
        'battery_current': pixhawk.battery_current,
        'battery_consumed': pixhawk.battery_consumed,
        'armed': pixhawk.armed
    })

@app.route('/set_mode', methods=['POST'])
def set_mode():
    mode = request.json.get('mode')
    if not mode:
        return jsonify({'success': False, 'error': 'Mode not specified'})
    success = pixhawk.set_mode(mode)
    return jsonify({'success': success})

@app.route('/arm', methods=['POST'])
def arm():
    arm_state = request.json.get('arm', True)
    success = pixhawk.arm(arm_state)
    return jsonify({'success': success})

# Add these endpoints to your existing Flask server

@app.route('/mission/start', methods=['POST'])
def start_mission():
    if not pixhawk.connected:
        return jsonify({'success': False, 'error': 'Not connected'})
        
    try:
        mission_data = request.json
        waypoints = mission_data['waypoints']
        settings = mission_data['settings']
        
        # Clear any existing mission
        pixhawk.connection.mav.mission_clear_all_send(
            pixhawk.connection.target_system,
            pixhawk.connection.target_component
        )
        
        # Wait for acknowledgment
        pixhawk.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
        
        # Upload new mission
        for i, wp in enumerate(waypoints):
            # Convert to MAVLink waypoint
            mission_item = pixhawk.connection.mav.mission_item_encode(
                pixhawk.connection.target_system,
                pixhawk.connection.target_component,
                i,                              # Sequence number
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,                              # Current waypoint (0: false, 1: true)
                1,                              # Auto continue to next waypoint
                0,                              # Hold time (seconds)
                settings['speed'],              # Acceptance radius (meters)
                0,                              # Pass radius (meters)
                0,                              # Yaw angle (degrees)
                wp['lat'],                      # Latitude
                wp['lon'],                      # Longitude
                wp['alt']                       # Altitude
            )
            pixhawk.connection.mav.send(mission_item)
            
            # Wait for acknowledgment
            pixhawk.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
        
        # If return to home is enabled, add RTL waypoint
        if settings['returnToHome']:
            rtl_item = pixhawk.connection.mav.mission_item_encode(
                pixhawk.connection.target_system,
                pixhawk.connection.target_component,
                len(waypoints),
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                0, 1, 0, 0, 0, 0, 0, 0, 0
            )
            pixhawk.connection.mav.send(rtl_item)
            pixhawk.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
        
        # Set mode to AUTO to start mission
        pixhawk.set_mode('AUTO')
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Mission start error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mission/stop', methods=['POST'])
def stop_mission():
    if not pixhawk.connected:
        return jsonify({'success': False, 'error': 'Not connected'})
        
    try:
        # Switch to LOITER mode to stop the mission
        pixhawk.set_mode('LOITER')
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Mission stop error: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)