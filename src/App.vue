<template>
  <div id="app">
    <div class="main-container">
      <!-- Header -->
      <header class="header">
        <h1>AI Powered Security Survilance</h1>
        <div class="connection-controls">
          <div class="status-indicator">
            <div :class="['status-dot', connected ? 'connected' : 'disconnected']"></div>
            <span>{{ connected ? 'Connected' : 'Disconnected' }}</span>
            <span v-if="currentMission" class="mission-status">
              Mission in Progress
            </span>
          </div>
          <button @click="connect" :disabled="connecting" class="connect-btn">
            {{ connecting ? 'Connecting...' : 'Connect' }}
          </button>
        </div>
      </header>

      <!-- Map with Mission Control -->
      <DroneMap 
        :latitude="telemetry.lat"
        :longitude="telemetry.lon"
        :connected="connected"
        :satellites="telemetry.satellites"
        @start-mission="handleStartMission"
        @stop-mission="handleStopMission"
      />

      <div class="dashboard-grid">
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
</template>

<script>
import DroneMap from './components/DroneMap.vue'
import DroneDashboard from './components/DroneDashboard.vue'
import LogContainer from './components/LogContainer.vue'
import { ref, onMounted, onUnmounted } from 'vue'

export default {
  name: 'App',
  components: {
    DroneMap,
    DroneDashboard,
    LogContainer
  },
  setup() {
    const API_URL = 'http://192.168.188.143:5000'
    const connected = ref(false)
    const connecting = ref(false)
    const connectionAttempts = ref(0)
    const MAX_RETRIES = 3
    const RETRY_DELAY = 2000 // 2 seconds
    const CONNECTION_TIMEOUT = 5000 // 5 seconds
    const currentMission = ref(null)
    const logs = ref([])
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
      satellites: 0,
    })

    let telemetryInterval = null
    let logsInterval = null
    let connectionTimeout = null

    const resetConnection = () => {
      stopTelemetryUpdates()
      stopLogUpdates()
      connected.value = false
      connecting.value = false
      clearTimeout(connectionTimeout)
    }

    const connect = async () => {
      if (connecting.value) return
      
      connecting.value = true
      connectionAttempts.value++

      // Set connection timeout
      connectionTimeout = setTimeout(() => {
        if (!connected.value) {
          console.error('Connection timeout')
          resetConnection()
          retryConnection()
        }
      }, CONNECTION_TIMEOUT)

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONNECTION_TIMEOUT);

        const response = await fetch(`${API_URL}/connect`, {
          method: 'POST',
          signal: controller.signal
        })
        clearTimeout(timeoutId)

        const data = await response.json()
        if (data.success) {
          connected.value = true
          connectionAttempts.value = 0
          startTelemetryUpdates()
          startLogUpdates()
        } else {
          throw new Error('Connection failed')
        }
      } catch (error) {
        console.error('Connection error:', error)
        resetConnection()
        retryConnection()
      } finally {
        clearTimeout(connectionTimeout)
        connecting.value = false
      }
    }

    const retryConnection = () => {
      if (connectionAttempts.value < MAX_RETRIES) {
        console.log(`Retrying connection (${connectionAttempts.value}/${MAX_RETRIES})...`)
        setTimeout(connect, RETRY_DELAY)
      } else {
        console.error('Max connection attempts reached')
        connectionAttempts.value = 0
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
        fetchLogs() // Initial fetch
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
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout

        const response = await fetch(`${API_URL}/telemetry`, {
          signal: controller.signal
        })
        clearTimeout(timeoutId)

        const data = await response.json()
        telemetry.value = { ...telemetry.value, ...data }
        
        if (!data.connected && connected.value) {
          console.log('Lost connection to server')
          resetConnection()
          retryConnection()
        } else {
          connected.value = data.connected
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          console.error('Telemetry request timeout')
        } else {
          console.error('Telemetry update failed:', error)
        }
        resetConnection()
        retryConnection()
      }
    }

    const fetchLogs = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        const response = await fetch(`${API_URL}/logs`, {
          signal: controller.signal
        })
        clearTimeout(timeoutId)

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
        await fetch(`${API_URL}/logs/clear`, { 
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        logs.value = []
      } catch (error) {
        console.error('Failed to clear logs:', error)
      }
    }

    const handleSetMode = async (mode) => {
      if (!connected.value) return
      
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        const response = await fetch(`${API_URL}/set_mode`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ mode }),
          signal: controller.signal
        })
        clearTimeout(timeoutId)

        const data = await response.json()
        if (!data.success) {
          console.error('Failed to set mode:', data.error)
        }
      } catch (error) {
        console.error('Mode change error:', error)
      }
    }

    const handleToggleArm = async () => {
      if (!connected.value) return
      
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        const response = await fetch(`${API_URL}/arm`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ arm: !telemetry.value.armed }),
          signal: controller.signal
        })
        clearTimeout(timeoutId)

        const data = await response.json()
        if (!data.success) {
          console.error('Failed to arm/disarm:', data.error)
        }
      } catch (error) {
        console.error('Arm/disarm error:', error)
      }
    }

    const handleStartMission = async (mission) => {
      if (!connected.value) return

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(`${API_URL}/mission/start`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
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
          signal: controller.signal
        })
        clearTimeout(timeoutId)

        const data = await response.json()
        if (data.success) {
          currentMission.value = mission
          await handleSetMode('AUTO')
        } else {
          console.error('Failed to start mission:', data.error)
        }
      } catch (error) {
        console.error('Mission start error:', error)
      }
    }

    const handleStopMission = async () => {
      if (!connected.value || !currentMission.value) return

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        const response = await fetch(`${API_URL}/mission/stop`, {
          method: 'POST',
          signal: controller.signal
        })
        clearTimeout(timeoutId)

        const data = await response.json()
        if (data.success) {
          currentMission.value = null
          await handleSetMode('LOITER')
        } else {
          console.error('Failed to stop mission:', data.error)
        }
      } catch (error) {
        console.error('Mission stop error:', error)
      }
    }

    onMounted(() => {
      connect()
    })

    onUnmounted(() => {
      resetConnection()
    })

    return {
      connected,
      connecting,
      currentMission,
      telemetry,
      logs,
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
  max-width: 1200px;
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
}

.status-dot.connected {
  background-color: #4CAF50;
}

.status-dot.disconnected {
  background-color: #f44336;
}

.connect-btn {
  padding: 8px 16px;
  background-color: #1976D2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.connect-btn:hover {
  background-color: #1565C0;
}

.connect-btn:disabled {
  background-color: #90CAF9;
  cursor: not-allowed;
}

.mission-status {
  background-color: #FF9800;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 20px;
  margin-top: 20px;
}

@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
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
}
</style>