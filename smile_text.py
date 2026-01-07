import pygame
import math
from geometry import Point3D

class SmileText:
    """
    Phase 7: Narrative Trigger
    
    Reveals "SMILE" text at the back of the flower field after 5 seconds.
    Text is formed by simple line segments in 3D space with elegant glow.
    """
    
    def __init__(self, reveal_delay=5.0, fade_duration=2.0):
        self.reveal_delay = reveal_delay
        self.fade_duration = fade_duration
        self.visible = False
        self.alpha = 0.0
        self.reveal_start_time = None
        
        # Text position (deep in scene, behind flowers)
        self.text_z = 8.5
        self.text_y = 0.5
        self.text_x = 0.0  # centered
        
        self._create_letterforms()
        
    def _create_letterforms(self):
        """Define simple geometric letterforms for 'SMILE'."""
        letter_width = 0.4
        letter_height = 0.6
        spacing = 0.5
        
        # S - elegant curves
        s = [
            [(0.3, 0.6), (0.1, 0.6)],
            [(0.1, 0.6), (0.0, 0.5)],
            [(0.0, 0.5), (0.0, 0.4)],
            [(0.0, 0.4), (0.1, 0.3)],
            [(0.1, 0.3), (0.2, 0.3)],
            [(0.2, 0.3), (0.3, 0.2)],
            [(0.3, 0.2), (0.3, 0.1)],
            [(0.3, 0.1), (0.2, 0.0)],
            [(0.2, 0.0), (0.0, 0.0)],
        ]
        
        # Rest of letters...
        m = [[(0.0, 0.0), (0.0, 0.6)], [(0.0, 0.6), (0.15, 0.3)], [(0.15, 0.3), (0.3, 0.6)], [(0.3, 0.6), (0.3, 0.0)]]
        i = [[(0.15, 0.0), (0.15, 0.6)]]
        l = [[(0.0, 0.6), (0.0, 0.0)], [(0.0, 0.0), (0.3, 0.0)]]
        e = [[(0.0, 0.6), (0.0, 0.0)], [(0.0, 0.6), (0.3, 0.6)], [(0.0, 0.3), (0.25, 0.3)], [(0.0, 0.0), (0.3, 0.0)]]
        
        self.letters = []
        x_offset = -2.5 * spacing / 2
        
        for letter_lines in [s, m, i, l, e]:
            letter_3d = []
            for (x1, y1), (x2, y2) in letter_lines:
                p1 = Point3D(self.text_x + x_offset + x1, self.text_y + y1 - letter_height/2, self.text_z)
                p2 = Point3D(self.text_x + x_offset + x2, self.text_y + y2 - letter_height/2, self.text_z)
                letter_3d.append((p1, p2))
            self.letters.append(letter_3d)
            x_offset += spacing
    
    def update(self, dt, intro_time):
        """Update reveal state based on elapsed time."""
        # Start revealing after delay
        if intro_time >= self.reveal_delay and not self.visible:
            self.visible = True
            self.reveal_start_time = intro_time
            print(f"[SMILE_TEXT] Revealing text at intro_time={intro_time:.2f}s")
        
        # Fade in smoothly
        if self.visible and self.reveal_start_time is not None:
            elapsed = intro_time - self.reveal_start_time
            t = min(1.0, elapsed / self.fade_duration)
            self.alpha = t * t * (3 - 2 * t)
            # Only log ONCE when fully visible
            if t >= 1.0 and not hasattr(self, '_logged_full'):
                self._logged_full = True
                print(f"[SMILE_TEXT] Fully visible at intro_time={intro_time:.2f}s")
    
    def draw(self, surface, glow_surface, project_fn, intro_time):
        """Draw text with elegant glow effect."""
        # Track draw calls
        if not hasattr(self, '_draw_call_count'):
            self._draw_call_count = 0
        self._draw_call_count += 1
        
        # STRICT GUARD: Do not render anything before reveal time
        if intro_time < self.reveal_delay:
            if self._draw_call_count <= 3:  # Log first few blocked calls
                print(f"[TEXT DRAW BLOCKED] Call #{self._draw_call_count} at t={intro_time:.2f}s < reveal_delay={self.reveal_delay}s")
            return
            
        # Log first successful draw
        if not hasattr(self, '_first_draw_logged'):
            self._first_draw_logged = True
            print(f"[TEXT DRAW STARTED] First render at t={intro_time:.2f}s, alpha={self.alpha:.3f}")
        
        if not self.visible or self.alpha < 0.01:
            return
        
        base_color = (180, 200, 255)  # Elegant blue-white
        glow_alpha = int(self.alpha * 60)
        core_alpha = int(self.alpha * 255)  # Core line alpha
        
        for letter_lines in self.letters:
            for p1, p2 in letter_lines:
                proj1 = project_fn(p1)
                proj2 = project_fn(p2)
                
                if proj1 and proj2:
                    sx1, sy1 = proj1[:2]
                    sx2, sy2 = proj2[:2]
                    
                    # Glow layer
                    if glow_surface and glow_alpha > 5:
                        pygame.draw.line(glow_surface, (*base_color, glow_alpha), (int(sx1), int(sy1)), (int(sx2), int(sy2)), 6)
                    
                    # Core line WITH ALPHA
                    if core_alpha > 2:
                        pygame.draw.line(surface, (*base_color, core_alpha), (int(sx1), int(sy1)), (int(sx2), int(sy2)), 2)
