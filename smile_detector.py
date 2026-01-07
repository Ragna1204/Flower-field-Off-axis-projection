import math

# Utility: linear interpolation
def lerp(a, b, t):
    return a + (b - a) * t

# Configuration
SMILE_THRESHOLD = 0.22
SMILE_SMOOTHING = 0.08

class SmileDetector:
    """Simple smile detector that computes a smile_strength (0..1) from
    face landmark positions provided by MediaPipe.

    Usage: call `update(landmarks)` each frame with `landmarks` being the
    landmark list from MediaPipe (or None). The detector smooths the
    instantaneous metric and exposes `smile_strength`.
    """

    def __init__(self, threshold: float = SMILE_THRESHOLD, smooth: float = SMILE_SMOOTHING):
        self.threshold = threshold
        self.smooth = smooth
        self.smile_strength = 0.0
        self.baseline = None
        self.baseline_smooth = 0.02
        
        # Calibration to prevent false positives
        self.calibration_start_time = None
        self.calibration_duration = 2.0  # Require 2s of face visibility before detecting smiles
        self.is_calibrated = False
        self.calibration_sample_count = 0

    def compute_mouth_aspect(self, lm) -> float:
        """Compute a simple mouth aspect ratio from landmarks.
        Expects lm to be a sequence of landmarks with .x and .y attributes.
        We'll use lip corner indices (61, 291) and top/bottom inner lip (13, 14)
        which are available when refine_landmarks=True.
        """
        try:
            left = lm[61]
            right = lm[291]
            top = lm[13]
            bottom = lm[14]
        except Exception:
            return 0.0

        # horizontal distance between corners
        h = math.hypot(right.x - left.x, right.y - left.y)
        # vertical distance between inner lips
        v = math.hypot(bottom.x - top.x, bottom.y - top.y)
        if v <= 1e-6:
            return 0.0
        return (h / v)  # larger when smiling (corners stretch)

    def update(self, landmarks, current_time=None) -> None:
        """Call every frame with MediaPipe landmarks or None. Produces
        `self.smile_strength` in [0,1]."""
        if not landmarks:
            target = 0.0
            # Reset calibration if face lost
            self.calibration_start_time = None
            self.is_calibrated = False
        else:
            metric = self.compute_mouth_aspect(landmarks)
            
            # Initialize metric log counter
            if not hasattr(self, '_metric_log_count'):
                self._metric_log_count = 0
            
            # CRITICAL: Filter out invalid metrics from tracking errors
            # Valid mouth aspect ratios should be in range ~4-2000
            # User's smile can produce values as low as 4-6
            # Values outside this indicate tracking failure
            if metric < 4.0 or metric > 2000.0:
                # Bad tracking - skip this frame entirely
                if self._metric_log_count % 60 == 0:
                    print(f"[METRIC WARNING] Invalid metric={metric:.1f}, skipping frame")
                target = self.smile_strength  # Hold previous value
            else:
                # Initialize baseline if needed
                if self.baseline is None:
                    self.baseline = metric
                    self.calibration_start_time = current_time
                    print(f"[SMILE] Baseline calibration started at t={current_time:.1f}s (initial metric={metric:.3f})")

                # ONLY adapt baseline during calibration, then freeze it
                if not self.is_calibrated:
                    # Adapt baseline slowly during calibration
                    self.baseline = lerp(self.baseline, metric, self.baseline_smooth)
                    self.calibration_sample_count += 1

                # Check if calibration period is complete
                if not self.is_calibrated and current_time is not None and self.calibration_start_time is not None:
                    elapsed = current_time - self.calibration_start_time
                    if elapsed >= self.calibration_duration:
                        self.is_calibrated = True
                        print(f"[SMILE] Baseline FROZEN at t={current_time:.1f}s (baseline={self.baseline:.3f}, samples={self.calibration_sample_count})")
                
                # Only compute smile strength after calibration
                if self.is_calibrated:
                    # CRITICAL FIX: Smiling can INCREASE or DECREASE metric depending on person
                    # Some faces: corners stretch → metric increases
                    # Other faces: mouth opens → vertical increases more → metric DECREASES
                    # Solution: Use ABSOLUTE deviation from baseline
                    
                    diff = metric - self.baseline
                    abs_diff = abs(diff)
                    
                    # Scale based on absolute change (150pt = full smile strength)
                    scale = 150.0
                    raw = abs_diff / scale
                    target = max(0.0, min(1.0, raw))
                else:
                    # During calibration, force smile_strength to 0
                    target = 0.0

        # exponential smoothing (lerp)
        self.smile_strength = lerp(self.smile_strength, target, self.smooth)

    @property
    def smiling(self) -> bool:
        return self.smile_strength >= self.threshold
