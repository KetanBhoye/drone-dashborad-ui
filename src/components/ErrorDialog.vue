<template>
  <!-- The "fade" transition name corresponds to the CSS classes in the <style> block -->
  <transition name="fade">
    <div
      v-if="modelValue"
      class="modal-backdrop"
      role="dialog"
      aria-modal="true"
    >
      <!-- Click on backdrop to close -->
      <div class="modal-overlay" @click="close"></div>

      <!-- Modal Container -->
      <div class="modal-container">
        <!-- Header & Icon -->
        <div class="modal-header">
          <div class="error-icon-container">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01M4.06 19h15.88c1.54 0 2.5-1.67 1.73-3L13.73 5c-.77-1.33-2.69-1.33-3.46 0L2.33 16c-.77 1.33.19 3 1.73 3z"
              />
            </svg>
          </div>
          <div class="modal-header-text">
            <h3 class="modal-title">{{ title }}</h3>
            <p class="modal-message">{{ message }}</p>
            <p v-if="resolution" class="modal-resolution">{{ resolution }}</p>
          </div>
        </div>

        <!-- Footer -->
        <div class="modal-footer">
          <!-- Dynamic action buttons -->
          <template v-if="actions && actions.length">
            <button
              v-for="action in actions"
              :key="action.text"
              class="btn-action"
              @click="handleAction(action)"
            >
              {{ action.text }}
            </button>
          </template>

          <!-- Close button -->
          <button class="btn-close" @click="close">Close</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
export default {
  name: 'ErrorDialog',
  props: {
    // Controls whether the dialog is shown
    modelValue: {
      type: Boolean,
      required: true
    },
    title: {
      type: String,
      default: 'Error'
    },
    message: {
      type: String,
      required: true
    },
    resolution: {
      type: String,
      default: ''
    },
    actions: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:modelValue', 'action'],
  setup(props, { emit }) {
    const close = () => {
      emit('update:modelValue', false)
    }

    const handleAction = (action) => {
      if (action.action) {
        action.action()
      }
      emit('action', action)
      close()
    }

    return {
      close,
      handleAction
    }
  }
}
</script>

<style scoped>
/* 
  Fade + slide transition for the entire dialog.
  "fade" matches <transition name="fade"> in the template.
*/
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Slide animation for the .modal-container */
.fade-enter-active .modal-container,
.fade-leave-active .modal-container {
  transition: transform 0.3s ease-out;
}
.fade-enter-from .modal-container,
.fade-leave-to .modal-container {
  transform: translateY(-1rem);
}

/* 
  The backdrop covers the entire screen and centers the dialog.
*/
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50; /* or 9999, or any value higher than the map’s z-index */
  overflow-y: auto;
}


/* Semi-transparent overlay behind the dialog */
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0,0,0,0.5);
}

/* The dialog box itself */
.modal-container {
  display: flex;
  flex-direction: column;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  max-width: 500px;
  margin: 2rem auto;
  padding: 1.5rem;
  position: relative;
}

/* Header area: icon + text */
.modal-header {
  display: flex;
  align-items: center;
}

/* Container for the red error icon */
.error-icon-container {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #fee2e2; /* Light red background */
  border-radius: 9999px;
  width: 40px;
  height: 40px;
  margin-right: 1rem;
}

/* SVG icon styling */
.error-icon-container svg {
  width: 24px;
  height: 24px;
  stroke: #dc2626; /* Red stroke color */
}

/* Header text (title, message, resolution) */
.modal-header-text {
  display: flex;
  flex-direction: column;
}

.modal-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827; /* Dark text */
}

.modal-message {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280; /* Gray text */
}

.modal-resolution {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #374151; /* Slightly darker gray */
}

/* Footer: action buttons + close button */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.5rem;
  gap: 0.5rem;
}

/* Primary action button styling */
.btn-action {
  background-color: #2563eb; /* Blue background */
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: none;
  font-size: 0.875rem;
  cursor: pointer;
}
.btn-action:hover {
  background-color: #1d4ed8; /* Darker blue */
}

/* Secondary/close button styling */
.btn-close {
  background-color: #fff;
  color: #374151; /* Gray text */
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db; /* Light gray border */
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
}
.btn-close:hover {
  background-color: #f9fafb; /* Very light gray */
}
</style>
