// DroneCamera.vue
<template>
  <div class="camera-container">
    <div class="camera-header">
      <h3>Live Camera Feed</h3>
      <div class="camera-status" :class="{ active: streamActive }">
        {{ streamActive ? 'Stream Active' : 'Stream Inactive' }}
      </div>
    </div>
    
    <div class="camera-view" :class="{ 'no-signal': !streamActive }">
      <!-- JSMpeg player will be mounted here -->
      <div ref="videoCanvas" class="video-canvas"></div>
      
      <!-- Fallback/placeholder when stream is not active -->
      <div v-if="!streamActive" class="no-signal-message">
        <div class="no-signal-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10 10L2 18M10 10L18 2M10 10L2 2M10 10L18 18"></path>
          </svg>
        </div>
        <p>{{ connected ? 'Connecting to stream...' : 'Camera stream unavailable' }}</p>
      </div>
    </div>
    
    <div class="camera-controls">
      <button @click="toggleFullscreen" class="control-btn">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 3v3M3 8h3m10-5v3m5 2h-3M8 21v-3m-5-2h3m10 5v-3m5-2h-3"></path>
        </svg>
        Fullscreen
      </button>
      
      <button @click="reloadStream" class="control-btn" :disabled="!connected">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 10c0-3.314 2.686-6 6-6s6 2.686 6 6-2.686 6-6 6-6-2.686-6-6zm12 0h4m-4 0l2-2m-2 2l2 2"></path>
        </svg>
        Reload Stream
      </button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue';

// Tell ESLint that JSMpeg is a global variable from an external script
/* global JSMpeg */

export default {
  name: 'DroneCamera',
  props: {
    connected: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const videoCanvas = ref(null);
    const streamActive = ref(false);
    let player = null;
    let reconnectTimer = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    
    // Server URL - update this to your Digital Ocean server address
    const SERVER_URL = 'http://139.59.81.191';
    
    const initializePlayer = () => {
      // Check if JSMpeg library is loaded
      if (typeof JSMpeg === 'undefined') {
        console.error('JSMpeg library not loaded');
        loadJSMpegScript();
        return;
      }
      
      if (!videoCanvas.value) return;
      
      // Destroy existing player if it exists
      if (player) {
        player.destroy();
        player = null;
      }
      
      try {
        // Create WebSocket URL for the stream
        const wsUrl = `ws://${SERVER_URL.replace(/^https?:\/\//, '')}/live/drone`;
        
        // Configure and create the player
        player = new JSMpeg.Player(wsUrl, {
          canvas: videoCanvas.value,
          autoplay: true,
          audio: false,
          loop: false,
          onSourceEstablished: () => {
            console.log('Stream source established');
            streamActive.value = true;
            reconnectAttempts = 0;
            if (reconnectTimer) {
              clearTimeout(reconnectTimer);
              reconnectTimer = null;
            }
          },
          onSourceCompleted: () => {
            console.log('Stream source completed');
            streamActive.value = false;
            scheduleReconnect();
          },
          onStalled: () => {
            console.log('Stream stalled');
            streamActive.value = false;
            scheduleReconnect();
          }
        });
      } catch (error) {
        console.error('Error initializing video player:', error);
        streamActive.value = false;
        scheduleReconnect();
      }
    };
    
    const loadJSMpegScript = () => {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsmpeg/0.2/jsmpeg.min.js';
      script.onload = () => {
        console.log('JSMpeg library loaded');
        initializePlayer();
      };
      script.onerror = () => {
        console.error('Failed to load JSMpeg library');
      };
      document.head.appendChild(script);
    };
    
    const scheduleReconnect = () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        console.log('Max reconnect attempts reached');
        return;
      }
      
      reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000); // Exponential backoff with max 30s
      
      console.log(`Scheduling stream reconnect in ${delay}ms (attempt ${reconnectAttempts})`);
      reconnectTimer = setTimeout(() => {
        if (props.connected) {
          console.log('Attempting to reconnect to stream...');
          initializePlayer();
        }
      }, delay);
    };
    
    const reloadStream = () => {
      if (!props.connected) return;
      
      console.log('Manually reloading stream');
      reconnectAttempts = 0;
      initializePlayer();
    };
    
    const toggleFullscreen = () => {
      const container = videoCanvas.value?.parentElement;
      if (!container) return;
      
      if (!document.fullscreenElement) {
        container.requestFullscreen().catch(err => {
          console.error(`Error attempting to enable fullscreen mode: ${err.message}`);
        });
      } else {
        document.exitFullscreen();
      }
    };
    
    // Watch for connection status changes
    watch(() => props.connected, (newValue) => {
      if (newValue) {
        // Connection established, initialize player
        initializePlayer();
      } else {
        // Connection lost, update UI
        streamActive.value = false;
        if (player) {
          player.destroy();
          player = null;
        }
      }
    });
    
    onMounted(() => {
      // Check if JSMpeg is already loaded
      if (typeof JSMpeg === 'undefined') {
        loadJSMpegScript();
      } else {
        // Initialize player if connection is already established
        if (props.connected) {
          initializePlayer();
        }
      }
      
      // Add fullscreen change event listener
      document.addEventListener('fullscreenchange', handleFullscreenChange);
    });
    
    onUnmounted(() => {
      // Clean up resources
      if (player) {
        player.destroy();
        player = null;
      }
      
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    });
    
    const handleFullscreenChange = () => {
      // You can add additional logic here if needed when fullscreen state changes
    };
    
    return {
      videoCanvas,
      streamActive,
      reloadStream,
      toggleFullscreen
    };
  }
}
</script>

<style scoped>
.camera-container {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
}

.camera-header {
  padding: 15px;
  background: #f8f9fa;
  border-bottom: 1px solid #e1e4e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.camera-header h3 {
  margin: 0;
  font-size: 18px;
  color: #2c3e50;
}

.camera-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  background-color: #f44336;
  color: white;
}

.camera-status.active {
  background-color: #4CAF50;
}

.camera-view {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background-color: #000;
  overflow: hidden;
}

.video-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.no-signal-message {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: white;
  background-color: rgba(0, 0, 0, 0.7);
}

.no-signal-icon {
  margin-bottom: 15px;
  opacity: 0.7;
}

.camera-controls {
  padding: 10px;
  background: #f8f9fa;
  border-top: 1px solid #e1e4e8;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.control-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  background-color: #f0f2f5;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.control-btn:hover:not(:disabled) {
  background-color: #e2e8f0;
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Fullscreen styles */
:fullscreen .camera-container {
  width: 100%;
  height: 100%;
}

:fullscreen .camera-view {
  flex: 1;
  aspect-ratio: auto;
}
</style>