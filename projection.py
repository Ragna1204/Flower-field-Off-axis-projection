def project_off_axis(p, head_x, head_y,
                     camera_pitch,
                     camera_height,
                     eye_depth,
                     near_clip,
                     unit_scale,
                     width,
                     height,
                     world_to_camera,
                     return_scale: bool = False):
    """
    Project a 3D point to 2D screen coordinates using off-axis projection.
    All required parameters are passed explicitly to avoid circular imports.
    """

    # Transform world point to camera space
    x_cam, y_cam, z_cam = world_to_camera(p, camera_pitch, camera_height)

    total_depth = eye_depth + z_cam
    if total_depth <= near_clip:
        return None

    ratio = eye_depth / total_depth

    screen_x_virtual = head_x + (x_cam - head_x) * ratio
    screen_y_virtual = head_y + (y_cam - head_y) * ratio

    pixel_x = int(width / 2 + screen_x_virtual * unit_scale)
    pixel_y = int(height / 2 - screen_y_virtual * unit_scale)

    scale = (eye_depth / (eye_depth + z_cam)) * unit_scale

    if return_scale:
        return (pixel_x, pixel_y, scale)
    return (pixel_x, pixel_y)