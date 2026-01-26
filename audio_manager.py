"""
Audio Manager for music playback and crossfading.

Handles:
- Afterthought (Joji) → plays from start to finish
- Crossfade to Touch Tank (Quinnie)
- Touch Tank plays to finish
"""

import pygame
import os
import time

class AudioManager:
    """Manages music playback with automatic crossfading."""
    
    def __init__(self, audio_dir="audio", crossfade_duration=5.0):
        """Initialize audio manager.
        
        Args:
            audio_dir: Directory containing audio files
            crossfade_duration: Crossfade duration in seconds (default: 5s)
        """
        self.audio_dir = audio_dir
        self.crossfade_duration = crossfade_duration
        
        # Paths
        self.afterthought_path = os.path.join(audio_dir, "afterthought.mp3")
        self.touch_tank_path = os.path.join(audio_dir, "touch_tank.mp3")
        
        # State
        self.music_started = False
        self.crossfade_started = False
        self.afterthought_channel = None
        self.touch_tank_channel = None
        
        # Initialize pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.set_num_channels(8)  # Multiple channels for crossfade
        
        # Load sounds
        self.afterthought_sound = None
        self.touch_tank_sound = None
        
        self._load_audio()
    
    def _load_audio(self):
        """Load audio files."""
        try:
            if os.path.exists(self.afterthought_path):
                self.afterthought_sound = pygame.mixer.Sound(self.afterthought_path)
                print(f"[AUDIO] Loaded: {self.afterthought_path}")
            else:
                print(f"[AUDIO] ERROR: File not found: {self.afterthought_path}")
            
            if os.path.exists(self.touch_tank_path):
                self.touch_tank_sound = pygame.mixer.Sound(self.touch_tank_path)
                print(f"[AUDIO] Loaded: {self.touch_tank_path}")
            else:
                print(f"[AUDIO] ERROR: File not found: {self.touch_tank_path}")
                
        except Exception as e:
            print(f"[AUDIO] ERROR loading files: {e}")
    
    def start_music(self):
        """Start playing Afterthought (called when flowers bloom)."""
        if self.music_started or not self.afterthought_sound:
            return
        
        print("[AUDIO] Starting Afterthought")
        self.afterthought_channel = self.afterthought_sound.play()
        if self.afterthought_channel:
            self.afterthought_channel.set_volume(1.0)
            self.music_started = True
    
    def update(self, dt):
        """Update audio system (call every frame).
        
        Args:
            dt: Delta time since last frame
        """
        if not self.music_started:
            return
        
        # Check if Afterthought finished and start crossfade
        if self.afterthought_channel and not self.crossfade_started:
            # Check if song is almost done (within crossfade duration)
            if not self.afterthought_channel.get_busy():
                # Song finished completely - start Touch Tank immediately
                self._start_touch_tank()
            elif self.afterthought_channel.get_queue() is None:
                # Check position - if we can get it
                # For now, use a simple busy check
                pass
    
    def _start_touch_tank(self):
        """Start Touch Tank (either immediate or crossfade)."""
        if self.crossfade_started or not self.touch_tank_sound:
            return
        
        print("[AUDIO] Afterthought ended, starting Touch Tank")
        self.touch_tank_channel = self.touch_tank_sound.play()
        if self.touch_tank_channel:
            # Start at low volume and fade in
            self.touch_tank_channel.set_volume(0.0)
            self.crossfade_started = True
            self._crossfade()
    
    def _crossfade(self):
        """Perform crossfade between songs."""
        # Fade out Afterthought (if still playing)
        if self.afterthought_channel:
            current_vol = self.afterthought_channel.get_volume()
            for i in range(100):
                vol = current_vol * (1.0 - i / 100.0)
                if self.afterthought_channel.get_busy():
                    self.afterthought_channel.set_volume(vol)
        
        # Fade in Touch Tank
        if self.touch_tank_channel:
            for i in range(100):
                vol = i / 100.0
                if self.touch_tank_channel.get_busy():
                    self.touch_tank_channel.set_volume(vol)
        
        print("[AUDIO] Crossfade complete")
    
    def stop(self):
        """Stop all audio."""
        if self.afterthought_channel:
            self.afterthought_channel.stop()
        if self.touch_tank_channel:
            self.touch_tank_channel.stop()
        print("[AUDIO] Stopped")
