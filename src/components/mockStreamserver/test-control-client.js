// In a browser console:
const socket = io("http://128.199.26.169:3001/video");
socket.on('connect', () => {
  console.log("Connected to video relay as control");
  socket.emit('identify', 'control');
});
socket.on('webrtc-signal', (data) => {
  console.log("Received webrtc-signal:", data);
  // You can simulate sending an answer:
  if(data.type === 'offer'){
    // Here you would normally create an RTCPeerConnection to answer the offer.
    // For testing, you might just log it.
    console.log("Offer received:", data);
  }
});
