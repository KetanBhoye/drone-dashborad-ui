# src/components/LogContainer.vue
<template>
  <div class="panel log-container">
    <div class="panel-header">
      <h2>System Logs</h2>
      <div class="log-controls">
        <select v-model="filterType" class="filter-select">
          <option value="all">All Logs</option>
          <option value="error">Errors</option>
          <option value="warning">Warnings</option>
          <option value="info">Info</option>
        </select>
        <button @click="clearLogs" class="clear-btn">
          Clear Logs
        </button>
      </div>
    </div>
    
    <div class="log-content" ref="logContent" @scroll="handleScroll">
      <div v-if="filteredLogs.length === 0" class="no-logs">
        No logs to display
      </div>
      <div 
        v-for="(log, index) in filteredLogs" 
        :key="index"
        :class="['log-entry', `log-${log.type}`]"
      >
        <div class="log-header">
          <span class="log-timestamp">{{ formatTimestamp(log.timestamp) }}</span>
          <span :class="['log-type', `type-${log.type}`]">{{ log.type.toUpperCase() }}</span>
        </div>
        <div class="log-message">{{ log.message }}</div>
        <div v-if="log.details" class="log-details">
          {{ log.details }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, nextTick } from 'vue'

export default {
  name: 'LogContainer',
  props: {
    logs: {
      type: Array,
      required: true
    }
  },
  
  setup(props, { emit }) {
    const logContent = ref(null)
    const filterType = ref('all')
    const autoScroll = ref(true)

    const filteredLogs = computed(() => {
      if (filterType.value === 'all') return props.logs
      return props.logs.filter(log => log.type === filterType.value)
    })

    const formatTimestamp = (timestamp) => {
      const date = new Date(timestamp)
      return date.toLocaleTimeString() + '.' + 
             date.getMilliseconds().toString().padStart(3, '0')
    }

    const scrollToBottom = async () => {
      if (!autoScroll.value) return
      await nextTick()
      if (logContent.value) {
        logContent.value.scrollTop = logContent.value.scrollHeight
      }
    }

    const clearLogs = () => {
      emit('clear-logs')
    }

    watch(() => props.logs.length, () => {
      scrollToBottom()
    })

    const handleScroll = () => {
      if (!logContent.value) return
      
      const { scrollTop, scrollHeight, clientHeight } = logContent.value
      const scrolledToBottom = scrollHeight - scrollTop - clientHeight < 50
      autoScroll.value = scrolledToBottom
    }

    return {
      logContent,
      filterType,
      filteredLogs,
      formatTimestamp,
      clearLogs,
      handleScroll
    }
  }
}
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  height: 100%; /* Ensure full height of parent container */
}

.panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.log-container {
  grid-column: span 2; /* Take up 2 columns */
  max-height: 500px; /* Consistent with other containers */
  overflow: hidden;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  font-size: 14px;
}

@media (max-width: 1200px) {
  .log-container {
    grid-column: span 1; /* Take up 1 column on smaller screens */
  }
}
.panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 15px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h2 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.log-controls {
  display: flex;
  gap: 10px;
}

.filter-select {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.clear-btn {
  padding: 4px 8px;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.clear-btn:hover {
  background: #e0e0e0;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  font-size: 14px;
}

.log-entry {
  margin-bottom: 10px;
  padding: 10px;
  border-radius: 4px;
  border-left: 4px solid transparent;
}

.log-entry.log-error {
  background: #fff5f5;
  border-left-color: #f56565;
}

.log-entry.log-warning {
  background: #fffaf0;
  border-left-color: #ed8936;
}

.log-entry.log-info {
  background: #f7fafc;
  border-left-color: #4299e1;
}

.log-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 12px;
}

.log-timestamp {
  color: #666;
}

.log-type {
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
}

.type-error {
  background: #fff5f5;
  color: #c53030;
}

.type-warning {
  background: #fffaf0;
  color: #c05621;
}

.type-info {
  background: #f7fafc;
  color: #2b6cb0;
}

.log-message {
  color: #2d3748;
  line-height: 1.4;
}

.log-details {
  margin-top: 4px;
  font-size: 12px;
  color: #718096;
}

.no-logs {
  text-align: center;
  color: #a0aec0;
  padding: 20px;
}

@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  
  .log-controls {
    flex-direction: column;
  }
}
</style>