# src/components/DroneMap.vue
<template>
  <div class="map-container">
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
      formatCoord
    };
  }
};
</script>

<style scoped>
.map-container {
  position: relative;
  height: 600px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}

#drone-map {
  height: 100%;
  border-radius: 8px;
}

.mission-control {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  max-width: 300px;
  max-height: calc(100% - 20px);
  overflow-y: auto;
}

.mission-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 15px;
}

.control-btn {
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  background: #2196F3;
  color: white;
  cursor: pointer;
  font-size: 14px;
}

.control-btn:hover {
  background: #1976D2;
}

.control-btn:disabled {
  background: #90CAF9;
  cursor: not-allowed;
}

.control-btn.active {
  background: #4CAF50;
}

.control-btn.stop-mission {
  background: #f44336;
}

.control-btn.stop-mission:hover {
  background: #d32f2f;
}

.mission-settings {
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 4px;
}

.setting-group {
  margin: 10px 0;
}

.setting-group label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-group input[type="number"] {
  width: 60px;
  padding: 4px;
}

.waypoint-list {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
}

.waypoint-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: white;
  margin: 5px 0;
  border-radius: 4px;
  font-size: 14px;
}

.waypoint-coords {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: #666;
}

.delete-waypoint {
  background: none;
  border: none;
  color: #f44336;
  cursor: pointer;
  font-size: 18px;
  padding: 0 5px;
}

.delete-waypoint:hover {
  color: #d32f2f;
}

/* Waypoint marker style */
:global(.custom-waypoint .waypoint-marker) {
  width: 20px;
  height: 20px;
  background: #2196F3;
  border: 3px solid white;
  border-radius: 50%;
  box-shadow: 0 0 4px rgba(0,0,0,0.4);
}

@media (max-width: 768px) {
  .map-container {
    height: 400px;
  }

  .mission-control {
    max-width: calc(100% - 20px);
    max-height: 50%;
  }
}
</style>