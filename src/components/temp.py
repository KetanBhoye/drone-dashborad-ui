#!/usr/bin/python3
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from pymavlink import mavutil
from threading import Thread, Lock, Event
import time
from datetime import datetime
import socket
import threading
import socketio  # New import for Socket.IO client
import json  # For serializing data

# Create a Socket.IO client
sio = socketio.Client(reconnection=True, reconnection_attempts=10, 
                     reconnection_delay=1, reconnection_delay_max=5)

# Define the relay server URL
RELAY_SERVER_URL = 'http://128.199.26.169'  # Your Digital Ocean server IP

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

class MissionError(Exception):
    """Custom exception for mission-related errors"""
    def __init__(self, message, error_type, resolution=None):
        self.message = message
        self.error_type = error_type
        self.resolution = resolution
        super().__init__(self.message)

class PixhawkConnection:
    def __init__(self):
        self.connection = None
        self.connected = False
        self.connection_lock = threading.Lock()
        self.last_heartbeat = 0
        self.connection_timeout = 5  # 5 seconds timeout
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
        self.gps_fix_type = 0
        self.satellites_visible = 0
        self.logs = []
        self.max_logs = 1000
        self.logs_lock = Lock()
        self.armed = False
        self.update_telemetry_thread = None
        self.stop_thread = Event()
        self.mission_in_progress = False
        self.relay_connected = False
        self.telemetry_interval = None
        self.log_sync_interval = None

    def add_log(self, message, log_type='info', details=None):
        with self.logs_lock:
            log_entry = {
                'timestamp': int(time.time() * 1000),
                'message': message,
                'type': log_type,
                'details': details
            }
            self.logs.insert(0, log_entry)
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[:self.max_logs]
            
            # If connected to relay server, send log immediately
            if self.relay_connected:
                try:
                    sio.emit('logs', self.logs[:100])  # Send only most recent logs
                except Exception as e:
                    print(f"Failed to send log to relay: {str(e)}")

    def check_connection_health(self):
        """Check if the connection is healthy based on heartbeat"""
        with self.connection_lock:
            if not self.connected:
                return False
            current_time = time.time()
            return (current_time - self.last_heartbeat) < self.connection_timeout

    def connect(self):
        with self.connection_lock:
            if self.connected:
                return True
            
            try:
                print("Connecting to Pixhawk...")
                self.connection = mavutil.mavlink_connection('/dev/serial0', baud=921600)
                print("Waiting for heartbeat...")
                self.connection.wait_heartbeat(timeout=5)
                self.connected = True
                self.last_heartbeat = time.time()
                self.add_log("Successfully connected to Pixhawk", "info")
                print(f"Connected to system: {self.connection.target_system}")
                
                # Reset stop thread flag if it was set
                self.stop_thread.clear()
                
                # Start telemetry updates if not already running
                if not self.update_telemetry_thread or not self.update_telemetry_thread.is_alive():
                    self.update_telemetry_thread = Thread(
                        target=self.update_telemetry, 
                        daemon=True
                    )
                    self.update_telemetry_thread.start()
                
                # Start relay telemetry if connected to relay
                if self.relay_connected and not self.telemetry_interval:
                    self.start_telemetry_relay()
                
                return True
            except Exception as e:
                self.connected = False
                error_msg = f"Connection failed: {str(e)}"
                self.add_log(error_msg, "error")
                print(error_msg)
                return False

    def disconnect(self):
        """Safely disconnect from the Pixhawk"""
        with self.connection_lock:
            if self.connected:
                try:
                    self.stop_thread.set()
                    if self.update_telemetry_thread:
                        self.update_telemetry_thread.join(timeout=2)
                    if self.connection:
                        self.connection.close()
                    self.connected = False
                    self.add_log("Disconnected from Pixhawk", "info")
                except Exception as e:
                    self.add_log(f"Error during disconnect: {str(e)}", "error")
                finally:
                    self.connection = None

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
        while not self.stop_thread.is_set():
            try:
                if not self.check_connection_health():
                    time.sleep(1)
                    continue

                msg = self.connection.recv_match(blocking=True, timeout=1.0)
                if msg is None:
                    continue

                msg_type = msg.get_type()
                
                if msg_type == 'HEARTBEAT':
                    with self.connection_lock:
                        self.last_heartbeat = time.time()
                    new_mode = mavutil.mode_string_v10(msg)
                    if new_mode != self.mode:
                        self.add_log(f"Flight mode changed to {new_mode}", "info")
                        self.mode = new_mode
                    new_armed_state = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                    if new_armed_state != self.armed:
                        self.armed = new_armed_state
                        self.add_log(f"Vehicle {'armed' if self.armed else 'disarmed'}", "info")

                elif msg_type == 'GLOBAL_POSITION_INT':
                    self.lat = msg.lat / 1e7
                    self.lon = msg.lon / 1e7
                    self.alt = msg.alt / 1000
                    self.relative_alt = msg.relative_alt / 1000
                    self.heading = msg.hdg / 100.0

                elif msg_type == 'VFR_HUD':
                    self.groundspeed = msg.groundspeed

                elif msg_type == 'GPS_RAW_INT':
                    self.gps_fix_type = msg.fix_type
                    self.satellites_visible = msg.satellites_visible

                elif msg_type == 'SYS_STATUS':
                    self.battery_percentage = msg.battery_remaining
                    self.battery_voltage = msg.voltage_battery / 1000
                    self.battery_current = msg.current_battery / 100
                    self.battery_consumed = msg.battery_remaining

                    if self.battery_percentage <= 20:
                        self.add_log(f"Low battery warning: {self.battery_percentage}%", "warning")
                    elif self.battery_percentage <= 10:
                        self.add_log(f"Critical battery level: {self.battery_percentage}%", "error")

                elif msg_type == 'MISSION_CURRENT':
                    if self.mission_in_progress:
                        self.add_log(f"Current waypoint: {msg.seq}", "info")

            except Exception as e:
                with self.connection_lock:
                    self.connected = False
                error_msg = f"Telemetry update error: {str(e)}"
                self.add_log(error_msg, "error")
                print(error_msg)
                time.sleep(1)

    # Function to send telemetry data to the relay server
    def start_telemetry_relay(self):
        """Start sending telemetry data to the relay server"""
        if self.telemetry_interval:
            return
        
        # Send telemetry data every second
        def send_telemetry():
            while self.relay_connected:
                try:
                    telemetry_data = {
                        'connected': self.check_connection_health(),
                        'lat': self.lat,
                        'lon': self.lon,
                        'alt': self.alt,
                        'relative_alt': self.relative_alt,
                        'heading': self.heading,
                        'groundspeed': self.groundspeed,
                        'battery_percentage': self.battery_percentage,
                        'mode': self.mode,
                        'battery_voltage': self.battery_voltage,
                        'battery_current': self.battery_current,
                        'battery_consumed': self.battery_consumed,
                        'armed': self.armed,
                        'gps_fix_type': self.gps_fix_type,
                        'satellites_visible': self.satellites_visible,
                        'mission_in_progress': self.mission_in_progress
                    }
                    sio.emit('telemetry', telemetry_data)
                except Exception as e:
                    print(f"Failed to send telemetry: {str(e)}")
                time.sleep(1)
        
        self.telemetry_interval = Thread(target=send_telemetry, daemon=True)
        self.telemetry_interval.start()
        print("Started telemetry relay")

    def connect_to_relay(self):
        """Connect to the relay server"""
        if self.relay_connected:
            return True
            
        try:
            # Connect to the Socket.IO server
            sio.connect(RELAY_SERVER_URL)
            self.relay_connected = True
            
            # Identify as a drone to the relay server
            sio.emit('identify', 'drone')
            
            # Start sending telemetry if connected to Pixhawk
            if self.check_connection_health():
                self.start_telemetry_relay()
            
            # Send initial logs
            with self.logs_lock:
                sio.emit('logs', self.logs[:100])
                
            return True
        except Exception as e:
            print(f"Failed to connect to relay server: {str(e)}")
            self.relay_connected = False
            return False

    def disconnect_from_relay(self):
        """Disconnect from the relay server"""
        if not self.relay_connected:
            return
            
        try:
            sio.disconnect()
        except Exception as e:
            print(f"Error during relay disconnect: {str(e)}")
        finally:
            self.relay_connected = False
            if self.telemetry_interval:
                self.telemetry_interval = None
            if self.log_sync_interval:
                self.log_sync_interval = None

    def check_mission_prerequisites(self):
        """Check all prerequisites before starting a mission"""
        try:
            if not self.check_connection_health():
                raise MissionError(
                    "No connection to drone",
                    "CONNECTION_ERROR",
                    "Ensure drone is powered and connected. Try reconnecting."
                )

            if not hasattr(self, 'gps_fix_type') or self.gps_fix_type < 3:
                raise MissionError(
                    "Insufficient GPS signal",
                    "GPS_ERROR",
                    "Move to an open area with clear sky view and wait for GPS lock."
                )

            if not self.armed:
                raise MissionError(
                    "Vehicle is not armed",
                    "ARM_ERROR",
                    "Arm the vehicle before starting the mission."
                )

            if self.mode not in ['GUIDED', 'AUTO']:
                raise MissionError(
                    f"Invalid flight mode: {self.mode}",
                    "MODE_ERROR",
                    "Switch to GUIDED mode before starting the mission."
                )

            if self.battery_percentage < 30:
                raise MissionError(
                    f"Low battery: {self.battery_percentage}%",
                    "BATTERY_ERROR",
                    "Charge or replace battery before starting mission."
                )

            if self.mission_in_progress:
                raise MissionError(
                    "Mission already in progress",
                    "MISSION_STATE_ERROR",
                    "Stop current mission before starting a new one."
                )

            return True, None

        except MissionError as e:
            return False, {
                'message': e.message,
                'type': e.error_type,
                'resolution': e.resolution
            }
        except Exception as e:
            return False, {
                'message': f"Unexpected error: {str(e)}",
                'type': 'UNKNOWN_ERROR',
                'resolution': "Contact support if problem persists."
            }

    def validate_mission_parameters(self, waypoints, settings):
        """Validate mission parameters before upload"""
        try:
            if not waypoints or len(waypoints) == 0:
                raise MissionError(
                    "No waypoints provided",
                    "WAYPOINT_ERROR",
                    "Add at least one waypoint to the mission."
                )

            if len(waypoints) > 100:
                raise MissionError(
                    "Too many waypoints",
                    "WAYPOINT_ERROR",
                    "Reduce number of waypoints (maximum 100)."
                )

            for i, wp in enumerate(waypoints):
                if not all(k in wp for k in ['lat', 'lon', 'alt']):
                    raise MissionError(
                        f"Invalid waypoint at position {i+1}",
                        "WAYPOINT_ERROR",
                        "Ensure all waypoints have latitude, longitude, and altitude."
                    )

                if not (-90 <= wp['lat'] <= 90) or not (-180 <= wp['lon'] <= 180):
                    raise MissionError(
                        f"Invalid coordinates at waypoint {i+1}",
                        "COORDINATE_ERROR",
                        "Ensure coordinates are within valid ranges."
                    )

            if not settings:
                raise MissionError(
                    "Mission settings not provided",
                    "SETTINGS_ERROR",
                    "Provide valid mission settings."
                )

            required_settings = ['altitude', 'speed', 'returnToHome']
            missing_settings = [s for s in required_settings if s not in settings]
            if missing_settings:
                raise MissionError(
                    f"Missing settings: {', '.join(missing_settings)}",
                    "SETTINGS_ERROR",
                    "Ensure all required settings are provided."
                )

            if not (0 <= settings['altitude'] <= 120):
                raise MissionError(
                    f"Invalid altitude: {settings['altitude']}m",
                    "ALTITUDE_ERROR",
                    "Set altitude between 0 and 120 meters."
                )

            if not (0 < settings['speed'] <= 15):
                raise MissionError(
                    f"Invalid speed: {settings['speed']}m/s",
                    "SPEED_ERROR",
                    "Set speed between 0 and 15 m/s."
                )

            return True, None

        except MissionError as e:
            return False, {
                'message': e.message,
                'type': e.error_type,
                'resolution': e.resolution
            }
        except Exception as e:
            return False, {
                'message': f"Unexpected error: {str(e)}",
                'type': 'UNKNOWN_ERROR',
                'resolution': "Contact support if problem persists."
            }

    def upload_mission(self, waypoints, settings):
        """Upload a mission to the vehicle following proper MAVLink protocol"""
        try:
            self.add_log("Clearing existing mission", "info")
            self.connection.mav.mission_clear_all_send(
                self.connection.target_system,
                self.connection.target_component
            )
            
            ack = self.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
            if not ack:
                raise MissionError(
                    "Failed to clear existing mission",
                    "MISSION_CLEAR_ERROR",
                    "Try restarting the vehicle."
                )

            total_waypoints = len(waypoints) + (1 if settings['returnToHome'] else 0)

            self.add_log(f"Initiating upload of {total_waypoints} waypoints", "info")
            self.connection.mav.mission_count_send(
                self.connection.target_system,
                self.connection.target_component,
                total_waypoints
            )

            for i in range(len(waypoints)):
                msg = self.connection.recv_match(type=['MISSION_REQUEST'], blocking=True, timeout=5)
                if not msg:
                    raise MissionError(
                        f"No mission request received for waypoint {i}",
                        "UPLOAD_ERROR",
                        "Check connection and try again."
                    )

                if msg.seq != i:
                    raise MissionError(
                        f"Mission sequence mismatch. Expected {i}, got {msg.seq}",
                        "SEQUENCE_ERROR",
                        "Try uploading the mission again."
                    )

                mission_item = self.connection.mav.mission_item_encode(
                    self.connection.target_system,
                    self.connection.target_component,
                    i,
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    0,
                    1,
                    2.0,
                    3.0,
                    5.0,
                    float('nan'),
                    waypoints[i]['lat'],
                    waypoints[i]['lon'],
                    float(settings['altitude'])
                )
                self.connection.mav.send(mission_item)
                self.add_log(f"Uploaded waypoint {i+1}/{total_waypoints}", "info")

            if settings['returnToHome']:
                msg = self.connection.recv_match(type=['MISSION_REQUEST'], blocking=True, timeout=5)
                if not msg:
                    raise MissionError(
                        "No mission request received for RTL waypoint",
                        "UPLOAD_ERROR",
                        "Try uploading the mission again."
                    )

                rtl_item = self.connection.mav.mission_item_encode(
                    self.connection.target_system,
                    self.connection.target_component,
                    len(waypoints),
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                    0, 1, 0, 0, 0, 0, 0, 0, 0
                )
                self.connection.mav.send(rtl_item)
                self.add_log("Added Return to Launch waypoint", "info")

            final_ack = self.connection.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
            if not final_ack:
                raise MissionError(
                    "No final mission acknowledgment received",
                    "UPLOAD_ERROR",
                    "Try uploading the mission again."
                )

            return True

        except MissionError as e:
            self.add_log(f"Mission upload failed: {e.message}", "error")
            return False
        except Exception as e:
            self.add_log(f"Unexpected error during mission upload: {str(e)}", "error")
            return False

    def start_mission(self):
        """Start the uploaded mission with validation"""
        try:
            # First check all prerequisites
            ready, error = self.check_mission_prerequisites()
            if not ready:
                return False, error

            # Set the first waypoint as current
            self.connection.mav.mission_set_current_send(
                self.connection.target_system,
                self.connection.target_component,
                0
            )
            
            # Wait for acknowledgment
            ack = self.connection.recv_match(type='MISSION_CURRENT', blocking=True, timeout=5)
            if not ack:
                raise MissionError(
                    "Failed to set initial waypoint",
                    "MISSION_START_ERROR",
                    "Try uploading the mission again."
                )

            # Switch to AUTO mode to start mission
            if not self.set_mode('AUTO'):
                raise MissionError(
                    "Failed to enter AUTO mode",
                    "MODE_ERROR",
                    "Ensure vehicle is armed and in a valid starting position."
                )

            self.mission_in_progress = True
            self.add_log("Mission started successfully", "info")
            return True, None

        except MissionError as e:
            return False, {
                'message': e.message,
                'type': e.error_type,
                'resolution': e.resolution
            }
        except Exception as e:
            return False, {
                'message': f"Unexpected error: {str(e)}",
                'type': 'UNKNOWN_ERROR',
                'resolution': "Contact support if problem persists."
            }

    def set_mode(self, mode):
        if not self.check_connection_health():
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
            
            # Wait for mode change confirmation
            start_time = time.time()
            while time.time() - start_time < 5:  # 5 second timeout
                if self.mode == mode:
                    return True
                time.sleep(0.1)
            
            raise MissionError(
                f"Mode change to {mode} timed out",
                "MODE_ERROR",
                "Check if mode change is allowed in current state"
            )
        except Exception as e:
            error_msg = f"Failed to set mode: {str(e)}"
            self.add_log(error_msg, "error")
            print(error_msg)
            return False

    def arm(self, arm=True):
        if not self.check_connection_health():
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
            
            # Wait for arm/disarm confirmation
            start_time = time.time()
            while time.time() - start_time < 5:  # 5 second timeout
                if self.armed == arm:
                    return True
                time.sleep(0.1)
            
            raise MissionError(
                f"{'Arm' if arm else 'Disarm'} command timed out",
                "ARM_ERROR",
                "Check if arming is allowed in current state"
            )
        except Exception as e:
            error_msg = f"Failed to {'arm' if arm else 'disarm'}: {str(e)}"
            self.add_log(error_msg, "error")
            print(error_msg)
            return False

    def clear_logs(self):
        with self.logs_lock:
            self.logs = []
            self.add_log("Logs cleared", "info")

# Initialize Pixhawk connection
pixhawk = PixhawkConnection()

# Socket.IO event handlers
@sio.event
def connect():
    print('Connected to relay server')
    pixhawk.relay_connected = True
    # Identify as a drone
    sio.emit('identify', 'drone')
    pixhawk.add_log("Connected to relay server", "info")
    
    # Start telemetry relay if connected to Pixhawk
    if pixhawk.check_connection_health():
        pixhawk.start_telemetry_relay()

@sio.event
def disconnect():
    print('Disconnected from relay server')
    pixhawk.relay_connected = False
    pixhawk.add_log("Disconnected from relay server", "warning")

@sio.event
def command(data):
    print(f"Received command: {data['type']}")
    
    if data['type'] == 'set_mode':
        mode = data.get('mode')
        if mode:
            success = pixhawk.set_mode(mode)
            sio.emit('command_response', {
                'type': 'set_mode',
                'success': success,
                'mode': mode
            })
    
    elif data['type'] == 'arm':
        arm_state = data.get('arm', True)
        success = pixhawk.arm(arm_state)
        sio.emit('command_response', {
            'type': 'arm',
            'success': success,
            'armed': pixhawk.armed
        })
    
    elif data['type'] == 'connect':
        success = pixhawk.connect()
        sio.emit('command_response', {
            'type': 'connect',
            'success': success
        })
    
    elif data['type'] == 'disconnect':
        pixhawk.disconnect()
        sio.emit('command_response', {
            'type': 'disconnect',
            'success': True
        })

@sio.event
def mission(data):
    print("Received mission command")
    
    if data['type'] == 'start':
        # Process mission data
        waypoints = data.get('waypoints')
        settings = data.get('settings')
        
        # Validate mission parameters
        valid, error = pixhawk.validate_mission_parameters(waypoints, settings)
        if not valid:
            sio.emit('command_response', {
                'type': 'mission_start',
                'success': False,
                'error': error['message'],
                'error_type': error['type'],
                'resolution': error['resolution']
            })
            return
        
        # Upload the mission
        pixhawk.add_log("Starting mission upload process", "info")
        if not pixhawk.upload_mission(waypoints, settings):
            sio.emit('command_response', {
                'type': 'mission_start',
                'success': False,
                'error': 'Failed to upload mission',
                'error_type': 'UPLOAD_ERROR',
                'resolution': 'Check connection and try again'
            })
            return
        
        # Start the mission
        success, error = pixhawk.start_mission()
        if not success:
            sio.emit('command_response', {
                'type': 'mission_start',
                'success': False,
                'error': error['message'],
                'error_type': error['type'],
                'resolution': error['resolution']
            })
            return
        
        sio.emit('command_response', {
            'type': 'mission_start',
            'success': True
        })
    
    elif data['type'] == 'stop':
        if not pixhawk.check_connection_health():
            sio.emit('command_response', {
                'type': 'mission_stop',
                'success': False,
                'error': 'Not connected',
                'error_type': 'CONNECTION_ERROR',
                'resolution': 'Check connection and try again'
            })
            return
        
        try:
            if not pixhawk.set_mode('LOITER'):
                sio.emit('command_response', {
                    'type': 'mission_stop',
                    'success': False,
                    'error': 'Failed to set LOITER mode',
                    'error_type': 'MODE_ERROR',
                    'resolution': 'Ensure vehicle allows mode change'
                })
                return
            
            pixhawk.mission_in_progress = False
            pixhawk.add_log("Mission stopped - Switched to LOITER mode", "info")
            
            sio.emit('command_response', {
                'type': 'mission_stop',
                'success': True
            })
        except Exception as e:
            error_msg = f"Mission stop error: {str(e)}"
            pixhawk.add_log(error_msg, "error")
            
            sio.emit('command_response', {
                'type': 'mission_stop',
                'success': False,
                'error': error_msg,
                'error_type': 'STOP_ERROR',
                'resolution': 'Try switching to LOITER mode manually'
            })

# Flask routes - we'll keep these for local access if needed
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'connected': pixhawk.check_connection_health(),
        'relay_connected': pixhawk.relay_connected,
        'gps': {
            'fix_type': pixhawk.gps_fix_type,
            'satellites': pixhawk.satellites_visible
        },
        'battery': pixhawk.battery_percentage,
        'mode': pixhawk.mode,
        'armed': pixhawk.armed
    })

@app.route('/connect', methods=['POST'])
def connect():
    try:
        # Connect to Pixhawk
        success = pixhawk.connect()
        
        # Also connect to relay server if not already connected
        if success and not pixhawk.relay_connected:
            pixhawk.connect_to_relay()
            
        pixhawk.request_data_streams()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/disconnect', methods=['POST'])
def disconnect():
    try:
        pixhawk.disconnect()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    return jsonify({
        'connected': pixhawk.check_connection_health(),
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
        'armed': pixhawk.armed,
        'gps_fix_type': pixhawk.gps_fix_type,
        'satellites_visible': pixhawk.satellites_visible,
        'mission_in_progress': pixhawk.mission_in_progress
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
        return jsonify({
            'success': False, 
            'error': 'Mode not specified',
            'error_type': 'PARAMETER_ERROR',
            'resolution': 'Specify a valid flight mode'
        })
    success = pixhawk.set_mode(mode)
    return jsonify({'success': success})

@app.route('/arm', methods=['POST'])
def arm():
    arm_state = request.json.get('arm', True)
    success = pixhawk.arm(arm_state)
    return jsonify({'success': success})

@app.route('/mission/start', methods=['POST'])
def start_mission():
    try:
        mission_data = request.json
        waypoints = mission_data.get('waypoints')
        settings = mission_data.get('settings')

        # Validate mission parameters
        valid, error = pixhawk.validate_mission_parameters(waypoints, settings)
        if not valid:
            return jsonify({
                'success': False,
                'error': error['message'],
                'error_type': error['type'],
                'resolution': error['resolution']
            })

        # Upload the mission
        pixhawk.add_log("Starting mission upload process", "info")
        if not pixhawk.upload_mission(waypoints, settings):
            return jsonify({
                'success': False,
                'error': 'Failed to upload mission',
                'error_type': 'UPLOAD_ERROR',
                'resolution': 'Check connection and try again'
            })

        # Start the mission
        success, error = pixhawk.start_mission()
        if not success:
            return jsonify({
                'success': False,
                'error': error['message'],
                'error_type': error['type'],
                'resolution': error['resolution']
            })

        return jsonify({'success': True})

    except Exception as e:
        error_msg = f"Mission start error: {str(e)}"
        pixhawk.add_log(error_msg, "error")
        return jsonify({
            'success': False,
            'error': error_msg,
            'error_type': 'UNKNOWN_ERROR',
            'resolution': 'Contact support if problem persists'
        })

@app.route('/mission/stop', methods=['POST'])
def stop_mission():
    if not pixhawk.check_connection_health():
        return jsonify({
            'success': False, 
            'error': 'Not connected',
            'error_type': 'CONNECTION_ERROR',
            'resolution': 'Check connection and try again'
        })

    try:
        if not pixhawk.set_mode('LOITER'):
            raise MissionError(
                "Failed to set LOITER mode",
                "MODE_ERROR",
                "Ensure vehicle allows mode change"
            )

        pixhawk.mission_in_progress = False
        pixhawk.add_log("Mission stopped - Switched to LOITER mode", "info")
        return jsonify({'success': True})

    except Exception as e:
        error_msg = f"Mission stop error: {str(e)}"
        pixhawk.add_log(error_msg, "error")
        return jsonify({
            'success': False,
            'error': error_msg,
            'error_type': 'STOP_ERROR',
            'resolution': 'Try switching to LOITER mode manually'
        })

# Main function
if __name__ == '__main__':
    try:
        # Try to connect to the relay server first
        print("Connecting to relay server...")
        pixhawk.connect_to_relay()
        
        # Then try to connect to Pixhawk
        print("Connecting to Pixhawk...")
        pixhawk.connect()
        pixhawk.request_data_streams()
        
        # Start the Flask app (still useful for local access if needed)
        print("Starting Drone Server on port 5000...")
        app.run(host='0.0.0.0', port=5000, threaded=True)
    except Exception as e:
        print(f"Failed to start server: {str(e)}")
        exit(1)
    finally:
        # Ensure clean disconnect on server shutdown
        if pixhawk.connected:
            pixhawk.disconnect()
        if pixhawk.relay_connected:
            pixhawk.disconnect_from_relay()