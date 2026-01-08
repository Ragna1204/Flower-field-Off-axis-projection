import pygame
from geometry import Point3D

class Letter:
    """Individual letter with its own animation state."""
    def __init__(self, lines, index):
        self.lines = lines  # List of (p1, p2) 3D line segments
        self.index = index
        self.alpha = 0.0
        self.target_alpha = 0.0
        
class SmileText:
    """Reveals 'SMILE' text with letter-by-letter animation.
    
    Letters fade in sequentially (S→M→I→L→E) and fade out in reverse (E→L→I→M→S).
    Each letter has multi-layer glow that follows its individual alpha.
    """
    
    # Animation states
    STATE_HIDDEN = 0
    STATE_FADING_IN = 1
    STATE_VISIBLE = 2
    STATE_FADING_OUT = 3
    STATE_GONE = 4
    
    def __init__(self, reveal_delay=5.0):
        self.reveal_delay = reveal_delay
        self.state = self.STATE_HIDDEN
        self.animation_start_time = None
        
        # Per-letter timing
        self.letter_fade_in_duration = 0.5
        self.letter_delay = 0.3  # Time between letter starts
        self.letter_fade_out_duration = 0.4
        self.letter_delay_out = 0.2
        
        # Position in 3D space (on back wall, above flowers)
        self.text_z = 8.5  # Deep in scene (back wall)
        self.text_y = 1.5  # Raised higher to avoid flower overlap
        self.text_x = -0.5
        
        # Visual parameters
        self.base_color = (220, 235, 255)  # Brighter blue-white
        self.glow_layers = [
            (12, 0.25),  # Outer: large, very subtle
            (8, 0.4),    # Mid: medium, soft
            (4, 0.7)     # Inner: small, bright
        ]
        self.core_width = 1  # Thinner core line
        
        # Fade-out delay (wait for flowers to bloom before fading)
        self.fadeout_delay = 3.0  # Start fade-out 3s after awakening begins
        self.fadeout_requested = False
        
        self.letters = []
        self._create_letterforms()
        
    def _create_letterforms(self):
        """Define geometric letterforms with smooth, bubbly curves."""
        letter_height = 0.6
        spacing = 0.5
        
        # S - bubble style with rounded curves
        s = [
            # Top curve (more rounded)
            [(0.3, 0.6), (0.2, 0.6)],
            [(0.2, 0.6), (0.1, 0.58)],
            [(0.1, 0.58), (0.05, 0.55)],
            [(0.05, 0.55), (0.02, 0.52)],
            [(0.02, 0.52), (0.0, 0.48)],
            [(0.0, 0.48), (0.0, 0.44)],
            # Middle transition
            [(0.0, 0.44), (0.02, 0.4)],
            [(0.02, 0.4), (0.05, 0.37)],
            [(0.05, 0.37), (0.1, 0.34)],
            [(0.1, 0.34), (0.18, 0.32)],
            [(0.18, 0.32), (0.25, 0.28)],
            # Bottom curve (more rounded)
            [(0.25, 0.28), (0.28, 0.24)],
            [(0.28, 0.24), (0.3, 0.2)],
            [(0.3, 0.2), (0.3, 0.15)],
            [(0.3, 0.15), (0.3, 0.1)],
            [(0.3, 0.1), (0.28, 0.06)],
            [(0.28, 0.06), (0.25, 0.03)],
            [(0.25, 0.03), (0.2, 0.01)],
            [(0.2, 0.01), (0.1, 0.0)],
            [(0.1, 0.0), (0.0, 0.0)],
        ]
        
        # M - rounded peaks
        m = [
            [(0.0, 0.0), (0.0, 0.6)],
            [(0.0, 0.6), (0.05, 0.5)],
            [(0.05, 0.5), (0.1, 0.4)],
            [(0.1, 0.4), (0.15, 0.3)],
            [(0.15, 0.3), (0.2, 0.4)],
            [(0.2, 0.4), (0.25, 0.5)],
            [(0.25, 0.5), (0.3, 0.6)],
            [(0.3, 0.6), (0.3, 0.0)]
        ]
        
        # I - simple with rounded ends
        i = [
            [(0.15, 0.0), (0.15, 0.6)]
        ]
        
        # L - rounded corner
        l = [
            [(0.0, 0.6), (0.0, 0.02)],
            [(0.0, 0.02), (0.02, 0.01)],
            [(0.02, 0.01), (0.1, 0.0)],
            [(0.1, 0.0), (0.3, 0.0)]
        ]
        
        # E - rounded with bubbly curves
        e = [
            [(0.0, 0.6), (0.0, 0.0)],
            [(0.0, 0.6), (0.1, 0.6)],
            [(0.1, 0.6), (0.25, 0.59)],
            [(0.25, 0.59), (0.3, 0.57)],
            [(0.0, 0.3), (0.15, 0.3)],
            [(0.15, 0.3), (0.22, 0.29)],
            [(0.0, 0.0), (0.1, 0.0)],
            [(0.1, 0.0), (0.25, 0.01)],
            [(0.25, 0.01), (0.3, 0.03)],
        ]
        
        # Convert to 3D and create Letter objects
        x_offset = -2.5 * spacing / 2
        
        for idx, letter_lines in enumerate([s, m, i, l, e]):
            letter_3d = []
            for (x1, y1), (x2, y2) in letter_lines:
                p1 = Point3D(
                    self.text_x + x_offset + x1,
                    self.text_y + y1 - letter_height/2,
                    self.text_z
                )
                p2 = Point3D(
                    self.text_x + x_offset + x2,
                    self.text_y + y2 - letter_height/2,
                    self.text_z
                )
                letter_3d.append((p1, p2))
            
            self.letters.append(Letter(letter_3d, idx))
            x_offset += spacing
    
    def start_fadeout(self, awakening_time):
        """Request fade-out (will start after delay for mid-bloom timing)."""
        if self.state in [self.STATE_FADING_IN, self.STATE_VISIBLE]:
            self.fadeout_requested = True
            self.fadeout_request_time = awakening_time
            print(f"[SMILE_TEXT] Fade-out requested, will start at awakening_time={self.fadeout_delay}s")
    
    def update(self, dt, intro_time, awakening_time=0.0):
        """Update letter animations based on current state."""
        # Transition from hidden to fading in
        if self.state == self.STATE_HIDDEN and intro_time >= self.reveal_delay:
            self.state = self.STATE_FADING_IN
            self.animation_start_time = intro_time
            print(f"[SMILE_TEXT] Starting fade-in at t={intro_time:.1f}s")
        
        # Check if fade-out should begin (after delay, and only once)
        if self.fadeout_requested and awakening_time >= self.fadeout_delay:
            if self.state not in [self.STATE_FADING_OUT, self.STATE_GONE]:
                self.state = self.STATE_FADING_OUT
                self.animation_start_time = awakening_time  # Use awakening_time for consistency
                self.fadeout_requested = False  # Prevent re-triggering
                print(f"[SMILE_TEXT] Starting fade-out at awakening_time={awakening_time:.1f}s")
        
        # Update fade-in
        if self.state == self.STATE_FADING_IN:
            elapsed = intro_time - self.animation_start_time
            all_complete = True
            
            for letter in self.letters:
                letter_start = letter.index * self.letter_delay
                letter_elapsed = elapsed - letter_start
                
                if letter_elapsed >= 0:
                    t = min(1.0, letter_elapsed / self.letter_fade_in_duration)
                    letter.target_alpha = t * t * (3 - 2 * t)  # Smoothstep
                    
                    if t < 1.0:
                        all_complete = False
                else:
                    all_complete = False
            
            if all_complete:
                self.state = self.STATE_VISIBLE
                print(f"[SMILE_TEXT] All letters visible at t={intro_time:.1f}s")
        
        # Update fade-out (reverse order: E→L→I→M→S)
        if self.state == self.STATE_FADING_OUT:
            elapsed = awakening_time - self.animation_start_time
            all_complete = True
            
            for letter in self.letters:
                # Reverse index: E(4)→0, L(3)→1, I(2)→2, M(1)→3, S(0)→4
                reverse_idx = len(self.letters) - 1 - letter.index
                letter_start = reverse_idx * self.letter_delay_out
                letter_elapsed = elapsed - letter_start
                
                if letter_elapsed >= 0:
                    t = min(1.0, letter_elapsed / self.letter_fade_out_duration)
                    letter.target_alpha = 1.0 - (t * t * (3 - 2 * t))
                    
                    if t < 1.0:
                        all_complete = False
            
            if all_complete:
                self.state = self.STATE_GONE
                print(f"[SMILE_TEXT] Fade-out complete at t={intro_time:.1f}s")
        
        # Smooth alpha transitions
        for letter in self.letters:
            letter.alpha += (letter.target_alpha - letter.alpha) * 0.2
    
    def draw(self, surface, glow_surface, project_fn, intro_time):
        """Draw letters with multi-layer glow."""
        if self.state == self.STATE_HIDDEN or self.state == self.STATE_GONE:
            return
        
        for letter in self.letters:
            if letter.alpha < 0.01:
                continue
            
            # Draw each line segment of the letter
            for p1, p2 in letter.lines:
                proj1 = project_fn(p1)
                proj2 = project_fn(p2)
                
                if proj1 and proj2:
                    sx1, sy1 = proj1[:2]
                    sx2, sy2 = proj2[:2]
                    pt1 = (int(sx1), int(sy1))
                    pt2 = (int(sx2), int(sy2))
                    
                    # Multi-layer glow
                    if glow_surface:
                        for radius, alpha_mult in self.glow_layers:
                            glow_alpha = int(letter.alpha * 255 * alpha_mult)
                            if glow_alpha > 5:
                                pygame.draw.line(
                                    glow_surface,
                                    (*self.base_color, glow_alpha),
                                    pt1, pt2, radius
                                )
                    
                    # Core line
                    core_alpha = int(letter.alpha * 255)
                    if core_alpha > 2:
                        pygame.draw.line(
                            surface,
                            (*self.base_color, core_alpha),
                            pt1, pt2, self.core_width
                        )
