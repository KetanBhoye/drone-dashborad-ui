<template>
    <Transition name="fade">
      <div v-if="modelValue" class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" @click="close"></div>
  
        <!-- Dialog -->
        <div class="flex min-h-screen items-center justify-center p-4">
          <div class="relative w-full max-w-lg transform overflow-hidden rounded-lg bg-white shadow-xl transition-all">
            <!-- Header -->
            <div class="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
              <div class="sm:flex sm:items-start">
                <!-- Error Icon -->
                <div class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                  <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
  
                <!-- Content -->
                <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                  <h3 class="text-lg font-medium leading-6 text-gray-900">
                    {{ title }}
                  </h3>
                  <div class="mt-2">
                    <p class="text-sm text-gray-500">
                      {{ message }}
                    </p>
                    <p v-if="resolution" class="mt-2 text-sm text-gray-700">
                      {{ resolution }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
  
            <!-- Footer -->
            <div class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
              <!-- Action Buttons -->
              <template v-if="actions && actions.length">
                <button
                  v-for="action in actions"
                  :key="action.text"
                  type="button"
                  class="inline-flex w-full justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 sm:ml-3 sm:w-auto sm:text-sm"
                  @click="handleAction(action)"
                >
                  {{ action.text }}
                </button>
              </template>
  
              <!-- Close Button -->
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-base font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 sm:mt-0 sm:w-auto sm:text-sm"
                @click="close"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </template>
  
  <script>
  export default {
    name: 'ErrorDialog',
    props: {
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
  .fade-enter-active,
  .fade-leave-active {
    transition: opacity 0.3s ease;
  }
  
  .fade-enter-from,
  .fade-leave-to {
    opacity: 0;
  }
  
  /* Slide animation for dialog */
  .fade-enter-active .relative,
  .fade-leave-active .relative {
    transition: transform 0.3s ease-out;
  }
  
  .fade-enter-from .relative,
  .fade-leave-to .relative {
    transform: translateY(-1rem);
  }
  </style>