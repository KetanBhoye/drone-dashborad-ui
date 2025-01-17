# App.vue
<template>
  <div id="app">
    <div class="main-container">
      <!-- Header -->
      <header class="header">
        <h1>Drone Control Panel</h1>
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
        @start-mission="handleStartMission"
        @stop-mission="handleStopMission"
      />

      <!-- Dashboard -->
      <DroneDashboard 
        :connected="connected"
        :telemetry="telemetry"
        @set-mode="handleSetMode"
        @toggle-arm="handleToggleArm"
      />
    </div>
  </div>
</template>

<script>
import DroneMap from './components/DroneMap.vue'
import DroneDashboard from './components/DroneDashboard.vue'
import { ref, onMounted, onUnmounted } from 'vue'

export default {
  name: 'App',
  components: {
    DroneMap,
    DroneDashboard
  },
  setup() {
    const API_URL = 'http://192.168.188.143:5000'
    const connected = ref(false)
    const connecting = ref(false)
    const currentMission = ref(null)
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
      armed: false
    })

    let telemetryInterval = null

    const connect = async () => {
      if (connecting.value) return
      
      connecting.value = true
      try {
        const response = await fetch(`${API_URL}/connect`, {
          method: 'POST'
        })
        const data = await response.json()
        if (data.success) {
          connected.value = true
          startTelemetryUpdates()
        }
      } catch (error) {
        console.error('Connection error:', error)
      } finally {
        connecting.value = false
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

    const updateTelemetry = async () => {
      try {
        const response = await fetch(`${API_URL}/telemetry`)
        const data = await response.json()
        telemetry.value = { ...telemetry.value, ...data }
        connected.value = data.connected
        if (!data.connected) {
          stopTelemetryUpdates()
        }
      } catch (error) {
        console.error('Telemetry update failed:', error)
        connected.value = false
        stopTelemetryUpdates()
      }
    }

    const handleSetMode = async (mode) => {
      if (!connected.value) return
      
      try {
        await fetch(`${API_URL}/set_mode`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ mode })
        })
      } catch (error) {
        console.error('Mode change error:', error)
      }
    }

    const handleToggleArm = async () => {
      if (!connected.value) return
      
      try {
        await fetch(`${API_URL}/arm`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ arm: !telemetry.value.armed })
        })
      } catch (error) {
        console.error('Arm/disarm error:', error)
      }
    }

    const handleStartMission = async (mission) => {
      if (!connected.value) return

      try {
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
          })
        })

        const data = await response.json()
        if (data.success) {
          currentMission.value = mission
          // Set mode to AUTO or GUIDED depending on your drone's configuration
          await handleSetMode('AUTO')
        }
      } catch (error) {
        console.error('Mission start error:', error)
      }
    }

    const handleStopMission = async () => {
      if (!connected.value || !currentMission.value) return

      try {
        const response = await fetch(`${API_URL}/mission/stop`, {
          method: 'POST'
        })

        const data = await response.json()
        if (data.success) {
          currentMission.value = null
          // Return to a stable mode
          await handleSetMode('LOITER')
        }
      } catch (error) {
        console.error('Mission stop error:', error)
      }
    }

    onMounted(() => {
      connect()
    })

    onUnmounted(() => {
      stopTelemetryUpdates()
    })

    return {
      connected,
      connecting,
      currentMission,
      telemetry,
      connect,
      handleSetMode,
      handleToggleArm,
      handleStartMission,
      handleStopMission
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