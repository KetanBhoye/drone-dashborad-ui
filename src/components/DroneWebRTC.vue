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
      // Create the Socket.IO client connecting to your relay server (update the URL and port)
      const socket = io('http://128.199.26.169:3000/video');
  
        // Identify as a control client once connected
        socket.on('connect', () => {
            console.log("Connected to video namespace");
            socket.emit('identify', 'control'); // Important for signaling server
        });

  
      // Handle incoming WebRTC signaling messages
      socket.on('webrtc-signal', async (data) => {
        console.log("Received WebRTC signal on frontend:", data);
        // Check if this is an SDP offer from the drone
        if (data.type === 'offer') {
          if (!pc) {
            // Create a new RTCPeerConnection
            pc = new RTCPeerConnection();
  
              // Send ICE candidates to the drone as they are gathered
              pc.onicecandidate = (event) => {
                  if (event.candidate) {
                      socket.emit('webrtc-signal', {
                          target: 'drone',
                          signal: { candidate: event.candidate }
                      });
                  }
              };
  
            // When a track (stream) is received, attach it to the video element
            pc.ontrack = (event) => {
              console.log("Received remote track");
              if (videoElement.value) {
                videoElement.value.srcObject = event.streams[0];
              }
            };
          }
          // Set the remote description with the received SDP offer
          await pc.setRemoteDescription(new RTCSessionDescription({
            sdp: data.sdp,
            type: data.type
          }));
  
          // Create an SDP answer
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
  
          // Send the SDP answer back to the drone via the relay server
          socket.emit('webrtc-signal', {
            target: 'drone',
            signal: {
              sdp: pc.localDescription.sdp,
              type: pc.localDescription.type
            }
          });
          console.log("Sent SDP answer to drone");
  
        } else if (data.candidate) {
          // If ICE candidate data is received, add it to the RTCPeerConnection
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
  
      onMounted(() => {
        // Nothing extra needed on mount, as the socket connection will auto-initiate
      });
  
      onUnmounted(() => {
        if (pc) {
          pc.close();
          pc = null;
        }
        socket.disconnect();
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
  