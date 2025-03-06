<template>
    <div class="webrtc-container">
      <h3>Live Drone Stream (WebRTC)</h3>
      <video ref="videoElement" autoplay playsinline controls></video>
    </div>
  </template>
  
  <script>
  import { ref, onMounted, onUnmounted } from 'vue';
  import { io } from 'socket.io-client';
  
  export default {
    name: 'DroneWebRTC',
    setup() {
      const videoElement = ref(null);
      let pc = null;
      let captureInterval = null;
      
      // Connect to the video relay server
      const socket = io('http://128.199.26.169:3000/video');
  
      socket.on('connect', () => {
        console.log("Connected to video namespace");
        socket.emit('identify', 'control');
      });
  
      // Handle incoming WebRTC signaling messages
      socket.on('webrtc-signal', async (data) => {
        console.log("Received WebRTC signal on frontend:", data);
        if (data.type === 'offer') {
          if (!pc) {
            pc = new RTCPeerConnection();
  
            // Send ICE candidates to the drone
            pc.onicecandidate = (event) => {
              if (event.candidate) {
                socket.emit('webrtc-signal', {
                  target: 'drone',
                  signal: { candidate: event.candidate }
                });
              }
            };
  
            // Attach incoming stream to the video element
            pc.ontrack = (event) => {
              console.log("Received remote track");
              if (videoElement.value) {
                videoElement.value.srcObject = event.streams[0];
              }
            };
          }
          await pc.setRemoteDescription(new RTCSessionDescription({
            sdp: data.sdp,
            type: data.type
          }));
  
          // Create and send SDP answer
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          socket.emit('webrtc-signal', {
            target: 'drone',
            signal: {
              sdp: pc.localDescription.sdp,
              type: pc.localDescription.type
            }
          });
          console.log("Sent SDP answer to drone");
  
        } else if (data.candidate) {
          if (pc) {
            try {
              await pc.addIceCandidate(data.candidate);
              console.log("Added ICE candidate", data.candidate);
            } catch (err) {
              console.error("Error adding ICE candidate:", err);
            }
          }
        }
      });
  
      // Capture frame from video and upload to the backend service on port 3004
      const captureFrame = () => {
        const video = videoElement.value;
        if (!video || video.readyState < 2) {
          return;
        }
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert the canvas content to a PNG data URL
        const dataURL = canvas.toDataURL('image/png');
        
        // Upload the captured image to the backend service
        fetch('http://128.199.26.169:3004/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ imageData: dataURL })
        })
        .then(response => response.json())
        .then(data => console.log('Image uploaded:', data))
        .catch(err => console.error('Upload error:', err));
      };
  
      onMounted(() => {
        // Start capturing a frame every 3 seconds
        captureInterval = setInterval(captureFrame, 3000);
      });
  
      onUnmounted(() => {
        if (pc) {
          pc.close();
          pc = null;
        }
        socket.disconnect();
        if (captureInterval) {
          clearInterval(captureInterval);
        }
      });
  
      return { videoElement };
    }
  };
  </script>
  
  <style scoped>
  .webrtc-container {
    background: #000;
    border-radius: 8px;
    padding: 10px;
    text-align: center;
    color: #fff;
  }
  video {
    width: 100%;
    max-height: 400px;
    border: 1px solid #333;
    border-radius: 4px;
    margin-top: 10px;
  }
  </style>
  