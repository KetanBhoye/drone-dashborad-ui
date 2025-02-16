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
import { ref, onMounted, onUnmounted } from 'vue'
import DroneCamera from './components/DroneCamera.vue'
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
    const API_URL = 'http://192.168.117.33:5000/'
    const connected = ref(false)
    const connecting = ref(false)
    const connectionAttempts = ref(0)
    const MAX_RETRIES = 3
    const RETRY_DELAY = 5000 // 5 seconds
    const CONNECTION_TIMEOUT = 5000 // 5 seconds
    const currentMission = ref(null)
    const missionInProgress = ref(false)
    const logs = ref([])

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
      gps_fix_type: 0
    })

    let telemetryInterval = null
    let logsInterval = null
    let healthCheckInterval = null

    const resetConnection = () => {
      stopTelemetryUpdates()
      stopLogUpdates()
      stopHealthCheck()
      connected.value = false
      connecting.value = false
      missionInProgress.value = false
    }

    const fetchWithTimeout = (resource, options = {}) => {
      const { timeout = 5000 } = options
      const controller = new AbortController()
      const id = setTimeout(() => controller.abort(), timeout)
      
      return fetch(resource, {
        ...options,
        signal: controller.signal
      }).finally(() => clearTimeout(id))
    }

    const handleConnectionError = (error) => {
      let errorMessage = 'Connection failed'
      let resolution = 'Please try again'

      if (error.name === 'AbortError') {
        errorMessage = 'Connection timed out'
        resolution = 'Check if the server is running and accessible'
      } else if (error.message) {
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

    const connect = async () => {
      if (connecting.value) return
      
      connecting.value = true
      connectionAttempts.value++

      try {
        const healthResponse = await fetchWithTimeout(`${API_URL}/health`, {
          method: 'GET',
          timeout: CONNECTION_TIMEOUT
        })
        const healthData = await healthResponse.json()
        
        if (!healthData.status === 'healthy') {
          throw new Error('Server health check failed')
        }

        const response = await fetchWithTimeout(`${API_URL}/connect`, {
          method: 'POST',
          timeout: CONNECTION_TIMEOUT
        })
        const data = await response.json()

        if (data.success) {
          connected.value = true
          connectionAttempts.value = 0
          startTelemetryUpdates()
          startLogUpdates()
          startHealthCheck()
        } else {
          throw new Error(data.error || 'Connection failed')
        }
      } catch (error) {
        console.error('Connection error:', error)
        handleConnectionError(error)
      } finally {
        connecting.value = false
      }
    }

    const startHealthCheck = () => {
      if (healthCheckInterval) return
      
      healthCheckInterval = setInterval(async () => {
        try {
          const response = await fetchWithTimeout(`${API_URL}/health`, {
            timeout: 3000
          })
          const data = await response.json()
          
          if (!data.status === 'healthy' || !data.connected) {
            handleConnectionLost()
          }
        } catch (error) {
          handleConnectionLost()
        }
      }, 5000)
    }

    const stopHealthCheck = () => {
      if (healthCheckInterval) {
        clearInterval(healthCheckInterval)
        healthCheckInterval = null
      }
    }

    const startTelemetryUpdates = () => {
      if (!telemetryInterval) {
        telemetryInterval = setInterval(updateTelemetry, 1000)
      }
    }

    const stopTelemetryUpdates = () => {
      if (telemetryInterval) {
        clearInterval(telemetryInterval)
        telemetryInterval = null
      }
    }

    const startLogUpdates = () => {
      if (!logsInterval) {
        logsInterval = setInterval(fetchLogs, 2000)
        fetchLogs()
      }
    }

    const stopLogUpdates = () => {
      if (logsInterval) {
        clearInterval(logsInterval)
        logsInterval = null
      }
    }

    const updateTelemetry = async () => {
      try {
        const response = await fetchWithTimeout(`${API_URL}/telemetry`, {
          timeout: 3000
        })
        
        const data = await response.json()
        telemetry.value = data
        
        // Update status refs
        gpsStatus.value = {
          fix_type: data.gps_fix_type,
          satellites: data.satellites_visible
        }
        
        vehicleStatus.value = {
          armed: data.armed,
          mode: data.mode,
          battery: data.battery_percentage
        }

        missionInProgress.value = data.mission_in_progress
        
        if (!data.connected && connected.value) {
          handleConnectionLost()
        }
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Telemetry update failed:', error)
          handleConnectionLost()
        }
      }
    }

    const fetchLogs = async () => {
      try {
        const response = await fetchWithTimeout(`${API_URL}/logs`, {
          timeout: 3000
        })
        const data = await response.json()
        logs.value = data.logs
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Failed to fetch logs:', error)
        }
      }
    }

    const clearLogs = async () => {
      try {
        await fetchWithTimeout(`${API_URL}/logs/clear`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          timeout: 3000
        })
        logs.value = []
      } catch (error) {
        console.error('Failed to clear logs:', error)
        showErrorDialog('Error', 'Failed to clear logs', 'Please try again')
      }
    }

    const handleSetMode = async (mode) => {
      if (!connected.value) return
      
      try {
        const response = await fetchWithTimeout(`${API_URL}/set_mode`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode }),
          timeout: 5000
        })

        const data = await response.json()
        if (!data.success) {
          showErrorDialog(
            'Mode Change Failed',
            data.error,
            data.resolution || 'Please try again'
          )
        }
      } catch (error) {
        console.error('Mode change error:', error)
        showErrorDialog(
          'Mode Change Failed',
          'Failed to change flight mode',
          'Check vehicle status and try again'
        )
      }
    }

    const handleToggleArm = async () => {
      if (!connected.value) return
      
      try {
        const response = await fetchWithTimeout(`${API_URL}/arm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ arm: !telemetry.value.armed }),
          timeout: 5000
        })

        const data = await response.json()
        if (!data.success) {
          showErrorDialog(
            'Arm/Disarm Failed',
            data.error,
            data.resolution || 'Please try again'
          )
        }
      } catch (error) {
        console.error('Arm/disarm error:', error)
        showErrorDialog(
          'Arm/Disarm Failed',
          'Failed to arm/disarm vehicle',
          'Check vehicle status and try again'
        )
      }
    }

    const handleStartMission = async (mission) => {
      if (!connected.value) {
        showErrorDialog('Not Connected', 'Please connect before starting mission', 'Connect to the drone first')
        return
      }

      try {
        const response = await fetchWithTimeout(`${API_URL}/mission/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
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
          }),
          timeout: 10000
        })

        const data = await response.json()
        
        if (!data.success) {
          handleMissionError(data)
        } else {
          currentMission.value = mission
          missionInProgress.value = true
          showSuccessMessage('Mission started successfully')
        }
      } catch (error) {
        console.error('Mission start error:', error)
        handleMissionError({
          error: error.message,
          error_type: 'CONNECTION_ERROR',
          resolution: 'Check your connection and try again'
        })
      }
    }

    const handleMissionError = (error) => {
      const actions = []

      switch (error.error_type) {
        case 'GPS_ERROR':
          actions.push({
            text: 'Check GPS Status',
            action: showGPSStatus
          })
          break
        case 'BATTERY_ERROR':
          actions.push({
            text: 'Check Battery',
            action: showBatteryStatus
          })
          break
        case 'ARM_ERROR':
          actions.push({
            text: 'Arm Vehicle',
            action: handleToggleArm
          })
          break
        case 'MODE_ERROR':
          actions.push({
            text: 'Set Mode',
            action: () => handleSetMode('GUIDED')
          })
          break
      }

      showErrorDialog(
        'Mission Error',
        error.error,
        error.resolution,
        actions
      )
    }

    const handleStopMission = async () => {
      if (!connected.value || !missionInProgress.value) return

      try {
        const response = await fetchWithTimeout(`${API_URL}/mission/stop`, {
          method: 'POST',
          timeout: 5000
        })

        const data = await response.json()
        if (data.success) {
          currentMission.value = null
          missionInProgress.value = false
          showSuccessMessage('Mission stopped successfully')
        } else {
          handleMissionError(data)
        }
      } catch (error) {
        console.error('Mission stop error:', error)
        showErrorDialog(
          'Stop Mission Failed',
          'Failed to stop mission',
          'Try switching to LOITER mode manually'
        )
      }
    }

    const handleConnectionLost = () => {
      console.log('Lost connection to server')
      resetConnection()
      showErrorDialog('Connection Lost', 'Lost connection to drone', 'Attempting to reconnect...')
      retryConnection()
    }

    const showErrorDialog = (title, message, resolution, actions = []) => {
      errorDetails.value = {
        title,
        message,
        resolution,
        actions
      }
      showError.value = true
    }

    const showSuccessMessage = (message) => {
        // You can implement this with your preferred UI component/library
        console.log('Success:', message)
      }

      const showGPSStatus = () => {
        showErrorDialog(
          'GPS Status',
          `Fix Type: ${getGPSFixTypeText(gpsStatus.value.fix_type)}
           Satellites: ${gpsStatus.value.satellites}`,
          'Ensure you have clear view of the sky'
        )
      }

      const showBatteryStatus = () => {
        showErrorDialog(
          'Battery Status',
          `Battery Level: ${vehicleStatus.value.battery}%
           Voltage: ${telemetry.value.battery_voltage}V
           Current: ${telemetry.value.battery_current}A`,
          'Ensure battery is sufficiently charged'
        )
      }

      const getGPSFixTypeText = (fixType) => {
        switch (fixType) {
          case 0: return 'No GPS'
          case 1: return '1D Fix'
          case 2: return '2D Fix'
          case 3: return '3D Fix'
          case 4: return '3D Fix + DGPS'
          case 5: return 'RTK Float'
          case 6: return 'RTK Fixed'
          default: return 'Unknown'
        }
      }

      const retryConnection = () => {
        if (connectionAttempts.value < MAX_RETRIES) {
          console.log(`Retrying connection (${connectionAttempts.value}/${MAX_RETRIES})...`)
          setTimeout(connect, RETRY_DELAY)
        } else {
          console.error('Max connection attempts reached')
          connectionAttempts.value = 0
          showErrorDialog(
            'Connection Failed',
            'Maximum connection attempts reached',
            'Please check your network connection and try again'
          )
        }
      }

      onMounted(() => {
        connect()
      })

      onUnmounted(() => {
        resetConnection()
      })

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
      }
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

/* Other existing styles remain the same */

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