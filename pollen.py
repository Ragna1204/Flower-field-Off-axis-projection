"""
Pollen Particle System - Organic upward drift from flower centers
"""

import pygame
import random
import math
from geometry import Point3D

class PollenParticle:
    """Single pollen particle with organic motion."""
    
    def __init__(self, flower_pos, birth_time):
        """
        Args:
            flower_pos: Point3D of flower center
            birth_time: Time when particle was spawned
        """
        # Start at flower center with small random offset
        self.pos = Point3D(
            flower_pos.x + random.uniform(-0.05, 0.05),
            flower_pos.y + random.uniform(-0.05, 0.05),
            flower_pos.z + random.uniform(-0.05, 0.05)
        )
        
        self.birth_time = birth_time
        self.age = 0.0
        
        # Upward drift velocity (very slow)
        self.velocity = Point3D(
            random.uniform(-0.002, 0.002),  # Slight horizontal drift
            random.uniform(0.008, 0.015),   # Upward drift (main motion)
            random.uniform(-0.002, 0.002)   # Slight depth drift
        )
        
        # Spiral parameters for organic motion
        self.spiral_phase = random.uniform(0, math.pi * 2)
        self.spiral_radius = random.uniform(0.01, 0.03)
        self.spiral_speed = random.uniform(0.02, 0.05)
        
        # Visual properties
        self.base_size = random.uniform(1.5, 3.5)  # Pixel size
        self.glow_intensity = random.uniform(0.6, 1.0)
        
        # Color variation (warm tones)
        self.color_hue = random.uniform(0, 60)  # Yellow to orange
        
        self.alive = True
        
    def update(self, dt):
        """Update particle position and state."""
        self.age += dt
        
        # Spiral motion
        spiral_offset_x = math.cos(self.spiral_phase) * self.spiral_radius
        spiral_offset_z = math.sin(self.spiral_phase) * self.spiral_radius
        self.spiral_phase += self.spiral_speed * dt
        
        # Update position with drift + spiral
        self.pos = Point3D(
            self.pos.x + self.velocity.x + spiral_offset_x * dt,
            self.pos.y + self.velocity.y,
            self.pos.z + self.velocity.z + spiral_offset_z * dt
        )
        
        # Die if particle drifts too high or old
        if self.pos.y > 2.4 or self.age > 30.0:  # Ceiling height or max age
            self.alive = False
    
    def get_alpha(self):
        """Get particle alpha based on age (fade in/out)."""
        if self.age < 0.5:
            # Fade in
            return int(255 * (self.age / 0.5))
        elif self.age > 28.0:
            # Fade out before death
            return int(255 * ((30.0 - self.age) / 2.0))
        else:
            return 255
    
    def get_color(self):
        """Get particle color (warm glow)."""
        # Convert HSV to RGB (hue=0-60, sat=100%, val=100%)
        h = self.color_hue / 360.0
        s = 1.0
        v = 1.0
        
        if s == 0.0:
            r = g = b = v
        else:
            i = int(h * 6.0)
            f = (h * 6.0) - i
            p = v * (1.0 - s)
            q = v * (1.0 - s * f)
            t = v * (1.0 - s * (1.0 - f))
            i = i % 6
            
            if i == 0:
                r, g, b = v, t, p
            elif i == 1:
                r, g, b = q, v, p
            elif i == 2:
                r, g, b = p, v, t
            elif i == 3:
                r, g, b = p, q, v
            elif i == 4:
                r, g, b = t, p, v
            else:
                r, g, b = v, p, q
        
        return (int(r * 255), int(g * 255), int(b * 255))


class PollenSystem:
    """Manages all pollen particles."""
    
    def __init__(self):
        self.particles = []
        self.spawn_timer = 0.0
        self.spawn_rate = 0.15  # Spawn interval in seconds (start slow)
        self.min_spawn_rate = 0.08  # Gradually speed up to this
        self.active = False
        self.time_since_activation = 0.0
        
    def activate(self):
        """Start spawning particles."""
        self.active = True
        self.time_since_activation = 0.0
        
    def update(self, dt, flowers, current_time):
        """
        Update all particles and spawn new ones.
        
        Args:
            dt: Delta time
            flowers: List of Flower objects
            current_time: Current time since awakening start
        """
        if not self.active:
            return
        
        self.time_since_activation += dt
        
        # Gradually increase spawn rate over time (more particles as time goes on)
        progress = min(self.time_since_activation / 30.0, 1.0)  # Max after 30s
        self.spawn_rate = self.spawn_rate - (self.spawn_rate - self.min_spawn_rate) * progress * 0.01
        
        # Update existing particles
        for particle in self.particles[:]:
            particle.update(dt)
            if not particle.alive:
                self.particles.remove(particle)
        
        # Spawn new particles from random flowers
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_rate:
            self.spawn_timer = 0.0
            
            # Spawn from few random flowers
            num_spawns = random.randint(1, 3)
            for _ in range(num_spawns):
                if flowers:
                    flower = random.choice(flowers)
                    # Only spawn from fully bloomed flowers
                    if flower.life >= 1.0:
                        flower_pos = Point3D(flower.x, flower.y, flower.z)
                        particle = PollenParticle(flower_pos, current_time)
                        self.particles.append(particle)
    
    def render(self, screen, projection):
        """
        Render all particles.
        
        Args:
            screen: Pygame surface
            projection: Projection object with project() method
        """
        # Sort particles by depth (back to front)
        sorted_particles = sorted(self.particles, key=lambda p: p.pos.z, reverse=True)
        
        for particle in sorted_particles:
            # Project to screen
            screen_pos = projection.project(particle.pos)
            if screen_pos is None:
                continue
            
            x, y = screen_pos
            
            # Get visual properties
            alpha = particle.get_alpha()
            color = particle.get_color()
            size = particle.base_size
            
            # Draw glow (outer layer)
            glow_size = size * 2.5
            glow_surf = pygame.Surface((int(glow_size * 2), int(glow_size * 2)), pygame.SRCALPHA)
            glow_alpha = int(alpha * 0.3 * particle.glow_intensity)
            pygame.draw.circle(
                glow_surf,
                (*color, glow_alpha),
                (int(glow_size), int(glow_size)),
                int(glow_size)
            )
            screen.blit(
                glow_surf,
                (int(x - glow_size), int(y - glow_size)),
                special_flags=pygame.BLEND_ADD
            )
            
            # Draw core particle
            core_surf = pygame.Surface((int(size * 2), int(size * 2)), pygame.SRCALPHA)
            pygame.draw.circle(
                core_surf,
                (*color, alpha),
                (int(size), int(size)),
                int(size)
            )
            screen.blit(
                core_surf,
                (int(x - size), int(y - size)),
                special_flags=pygame.BLEND_ADD
            )
    
    def get_particle_count(self):
        """Get current particle count."""
        return len(self.particles)
