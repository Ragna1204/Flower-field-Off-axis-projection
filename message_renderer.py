"""
Message Renderer for timed text display on back wall.

Displays messages with fade in/out animations, synchronized with music timing.
"""

import pygame
from geometry import Point3D

class MessageRenderer:
    """Renders timed text messages with fade animations."""
    
    def __init__(self):
        """Initialize message renderer."""
        # Font setup
        pygame.font.init()
        self.font = pygame.font.Font(None, 48)  # Default font, size 48
        self.small_font = pygame.font.Font(None, 36)  # For longer messages
        
        # Animation parameters
        self.fade_in_duration = 1.0  # seconds
        self.fade_out_duration = 1.0  # seconds
        
        # State
        self.current_message_index = 0
        self.message_timer = 0.0
        self.message_state = "idle"  # idle, fading_in, showing, fading_out
        self.current_alpha = 0.0
        
        # Message list with timing
        self.messages = self._create_message_list()
        
    def _create_message_list(self):
        """Create list of timed messages.
        
        Returns list of dicts with:
        - text: Message text
        - start_time: When to show (seconds after awakening)
        - duration: How long to show (seconds)
        - pause_after: Extra pause after this message (seconds)
        """
        messages = [
            # During Afterthought - minimal text
            {"text": "Sorry it took so long", "start": 7, "duration": 3.5, "pause": 0},
            {"text": "Didnt want to rush this", "start": 12, "duration": 3.5, "pause": 0},
            {"text": "This was the \"project\" I \nhad to do lol", "start": 26, "duration": 4, "pause": 0},
            {"text": "Lowkey took way more time \nthan I expected", "start": 32, "duration": 5, "pause": 0},
            {"text": "Hope its not a bad time", "start": 72, "duration": 4, "pause": 0},
            {"text": "Sorry if I did or said \nsomething I shouldnt have", "start": 78, "duration": 5, "pause": 3},
            {"text": "Hope you dont have the fever \nanymore", "start": 85, "duration": 4, "pause": 0},
            
            {"text": "Yk that sunflowers look at each other\nwhen not in sunlight?", "start": 108, "duration": 5, "pause": 0},
            {"text": "Anyways", "start": 115, "duration": 1, "pause": 0},
            {"text": "This would be the song \nid dedicate to u", "start": 148, "duration": 4, "pause": 0},
            {"text": "Band karde kuch ni hai \niske baad", "start": 160, "duration": 3, "pause": 3},
            
            {"text": "Nahi?", "start": 168, "duration": 2, "pause": 0},
            {"text": "Jaisi marzi", "start": 176, "duration": 2, "pause": 0},
            {"text": "If you are still here...", "start": 185, "duration": 4, "pause": 0},
            
            # Touch Tank starts ~95-100s (after Afterthought 3:14 = 194s)
            # Adjust these based on actual song length
            {"text": ":)", "start": 191, "duration": 3, "pause": 0},
            {"text": "None of ts is done w ai btw", "start": 195, "duration": 4, "pause": 0},
            {"text": "Okay omveer appreciation day", "start": 201, "duration": 4, "pause": 0},
            {"text": "W music taste btw", "start": 207, "duration": 4, "pause": 0},  # when beat starts
            {"text": "What else", "start": 213, "duration": 3, "pause": 0},
            {"text": "Idk nothing much\n<(￣︶￣)>", "start": 218, "duration": 4, "pause": 0},
            
            {"text": "I have fun whenever im with you\nGenuinely", "start": 225, "duration": 5, "pause": 0},
            {"text": "I like being with you", "start": 232, "duration": 4, "pause": 0},
            {"text": "We both have our differences", "start": 238, "duration": 4, "pause": 0},
            {"text": "I know a lot of people\nbut i dont hang out with a lot of people", "start": 244, "duration": 6, "pause": 0},
            {"text": "You are amongst the very few\nI like being with", "start": 252, "duration": 5, "pause": 0},
            
            {"text": "We also got the lifetime bestie scar too, twin", "start": 259, "duration": 5, "pause": 0},
            {"text": "Certified trauma bonding", "start": 266, "duration": 4, "pause": 0},
            {"text": "Even then, the only thing in my head was\nki tujhe kuch nahi hona chahiye", "start": 272, "duration": 6, "pause": 0},
            {"text": "Still got the scar", "start": 278, "duration": 3, "pause": 0},
            {"text": "Looks cool not even kidding", "start": 283, "duration": 4, "pause": 0},
            {"text": "Mine not yours", "start": 289, "duration": 3, "pause": 0},
            {"text": "Yours too 👁️👅👁️", "start": 294, "duration": 3, "pause": 0},
            
            {"text": "Should not be typing this much", "start": 299, "duration": 4, "pause": 0},
            {"text": "If you wish to disable this text,\ngo settings > hide text", "start": 305, "duration": 5, "pause": 3},
            {"text": "Did not add that shit", "start": 311, "duration": 3, "pause": 0},
            
            {"text": "I want to know you more", "start": 316, "duration": 4, "pause": 0},
            {"text": "I want you to know me more too", "start": 322, "duration": 4, "pause": 0},
            {"text": "We leave a lot of planned things undone", "start": 328, "duration": 5, "pause": 0},
            {"text": "There are many things id want to do together", "start": 334, "duration": 5, "pause": 0},
            {"text": "Chowki dhani definately being one of them 🥀", "start": 341, "duration": 5, "pause": 0},
            {"text": "Hmm split fiction", "start": 348, "duration": 3, "pause": 0},
            
            {"text": "I might not express it much", "start": 353, "duration": 4, "pause": 0},
            {"text": "You are very important to me", "start": 359, "duration": 5, "pause": 0},
            {"text": "Hope you know that", "start": 366, "duration": 4, "pause": 0},
            {"text": "Thank you for being here", "start": 372, "duration": 5, "pause": 0},
            {"text": "As will i be", "start": 379, "duration": 4, "pause": 0},
            
            {"text": "Got too sweet shit", "start": 385, "duration": 3, "pause": 0},
            {"text": "Lmao tu end tak hai", "start": 390, "duration": 3, "pause": 0},
            {"text": "Respect", "start": 395, "duration": 3, "pause": 0},
            {"text": "Double sided tape bhi dede\nabhi yaad aaya ;-;", "start": 400, "duration": 4, "pause": 0},
            
            {"text": "Hope you liked it", "start": 406, "duration": 4, "pause": 0},
            {"text": "Chal ab band karde", "start": 412, "duration": 4, "pause": 0},
        ]
        return messages
    
    def update(self, dt, total_time):
        """Update message state and animations.
        
        Args:
            dt: Delta time
            total_time: Total elapsed time since awakening (seconds)
        """
        # Check if we should show next message
        if self.message_state == "idle":
            # Skip past messages that should have already appeared
            while self.current_message_index < len(self.messages):
                msg = self.messages[self.current_message_index]
                msg_end_time = msg["start"] + msg["duration"] + self.fade_in_duration + self.fade_out_duration + msg.get("pause", 0)
                
                if total_time < msg["start"]:
                    # This message hasn't started yet
                    break
                elif total_time >= msg_end_time:
                    # This message already finished, skip it
                    self.current_message_index += 1
                else:
                    # This message should be showing now
                    print(f"[MESSAGE] Starting message {self.current_message_index} at t={total_time:.1f}s: '{msg['text'][:30]}...'")
                    self.message_state = "fading_in"
                    self.message_timer = 0.0
                    self.current_alpha = 0.0
                    break
        
        # Update animations
        if self.message_state == "fading_in":
            self.message_timer += dt
            self.current_alpha = min(1.0, self.message_timer / self.fade_in_duration)
            if self.message_timer >= self.fade_in_duration:
                self.message_state = "showing"
                self.message_timer = 0.0
        
        elif self.message_state == "showing":
            self.message_timer += dt
            msg = self.messages[self.current_message_index]
            if self.message_timer >= msg["duration"]:
                self.message_state = "fading_out"
                self.message_timer = 0.0
        
        elif self.message_state == "fading_out":
            self.message_timer += dt
            self.current_alpha = max(0.0, 1.0 - (self.message_timer / self.fade_out_duration))
            if self.message_timer >= self.fade_out_duration:
                # Move to next message
                print(f"[MESSAGE] Completed message {self.current_message_index}: '{self.messages[self.current_message_index]['text'][:30]}...'")
                self.current_message_index += 1
                self.message_state = "idle"
                self.current_alpha = 0.0
                print(f"[MESSAGE] Now at index {self.current_message_index}/{len(self.messages)}, state={self.message_state}")
    
    def draw(self, screen, project_fn):
        """Draw current message on back wall.
        
        Args:
            screen: Main surface to draw on
            project_fn: Projection function
        """
        if self.message_state == "idle" or self.current_message_index >= len(self.messages):
            return
        
        msg = self.messages[self.current_message_index]
        text = msg["text"]
        
        # Render text with alpha
        alpha = int(self.current_alpha * 255)
        
        # Handle multi-line text
        lines = text.split('\n')
        
        # Choose font based on text length
        font = self.small_font if len(text) > 40 else self.font
        
        # Render each line
        y_offset = 0
        line_height = font.get_height()
        total_height = len(lines) * line_height
        
        # Position at top of screen on back wall (z=9.5, slightly in front of back wall at z=10)
        base_y = 1.8  # Upper portion to avoid covering flowers
        
        for i, line in enumerate(lines):
            # Create text surface
            text_surface = font.render(line, True, (255, 255, 255))
            text_surface.set_alpha(alpha)
            
            # Position at back wall center
            # Calculate vertical offset for multi-line centering
            # Negative offset because y increases upward in 3D space
            line_y = base_y - (i - len(lines)/2 + 0.5) * 0.45
            
            # Project center point
            center_3d = Point3D(0, line_y, 9.5)
            proj = project_fn(center_3d)
            
            if proj:
                sx, sy = proj[:2]
                # Center the text surface
                text_rect = text_surface.get_rect(center=(int(sx), int(sy)))
                screen.blit(text_surface, text_rect)
