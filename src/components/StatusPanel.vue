<template>
  <div class="status-panel">
    <h2 class="status-title">Vehicle Status</h2>

    <!-- Main container: horizontal row (wrap on small screens) -->
    <div class="status-row">
      <!-- GPS Item -->
      <div class="status-item">
        <div class="icon-and-text">
          <!-- GPS Icon -->
          <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8c-1.654 0-3 .672-3 1.5S10.346 11 12 11s3-.672 3-1.5S13.654 8 12 8zm0 0v3.5m0 3.5v.01M4.929 4.929c3.905-3.905 10.237-3.905 14.142 0 3.905 3.905 3.905 10.237 0 14.142-3.905 3.905-10.237 3.905-14.142 0-3.905-3.905-3.905-10.237 0-14.142z"
            />
          </svg>
          <span class="status-label">GPS</span>
          <!-- GPS Dot + Fix Text -->
          <span class="gps-dot" :class="gpsDotClass"></span>
          <span class="status-value" :class="gpsStatusClass">
            {{ gpsStatusText }}
          </span>
        </div>
        <div class="status-subtext">
          Satellites: {{ gpsStatus.satellites }}
        </div>
      </div>

      <!-- Battery Item -->
      <div class="status-item">
        <div class="icon-and-text">
          <!-- Battery Icon -->
          <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <rect x="2" y="7" width="16" height="10" rx="2" ry="2" stroke-width="2"></rect>
            <path d="M22 11v2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
          </svg>
          <span class="status-label">Battery</span>
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
      </div>

      <!-- Mode Item -->
      <div class="status-item">
        <div class="icon-and-text">
          <!-- Mode Icon (Paper Airplane) -->
          <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10.125 14.313l2.374 6.22a1 1 0 0 0 1.88-.036l6.463-15.035a1 1 0 0 0-1.275-1.274L4.492 9.71a1 1 0 0 0-.036 1.88l6.22 2.374z"
            />
          </svg>
          <span class="status-label">Mode</span>
          <span class="status-value">{{ vehicleStatus.mode }}</span>
        </div>
      </div>

      <!-- Armed Item -->
      <div class="status-item">
        <div class="icon-and-text">
          <!-- Armed Icon (Lock) -->
          <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 11V7a4 4 0 1 1 8 0v4m-3 5v2m-2 0h4m-2-2v-2m6 2a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v5z"
            />
          </svg>
          <span class="status-label">Armed</span>
          <span class="status-value" :class="armedStatusClass">
            {{ vehicleStatus.armed ? 'ARMED' : 'DISARMED' }}
          </span>
        </div>
      </div>
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
      if (this.gpsStatus.fix_type < 2) {
        return 'gps-bad'
      } else if (this.gpsStatus.fix_type === 2) {
        return 'gps-medium'
      } else {
        return 'gps-good'
      }
    },
    gpsDotClass() {
      if (this.gpsStatus.fix_type < 2) {
        return 'gps-dot-bad'
      } else if (this.gpsStatus.fix_type === 2) {
        return 'gps-dot-medium'
      } else {
        return 'gps-dot-good'
      }
    },
    batteryStatusClass() {
      if (this.vehicleStatus.battery <= 20) {
        return 'battery-low'
      } else if (this.vehicleStatus.battery <= 50) {
        return 'battery-medium'
      } else {
        return 'battery-high'
      }
    },
    batteryBarClass() {
      if (this.vehicleStatus.battery <= 20) {
        return 'battery-bar-low'
      } else if (this.vehicleStatus.battery <= 50) {
        return 'battery-bar-medium'
      } else {
        return 'battery-bar-high'
      }
    },
    armedStatusClass() {
      return this.vehicleStatus.armed ? 'armed' : 'disarmed'
    }
  }
}
</script>

<style scoped>
/* Overall panel styling */
.status-panel {
  width: 100%;
  background-color: #ffffff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 20px;
  transition: transform 0.3s ease;
}
.status-panel:hover {
  transform: translateY(-2px);
}

.status-title {
  font-size: 1.25rem; /* ~20px */
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 1rem;
  border-bottom: 1px solid #e2e2e2;
  padding-bottom: 0.5rem;
}

/* Horizontal row of items, wrapping on small screens */
.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
}

/* Each item: flex column to stack subtext or bars */
.status-item {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 140px; /* Adjust as needed */
}

/* Icon + label + value in one row */
.icon-and-text {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 500;
  color: #4a5568;
}

/* The label is semi-bold, value is bold */
.status-label {
  font-weight: 500;
  color: #4a5568;
}

/* The actual numeric or text value (No Fix, 3D Fix, etc.) */
.status-value {
  font-weight: 600;
  color: #2d3748; /* slightly darker gray */
}

/* Subtext for satellites, etc. */
.status-subtext {
  margin-top: 0.2rem;
  font-size: 0.875rem;
  color: #718096;
}

/* Small icon size */
.status-icon {
  width: 18px;
  height: 18px;
  stroke-width: 2;
  stroke: #4a5568;
}

/* GPS Dot next to the label */
.gps-dot {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 9999px;
  margin-left: 0.2rem;
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

/* Text color states */
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
  color: #f56565;
}
.battery-medium {
  color: #ecc94b;
}
.battery-high {
  color: #48bb78;
}
.armed {
  color: #48bb78;
}
.disarmed {
  color: #f56565;
}

/* Battery bar container */
.battery-bar-container {
  margin-top: 0.3rem;
  background-color: #e2e8f0;
  height: 6px;
  border-radius: 9999px;
  position: relative;
  width: 100%;
}

/* Battery bar fill */
.battery-bar {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease;
}
.battery-bar-low {
  background-color: #f56565;
}
.battery-bar-medium {
  background-color: #ecc94b;
}
.battery-bar-high {
  background-color: #48bb78;
}
</style>
