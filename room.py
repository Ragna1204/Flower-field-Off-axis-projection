import pygame
from geometry import Point3D
from projection import project_off_axis

# Dark sci-fi grayscale base
WALL_COLOR = (18, 18, 25)
EDGE_NEON = (80, 120, 255)

class RoomRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        # Room size (world units)
        self.w = 3.5     # half width
        self.h = 2.4     # half height
        self.d = 10.0    # depth

    def draw_plane(self, surface, head_x, head_y,
                   camera_pitch, camera_height, eye_depth,
                   near_clip, unit_scale, width, height, world_to_camera,
                   p1, p2, p3, p4, color):

        q1 = project_off_axis(p1, head_x, head_y,
                              camera_pitch, camera_height,
                              eye_depth, near_clip, unit_scale,
                              width, height, world_to_camera)

        q2 = project_off_axis(p2, head_x, head_y,
                              camera_pitch, camera_height,
                              eye_depth, near_clip, unit_scale,
                              width, height, world_to_camera)

        q3 = project_off_axis(p3, head_x, head_y,
                              camera_pitch, camera_height,
                              eye_depth, near_clip, unit_scale,
                              width, height, world_to_camera)

        q4 = project_off_axis(p4, head_x, head_y,
                              camera_pitch, camera_height,
                              eye_depth, near_clip, unit_scale,
                              width, height, world_to_camera)

        if not (q1 and q2 and q3 and q4):
            return

        pygame.draw.polygon(surface, color, [q1, q2, q3, q4])

        # Neon sci-fi edges
        pygame.draw.line(surface, EDGE_NEON, q1, q2, 2)
        pygame.draw.line(surface, EDGE_NEON, q2, q3, 2)
        pygame.draw.line(surface, EDGE_NEON, q3, q4, 2)
        pygame.draw.line(surface, EDGE_NEON, q4, q1, 2)

    def draw(self, surface, head_x, head_y,
             camera_pitch, camera_height,
             eye_depth, near_clip, unit_scale,
             width, height, world_to_camera):

        w = self.w
        h = self.h
        d = self.d

        # ---------- FLOOR ----------
        self.draw_plane(surface, head_x, head_y,
                        camera_pitch, camera_height, eye_depth,
                        near_clip, unit_scale, width, height, world_to_camera,
                        Point3D(-w, -h, 0),
                        Point3D( w, -h, 0),
                        Point3D( w, -h, d),
                        Point3D(-w, -h, d),
                        WALL_COLOR)

        # ---------- CEILING ----------
        self.draw_plane(surface, head_x, head_y,
                        camera_pitch, camera_height, eye_depth,
                        near_clip, unit_scale, width, height, world_to_camera,
                        Point3D(-w, h, 0),
                        Point3D( w, h, 0),
                        Point3D( w, h, d),
                        Point3D(-w, h, d),
                        WALL_COLOR)

        # ---------- LEFT WALL ----------
        self.draw_plane(surface, head_x, head_y,
                        camera_pitch, camera_height, eye_depth,
                        near_clip, unit_scale, width, height, world_to_camera,
                        Point3D(-w, -h, 0),
                        Point3D(-w,  h, 0),
                        Point3D(-w,  h, d),
                        Point3D(-w, -h, d),
                        WALL_COLOR)

        # ---------- RIGHT WALL ----------
        self.draw_plane(surface, head_x, head_y,
                        camera_pitch, camera_height, eye_depth,
                        near_clip, unit_scale, width, height, world_to_camera,
                        Point3D(w, -h, 0),
                        Point3D(w,  h, 0),
                        Point3D(w,  h, d),
                        Point3D(w, -h, d),
                        WALL_COLOR)

        # ---------- BACK WALL ----------
        self.draw_plane(surface, head_x, head_y,
                        camera_pitch, camera_height, eye_depth,
                        near_clip, unit_scale, width, height, world_to_camera,
                        Point3D(-w, -h, d),
                        Point3D( w, -h, d),
                        Point3D( w,  h, d),
                        Point3D(-w,  h, d),
                        WALL_COLOR)

