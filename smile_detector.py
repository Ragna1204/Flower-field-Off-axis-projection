def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t

# Default configuration  
SMILE_THRESHOLD = 0.65
SMILE_SMOOTHING = 0.12

class SmileDetector:
    """Detects smiles using lip corner movement.
    
    Tracks distance between lip corners - they move apart when smiling.
    More reliable than mouth aspect ratio.
    """
    
    def __init__(self, threshold: float = SMILE_THRESHOLD, smooth: float = SMILE_SMOOTHING):
        self.threshold = threshold
        self.smooth = smooth
        self.smile_strength = 0.0
        self.baseline = None
        self.is_calibrated = False
        self.calibration_samples = []
        self.calibration_duration = 60  # 60 frames ≈ 1 second

    def compute_lip_corner_distance(self, lm) -> float:
        """Compute horizontal distance between lip corners.
        When smiling, corners move apart."""
        try:
            left_corner = lm[61]   # Left mouth corner
            right_corner = lm[291]  # Right mouth corner
            
            # Horizontal distance (x-axis)
            distance = abs(right_corner.x - left_corner.x)
            return distance * 1000  # Scale for easier threshold tuning
        except Exception:
            return 0.0

    def update(self, landmarks, current_time=None) -> None:
        """Update smile strength based on lip corner distance."""
        if not landmarks:
            target = 0.0
            # Don't reset calibration - preserve it across temporary face loss
        else:
            metric = self.compute_lip_corner_distance(landmarks)
            
            # Filter invalid metrics
            if metric < 10.0 or metric > 500.0:
                target = self.smile_strength
            else:
                # Calibration: collect neutral samples
                if not self.is_calibrated:
                    self.calibration_samples.append(metric)
                    
                    if len(self.calibration_samples) >= self.calibration_duration:
                        # Use median of samples as baseline (robust to outliers)
                        self.calibration_samples.sort()
                        self.baseline = self.calibration_samples[len(self.calibration_samples) // 2]
                        self.is_calibrated = True
                        print(f"[SMILE] Baseline calibrated: {self.baseline:.1f} (lip corner distance)")
                    
                    target = 0.0  # No smile detection during calibration
                else:
                    # Detect smile as deviation above baseline
                    diff = metric - self.baseline
                    
                    # Only positive deviations count (corners moving apart)
                    if diff > 0:
                        # Normalize to 0-1 range (scale: 15 units = full smile)
                        raw = diff / 15.0
                        target = max(0.0, min(1.0, raw))
                    else:
                        target = 0.0

        # Smooth the result
        self.smile_strength = lerp(self.smile_strength, target, self.smooth)

    @property
    def smiling(self) -> bool:
        return self.smile_strength >= self.threshold
