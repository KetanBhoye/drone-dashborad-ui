# src/components/DroneDashboard.vue
<template>
  <div class="control-grid">
    <!-- Flight Control -->
    <div class="panel">
      <h2>Flight Control</h2>
      <div class="control-content">
        <div class="mode-select">
          <label>Flight Mode</label>
          <select v-model="selectedMode" @change="setMode" :disabled="!connected">
            <option v-for="mode in flightModes" :key="mode" :value="mode">
              {{ mode }}
            </option>
          </select>
        </div>
        <button 
          @click="toggleArm" 
          :disabled="!connected"
          :class="['arm-btn', telemetry.armed ? 'armed' : 'disarmed']"
        >
          {{ telemetry.armed ? 'DISARM' : 'ARM' }}
        </button>
      </div>
    </div>

    <!-- Status Panel -->
    <div class="panel">
      <h2>Status</h2>
      <div class="status-content">
        <div class="status-row">
          <span>Current Mode:</span>
          <span>{{ telemetry.mode || 'N/A' }}</span>
        </div>
        <div class="status-row">
          <span>Armed Status:</span>
          <span :class="telemetry.armed ? 'armed-text' : 'disarmed-text'">
            {{ telemetry.armed ? 'ARMED' : 'DISARMED' }}
          </span>
        </div>
        <div class="status-row">
          <span>Ground Speed:</span>
          <span>{{ formatNumber(telemetry.groundspeed) }} m/s</span>
        </div>
        <div class="status-row">
          <span>Heading:</span>
          <span>{{ formatNumber(telemetry.heading) }}°</span>
        </div>
      </div>
    </div>

    <!-- Battery Panel -->
    <div class="panel">
      <h2>Battery</h2>
      <div class="battery-content">
        <div class="battery-row">
          <span>Battery Level:</span>
          <div class="battery-indicator">
            <div class="battery-bar">
              <div 
                class="battery-level" 
                :style="{ width: `${telemetry.battery_percentage || 0}%` }"
                :class="getBatteryClass(telemetry.battery_percentage)"
              ></div>
            </div>
            <span>{{ telemetry.battery_percentage || 0 }}%</span>
          </div>
        </div>
        <div class="battery-row">
          <span>Voltage:</span>
          <span>{{ formatNumber(telemetry.battery_voltage) }}V</span>
        </div>
        <div class="battery-row">
          <span>Current:</span>
          <span>{{ formatNumber(telemetry.battery_current) }}A</span>
        </div>
      </div>
    </div>

    <!-- Location Panel -->
    <div class="panel">
      <h2>Location</h2>
      <div class="location-content">
        <div class="location-row">
          <span>Latitude:</span>
          <span>{{ formatNumber(telemetry.lat, 6) }}°</span>
        </div>
        <div class="location-row">
          <span>Longitude:</span>
          <span>{{ formatNumber(telemetry.lon, 6) }}°</span>
        </div>
        <div class="location-row">
          <span>Altitude:</span>
          <span>{{ formatNumber(telemetry.alt) }}m</span>
        </div>
        <div class="location-row">
          <span>Relative Alt:</span>
          <span>{{ formatNumber(telemetry.relative_alt) }}m</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'DroneDashboard',
  props: {
    connected: {
      type: Boolean,
      required: true
    },
    telemetry: {
      type: Object,
      required: true
    }
  },
  setup(props, { emit }) {
    const selectedMode = ref('STABILIZE')
    
    const flightModes = [
      'STABILIZE',
      'ALTHOLD',
      'LOITER',
      'RTL',
      'GUIDED',
      'AUTO',
      'LAND'
    ]

    const formatNumber = (value, decimals = 1) => {
      if (value === undefined || value === null) return 'N/A'
      return Number(value).toFixed(decimals)
    }

    const getBatteryClass = (percentage) => {
      if (percentage < 20) return 'battery-critical'
      if (percentage < 50) return 'battery-warning'
      return 'battery-good'
    }

    const setMode = () => {
      emit('set-mode', selectedMode.value)
    }

    const toggleArm = () => {
      emit('toggle-arm')
    }

    return {
      selectedMode,
      flightModes,
      formatNumber,
      getBatteryClass,
      setMode,
      toggleArm
    }
  }
}
</script>

<style scoped>
.control-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.panel {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.panel h2 {
  color: #333;
  font-size: 18px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}

.mode-select {
  margin-bottom: 16px;
}

.mode-select label {
  display: block;
  margin-bottom: 8px;
  color: #666;
}

select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
}

.arm-btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-weight: bold;
}

.arm-btn.armed {
  background-color: #f44336;
}

.arm-btn.disarmed {
  background-color: #4CAF50;
}

.arm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-row,
.battery-row,
.location-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.armed-text {
  color: #f44336;
  font-weight: bold;
}

.disarmed-text {
  color: #4CAF50;
  font-weight: bold;
}

.battery-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.battery-bar {
  width: 100px;
  height: 16px;
  background-color: #eee;
  border-radius: 8px;
  overflow: hidden;
}

.battery-level {
  height: 100%;
  transition: width 0.3s ease;
}

.battery-good {
  background-color: #4CAF50;
}

.battery-warning {
  background-color: #FFC107;
}

.battery-critical {
  background-color: #f44336;
}
</style>