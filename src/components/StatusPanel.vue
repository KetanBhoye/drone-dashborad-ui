<template>
  <div class="status-panel">
    <h2 class="status-title">Vehicle Status</h2>

    <!-- GPS Status -->
    <div class="status-row">
      <div class="status-label">
        <span>GPS</span>
        <!-- Dot indicator based on fix quality -->
        <span class="status-dot" :class="gpsDotClass"></span>
      </div>
      <span class="status-value" :class="gpsStatusClass">
        {{ gpsStatusText }}
      </span>
    </div>
    <div class="status-subtext">Satellites: {{ gpsStatus.satellites }}</div>

    <!-- Battery Status -->
    <div class="status-row">
      <div class="status-label">Battery</div>
      <span class="status-value" :class="batteryStatusClass">
        {{ vehicleStatus.battery }}%
      </span>
    </div>
    <div class="battery-bar-container">
      <div 
        class="battery-bar" 
        :class="batteryBarClass" 
        :style="{ width: `${vehicleStatus.battery}%` }"
      ></div>
    </div>

    <!-- Mode -->
    <div class="status-row">
      <div class="status-label">Mode</div>
      <span class="status-value">{{ vehicleStatus.mode }}</span>
    </div>

    <!-- Armed Status -->
    <div class="status-row">
      <div class="status-label">Armed</div>
      <span class="status-value" :class="armedStatusClass">
        {{ vehicleStatus.armed ? 'ARMED' : 'DISARMED' }}
      </span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StatusPanel',
  props: {
    gpsStatus: {
      type: Object,
      required: true,
      default: () => ({
        fix_type: 0,
        satellites: 0
      })
    },
    vehicleStatus: {
      type: Object,
      required: true,
      default: () => ({
        armed: false,
        mode: 'UNKNOWN',
        battery: 0
      })
    }
  },
  computed: {
    gpsStatusText() {
      const fixTypes = {
        0: 'No Fix',
        1: '1D Fix',
        2: '2D Fix',
        3: '3D Fix',
        4: '3D Fix+DGPS',
        5: 'RTK Float',
        6: 'RTK Fixed'
      }
      return fixTypes[this.gpsStatus.fix_type] || 'Unknown'
    },
    gpsStatusClass() {
      // Dynamically set text color based on GPS fix type
      if (this.gpsStatus.fix_type < 2) {
        return 'gps-bad'
      } else if (this.gpsStatus.fix_type === 2) {
        return 'gps-medium'
      } else {
        return 'gps-good'
      }
    },
    gpsDotClass() {
      // Dot color to visually indicate fix quality
      if (this.gpsStatus.fix_type < 2) {
        return 'gps-dot-bad'
      } else if (this.gpsStatus.fix_type === 2) {
        return 'gps-dot-medium'
      } else {
        return 'gps-dot-good'
      }
    },
    batteryStatusClass() {
      // Battery text color based on percentage
      if (this.vehicleStatus.battery <= 20) {
        return 'battery-low'
      } else if (this.vehicleStatus.battery <= 50) {
        return 'battery-medium'
      } else {
        return 'battery-high'
      }
    },
    batteryBarClass() {
      // Battery bar color fill
      if (this.vehicleStatus.battery <= 20) {
        return 'battery-bar-low'
      } else if (this.vehicleStatus.battery <= 50) {
        return 'battery-bar-medium'
      } else {
        return 'battery-bar-high'
      }
    },
    armedStatusClass() {
      // Armed vs. Disarmed text color
      return this.vehicleStatus.armed ? 'armed' : 'disarmed'
    }
  }
}
</script>

<style scoped>
/* Container styles */
.status-panel {
  background-color: #ffffff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  border-radius: 8px;
  padding: 20px;
  transition: transform 0.3s ease;
  max-width: 400px;
  margin-bottom: 20px; /* if needed */
}

.status-panel:hover {
  transform: translateY(-4px);
}

.status-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 1rem;
  border-bottom: 1px solid #e2e2e2;
  padding-bottom: 0.5rem;
}

/* Row for each status item */
.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.status-label {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #4a5568; /* A medium gray */
}

.status-dot {
  margin-left: 0.5rem;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 9999px;
}

/* Dot color states */
.gps-dot-bad {
  background-color: #f56565; /* red */
}
.gps-dot-medium {
  background-color: #ecc94b; /* yellow */
}
.gps-dot-good {
  background-color: #48bb78; /* green */
}

/* Text value states */
.status-value {
  font-weight: 600;
}

.gps-bad {
  color: #f56565; /* red */
}
.gps-medium {
  color: #ecc94b; /* yellow */
}
.gps-good {
  color: #48bb78; /* green */
}

.battery-low {
  color: #f56565; /* red */
}
.battery-medium {
  color: #ecc94b; /* yellow */
}
.battery-high {
  color: #48bb78; /* green */
}

.armed {
  color: #48bb78; /* green */
}
.disarmed {
  color: #f56565; /* red */
}

.status-subtext {
  font-size: 0.875rem;
  color: #718096;
  margin-bottom: 1.5rem;
}

/* Battery bar container */
.battery-bar-container {
  width: 100%;
  background-color: #e2e8f0; /* a light gray */
  height: 8px;
  border-radius: 9999px;
  margin-bottom: 1rem;
  position: relative;
}

/* Battery bar fill */
.battery-bar {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.battery-bar-low {
  background-color: #f56565; /* red */
}
.battery-bar-medium {
  background-color: #ecc94b; /* yellow */
}
.battery-bar-high {
  background-color: #48bb78; /* green */
}
</style>
