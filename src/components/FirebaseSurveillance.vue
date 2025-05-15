<template>
  <div class="firebase-surveillance">
    <div class="card">
      <div class="card-header">
        <h3>AI Surveillance Feed</h3>
        <div class="detection-badge" v-if="latestImage">
          <span :class="['badge', getStatusClass(latestImage.Category)]">
            {{ latestImage.Category }}
          </span>
        </div>
      </div>
      
      <div class="card-body">
        <div v-if="loading" class="loading-container">
          <div class="spinner"></div>
          <p>Loading surveillance feed...</p>
        </div>
        
        <div v-else-if="error" class="error-container">
          <p>{{ error }}</p>
          <button @click="reconnectFirebase" class="btn btn-primary">Try Again</button>
        </div>
        
        <div v-else-if="latestImage" class="image-container">
          <img :src="latestImage.URL" alt="Surveillance Feed" class="surveillance-image" />
          
          <div class="image-overlay">
            <div class="timestamp">{{ formatTime(latestImage.Time) }}</div>
            
            <div v-if="showInfo" class="info-panel">
              <div class="info-row">
                <span class="info-label">Time:</span>
                <span class="info-value">{{ formatTime(latestImage.Time) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">Location:</span>
                <span class="info-value">
                  {{ latestImage.Latitude }}, {{ latestImage.Longitude }}
                </span>
              </div>
              <div class="info-row" v-if="latestImage.Confidence !== undefined">
                <span class="info-label">Confidence:</span>
                <span class="info-value">{{ (latestImage.Confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          
          <div class="controls">
            <button @click="showInfo = !showInfo" class="btn btn-sm btn-secondary">
              {{ showInfo ? 'Hide Info' : 'Show Info' }}
            </button>
          </div>
        </div>
        
        <div v-else class="no-image">
          <p>No surveillance images available</p>
        </div>
      </div>
    </div>
    
    <div class="detection-history">
      <h4>Detection History</h4>
      <div class="history-list">
        <div v-if="imageHistory.length === 0" class="no-history">
          <p>No detection history available</p>
        </div>
        <div v-else class="history-items">
          <div 
            v-for="(image, index) in imageHistory" 
            :key="index" 
            class="history-item"
            @click="viewHistoryImage(image)"
          >
            <div class="history-thumbnail">
              <img :src="image.URL" alt="Detection" />
            </div>
            <div class="history-details">
              <div :class="['history-category', getCategoryClass(image.Category)]">
                {{ image.Category }}
              </div>
              <div class="history-time">{{ formatTime(image.Time) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Modal for viewing history images -->
    <div v-if="selectedImage" class="history-modal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ selectedImage.Category }}</h3>
          <button @click="selectedImage = null" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <img :src="selectedImage.URL" alt="Detection" class="modal-image" />
          <div class="modal-details">
            <div class="info-row">
              <span class="info-label">Time:</span>
              <span class="info-value">{{ formatTime(selectedImage.Time) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Location:</span>
              <span class="info-value">
                {{ selectedImage.Latitude }}, {{ selectedImage.Longitude }}
              </span>
            </div>
            <div class="info-row" v-if="selectedImage.Confidence !== undefined">
              <span class="info-label">Confidence:</span>
              <span class="info-value">
                {{ (selectedImage.Confidence * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';
import firebase from 'firebase/app';
import 'firebase/database';

export default {
  name: 'FirebaseSurveillance',
  emits: ['detection'],
  setup(props, { emit }) {
    const latestImage = ref(null);
    const imageHistory = ref([]);
    const loading = ref(true);
    const error = ref(null);
    const showInfo = ref(true);
    const selectedImage = ref(null);
    
    // Firebase configuration
    const firebaseConfig = {
      apiKey: "",
      authDomain: "wce-surveillance.firebaseapp.com",
      databaseURL: "https://wce-surveillance-default-rtdb.firebaseio.com",
      projectId: "wce-surveillance",
      storageBucket: "wce-surveillance.appspot.com",
      messagingSenderId: "224246463722",
      appId: "1:224246463722:web:3e34b89fd00c14ea9582d4"
    };
    
    // Initialize Firebase if not already initialized
    if (!firebase.apps.length) {
      firebase.initializeApp(firebaseConfig);
    }
    
    // Reference to images in Firebase
    const imagesRef = firebase.database().ref('images');
    
    // Listen for image updates
    const setupFirebaseListener = () => {
      loading.value = true;
      error.value = null;
      
      imagesRef.limitToLast(10).on('value', (snapshot) => {
        loading.value = false;
        
        try {
          const data = snapshot.val();
          
          if (data) {
            // Convert to array and sort by time
            const imagesArray = Object.entries(data).map(([key, value]) => ({
              id: key,
              ...value
            })).sort((a, b) => {
              // Sort by time (newest first)
              return new Date(b.Time) - new Date(a.Time);
            });
            
            // Update latest image and history
            if (imagesArray.length > 0) {
              // Check if latest image is different
              if (!latestImage.value || 
                  latestImage.value.id !== imagesArray[0].id) {
                
                const newImage = imagesArray[0];
                latestImage.value = newImage;
                
                // Emit detection event if category is significant
                const category = newImage.Category.toLowerCase();
                if (category.includes('violence') || 
                    category.includes('fire') || 
                    category.includes('crowd')) {
                  emit('detection', {
                    type: category.includes('violence') ? 'violence' : 
                          category.includes('fire') ? 'fire' : 'crowd',
                    image: newImage,
                    message: `${newImage.Category} detected!`,
                    confidence: newImage.Confidence
                  });
                }
              }
            }
            
            // Update history
            imageHistory.value = imagesArray;
          } else {
            latestImage.value = null;
            imageHistory.value = [];
          }
        } catch (err) {
          console.error('Error processing Firebase data:', err);
          error.value = 'Error loading surveillance data';
        }
      }, (err) => {
        loading.value = false;
        error.value = `Firebase error: ${err.message}`;
        console.error('Firebase error:', err);
      });
    };
    
    // Reconnect to Firebase
    const reconnectFirebase = () => {
      imagesRef.off(); // Detach listeners
      setupFirebaseListener(); // Reconnect
    };
    
    // View history image
    const viewHistoryImage = (image) => {
      selectedImage.value = image;
    };
    
    // Format time
    const formatTime = (timeString) => {
      if (!timeString) return 'Unknown';
      
      try {
        const date = new Date(timeString);
        return date.toLocaleString();
      } catch (e) {
        return timeString;
      }
    };
    
    // Get status class for category
    const getStatusClass = (category) => {
      if (!category) return '';
      
      const lowerCategory = category.toLowerCase();
      
      if (lowerCategory.includes('violence')) {
        return 'danger';
      } else if (lowerCategory.includes('fire')) {
        return 'warning';
      } else if (lowerCategory.includes('crowd')) {
        return 'info';
      } else {
        return 'success';
      }
    };
    
    // Get category class
    const getCategoryClass = (category) => {
      return `cat-${getStatusClass(category)}`;
    };
    
    // Setup when component mounts
    onMounted(() => {
      setupFirebaseListener();
    });
    
    // Clean up when component unmounts
    onUnmounted(() => {
      imagesRef.off();
    });
    
    return {
      latestImage,
      imageHistory,
      loading,
      error,
      showInfo,
      selectedImage,
      reconnectFirebase,
      viewHistoryImage,
      formatTime,
      getStatusClass,
      getCategoryClass
    };
  }
};
</script>

<style scoped>
.firebase-surveillance {
  width: 100%;
  margin-bottom: 20px;
}

.card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #eee;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #2c3e50;
}

.detection-badge .badge {
  padding: 6px 10px;
  border-radius: 4px;
  font-weight: bold;
  color: white;
}

.badge.danger {
  background-color: #e74c3c;
}

.badge.warning {
  background-color: #f39c12;
}

.badge.info {
  background-color: #3498db;
}

.badge.success {
  background-color: #2ecc71;
}

.card-body {
  padding: 0;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  padding: 20px;
}

.error-container p {
  color: #e74c3c;
  margin-bottom: 15px;
}

.image-container {
  position: relative;
  width: 100%;
  height: 0;
  padding-bottom: 60%; /* 16:9 aspect ratio */
  background-color: #000;
}

.surveillance-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 10px;
}

.timestamp {
  background-color: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: inline-block;
}

.info-panel {
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
}

.info-row {
  margin-bottom: 5px;
}

.info-label {
  font-weight: bold;
  margin-right: 5px;
}

.controls {
  position: absolute;
  top: 10px;
  right: 10px;
}

.no-image {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #7f8c8d;
}

.detection-history {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 15px;
}

.detection-history h4 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
  color: #2c3e50;
}

.history-list {
  max-height: 300px;
  overflow-y: auto;
}

.no-history {
  padding: 20px;
  text-align: center;
  color: #7f8c8d;
}

.history-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 10px;
}

.history-item {
  display: flex;
  background-color: #f8f9fa;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;
}

.history-item:hover {
  transform: scale(1.02);
}

.history-thumbnail {
  width: 80px;
  height: 80px;
  overflow: hidden;
  flex-shrink: 0;
}

.history-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.history-details {
  padding: 8px;
  flex-grow: 1;
}

.history-category {
  font-weight: bold;
  padding: 3px 6px;
  border-radius: 3px;
  font-size: 12px;
  display: inline-block;
  color: white;
  margin-bottom: 5px;
}

.cat-danger {
  background-color: #e74c3c;
}

.cat-warning {
  background-color: #f39c12;
}

.cat-info {
  background-color: #3498db;
}

.cat-success {
  background-color: #2ecc71;
}

.history-time {
  font-size: 12px;
  color: #7f8c8d;
}

.history-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #7f8c8d;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.modal-image {
  max-width: 100%;
  max-height: 60vh;
  object-fit: contain;
  margin: 0 auto;
}

.modal-details {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
}

/* Responsive design */
@media (max-width: 768px) {
  .history-items {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    width: 95%;
  }
}
</style>
