"""
Retro 8-Bit Audio Engine
Uses Windows native winsound.Beep on asynchronous threads to play authentic chiptune sounds.
"""

import threading
import queue
import time
import os

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class RetroSoundEngine:
    """Threaded sound manager for 8-bit arcade sound effects."""

    def __init__(self):
        self.enabled = True
        self.queue = queue.Queue()
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def _process_queue(self):
        while self._running:
            try:
                tones = self.queue.get(timeout=0.2)
                if not self.enabled or not HAS_WINSOUND:
                    self.queue.task_done()
                    continue

                for freq, duration_ms in tones:
                    if not self.enabled:
                        break
                    try:
                        winsound.Beep(int(freq), int(duration_ms))
                    except Exception:
                        pass
                self.queue.task_done()
            except queue.Empty:
                continue

    def toggle(self):
        """Toggle sound on/off."""
        self.enabled = not self.enabled
        if self.enabled:
            self.play_powerup()
        return self.enabled

    def play_click(self):
        """Short retro click / button press."""
        if self.enabled:
            self.queue.put([(1400, 25)])

    def play_check(self):
        """Ascending two-tone for selecting an item."""
        if self.enabled:
            self.queue.put([(750, 25), (1150, 35)])

    def play_uncheck(self):
        """Descending two-tone for deselecting an item."""
        if self.enabled:
            self.queue.put([(950, 20), (600, 25)])

    def play_powerup(self):
        """Chiptune 8-bit level up / preset activation fanfare."""
        if self.enabled:
            self.queue.put([
                (523, 30),  # C5
                (659, 30),  # E5
                (784, 35),  # G5
                (1046, 60)  # C6
            ])

    def play_install_start(self):
        """Arcade coin insert / mission start sound."""
        if self.enabled:
            self.queue.put([
                (988, 40),  # B5
                (1319, 80)  # E6
            ])

    def play_success(self):
        """Mission Accomplished victory melody."""
        if self.enabled:
            self.queue.put([
                (523, 50),
                (659, 50),
                (784, 60),
                (1046, 90),
                (880, 50),
                (1046, 140)
            ])

    def play_error(self):
        """8-bit buzz / error alert."""
        if self.enabled:
            self.queue.put([
                (320, 60),
                (220, 100)
            ])


# Global singleton instance
sound = RetroSoundEngine()
