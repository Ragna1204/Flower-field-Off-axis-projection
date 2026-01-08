"""
Energy-Responsive Room with Rainbow Edge Cycling
"""

import pygame
import math
from geometry import Point3D

class RoomRenderer:
    """Renders a room with subtle rainbow edge cycling after awakening."""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # Room dimensions
        self.room_width = 4.0
        self.room_height = 2.6
        self.room_depth = 10.0
        
        # Grid spacing
        self.floor_ceiling_spacing = 0.8
        self.wall_spacing = 2.0
        
        self.glow_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.fog_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Rainbow cycling state
        self.rainbow_phase = 0.0
        
    def compute_depth_factor(self, z):
        """Depth-based brightness falloff."""
        if z <= 0:
            return 1.0
        if z >= self.room_depth:
            return 0.35
        
        normalized = z / self.room_depth
        return 1.0 - (normalized ** 1.3) * 0.65
    
    def get_rainbow_color(self, phase_offset=0.0):
        """Get rainbow color based on current phase.
        
        Returns RGB tuple cycling through spectrum.
        """
        # Cycle through hue (0-360 degrees)
        hue = ((self.rainbow_phase + phase_offset) % 360) / 360.0
        
        # Convert HSV to RGB (simplified)
        # We want: red→orange→yellow→green→cyan→blue→magenta→red
        h = hue * 6.0
        c = 1.0
        x = 1.0 - abs((h % 2) - 1.0)
        
        if h < 1:
            r, g, b = c, x, 0
        elif h < 2:
            r, g, b = x, c, 0
        elif h < 3:
            r, g, b = 0, c, x
        elif h < 4:
            r, g, b = 0, x, c
        elif h < 5:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def blend_colors(self, base_r, base_g, base_b, rainbow_r, rainbow_g, rainbow_b, rainbow_strength):
        """Blend base red with rainbow color.
        
        Args:
            base_r, base_g, base_b: Base red color
            rainbow_r, rainbow_g, rainbow_b: Rainbow color
            rainbow_strength: How much rainbow to blend (0-1)
        """
        # Keep base red dominant, add subtle rainbow tint
        r = int(base_r * (1 - rainbow_strength * 0.4) + rainbow_r * rainbow_strength * 0.4)
        g = int(base_g * (1 - rainbow_strength * 0.4) + rainbow_g * rainbow_strength * 0.4)
        b = int(base_b * (1 - rainbow_strength * 0.4) + rainbow_b * rainbow_strength * 0.4)
        
        return (r, g, b)
    
    def project_point(self, point, project_fn):
        """Project 3D point to screen."""
        result = project_fn(point)
        if result and len(result) >= 2:
            return (int(result[0]), int(result[1]))
        return None
    
    def draw(self, screen, project_fn, energy=0.0):
        """Draw room with subtle rainbow cycling.
        
        Args:
            screen: Screen surface
            project_fn: Projection function
            energy: Awakening energy (0=dormant, 1=fully alive)
        """
        w = self.room_width
        h = self.room_height
        d = self.room_depth
        
        self.glow_surface.fill((0, 0, 0, 0))
        self.fog_surface.fill((0, 0, 0, 0))
        
        # Update rainbow phase (slow cycling)
        if energy > 0.8:  # Only cycle when fully awakened
            self.rainbow_phase += 0.3  # Degrees per frame (slow)
            if self.rainbow_phase >= 360:
                self.rainbow_phase -= 360
        
        # Get current rainbow color
        rainbow_color = self.get_rainbow_color()
        
        # Rainbow strength based on energy (subtle)
        rainbow_strength = max(0, energy - 0.3) / 0.7  # Starts at energy=0.3, full at 1.0
        
        # ============== FLOOR GRID ==============
        x = -w
        while x <= w + 0.01:
            p1 = self.project_point(Point3D(x, -h, 0), project_fn)
            p2 = self.project_point(Point3D(x, -h, d), project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(d / 2)
                
                # Base red with subtle rainbow blend
                base = (100, 30, 40)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                # Glow with rainbow
                glow_base = (180, 60, 80)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((35 + 20 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 2)
            
            x += self.floor_ceiling_spacing
        
        z = 0
        while z <= d + 0.01:
            p1 = self.project_point(Point3D(-w, -h, z), project_fn)
            p2 = self.project_point(Point3D(w, -h, z), project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(z)
                
                base = (100, 30, 40)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                glow_base = (180, 60, 80)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((35 + 20 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 2)
            
            z += self.floor_ceiling_spacing
        
        # ============== CEILING GRID ==============
        x = -w
        while x <= w + 0.01:
            p1 = self.project_point(Point3D(x, h, 0), project_fn)
            p2 = self.project_point(Point3D(x, h, d), project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(d / 2)
                
                base = (115, 35, 48)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                glow_base = (200, 70, 90)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((40 + 25 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 2)
            
            x += self.floor_ceiling_spacing
        
        z = 0
        while z <= d + 0.01:
            p1 = self.project_point(Point3D(-w, h, z), project_fn)
            p2 = self.project_point(Point3D(w, h, z), project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(z)
                
                base = (115, 35, 48)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                glow_base = (200, 70, 90)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((40 + 25 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 2)
            
            z += self.floor_ceiling_spacing
        
        # ============== WALLS (similar pattern) ==============
        # Left wall
        y = -h
        while y <= h + 0.01:
            p1 = self.project_point(Point3D(-w, y, 0), project_fn)
            p2 = self.project_point(Point3D(-w, y, d), project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(d / 2)
                
                base = (108, 32, 44)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                glow_base = (190, 65, 85)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((37 + 22 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 2)
            
            y += self.wall_spacing
        
        z = 0
        while z <= d + 0.01:
            p1 = self.project_point(Point3D(-w, -h, z), project_fn)
            p2 = self.project_point(Point3D(-w, h, z), project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(z)
                
                base = (108, 32, 44)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                glow_base = (190, 65, 85)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((37 + 22 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 2)
            
            z += self.wall_spacing
        
        # Right wall
        y = -h
        while y <= h + 0.01:
            p1 = self.project_point(Point3D(w, y, 0), project_fn)
            p2 = self.project_point(Point3D(w, y, d), project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(d / 2)
                
                base = (108, 32, 44)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                glow_base = (190, 65, 85)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((37 + 22 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 2)
            
            y += self.wall_spacing
        
        z = 0
        while z <= d + 0.01:
            p1 = self.project_point(Point3D(w, -h, z), project_fn)
            p2 = self.project_point(Point3D(w, h, z), project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(z)
                
                base = (108, 32, 44)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                glow_base = (190, 65, 85)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((37 + 22 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 2)
            
            z += self.wall_spacing
        
        # ============== BACK WALL ==============
        corners = [
            Point3D(-w, -h, d),
            Point3D(w, -h, d),
            Point3D(w, h, d),
            Point3D(-w, h, d),
        ]
        
        for i in range(4):
            p1 = self.project_point(corners[i], project_fn)
            p2 = self.project_point(corners[(i + 1) % 4], project_fn)
            
            if p1 and p2:
                depth = self.compute_depth_factor(d)
                
                base = (130, 45, 58)
                blended = self.blend_colors(*base, *rainbow_color, rainbow_strength)
                core_color = (
                    int(blended[0] * depth),
                    int(blended[1] * depth),
                    int(blended[2] * depth)
                )
                pygame.draw.line(screen, core_color, p1, p2, 1)
                
                glow_base = (210, 80, 95)
                glow_blended = self.blend_colors(*glow_base, *rainbow_color, rainbow_strength)
                glow_alpha = int((50 + 30 * energy) * depth)
                glow_color = (*glow_blended, glow_alpha)
                pygame.draw.line(self.glow_surface, glow_color, p1, p2, 3)
        
        # ============== COMPOSITE ==============
        # Apply glow
        glow_small = pygame.transform.smoothscale(
            self.glow_surface,
            (self.width // 3, self.height // 3)
        )
        glow_blurred = pygame.transform.smoothscale(glow_small, (self.width, self.height))
        screen.blit(glow_blurred, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
