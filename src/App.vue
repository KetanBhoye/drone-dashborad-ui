// App.vue
<template>
  <div id="app">
    <div class="main-container">
      <!-- Header -->
      <header class="header">
        <h1>AI Powered Security Surveillance</h1>
        <div class="connection-controls">
          <div class="status-indicator">
            <div :class="['status-dot', connected ? 'connected' : 'disconnected']"></div>
            <span>{{ connected ? 'Connected' : 'Disconnected' }}</span>
            <span v-if="missionInProgress" class="mission-status">
              Mission in Progress
            </span>
          </div>
          <button @click="connect" :disabled="connecting" class="connect-btn">
            {{ connecting ? 'Connecting...' : 'Connect' }}
          </button>
        </div>
      </header>

      <!-- Status Panel -->
      <StatusPanel 
        :gps-status="gpsStatus"
        :vehicle-status="vehicleStatus"
        class="status-panel"
      />

      <div class="content-grid">
        <!-- Left Column: Map and Camera -->
        <div class="main-content">
          <!-- Map with Mission Control -->
          <DroneMap 
            :latitude="telemetry.lat"
            :longitude="telemetry.lon"
            :connected="connected"
            :mission-in-progress="missionInProgress"
            :satellites="telemetry.satellites_visible"
            @start-mission="handleStartMission"
            @stop-mission="handleStopMission"
          />
          
          <!-- Camera Feed -->
          <DroneCamera 
            :connected="connected"
          />
        </div>

        <!-- Right Column: Dashboard and Logs -->
        <div class="side-panel">
          <!-- Dashboard -->
          <DroneDashboard 
            :connected="connected"
            :telemetry="telemetry"
            @set-mode="handleSetMode"
            @toggle-arm="handleToggleArm"
          />
          
          <!-- Logs -->
          <LogContainer 
            :logs="logs"
            @clear-logs="clearLogs"
          />
        </div>
      </div>
    </div>

    <!-- Error Dialog -->
    <ErrorDialog
      v-model="showError"
      :title="errorDetails.title"
      :message="errorDetails.message"
      :resolution="errorDetails.resolution"
      :actions="errorDetails.actions"
    />
  </div>
</template>

<script>
import DroneMap from './components/DroneMap.vue'
import DroneDashboard from './components/DroneDashboard.vue'
import LogContainer from './components/LogContainer.vue'
import StatusPanel from './components/StatusPanel.vue'
import ErrorDialog from './components/ErrorDialog.vue'
import DroneCamera from './components/DroneCamera.vue'
import { ref, onMounted, onUnmounted } from 'vue'
import { io } from "socket.io-client"

export default {
  name: 'App',
  components: {
    DroneMap,
    DroneDashboard,
    LogContainer,
    StatusPanel,
    ErrorDialog,
    DroneCamera
  },
  setup() {
    // Use the cloud relay server instead of direct connection
    const RELAY_SERVER_URL = 'http://128.199.26.169:3000'
    const connected = ref(false)
    const connecting = ref(false)
    const connectionAttempts = ref(0)
    const MAX_RETRIES = 3
    const RETRY_DELAY = 5000 // 5 seconds
    const CONNECTION_TIMEOUT = 10000 // 10 seconds
    const currentMission = ref(null)
    const missionInProgress = ref(false)
    const logs = ref([])
    const socket = ref(null)
    const droneConnected = ref(false)

    // Error handling
    const showError = ref(false)
    const errorDetails = ref({
      title: '',
      message: '',
      resolution: '',
      actions: []
    })

    // Status tracking
    const gpsStatus = ref({
      fix_type: 0,
      satellites: 0
    })
    const vehicleStatus = ref({
      armed: false,
      mode: 'UNKNOWN',
      battery: 0
    })

    const telemetry = ref({
      lat: 0,
      lon: 0,
      alt: 0,
      relative_alt: 0,
      heading: 0,
      groundspeed: 0,
      battery_percentage: 0,
      mode: 'UNKNOWN',
      battery_voltage: 0,
      battery_current: 0,
      battery_consumed: 0,
      armed: false,
      satellites_visible: 0,
      gps_fix_type: 0,
      connected: false,
      mission_in_progress: false
    })

    const connectTimeout = ref(null)

    const resetConnection = () => {
      if (socket.value) {
        socket.value.disconnect()
        socket.value = null
      }
      
      connected.value = false
      droneConnected.value = false
      connecting.value = false
      missionInProgress.value = false
      
      if (connectTimeout.value) {
        clearTimeout(connectTimeout.value)
        connectTimeout.value = null
      }
    }

    const handleConnectionError = (error) => {
      let errorMessage = 'Connection failed'
      let resolution = 'Please try again'

      if (error.message) {
        errorMessage = error.message
      }

      showErrorDialog('Connection Error', errorMessage, resolution)
      resetConnection()
      
      if (connectionAttempts.value < MAX_RETRIES) {
        setTimeout(connect, RETRY_DELAY)
      } else {
        connectionAttempts.value = 0
        showErrorDialog(
          'Connection Failed', 
          'Max connection attempts reached', 
          'Please check your network connection and try again'
        )
      }
    }

    const setupSocketEvents = () => {
      socket.value.on('connect', () => {
        console.log('Connected to relay server');
        connected.value = true;
        connecting.value = false;
        connectionAttempts.value = 0;
        
        // Identify as control client
        socket.value.emit('identify', 'control');
        
        // Clear timeout if it exists
        if (connectTimeout.value) {
          clearTimeout(connectTimeout.value);
          connectTimeout.value = null;
        }
      });
      
      socket.value.on('disconnect', () => {
        console.log('Disconnected from relay server');
        connected.value = false;
        droneConnected.value = false;
        showErrorDialog('Connection Lost', 'Lost connection to server', 'Attempting to reconnect...');
      });
      
      socket.value.on('connect_error', (error) => {
        console.error('Connection error:', error);
        handleConnectionError(error);
      });
      
      socket.value.on('drone_connection', (data) => {
        console.log('Drone connection status:', data);
        droneConnected.value = data.connected;
        
        if (data.connected) {
          showSuccessMessage('Drone connected to server');
        } else {
          showErrorDialog('Drone Disconnected', 'The drone is not connected to the server', 'Check the drone\'s internet connection');
        }
      });
      
      socket.value.on('telemetry', (data) => {
        // Update telemetry data
        telemetry.value = data;
        
        // Update status refs
        gpsStatus.value = {
          fix_type: data.gps_fix_type,
          satellites: data.satellites_visible
        };
        
        vehicleStatus.value = {
          armed: data.armed,
          mode: data.mode,
          battery: data.battery_percentage
        };
        
        missionInProgress.value = data.mission_in_progress;
      });
      
      socket.value.on('logs', (logsData) => {
        logs.value = logsData;
      });
      
      socket.value.on('command_response', (response) => {
        console.log('Command response:', response);
        
        if (!response.success) {
          // Handle errors based on command type
          switch (response.type) {
            case 'mission_start':
              handleMissionError({
                error: response.error,
                error_type: response.error_type,
                resolution: response.resolution
              });
              break;
              
            case 'mission_stop':
              showErrorDialog('Stop Mission Failed', response.error, response.resolution);
              break;
              
            case 'set_mode':
              showErrorDialog('Mode Change Failed', response.error, response.resolution || 'Please try again');
              break;
              
            case 'arm':
              showErrorDialog('Arm/Disarm Failed', response.error, response.resolution || 'Please try again');
              break;
              
            default:
              showErrorDialog('Command Failed', response.error, response.resolution || 'Please try again');
          }
        } else {
          // Handle success messages
          switch (response.type) {
            case 'mission_start':
              showSuccessMessage('Mission started successfully');
              break;
              
            case 'mission_stop':
              missionInProgress.value = false;
              currentMission.value = null;
              showSuccessMessage('Mission stopped successfully');
              break;
          }
        }
      });
      
      socket.value.on('error', (error) => {
        console.error('Server error:', error);
        showErrorDialog('Server Error', error.message, error.resolution || 'Please try again');
      });
    };

    const connect = () => {
      if (connecting.value || connected.value) return;
      
      connecting.value = true;
      connectionAttempts.value++;
      
      try {
        // Create socket connection if it doesn't exist
        if (!socket.value) {
          socket.value = io(RELAY_SERVER_URL, {
            reconnectionAttempts: 5,
            timeout: CONNECTION_TIMEOUT
          });
          
          // Setup socket event handlers
          setupSocketEvents();
        } else if (!socket.value.connected) {
          socket.value.connect();
        }
        
        // Set a timeout for connection
        connectTimeout.value = setTimeout(() => {
          if (!connected.value) {
            handleConnectionError(new Error('Connection timed out'));
          }
        }, CONNECTION_TIMEOUT);
      } catch (error) {
        console.error('Connection setup error:', error);
        handleConnectionError(error);
      }
    };

    const handleSetMode = (mode) => {
      if (!connected.value || !droneConnected.value) {
        showErrorDialog('Not Connected', 'Cannot change mode while disconnected', 'Connect to the drone first');
        return;
      }
      
      socket.value.emit('command', {
        type: 'set_mode',
        mode: mode
      });
    };

    const handleToggleArm = () => {
      if (!connected.value || !droneConnected.value) {
        showErrorDialog('Not Connected', 'Cannot arm/disarm while disconnected', 'Connect to the drone first');
        return;
      }
      
      socket.value.emit('command', {
        type: 'arm',
        arm: !telemetry.value.armed
      });
    };

    const handleStartMission = (mission) => {
      if (!connected.value || !droneConnected.value) {
        showErrorDialog('Not Connected', 'Cannot start mission while disconnected', 'Connect to the drone first');
        return;
      }
      
      socket.value.emit('mission', {
        type: 'start',
        waypoints: mission.waypoints.map(wp => ({
          lat: wp.lat,
          lon: wp.lng,
          alt: wp.alt
        })),
        settings: {
          altitude: mission.settings.altitude,
          speed: mission.settings.speed,
          returnToHome: mission.settings.returnToHome
        }
      });
      
      // Update local state
      currentMission.value = mission;
    };

    const handleStopMission = () => {
      if (!connected.value || !droneConnected.value || !missionInProgress.value) {
        return;
      }
      
      socket.value.emit('mission', {
        type: 'stop'
      });
    };

    const handleMissionError = (error) => {
      const actions = [];

      switch (error.error_type) {
        case 'GPS_ERROR':
          actions.push({
            text: 'Check GPS Status',
            action: showGPSStatus
          });
          break;
        case 'BATTERY_ERROR':
          actions.push({
            text: 'Check Battery',
            action: showBatteryStatus
          });
          break;
        case 'ARM_ERROR':
          actions.push({
            text: 'Arm Vehicle',
            action: handleToggleArm
          });
          break;
        case 'MODE_ERROR':
          actions.push({
            text: 'Set Mode',
            action: () => handleSetMode('GUIDED')
          });
          break;
      }

      showErrorDialog(
        'Mission Error',
        error.error,
        error.resolution,
        actions
      );
    };

    const clearLogs = () => {
      if (!connected.value || !droneConnected.value) {
        return;
      }
      
      socket.value.emit('command', {
        type: 'clear_logs'
      });
      
      // Optimistically clear logs locally too
      logs.value = [];
    };

    const showErrorDialog = (title, message, resolution, actions = []) => {
      errorDetails.value = {
        title,
        message,
        resolution,
        actions
      };
      showError.value = true;
    };

    const showSuccessMessage = (message) => {
      // You can implement this with your preferred UI component/library
      console.log('Success:', message);
      // Could be replaced with a toast notification
    };

    const showGPSStatus = () => {
      showErrorDialog(
        'GPS Status',
        `Fix Type: ${getGPSFixTypeText(gpsStatus.value.fix_type)}
         Satellites: ${gpsStatus.value.satellites}`,
        'Ensure you have clear view of the sky'
      );
    };

    const showBatteryStatus = () => {
      showErrorDialog(
        'Battery Status',
        `Battery Level: ${vehicleStatus.value.battery}%
         Voltage: ${telemetry.value.battery_voltage}V
         Current: ${telemetry.value.battery_current}A`,
        'Ensure battery is sufficiently charged'
      );
    };

    const getGPSFixTypeText = (fixType) => {
      switch (fixType) {
        case 0: return 'No GPS';
        case 1: return '1D Fix';
        case 2: return '2D Fix';
        case 3: return '3D Fix';
        case 4: return '3D Fix + DGPS';
        case 5: return 'RTK Float';
        case 6: return 'RTK Fixed';
        default: return 'Unknown';
      }
    };

    onMounted(() => {
      connect();
    });

    onUnmounted(() => {
      resetConnection();
    });

    return {
      // Connection state
      connected,
      connecting,
      currentMission,
      missionInProgress,

      // Status and telemetry
      gpsStatus,
      vehicleStatus,
      telemetry,
      logs,

      // Error handling
      showError,
      errorDetails,

      // Methods
      connect,
      handleSetMode,
      handleToggleArm,
      handleStartMission,
      handleStopMission,
      clearLogs
    };
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin: 0;
  padding: 20px;
  min-height: 100vh;
  background-color: #f0f2f5;
}

.main-container {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header h1 {
  margin: 0;
  font-size: 24px;
  color: #2c3e50;
}

.connection-controls {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transition: background-color 0.3s ease;
}

.status-dot.connected {
  background-color: #4CAF50;
}

.status-dot.disconnected {
  background-color: #f44336;
}

.mission-status {
  margin-left: 12px;
  padding: 4px 8px;
  background-color: #2196F3;
  color: white;
  border-radius: 4px;
  font-size: 0.8rem;
}

.connect-btn {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.connect-btn:hover {
  background-color: #388E3C;
}

.connect-btn:disabled {
  background-color: #9E9E9E;
  cursor: not-allowed;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 20px;
  margin-top: 20px;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Responsive Design */
@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
  
  .main-content {
    order: 1;
  }
  
  .side-panel {
    order: 2;
  }
}

@media (max-width: 768px) {
  #app {
    padding: 10px;
  }

  .header {
    flex-direction: column;
    text-align: center;
    gap: 15px;
  }

  .connection-controls {
    flex-direction: column;
    gap: 10px;
  }
}
</style>