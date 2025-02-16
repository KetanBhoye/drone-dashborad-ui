# sudo systemctl stop drone-server.service
# sudo systemctl start drone-server.service

#!/usr/bin/python3
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymavlink import mavutil
from threading import Thread, Lock
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

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
        self.max_logs = 1000  # Maximum number of logs to keep
        self.logs_lock = Lock()  # Thread-safe logging
        self.armed = False

    def add_log(self, message, log_type='info', details=None):
        with self.logs_lock:
            log_entry = {
                'timestamp': int(time.time() * 1000),  # milliseconds timestamp
                'message': message,
                'type': log_type,
                'details': details
            }
            self.logs.insert(0, log_entry)  # Add to beginning of list

            # Trim logs if they exceed maximum
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[:self.max_logs]

    def connect(self):
        try:
            print("Connecting to Pixhawk...")
            self.connection = mavutil.mavlink_connection('/dev/serial0', baud=921600)
            print("Waiting for heartbeat...")
            self.connection.wait_heartbeat()
            self.connected = True
            self.add_log("Successfully connected to Pixhawk", "info")
            print(f"Connected to system: {self.connection.target_system} component: {self.connection.target_component}")
            return True
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            self.add_log(error_msg, "error")
            print(error_msg)
            return False

    def request_data_streams(self):
        try:
            print("Requesting data streams...")
            self.connection.mav.request_data_stream_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL,
                4,  # 4 Hz update rate
                1
            )
            self.add_log("Data streams requested", "info")
        except Exception as e:
            self.add_log(f"Failed to request data streams: {str(e)}", "error")

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
                    new_mode = mavutil.mode_string_v10(msg)
                    if new_mode != self.mode:
                        self.add_log(f"Flight mode changed to {new_mode}", "info")
                        self.mode = new_mode
                    new_armed_state = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                    if new_armed_state != self.armed:
                        self.armed = new_armed_state
                        self.add_log(f"Vehicle {'armed' if self.armed else 'disarmed'}", "info")
                elif msg_type == 'SYS_STATUS':
                    self.battery_percentage = msg.battery_remaining
                    self.battery_voltage = msg.voltage_battery / 1000
                    self.battery_current = msg.current_battery / 100
                    self.battery_consumed = msg.battery_remaining

                    # Log low battery warnings
                    if self.battery_percentage <= 20:
                        self.add_log(f"Low battery warning: {self.battery_percentage}%", "warning")
                    elif self.battery_percentage <= 10:
                        self.add_log(f"Critical battery level: {self.battery_percentage}%", "error")

            except Exception as e:
                error_msg = f"Telemetry update error: {str(e)}"
                self.add_log(error_msg, "error")
                print(error_msg)
                time.sleep(1)

    def set_mode(self, mode):
        if not self.connected:
            self.add_log("Cannot set mode: Not connected", "warning")
            return False
        try:
            mode_id = self.connection.mode_mapping()[mode]
            self.connection.mav.set_mode_send(
                self.connection.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_id
            )
            self.add_log(f"Flight mode change requested: {mode}", "info")
            return True
        except Exception as e:
            error_msg = f"Failed to set mode: {str(e)}"
            self.add_log(error_msg, "error")
            print(error_msg)
            return False

    def arm(self, arm=True):
        if not self.connected:
            self.add_log("Cannot arm/disarm: Not connected", "warning")
            return False
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1 if arm else 0, 0, 0, 0, 0, 0, 0
            )
            self.add_log(f"{'Arming' if arm else 'Disarming'} command sent", "info")
            return True
        except Exception as e:
            error_msg = f"Failed to {'arm' if arm else 'disarm'}: {str(e)}"
            self.add_log(error_msg, "error")
            print(error_msg)
            return False

    def clear_logs(self):
        with self.logs_lock:
            self.logs = []
            self.add_log("Logs cleared", "info")

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

@app.route('/logs', methods=['GET'])
def get_logs():
    with pixhawk.logs_lock:
        return jsonify({'logs': pixhawk.logs})

@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    pixhawk.clear_logs()
    return jsonify({'success': True})

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

@app.route('/mission/start', methods=['POST'])
def start_mission():
    if not pixhawk.connected:
        return jsonify({'success': False, 'error': 'Not connected'})

    try:
        mission_data = request.json
        waypoints = mission_data['waypoints']
        settings = mission_data['settings']

        # Log mission start
        pixhawk.add_log(f"Starting new mission with {len(waypoints)} waypoints", "info", {
            'waypoints': len(waypoints),
            'altitude': settings['altitude'],
            'speed': settings['speed']
        })

        # Clear any existing mission
        pixhawk.connection.mav.mission_clear_all_send(
            pixhawk.connection.target_system,
            pixhawk.connection.target_component
        )

        # Wait for acknowledgment
        ack = pixhawk.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
        if not ack:
            raise Exception("Mission clear acknowledgment not received")

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
            ack = pixhawk.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
            if not ack:
                raise Exception(f"Mission item {i} acknowledgment not received")

            pixhawk.add_log(f"Uploaded waypoint {i+1}/{len(waypoints)}", "info")

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
            ack = pixhawk.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
            if not ack:
                raise Exception("RTL waypoint acknowledgment not received")

            pixhawk.add_log("Added Return to Launch waypoint", "info")

        # Set mode to AUTO to start mission
        if not pixhawk.set_mode('AUTO'):
            raise Exception("Failed to set AUTO mode")

        pixhawk.add_log("Mission started successfully", "info")
        return jsonify({'success': True})

    except Exception as e:
        error_msg = f"Mission start error: {str(e)}"
        pixhawk.add_log(error_msg, "error")
        print(error_msg)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mission/stop', methods=['POST'])
def stop_mission():
    if not pixhawk.connected:
        return jsonify({'success': False, 'error': 'Not connected'})

    try:
        # Switch to LOITER mode to stop the mission
        if not pixhawk.set_mode('LOITER'):
            raise Exception("Failed to set LOITER mode")

        pixhawk.add_log("Mission stopped - Switched to LOITER mode", "info")
        return jsonify({'success': True})

    except Exception as e:
        error_msg = f"Mission stop error: {str(e)}"
        pixhawk.add_log(error_msg, "error")
        print(error_msg)
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)