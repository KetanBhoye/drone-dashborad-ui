import asyncio
import subprocess
import time
import threading
import numpy as np
import cv2
import socketio
import logging

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from av import VideoFrame

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webrtc_stream")

# Retrieve the main event loop in the main thread
main_loop = asyncio.get_event_loop()

# Create a Socket.IO client instance and connect explicitly to the /video namespace
sio = socketio.Client()

# Global peer connection variable
pc = None

class LibcameraVideoStreamTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, width=1296, height=972, framerate=20):
        super().__init__()
        self.width = width
        self.height = height
        self.framerate = framerate
        self._process = None
        self._frame_buffer = None
        self._start_capture()
        self._start_time = time.time()
        self._frame_count = 0
        self._timestamp = 0
        self._timebase_num = 1
        self._timebase_den = 90000

    def _start_capture(self):
        command = [
            "libcamera-vid",
            "-t", "0",
            "--inline",
            "--width", str(self.width),
            "--height", str(self.height),
            "--framerate", str(self.framerate),
            "--codec", "mjpeg",
            "--output", "-"
        ]
        logging.info("Starting camera: " + " ".join(command))
        self._process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        threading.Thread(target=self._read_frames, daemon=True).start()

    def _read_frames(self):
        frame_data = bytearray()
        while True:
            chunk = self._process.stdout.read(8192)
            if not chunk:
                break
            frame_data.extend(chunk)
            start = frame_data.find(b'\xff\xd8')
            end = frame_data.find(b'\xff\xd9')
            if start != -1 and end != -1 and end > start:
                jpeg_bytes = frame_data[start:end + 2]
                frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    self._frame_buffer = frame
                    self._frame_count += 1
                frame_data = frame_data[end + 2:]

    async def next_timestamp(self):
        frame_duration = int(90000 / self.framerate)
        self._timestamp += frame_duration
        from fractions import Fraction
        return self._timestamp, Fraction(1, 90000)

    async def recv(self):
        elapsed_time = time.time() - self._start_time
        if elapsed_time > 5:
            fps = self._frame_count / elapsed_time
            logging.info(f"Streaming at {fps:.2f} FPS")
            self._start_time = time.time()
            self._frame_count = 0

        count = 0
        while self._frame_buffer is None:
            await asyncio.sleep(0.01)
            count += 1
            if count > 100:
                raise RuntimeError("No frames available from camera")

        frame = VideoFrame.from_ndarray(self._frame_buffer.copy(), format="bgr24")
        frame.pts, frame.time_base = await self.next_timestamp()
        return frame

    def stop(self):
        if self._process:
            self._process.terminate()
            self._process = None

@sio.event(namespace='/video')
def connect():
    logging.info("Connected to video signaling server")
    sio.emit("identify", "drone", namespace="/video")

@sio.event(namespace="/video")
def disconnect():
    logging.info("Disconnected from video signaling server")

@sio.on("webrtc-signal", namespace="/video")
def on_webrtc_signal(data):
    global pc
    if "sdp" in data and "type" in data:
        desc = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
        main_loop.call_soon_threadsafe(asyncio.ensure_future, handle_remote_description(desc))
    elif "candidate" in data:
        candidate_dict = data["candidate"]
        candidate = RTCIceCandidate(
            candidate=candidate_dict['candidate'],
            sdpMid=candidate_dict.get('sdpMid'),
            sdpMLineIndex=candidate_dict.get('sdpMLineIndex')
        )
        main_loop.call_soon_threadsafe(asyncio.ensure_future, pc.addIceCandidate(candidate))

async def handle_remote_description(desc):
    global pc
    await pc.setRemoteDescription(desc)
    if desc.type == "offer":
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        sio.emit("webrtc-signal", {
            "target": "control",
            "signal": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        }, namespace="/video")
        logging.info("Sent SDP answer to control client")

async def start_webrtc():
    global pc
    pc = RTCPeerConnection()
    pc.addTrack(LibcameraVideoStreamTrack(width=1296, height=972, framerate=20))
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    sio.emit("webrtc-signal", {
        "target": "control",
        "signal": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    }, namespace="/video")
    logging.info("Sent SDP offer to control client")

if __name__ == "__main__":
    sio.connect("http://128.199.26.169:3000/video", namespaces=['/video'])
    main_loop.run_until_complete(start_webrtc())
    main_loop.run_forever()