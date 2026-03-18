#!/usr/bin/env python3
"""
CARLA Camera Streamer

Captures camera frames from CARLA and provides them for streaming.
Supports video recording with ffmpeg encoding.
"""

import io
import os
import base64
import threading
import queue
import time
import subprocess
from pathlib import Path
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
        
        # Recording
        streamer.start_recording("/path/to/recordings", "scenario_id")
        # ... scenario runs ...
        video_path = streamer.stop_recording()
        
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
        
        # Recording state
        self.is_recording = False
        self.recording_dir: Optional[Path] = None
        self.scenario_id: Optional[str] = None
        self.frame_count = 0
        self.recording_fps = 30
        self.video_path: Optional[str] = None
        
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
            
            # Convert to JPEG for streaming
            if PIL_AVAILABLE:
                pil_image = Image.fromarray(array)
                buffer = io.BytesIO()
                pil_image.save(buffer, format='JPEG', quality=70)
                jpeg_bytes = buffer.getvalue()
            else:
                # Fallback: raw PNG using basic encoding
                jpeg_bytes = self._encode_basic(array)
            
            # Store latest frame for streaming
            with self.frame_lock:
                self.latest_frame = jpeg_bytes
            
            # Save frame to disk if recording
            if self.is_recording and self.recording_dir and PIL_AVAILABLE:
                frame_path = self.recording_dir / f"frame_{self.frame_count:06d}.jpg"
                pil_image.save(frame_path, format='JPEG', quality=85)
                self.frame_count += 1
                
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
        
        # Stop recording if active
        if self.is_recording:
            self.stop_recording()
        
        if self.camera:
            try:
                self.camera.stop()
                self.camera.destroy()
            except:
                pass
            self.camera = None
            
        self.latest_frame = None
        print("Camera stopped")
    
    def start_recording(self, base_dir: str, scenario_id: str) -> bool:
        """
        Start recording frames to disk.
        
        Args:
            base_dir: Base directory for recordings
            scenario_id: Unique identifier for this recording
            
        Returns:
            True if recording started successfully
        """
        if self.is_recording:
            print("Already recording")
            return False
            
        if not PIL_AVAILABLE:
            print("PIL required for recording")
            return False
        
        # Create recording directory
        self.recording_dir = Path(base_dir) / scenario_id
        self.recording_dir.mkdir(parents=True, exist_ok=True)
        
        self.scenario_id = scenario_id
        self.frame_count = 0
        self.is_recording = True
        
        print(f"Recording started: {self.recording_dir}")
        return True
    
    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and encode video.
        
        Returns:
            Path to encoded video, or None if encoding failed
        """
        if not self.is_recording:
            return None
            
        self.is_recording = False
        print(f"Recording stopped: {self.frame_count} frames captured")
        
        if self.frame_count < 5:
            print("Too few frames to encode")
            return None
        
        # Encode video with ffmpeg
        video_path = self._encode_video()
        
        # Cleanup frames after encoding
        if video_path:
            self._cleanup_frames()
        
        return video_path
    
    def _encode_video(self) -> Optional[str]:
        """Encode recorded frames to MP4 using ffmpeg."""
        if not self.recording_dir or not self.scenario_id:
            return None
        
        # Output video path (in parent directory, not frames folder)
        video_path = self.recording_dir.parent / f"{self.scenario_id}.mp4"
        frames_pattern = str(self.recording_dir / "frame_%06d.jpg")
        
        # ffmpeg command for encoding
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-framerate", str(self.recording_fps),
            "-i", frames_pattern,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",  # Web-friendly
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                self.video_path = str(video_path)
                print(f"Video encoded: {video_path}")
                return str(video_path)
            else:
                print(f"ffmpeg error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("ffmpeg encoding timed out")
            return None
        except FileNotFoundError:
            print("ffmpeg not found - install with: apt install ffmpeg")
            return None
        except Exception as e:
            print(f"Encoding error: {e}")
            return None
    
    def _cleanup_frames(self):
        """Remove individual frame files after encoding."""
        if not self.recording_dir:
            return
            
        try:
            for frame_file in self.recording_dir.glob("frame_*.jpg"):
                frame_file.unlink()
            # Remove empty directory
            self.recording_dir.rmdir()
            print("Frame files cleaned up")
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    def get_video_path(self) -> Optional[str]:
        """Get path to the last recorded video."""
        return self.video_path


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


class SpectatorStreamer:
    """
    Streams from CARLA's spectator camera (no vehicle needed).
    Used for preview mode to show live world view.
    """
    
    def __init__(
        self,
        world: 'carla.World',
        width: int = 800,
        height: int = 600,
        fov: int = 90,
    ):
        self.world = world
        self.width = width
        self.height = height
        self.fov = fov
        
        self.camera: Optional['carla.Sensor'] = None
        self.latest_frame: Optional[bytes] = None
        self.frame_lock = threading.Lock()
        self.running = False
        
    def _get_spawn_point_center(self) -> 'carla.Transform':
        """Get a good camera position based on map spawn points."""
        try:
            spawn_points = self.world.get_map().get_spawn_points()
            if spawn_points:
                # Use first spawn point as reference, elevated for overview
                sp = spawn_points[0]
                return carla.Transform(
                    carla.Location(x=sp.location.x, y=sp.location.y, z=50),
                    carla.Rotation(pitch=-60, yaw=sp.rotation.yaw)
                )
        except:
            pass
        # Fallback
        return carla.Transform(
            carla.Location(x=0, y=0, z=50),
            carla.Rotation(pitch=-60)
        )
    
    def _get_street_view(self) -> 'carla.Transform':
        """Get a street-level camera position."""
        try:
            spawn_points = self.world.get_map().get_spawn_points()
            if spawn_points:
                # Use first spawn point for street view
                sp = spawn_points[0]
                return carla.Transform(
                    carla.Location(x=sp.location.x - 10, y=sp.location.y, z=5),
                    carla.Rotation(pitch=-15, yaw=sp.rotation.yaw)
                )
        except:
            pass
        # Fallback
        return carla.Transform(
            carla.Location(x=0, y=0, z=5),
            carla.Rotation(pitch=-15)
        )
    
    def start(self, location: str = 'overview') -> bool:
        """Start spectator camera at a predefined location."""
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
            
            # Get spectator transform or use predefined locations
            if location == 'spectator':
                transform = self.world.get_spectator().get_transform()
            elif location == 'overview':
                # Bird's eye overview centered on spawn points
                transform = self._get_spawn_point_center()
            elif location == 'street':
                # Street level view near spawn
                transform = self._get_street_view()
            else:
                transform = self.world.get_spectator().get_transform()
            
            self._current_location = location
            
            # Spawn camera in world (not attached to vehicle)
            self.camera = self.world.spawn_actor(camera_bp, transform)
            
            # Register callback for frames
            self.running = True
            self.camera.listen(self._process_frame)
            
            print(f"Spectator camera started: {self.width}x{self.height} @ {location}")
            return True
            
        except Exception as e:
            print(f"Failed to start spectator camera: {e}")
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
                jpeg_bytes = array.tobytes()
            
            # Store latest frame
            with self.frame_lock:
                self.latest_frame = jpeg_bytes
                
        except Exception as e:
            print(f"Spectator frame processing error: {e}")
    
    def get_frame_base64(self) -> Optional[str]:
        """Get the latest frame as base64-encoded JPEG string."""
        with self.frame_lock:
            if self.latest_frame:
                return base64.b64encode(self.latest_frame).decode('utf-8')
        return None
    
    def set_location(self, location: str):
        """Move camera to a different location."""
        if not self.camera:
            return
        
        if location == 'spectator':
            transform = self.world.get_spectator().get_transform()
        elif location == 'overview':
            transform = self._get_spawn_point_center()
        elif location == 'street':
            transform = self._get_street_view()
        else:
            return
        
        self._current_location = location
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
        print("Spectator camera stopped")
