<template>
    <div class="bg-white shadow rounded-lg p-4">
      <h2 class="text-lg font-semibold mb-4">Vehicle Status</h2>
      
      <!-- GPS Status -->
      <div class="mb-4">
        <div class="flex items-center justify-between">
          <span class="text-gray-600">GPS</span>
          <span :class="gpsStatusClass">
            {{ gpsStatusText }}
          </span>
        </div>
        <div class="text-sm text-gray-500">
          Satellites: {{ gpsStatus.satellites }}
        </div>
      </div>
  
      <!-- Battery Status -->
      <div class="mb-4">
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Battery</span>
          <span :class="batteryStatusClass">
            {{ vehicleStatus.battery }}%
          </span>
        </div>
        <div class="w-full bg-gray-200 rounded h-2 mt-1">
          <div 
            class="h-full rounded" 
            :class="batteryBarClass"
            :style="{ width: `${vehicleStatus.battery}%` }"
          ></div>
        </div>
      </div>
  
      <!-- Mode -->
      <div class="mb-4">
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Mode</span>
          <span class="font-semibold">
            {{ vehicleStatus.mode }}
          </span>
        </div>
      </div>
  
      <!-- Armed Status -->
      <div>
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Armed</span>
          <span :class="armedStatusClass">
            {{ vehicleStatus.armed ? 'ARMED' : 'DISARMED' }}
          </span>
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
        return {
          'font-semibold': true,
          'text-red-500': this.gpsStatus.fix_type < 2,
          'text-yellow-500': this.gpsStatus.fix_type === 2,
          'text-green-500': this.gpsStatus.fix_type >= 3
        }
      },
      batteryStatusClass() {
        return {
          'font-semibold': true,
          'text-red-500': this.vehicleStatus.battery <= 20,
          'text-yellow-500': this.vehicleStatus.battery <= 50,
          'text-green-500': this.vehicleStatus.battery > 50
        }
      },
      batteryBarClass() {
        return {
          'bg-red-500': this.vehicleStatus.battery <= 20,
          'bg-yellow-500': this.vehicleStatus.battery <= 50,
          'bg-green-500': this.vehicleStatus.battery > 50
        }
      },
      armedStatusClass() {
        return {
          'font-semibold': true,
          'text-red-500': !this.vehicleStatus.armed,
          'text-green-500': this.vehicleStatus.armed
        }
      }
    }
  }
  </script>
  
  <style scoped>
  .status-panel {
    transition: all 0.3s ease;
  }
  
  .status-panel:hover {
    transform: translateY(-2px);
  }
  </style>