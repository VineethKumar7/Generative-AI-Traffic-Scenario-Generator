#!/usr/bin/env python3
"""
CARLA Camera Streamer

Captures camera frames from CARLA and provides them for streaming.
"""

import io
import base64
import threading
import queue
import time
from typing import Optional, Callable
import numpy as np

try:
    import carla
    CARLA_AVAILABLE = True
except ImportError:
    CARLA_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class CameraStreamer:
    """
    Manages a camera sensor in CARLA and streams frames.
    
    Usage:
        streamer = CameraStreamer(world, vehicle)
        streamer.start()
        
        # Get latest frame as base64 JPEG
        frame = streamer.get_frame_base64()
        
        streamer.stop()
    """
    
    def __init__(
        self,
        world: 'carla.World',
        vehicle: 'carla.Vehicle',
        width: int = 800,
        height: int = 600,
        fov: int = 90,
        camera_type: str = 'chase'  # 'chase', 'hood', 'bird'
    ):
        self.world = world
        self.vehicle = vehicle
        self.width = width
        self.height = height
        self.fov = fov
        self.camera_type = camera_type
        
        self.camera: Optional['carla.Sensor'] = None
        self.latest_frame: Optional[bytes] = None
        self.frame_lock = threading.Lock()
        self.running = False
        
        # Frame queue for async processing
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        
    def _get_camera_transform(self) -> 'carla.Transform':
        """Get camera transform based on camera type."""
        if self.camera_type == 'chase':
            # Behind and above the vehicle
            return carla.Transform(
                carla.Location(x=-8.0, z=4.0),
                carla.Rotation(pitch=-15.0)
            )
        elif self.camera_type == 'hood':
            # Hood camera (driver view)
            return carla.Transform(
                carla.Location(x=1.5, z=1.4),
                carla.Rotation(pitch=-5.0)
            )
        elif self.camera_type == 'bird':
            # Bird's eye view
            return carla.Transform(
                carla.Location(x=0, z=30.0),
                carla.Rotation(pitch=-90.0)
            )
        else:
            # Default chase cam
            return carla.Transform(
                carla.Location(x=-8.0, z=4.0),
                carla.Rotation(pitch=-15.0)
            )
    
    def start(self) -> bool:
        """Start the camera and begin capturing frames."""
        if not CARLA_AVAILABLE:
            print("CARLA not available")
            return False
            
        try:
            # Get camera blueprint
            blueprint_library = self.world.get_blueprint_library()
            camera_bp = blueprint_library.find('sensor.camera.rgb')
            
            # Set camera attributes
            camera_bp.set_attribute('image_size_x', str(self.width))
            camera_bp.set_attribute('image_size_y', str(self.height))
            camera_bp.set_attribute('fov', str(self.fov))
            
            # Spawn camera attached to vehicle
            transform = self._get_camera_transform()
            self.camera = self.world.spawn_actor(
                camera_bp,
                transform,
                attach_to=self.vehicle
            )
            
            # Register callback for frames
            self.running = True
            self.camera.listen(self._process_frame)
            
            print(f"Camera started: {self.width}x{self.height} @ {self.camera_type} view")
            return True
            
        except Exception as e:
            print(f"Failed to start camera: {e}")
            return False
    
    def _process_frame(self, image: 'carla.Image'):
        """Process incoming camera frame."""
        if not self.running:
            return
            
        try:
            # Convert CARLA image to numpy array
            array = np.frombuffer(image.raw_data, dtype=np.uint8)
            array = array.reshape((self.height, self.width, 4))  # BGRA
            array = array[:, :, :3]  # Remove alpha -> BGR
            array = array[:, :, ::-1]  # BGR -> RGB
            
            # Convert to JPEG
            if PIL_AVAILABLE:
                pil_image = Image.fromarray(array)
                buffer = io.BytesIO()
                pil_image.save(buffer, format='JPEG', quality=70)
                jpeg_bytes = buffer.getvalue()
            else:
                # Fallback: raw PNG using basic encoding
                jpeg_bytes = self._encode_basic(array)
            
            # Store latest frame
            with self.frame_lock:
                self.latest_frame = jpeg_bytes
                
        except Exception as e:
            print(f"Frame processing error: {e}")
    
    def _encode_basic(self, array: np.ndarray) -> bytes:
        """Basic encoding fallback if PIL not available."""
        # This is a minimal fallback - PIL is preferred
        return array.tobytes()
    
    def get_frame_bytes(self) -> Optional[bytes]:
        """Get the latest frame as JPEG bytes."""
        with self.frame_lock:
            return self.latest_frame
    
    def get_frame_base64(self) -> Optional[str]:
        """Get the latest frame as base64-encoded JPEG string."""
        frame = self.get_frame_bytes()
        if frame:
            return base64.b64encode(frame).decode('utf-8')
        return None
    
    def set_camera_type(self, camera_type: str):
        """Change camera view type."""
        if camera_type == self.camera_type:
            return
            
        self.camera_type = camera_type
        
        # Update camera transform
        if self.camera:
            transform = self._get_camera_transform()
            self.camera.set_transform(transform)
    
    def stop(self):
        """Stop the camera and cleanup."""
        self.running = False
        
        if self.camera:
            try:
                self.camera.stop()
                self.camera.destroy()
            except:
                pass
            self.camera = None
            
        self.latest_frame = None
        print("Camera stopped")


class MultiCameraStreamer:
    """
    Manages multiple camera views for comprehensive streaming.
    """
    
    def __init__(self, world: 'carla.World', vehicle: 'carla.Vehicle'):
        self.world = world
        self.vehicle = vehicle
        self.cameras: dict[str, CameraStreamer] = {}
        self.active_camera: str = 'chase'
        
    def add_camera(self, name: str, camera_type: str, width: int = 640, height: int = 480):
        """Add a camera view."""
        streamer = CameraStreamer(
            self.world, 
            self.vehicle,
            width=width,
            height=height,
            camera_type=camera_type
        )
        self.cameras[name] = streamer
        
    def start_all(self):
        """Start all cameras."""
        for name, camera in self.cameras.items():
            camera.start()
            
    def stop_all(self):
        """Stop all cameras."""
        for camera in self.cameras.values():
            camera.stop()
        self.cameras.clear()
        
    def get_frame(self, camera_name: Optional[str] = None) -> Optional[str]:
        """Get frame from specified camera or active camera."""
        name = camera_name or self.active_camera
        if name in self.cameras:
            return self.cameras[name].get_frame_base64()
        return None
        
    def set_active_camera(self, name: str):
        """Set the active camera view."""
        if name in self.cameras:
            self.active_camera = name
