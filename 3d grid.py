import pygame
import cv2
import numpy as np
import mediapipe as mp
import threading
import time
import math
from flowers import FlowerField, SmileDetector

# Configuration (initial values; updated to native resolution at runtime)
width, height = 1000, 700
eye_depth = 3.0  # Distance from viewer to screen plane (increased for less perspective exaggeration)
unit_scale = 150  # Pixels per unit in 3D space
room_depth = 8.0  # Depth of the room in 3D space

# Camera parameters for frontal perspective
camera_pitch_deg = 6.0  # degrees, positive = camera pitched DOWN (look slightly downward)
camera_pitch = math.radians(camera_pitch_deg)
camera_height = 0.3  # world units; camera height (shifted down to flower level)
near_clip = 0.1  # near plane clipping distance


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


# 3D Point class
class Point3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


def project_off_axis(p, head_x, head_y, camera_pitch=None, camera_height=None):
    """Project a 3D point to 2D screen coordinates using off-axis projection.
    
    Uses camera-space transformation to support camera pitch and height.
    """
    if camera_pitch is None:
        camera_pitch = globals()['camera_pitch']
    if camera_height is None:
        camera_height = globals()['camera_height']
    
    # Transform to camera space
    x_cam, y_cam, z_cam = world_to_camera(p, camera_pitch, camera_height)
    
    total_depth = eye_depth + z_cam
    if total_depth <= near_clip:
        return None

    ratio = eye_depth / total_depth
    screen_x_virtual = head_x + (x_cam - head_x) * ratio
    screen_y_virtual = head_y + (y_cam - head_y) * ratio

    pixel_x = int(width / 2 + screen_x_virtual * unit_scale)
    pixel_y = int(height / 2 - screen_y_virtual * unit_scale)
    return (pixel_x, pixel_y)


# Tracking engine
class HandTracking:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5)
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
        # overlay surface for glow effects (keep per-instance to avoid reallocating)
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
    
    def draw_full_grid(self, surface, head_x, head_y):
        # draw complete 3d grid (floor, walls, ceiling) with glow
        base_w = 3.0  # reduced room width to frame flowers tighter
        h_room = 2.4  # reduced room height
        grid_spacing = 1.0

        # scale room width to screen aspect so grid fills wider screens
        aspect = max(0.5, float(self.width) / max(1, self.height))
        w_room = base_w * aspect * 1.0

        # clear overlay
        self.overlay.fill((0, 0, 0, 0))

        # floor and ceiling
        for x in np.arange(-w_room, w_room + 0.1, grid_spacing):
            p1 = project_off_axis(Point3D(x, -h_room, 0), head_x, head_y)
            p2 = project_off_axis(Point3D(x, -h_room, w_room), head_x, head_y)
            if p1 and p2:
                pygame.draw.line(surface, (30, 40, 90), p1, p2, 1)
                pygame.draw.line(self.overlay, (70, 100, 255, 40), p1, p2, 4)

            p3 = project_off_axis(Point3D(x, h_room, 0), head_x, head_y)
            p4 = project_off_axis(Point3D(x, h_room, w_room), head_x, head_y)
            if p3 and p4:
                pygame.draw.line(surface, (30, 40, 90), p3, p4, 1)
                pygame.draw.line(self.overlay, (70, 100, 255, 40), p3, p4, 4)

        # walls
        for y in np.arange(-h_room, h_room + 0.1, grid_spacing):
            p1 = project_off_axis(Point3D(-w_room, y, 0), head_x, head_y)
            p2 = project_off_axis(Point3D(-w_room, y, w_room), head_x, head_y)
            if p1 and p2:
                pygame.draw.line(surface, (30, 40, 90), p1, p2, 1)
                pygame.draw.line(self.overlay, (70, 100, 255, 40), p1, p2, 3)

            p3 = project_off_axis(Point3D(w_room, y, 0), head_x, head_y)
            p4 = project_off_axis(Point3D(w_room, y, w_room), head_x, head_y)
            if p3 and p4:
                pygame.draw.line(surface, (30, 40, 90), p3, p4, 1)
                pygame.draw.line(self.overlay, (70, 100, 255, 40), p3, p4, 3)

        # traversing lines (depth lines)
        for z in np.arange(0, room_depth + 0.1, grid_spacing):
            tl = project_off_axis(Point3D(-w_room, h_room, z), head_x, head_y)
            tr = project_off_axis(Point3D(w_room, h_room, z), head_x, head_y)
            bl = project_off_axis(Point3D(-w_room, -h_room, z), head_x, head_y)
            br = project_off_axis(Point3D(w_room, -h_room, z), head_x, head_y)

            if tl and tr and bl and br:
                pygame.draw.line(surface, (30, 40, 90), tl, tr, 1) #top
                pygame.draw.line(surface, (30, 40, 90), bl, br, 1) #bottom
                pygame.draw.line(surface, (30, 40, 90), tl, bl, 1) #left
                pygame.draw.line(surface, (30, 40, 90), tr, br, 1) #right
                pygame.draw.line(self.overlay, (90, 130, 255, 28), tl, tr, 3)
                pygame.draw.line(self.overlay, (90, 130, 255, 28), bl, br, 3)
                pygame.draw.line(self.overlay, (90, 130, 255, 28), tl, bl, 2)
                pygame.draw.line(self.overlay, (90, 130, 255, 28), tr, br, 2)

        # blit overlay containing glow effects
        surface.blit(self.overlay, (0, 0))


# Main application loop
def main(debug_windowed=False):
    pygame.init()
    # Start fullscreen at native desktop resolution (avoid stretching)
    # Or windowed for debug
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

    tracker = HandTracking()
    renderer = GridRenderer(width, height)
    # place lanes near the bottom of the room
    flower_field = FlowerField(lanes=12, lane_y=-3.2, depth_layers=10)
    smile_detector = SmileDetector()

    running = True
    while running:
        dt = clock.tick(fps) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # Fill background (start grayscale)
        screen.fill((10, 10, 10))

        # Get head position from tracker
        head_x = tracker.head_x if tracker.detected else 0.0
        head_y = tracker.head_y if tracker.detected else 0.0

        # Update smile detector from latest landmarks produced by tracker
        smile_detector.update(getattr(tracker, 'landmarks', None))
        smile_strength = smile_detector.smile_strength

        # Update flower field
        flower_field.update(dt, head_x, head_y, smile_strength)

        # Draw scene: grid (room) then flowers
        renderer.draw_full_grid(screen, head_x, head_y)
        flower_field.draw(screen, project_off_axis, head_x, head_y)

        # Update display
        pygame.display.flip()

    # Cleanup
    tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    main(debug_windowed=True)  # True for windowed debug mode, False for fullscreen
