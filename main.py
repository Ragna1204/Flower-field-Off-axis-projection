import pygame
import cv2
import numpy as np
import mediapipe as mp
import threading
import time
import math
from flowers import FlowerField
from smile_detector import SmileDetector
from smile_text import SmileText
from geometry import Point3D
from projection import project_off_axis
from room import RoomRenderer

# Configuration (initial values; updated to native resolution at runtime)
width, height = 1000, 700

# CAMERA / PROJECTION (tuned for "standing in" the flower field)
eye_depth = 3.5         # distance from viewer to virtual screen plane (smaller -> stronger perspective)
unit_scale = 220        # pixels per world unit (increase to make flowers larger on screen)
room_depth = 10.0       # extend room depth for a deeper field

# Camera parameters tuned for eye-level standing view
camera_pitch_deg = 2.2            # small downward pitch (degrees)
camera_pitch = math.radians(camera_pitch_deg)
camera_height = 0.9               # eye height in world units (approx 1.6m = standing)
near_clip = 0.05                  # near plane clipping distance (smaller to avoid early culling)

# --- Head/world smoothing state & tuning (global state used by main loop) ---
head_world_x = 0.0
head_world_y = 0.0
HEAD_MAP_SCALE_X = 1.2   # maps normalized webcam (-1..1) to world units (left-right)
HEAD_MAP_SCALE_Y = 0.9   # maps normalized webcam (-1..1) to world units (up-down)
HEAD_SMOOTH = 0.03        # smoothing factor (0..1) for exponential smoothing

room_energy = 0.0 # energy level for room lighting (0..1)

# ---- WORLD STATE ----
WORLD_DORMANT = 0      # before smile
WORLD_AWAKENING = 1   # after smile, time-based
WORLD_ALIVE = 2       # fully awakened

world_state = WORLD_DORMANT
awakening_time = 0.0
intro_time = 0.0

# ---- AWAKENING TIMING ----
INTRO_DELAY = 5.0          # seconds before smile is allowed
AWAKEN_DURATION = 12.0     # seconds for full awakening


# Camera transformation helpers
def world_to_camera(p, camera_pitch, camera_height):
    """Transform a world-space point into camera-space coordinates.
    
    Args:
        p: Point3D in world space.
        camera_pitch: Camera pitch in radians (positive = tilted down).
        camera_height: Camera height in world units.
    
    Returns:
        (x_cam, y_cam, z_cam) in camera space.
    """
    c = math.cos(camera_pitch)
    s = math.sin(camera_pitch)
    y_rel = p.y - camera_height  # translate by camera height
    y_cam = y_rel * c + p.z * s  # rotate around X axis
    z_cam = -y_rel * s + p.z * c
    x_cam = p.x
    return x_cam, y_cam, z_cam


def camera_depth_for_point(p, camera_pitch, camera_height):
    """Compute camera-space depth and total depth for a world point.
    
    Returns:
        (z_cam, total_depth) where total_depth = eye_depth + z_cam.
    """
    x_cam, y_cam, z_cam = world_to_camera(p, camera_pitch, camera_height)
    return z_cam, eye_depth + z_cam

def ease(t):
    return t * t * (3 - 2 * t)  # smoothstep



# Tracking engine
class HandTracking:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.head_x, self.head_y = 0.0, 0.0
        self.detected = False
        self.landmarks = None
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                self.detected = True
                lm = results.multi_face_landmarks[0]
                pt = lm.landmark[1]

                # store landmarks for smile detector
                self.landmarks = lm.landmark

                self.head_x = (pt.x - 0.5) * 2
                self.head_y = (pt.y - 0.5) * 2
            else:
                self.detected = False
                self.landmarks = None
            time.sleep(1/60)

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()


# 3D Grid Renderer
class GridRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

    def draw_full_grid(
        self,
        surface,
        head_x, head_y,
        camera_pitch, camera_height,
        eye_depth, near_clip, unit_scale,
        width, height,
        world_to_camera,
        project_off_axis_func,
        room_depth=10.0
    ):
        """Draws the full grid using the updated off-axis projection API."""
        base_w = 3.0
        h_room = 2.4
        grid_spacing = 1.0

        # Scale room width with aspect
        aspect = max(0.5, float(self.width) / max(1, self.height))
        w_room = base_w * aspect

        # Clear glow overlay
        self.overlay.fill((0, 0, 0, 0))

        # Helper to call projection correctly
        def P(point):
            return project_off_axis_func(
                point,
                head_x, head_y,
                camera_pitch, camera_height,
                eye_depth, near_clip, unit_scale,
                width, height,
                world_to_camera
            )

        # ---------------- FLOOR + CEILING ----------------
        for x in np.arange(-w_room, w_room + 0.1, grid_spacing):
            p1 = P(Point3D(x, -h_room, 0))
            p2 = P(Point3D(x, -h_room, room_depth))
            if p1 and p2:
                pygame.draw.line(surface, (30, 40, 90), p1, p2, 1)
                pygame.draw.line(self.overlay, (70, 100, 255, 40), p1, p2, 4)

            p3 = P(Point3D(x, h_room, 0))
            p4 = P(Point3D(x, h_room, room_depth))
            if p3 and p4:
                pygame.draw.line(surface, (30, 40, 90), p3, p4, 1)
                pygame.draw.line(self.overlay, (70, 100, 255, 40), p3, p4, 4)

        # ---------------- LEFT + RIGHT WALLS ----------------
        for y in np.arange(-h_room, h_room + 0.1, grid_spacing):
            p1 = P(Point3D(-w_room, y, 0))
            p2 = P(Point3D(-w_room, y, room_depth))
            if p1 and p2:
                pygame.draw.line(surface, (30, 40, 90), p1, p2, 1)
                pygame.draw.line(self.overlay, (70, 100, 255, 40), p1, p2, 3)

            p3 = P(Point3D(w_room, y, 0))
            p4 = P(Point3D(w_room, y, room_depth))
            if p3 and p4:
                pygame.draw.line(surface, (30, 40, 90), p3, p4, 1)
                pygame.draw.line(self.overlay, (70, 100, 255, 40), p3, p4, 3)

        # ---------------- DEPTH LINES ----------------
        for z in np.arange(0, room_depth + 0.1, grid_spacing):
            tl = P(Point3D(-w_room, h_room, z))
            tr = P(Point3D(w_room, h_room, z))
            bl = P(Point3D(-w_room, -h_room, z))
            br = P(Point3D(w_room, -h_room, z))

            if tl and tr and bl and br:
                pygame.draw.line(surface, (30, 40, 90), tl, tr, 1)
                pygame.draw.line(surface, (30, 40, 90), bl, br, 1)
                pygame.draw.line(surface, (30, 40, 90), tl, bl, 1)
                pygame.draw.line(surface, (30, 40, 90), tr, br, 1)

                pygame.draw.line(self.overlay, (90, 130, 255, 28), tl, tr, 3)
                pygame.draw.line(self.overlay, (90, 130, 255, 28), bl, br, 3)
                pygame.draw.line(self.overlay, (90, 130, 255, 28), tl, bl, 2)
                pygame.draw.line(self.overlay, (90, 130, 255, 28), tr, br, 2)

        # Add soft glow overlay
        surface.blit(self.overlay, (0, 0))



# Main application loop
def main(debug_windowed=False):
    global room_energy, world_state, awakening_time, intro_time
    pygame.init()
    info = pygame.display.Info()

    if debug_windowed:
        screen = pygame.display.set_mode((1280, 800))
    else:
        screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)

    global width, height
    width, height = screen.get_width(), screen.get_height()

    pygame.display.set_caption("3D Off-Axis Projection Grid - Flowers")
    clock = pygame.time.Clock()
    fps = 60

    glow_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    tracker = HandTracking()
    renderer = GridRenderer(width, height)
    flower_field = FlowerField(lanes=12, lane_y=-1.35, depth_layers=14)
    smile_text = SmileText(reveal_delay=5.0)
    smile_detector = SmileDetector()
    
    # Smile trigger parameters
    smile_start_time = None
    SMILE_SUSTAIN_DURATION = 0.3
    SMILE_THRESHOLD = 0.6  # Raised from 0.5 to prevent false positives

    head_world_x = 0.0
    head_world_y = 0.0
    
    # Scene readiness - delays timer until rendering starts
    scene_ready = False
    frames_rendered = 0

    running = True
    while running:
        dt = clock.tick(fps) / 1000.0
        
        # Only start timer after scene is actually visible (not during black screen init)
        if scene_ready:
            intro_time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill((10, 10, 10))
        glow_surface.fill((0, 0, 0, 0))

        # --- Head Tracking ---
        raw_x = tracker.head_x if tracker.detected else 0.0
        raw_y = -(tracker.head_y) if tracker.detected else 0.0

        target_x = raw_x * HEAD_MAP_SCALE_X
        target_y = raw_y * HEAD_MAP_SCALE_Y

        head_world_x += (target_x - head_world_x) * HEAD_SMOOTH
        head_world_y += (target_y - head_world_y) * HEAD_SMOOTH
        
        # Start timer only after scene is visible (not during camera init)
        if not scene_ready:
            frames_rendered += 1
            if frames_rendered >= 3:
                scene_ready = True
                print(f"[SCENE READY] Timer starting")



        # Smile detection
        smile_detector.update(getattr(tracker, 'landmarks', None), intro_time)
        
        if world_state == WORLD_DORMANT:
            # Check for smile only after text is fully visible
            if smile_text.state == smile_text.STATE_VISIBLE:
                smile_strength = smile_detector.smile_strength
                is_detected = tracker.detected
                
                # Require sustained smile
                if is_detected and smile_strength > SMILE_THRESHOLD:
                    if smile_start_time is None:
                        smile_start_time = intro_time
                        print(f"[SMILE] Detected (strength={smile_strength:.2f})")
                    else:
                        sustain_duration = intro_time - smile_start_time
                        if sustain_duration >= SMILE_SUSTAIN_DURATION:
                            print(f"[AWAKENING] Triggered at t={intro_time:.1f}s")
                            world_state = WORLD_AWAKENING
                            awakening_time = 0.0
                            smile_text.start_fadeout(awakening_time)  # Request fade-out (delayed for mid-bloom)
                else:
                    smile_start_time = None


        if world_state == WORLD_AWAKENING:
            awakening_time += dt
            if awakening_time >= AWAKEN_DURATION:
                awakening_time = AWAKEN_DURATION
                world_state = WORLD_ALIVE


        # ---- PHASE D4: TIME-BASED ENERGY ----
        if world_state == WORLD_DORMANT:
            room_energy = 0.0

        elif world_state == WORLD_AWAKENING:
            # 12 seconds = full awakening (tweak later)
            room_energy = ease(min(awakening_time / 12.0, 1.0))

        else:  # WORLD_ALIVE
            room_energy = 1.0





        # ---- UPDATE ENTITIES ----
        smile_text.update(dt, intro_time, awakening_time)
        flower_field.update(dt, head_world_x, head_world_y, room_energy)

        # Draw Grid/Room
        renderer.draw_full_grid(
             screen,
             head_world_x, head_world_y,
             camera_pitch, camera_height,
             eye_depth, near_clip, unit_scale,
             width, height,
             world_to_camera,
             project_off_axis,
             room_depth=room_depth
        )
        
        # Shared Projection Wrapper
        def project_wrapper(p):
            return project_off_axis(
                p,
                head_world_x, head_world_y,
                camera_pitch, camera_height,
                eye_depth, near_clip, unit_scale,
                width, height,
                world_to_camera,
                return_scale=True
            )
            
        # Draw "SMILE" text (Phase 7: Narrative trigger)
        smile_text.draw(screen, glow_surface, project_wrapper, intro_time)
        
        # Draw Flowers
        flower_field.draw(screen, glow_surface, project_wrapper, screen_size=(width, height))

        # --- FOG DIFFUSION / BLOOM ---
        fog = pygame.transform.smoothscale(glow_surface, (width // 3, height // 3))
        fog = pygame.transform.smoothscale(fog, (width, height))

        screen.blit(fog, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        pygame.display.flip()

    tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    main(debug_windowed=True)  # True for windowed debug mode, False for fullscreen
