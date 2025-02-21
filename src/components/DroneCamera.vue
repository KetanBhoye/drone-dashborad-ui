<!-- DroneCamera.vue -->
<template>
    <div class="camera-container">
      <div class="camera-header">
        <h3>Live Camera Feed</h3>
        <div class="camera-status">
          <div :class="['status-indicator', streamActive ? 'active' : 'inactive']"></div>
          <span>{{ streamStatus }}</span>
        </div>
      </div>
      <div class="camera-feed">
        <img 
          v-if="connected"
          :src="streamUrl" 
          @load="handleStreamLoad" 
          @error="handleStreamError"
          alt="Drone Camera Feed"
        />
        <div v-else class="no-signal">
          <span>Camera feed unavailable</span>
          <small>Please connect to the drone</small>
        </div>
      </div>
    </div>
  </template>
  
  <script>
 export default {
  name: 'DroneCamera',
  props: {
    connected: {
      type: Boolean,
      required: true
    }
  },
  data() {
    return {
      streamActive: false,
      streamUrl: ' http://192.168.225.139:8000/stream',  // Updated port to 8000
      frameCount: 0,
      lastTime: Date.now()
    }
  },
  computed: {
    streamStatus() {
      if (!this.connected) return 'Disconnected'
      return this.streamActive ? 'Live' : 'No Signal'
    }
  },
  methods: {
    handleStreamLoad() {
      this.streamActive = true
      this.frameCount++
      const now = Date.now()
      if (now - this.lastTime >= 1000) {
        this.frameCount = 0
        this.lastTime = now
      }
    },
    handleStreamError() {
      this.streamActive = false
    }
  }
}
  </script>
  
  <style scoped>
  .camera-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow: hidden;
    margin-top: 20px;
  }
  
  .camera-header {
    padding: 15px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #eee;
  }
  
  .camera-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
  }
  
  .camera-status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
  }
  
  .status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #dc3545;
  }
  
  .status-indicator.active {
    background-color: #28a745;
  }
  
  .camera-feed {
    position: relative;
    width: 100%;
    height: 0;
    padding-bottom: 56.25%; /* 16:9 aspect ratio */
    background-color: #f8f9fa;
  }
  
  .camera-feed img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  
  .no-signal {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: #6c757d;
  }
  
  .no-signal small {
    margin-top: 8px;
    opacity: 0.7;
  }
  </style>