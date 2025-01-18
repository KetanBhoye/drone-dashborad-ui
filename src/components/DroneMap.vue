<template>
    <div class="map-container">
      <!-- Map Controls -->
      <div class="map-controls-left">
        <button 
          class="center-drone-btn"
          @click="centerOnDrone"
          :disabled="!connected"
          :title="connected ? 'Center on Drone' : 'Drone not connected'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" 
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 4l-6 6h12z"/>
            <path d="M12 20l6-6H12z"/>
            <path d="M4 12l6 6V6z"/>
            <path d="M20 12l-6-6v12z"/>
          </svg>
        </button>
      </div>
  
      <!-- Mission Control Panel -->
      <div class="mission-control">
        <div class="mission-buttons">
          <button 
            :class="['control-btn', { active: isSettingWaypoints }]" 
            @click="toggleWaypointMode"
          >
            {{ isSettingWaypoints ? 'Done Setting Waypoints' : 'Set Waypoints' }}
          </button>
          <button 
            class="control-btn" 
            @click="clearWaypoints"
            :disabled="waypoints.length === 0"
          >
            Clear Waypoints
          </button>
          <button 
            class="control-btn start-mission" 
            @click="startMission"
            :disabled="waypoints.length < 2 || missionInProgress"
          >
            Start Mission
          </button>
          <button 
            class="control-btn stop-mission" 
            @click="stopMission"
            :disabled="!missionInProgress"
          >
            Stop Mission
          </button>
        </div>
  
        <!-- Mission Settings -->
        <div class="mission-settings" v-if="waypoints.length > 0">
          <h3>Mission Settings</h3>
          <div class="setting-group">
            <label>
              Flight Altitude:
              <input 
                type="number" 
                v-model.number="missionSettings.altitude" 
                min="2"
                max="120"
              > meters
            </label>
          </div>
          <div class="setting-group">
            <label>
              Flight Speed:
              <input 
                type="number" 
                v-model.number="missionSettings.speed" 
                min="1"
                max="15"
              > m/s
            </label>
          </div>
          <div class="setting-group">
            <label>
              <input 
                type="checkbox" 
                v-model="missionSettings.returnToHome"
              > Return to Launch
            </label>
          </div>
        </div>
  
        <!-- Waypoint List -->
        <div class="waypoint-list" v-if="waypoints.length > 0">
          <h3>Waypoints</h3>
          <div class="waypoints">
            <div 
              v-for="(waypoint, index) in waypoints" 
              :key="index"
              class="waypoint-item"
            >
              <span>Waypoint {{ index + 1 }}</span>
              <div class="waypoint-coords">
                <span>Lat: {{ formatCoord(waypoint.lat) }}</span>
                <span>Lon: {{ formatCoord(waypoint.lng) }}</span>
                <span>Alt: {{ waypoint.alt }}m</span>
              </div>
              <button 
                class="delete-waypoint" 
                @click="removeWaypoint(index)"
                :disabled="missionInProgress"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      </div>
  
      <!-- Satellite Info -->
      <div class="satellite-info">
        <div class="satellite-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" 
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 21L21 4"/>
            <path d="M9 2L15 8"/>
            <path d="M2 9L8 15"/>
            <path d="M20 14L14 20"/>
          </svg>
        </div>
        <span class="satellite-count" :class="{'good': satellites >= 8, 'warning': satellites < 8 && satellites >= 6, 'poor': satellites < 6}">
          {{ satellites }} satellites
        </span>
      </div>
  
      <!-- Map -->
      <div id="drone-map"></div>
    </div>
  </template>
  
  <script>
  import { ref, onMounted, onUnmounted, watch } from 'vue';
  import 'leaflet/dist/leaflet.css';
  import L from 'leaflet';
  
  export default {
    name: 'DroneMap',
    props: {
      latitude: {
        type: Number,
        default: 0
      },
      longitude: {
        type: Number,
        default: 0
      },
      connected: {
        type: Boolean,
        default: false
      },
      satellites: {
        type: Number,
        default: 0
      }
    },
    
    setup(props, { emit }) {
      const map = ref(null);
      const droneMarker = ref(null);
      const dronePath = ref(null);
      const waypointLayer = ref(null);
      const missionPath = ref(null);
      const isSettingWaypoints = ref(false);
      const missionInProgress = ref(false);
      const waypoints = ref([]);
      const pathCoordinates = ref([]);
  
      const missionSettings = ref({
        altitude: 10,
        speed: 5,
        returnToHome: true
      });
  
      // Custom drone icon
      const droneIcon = L.icon({
        iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMiIgaGVpZ2h0PSIzMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMwMDAwMDAiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNMTIgNGwtNiA2aDEyeiIvPjxwYXRoIGQ9Ik0xMiAyMGw2LTZIMTJ6Ii8+PHBhdGggZD0iTTQgMTJsNiA2di0xMnoiLz48cGF0aCBkPSJNMjAgMTJsLTYtNnYxMnoiLz48L3N2Zz4=',
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });
  
      // Custom waypoint icon
      const waypointIcon = L.divIcon({
        className: 'custom-waypoint',
        html: '<div class="waypoint-marker"></div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      });
  
      const initMap = () => {
        map.value = L.map('drone-map').setView([props.latitude, props.longitude], 16);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors'
        }).addTo(map.value);
  
        droneMarker.value = L.marker([props.latitude, props.longitude], { 
          icon: droneIcon,
          zIndexOffset: 1000
        }).addTo(map.value);
        
        dronePath.value = L.polyline([], {
          color: '#FF4444',
          weight: 2
        }).addTo(map.value);
  
        waypointLayer.value = L.layerGroup().addTo(map.value);
        missionPath.value = L.polyline([], {
          color: '#4444FF',
          weight: 3,
          dashArray: '10, 10'
        }).addTo(map.value);
  
        map.value.on('click', handleMapClick);
      };
  
      const handleMapClick = (e) => {
        if (!isSettingWaypoints.value || !props.connected) return;
  
        const newWaypoint = {
          lat: e.latlng.lat,
          lng: e.latlng.lng,
          alt: missionSettings.value.altitude
        };
  
        waypoints.value.push(newWaypoint);
        updateWaypointVisualization();
      };
  
      const centerOnDrone = () => {
        if (map.value && droneMarker.value) {
          map.value.setView(droneMarker.value.getLatLng(), 18);
        }
      };
  
      const updateWaypointVisualization = () => {
        waypointLayer.value.clearLayers();
        
        waypoints.value.forEach((waypoint, index) => {
          const marker = L.marker([waypoint.lat, waypoint.lng], {
            icon: waypointIcon
          }).addTo(waypointLayer.value);
  
          marker.bindTooltip(`Waypoint ${index + 1}`, {
            permanent: true,
            direction: 'top'
          });
        });
  
        // Update mission path
        const pathCoords = waypoints.value.map(wp => [wp.lat, wp.lng]);
        if (missionSettings.value.returnToHome && pathCoords.length > 0) {
          pathCoords.push(pathCoords[0]); // Add return path
        }
        missionPath.value.setLatLngs(pathCoords);
      };
  
      const toggleWaypointMode = () => {
        isSettingWaypoints.value = !isSettingWaypoints.value;
        if (isSettingWaypoints.value) {
          map.value.getContainer().style.cursor = 'crosshair';
        } else {
          map.value.getContainer().style.cursor = '';
        }
      };
  
      const clearWaypoints = () => {
        waypoints.value = [];
        updateWaypointVisualization();
      };
  
      const removeWaypoint = (index) => {
        waypoints.value.splice(index, 1);
        updateWaypointVisualization();
      };
  
      const formatCoord = (coord) => {
        return coord.toFixed(6);
      };
  
      const startMission = () => {
        if (waypoints.value.length < 2) return;
        
        missionInProgress.value = true;
        isSettingWaypoints.value = false;
        
        const mission = {
          waypoints: waypoints.value,
          settings: { ...missionSettings.value }
        };
        
        emit('start-mission', mission);
      };
  
      const stopMission = () => {
        missionInProgress.value = false;
        emit('stop-mission');
      };
  
      // Watch for drone position updates
      watch(() => [props.latitude, props.longitude], ([newLat, newLon]) => {
        if (!map.value || !droneMarker.value) return;
        
        const newLatLng = [newLat, newLon];
        droneMarker.value.setLatLng(newLatLng);
        
        // Update drone path
        pathCoordinates.value.push(newLatLng);
        dronePath.value.setLatLngs(pathCoordinates.value);
        
        // Center map on first position
        if (pathCoordinates.value.length === 1) {
          map.value.setView(newLatLng, 16);
        }
      });
  
      onMounted(() => {
        initMap();
      });
  
      onUnmounted(() => {
        if (map.value) {
          map.value.remove();
        }
      });
  
      return {
        isSettingWaypoints,
        missionInProgress,
        waypoints,
        missionSettings,
        toggleWaypointMode,
        clearWaypoints,
        removeWaypoint,
        startMission,
        stopMission,
        formatCoord,
        centerOnDrone
      };
    }
  };
  </script>
  # DroneMap.vue styles
  <style>
  /* Container Styles */
  .map-container {
    position: relative;
    height: 600px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 20px;
    overflow: hidden;
  }
  
  #drone-map {
    height: 100%;
    border-radius: 8px;
  }
  
  /* Left Controls */
  .map-controls-left {
    position: absolute;
    top: 80px;
    left: 10px;
    z-index: 1000;
  }
  
  .center-drone-btn {
    width: 40px;
    height: 40px;
    border: none;
    border-radius: 4px;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
  }
  
  .center-drone-btn:hover {
    background: #f5f5f5;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
  }
  
  .center-drone-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  
  /* Mission Control Panel */
  .mission-control {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 1000;
    background: rgba(255, 255, 255, 0.95);
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    max-width: 300px;
    max-height: calc(100% - 20px);
    overflow-y: auto;
    backdrop-filter: blur(10px);
  }
  
  /* Mission Buttons */
  .mission-buttons {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 15px;
  }
  
  .control-btn {
    padding: 10px 12px;
    border: none;
    border-radius: 4px;
    background: #2196F3;
    color: white;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.3s ease;
  }
  
  .control-btn:hover {
    background: #1976D2;
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }
  
  .control-btn:disabled {
    background: #90CAF9;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  
  .control-btn.active {
    background: #4CAF50;
  }
  
  .control-btn.start-mission {
    background: #4CAF50;
  }
  
  .control-btn.start-mission:hover {
    background: #388E3C;
  }
  
  .control-btn.stop-mission {
    background: #f44336;
  }
  
  .control-btn.stop-mission:hover {
    background: #d32f2f;
  }
  
  /* Mission Settings */
  .mission-settings {
    margin-bottom: 15px;
    padding: 12px;
    background: rgba(245, 245, 245, 0.9);
    border-radius: 4px;
    border: 1px solid rgba(0,0,0,0.1);
  }
  
  .mission-settings h3 {
    margin: 0 0 12px 0;
    font-size: 16px;
    color: #333;
    font-weight: 500;
  }
  
  .setting-group {
    margin: 10px 0;
  }
  
  .setting-group label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #666;
  }
  
  .setting-group input[type="number"] {
    width: 70px;
    padding: 6px 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
    transition: border-color 0.2s ease;
  }
  
  .setting-group input[type="number"]:focus {
    border-color: #2196F3;
    outline: none;
  }
  
  .setting-group input[type="checkbox"] {
    width: 16px;
    height: 16px;
    cursor: pointer;
  }
  
  /* Waypoint List */
  .waypoint-list {
    background: rgba(245, 245, 245, 0.9);
    padding: 12px;
    border-radius: 4px;
    border: 1px solid rgba(0,0,0,0.1);
  }
  
  .waypoint-list h3 {
    margin: 0 0 12px 0;
    font-size: 16px;
    color: #333;
    font-weight: 500;
  }
  
  .waypoints {
    max-height: 200px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(0,0,0,0.2) transparent;
  }
  
  .waypoints::-webkit-scrollbar {
    width: 6px;
  }
  
  .waypoints::-webkit-scrollbar-track {
    background: transparent;
  }
  
  .waypoints::-webkit-scrollbar-thumb {
    background-color: rgba(0,0,0,0.2);
    border-radius: 3px;
  }
  
  .waypoint-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    background: white;
    margin: 5px 0;
    border-radius: 4px;
    font-size: 14px;
    transition: all 0.2s ease;
    border: 1px solid transparent;
  }
  
  .waypoint-item:hover {
    background: #f8f8f8;
    border-color: #e0e0e0;
    transform: translateX(2px);
  }
  
  .waypoint-coords {
    display: flex;
    flex-direction: column;
    font-size: 12px;
    color: #666;
    gap: 3px;
  }
  
  .delete-waypoint {
    background: none;
    border: none;
    color: #f44336;
    cursor: pointer;
    font-size: 20px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s ease;
  }
  
  .delete-waypoint:hover {
    background-color: rgba(244, 67, 54, 0.1);
  }
  
  .delete-waypoint:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  /* Satellite Info */
  .satellite-info {
    position: absolute;
    bottom: 10px;
    left: 10px;
    z-index: 1000;
    background: rgba(255, 255, 255, 0.95);
    padding: 8px 12px;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
  }
  
  .satellite-icon {
    color: #666;
    display: flex;
    align-items: center;
  }
  
  .satellite-count {
    font-weight: 500;
    transition: color 0.3s ease;
  }
  
  .satellite-count.good {
    color: #4CAF50;
  }
  
  .satellite-count.warning {
    color: #FF9800;
  }
  
  .satellite-count.poor {
    color: #f44336;
  }
  
  /* Waypoint Marker Style */
  :global(.custom-waypoint .waypoint-marker) {
    width: 20px;
    height: 20px;
    background: rgba(33, 150, 243, 0.9);
    border: 3px solid white;
    border-radius: 50%;
    box-shadow: 0 0 4px rgba(0,0,0,0.4);
    transition: all 0.2s ease;
  }
  
  :global(.custom-waypoint:hover .waypoint-marker) {
    transform: scale(1.1);
    box-shadow: 0 0 6px rgba(0,0,0,0.6);
  }
  
  :global(.leaflet-tooltip) {
    background: rgba(255, 255, 255, 0.9);
    border: none;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    padding: 4px 8px;
    font-size: 12px;
    font-weight: 500;
    backdrop-filter: blur(5px);
  }
  
  /* Responsive Design */
  @media (max-width: 1024px) {
    .mission-control {
      max-width: 280px;
    }
  }
  
  @media (max-width: 768px) {
    .map-container {
      height: 400px;
    }
  
    .mission-control {
      max-width: calc(100% - 20px);
      max-height: 50%;
    }
  
    .waypoints {
      max-height: 150px;
    }
  
    .satellite-info {
      bottom: 20px;
    }
  
    .control-btn {
      padding: 8px 10px;
    }
  }
  
  @media (max-width: 480px) {
    .mission-control {
      top: auto;
      bottom: 60px;
      left: 10px;
      right: 10px;
      max-width: none;
    }
  
    .setting-group label {
      flex-wrap: wrap;
    }
  
    .satellite-info {
      left: 5px;
      right: 5px;
      bottom: 5px;
      justify-content: center;
    }
  }
  </style>