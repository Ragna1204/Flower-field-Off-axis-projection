import math

def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t

# Default configuration
SMILE_THRESHOLD = 0.22
SMILE_SMOOTHING = 0.08

class SmileDetector:
    """Detects smiles from MediaPipe face landmarks using mouth aspect ratio.
    
    Uses absolute deviation from baseline to work for all face types -
    some people's metrics increase when smiling, others decrease.
    """
    
    def __init__(self, threshold: float = SMILE_THRESHOLD, smooth: float = SMILE_SMOOTHING):
        self.threshold = threshold
        self.smooth = smooth
        self.smile_strength = 0.0
        self.baseline = None
        self.baseline_smooth = 0.02
        
        # Calibration prevents false positives during initialization
        self.calibration_start_time = None
        self.calibration_duration = 2.0
        self.is_calibrated = False
        self.calibration_sample_count = 0

    def compute_mouth_aspect(self, lm) -> float:
        """Compute mouth aspect ratio: horizontal distance / vertical distance.
        Uses lip corners (61, 291) and inner lips (13, 14)."""
        try:
            left, right = lm[61], lm[291]
            top, bottom = lm[13], lm[14]
        except Exception:
            return 0.0

        h = math.hypot(right.x - left.x, right.y - left.y)
        v = math.hypot(bottom.x - top.x, bottom.y - top.y)
        
        if v <= 1e-6:
            return 0.0
        return h / v

    def update(self, landmarks, current_time=None) -> None:
        """Update smile strength based on current landmarks."""
        if not landmarks:
            target = 0.0
            self.calibration_start_time = None
            self.is_calibrated = False
        else:
            metric = self.compute_mouth_aspect(landmarks)
            
            # Filter invalid metrics from tracking errors
            if metric < 4.0 or metric > 2000.0:
                target = self.smile_strength  # Hold previous value
            else:
                # Initialize baseline on first valid frame
                if self.baseline is None:
                    self.baseline = metric
                    self.calibration_start_time = current_time
                    print(f"[SMILE] Baseline calibration started at t={current_time:.1f}s")

                # Adapt baseline only during calibration, then freeze
                if not self.is_calibrated:
                    self.baseline = lerp(self.baseline, metric, self.baseline_smooth)
                    self.calibration_sample_count += 1

                # Check calibration completion
                if not self.is_calibrated and current_time and self.calibration_start_time:
                    elapsed = current_time - self.calibration_start_time
                    if elapsed >= self.calibration_duration:
                        self.is_calibrated = True
                        print(f"[SMILE] Baseline frozen at t={current_time:.1f}s (baseline={self.baseline:.1f})")
                
                # Compute smile strength after calibration
                if self.is_calibrated:
                    # Use absolute deviation (works for both increasing/decreasing metrics)
                    abs_diff = abs(metric - self.baseline)
                    raw = abs_diff / 150.0  # 150pt change = full smile
                    target = max(0.0, min(1.0, raw))
                else:
                    target = 0.0

        # Smooth the result
        self.smile_strength = lerp(self.smile_strength, target, self.smooth)

    @property
    def smiling(self) -> bool:
        return self.smile_strength >= self.threshold
