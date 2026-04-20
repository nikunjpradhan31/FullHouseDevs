import cv2
from dataclasses import dataclass
from typing import Callable
import socket
import struct

from ultralytics import YOLO

# Broadcast settings
BROADCAST_HOST = "localhost"
BROADCAST_PORT = 9999

#added for kafka for the ability to send card detection to game state manager
#singular call when a card is locked in
from core.kafka import send_card_detection
import time


# ------------------------------------------------------------------
# Tunable constants
# ------------------------------------------------------------------

MODEL_PATH = "./cv_models/yolo26n_640.onnx"

LOCK_FRAMES = 5            # consecutive frames before a card is locked in
DEALER_ZONE_RATIO = 0.40    # top 35% of frame height belongs to the dealer zone
MATCH_THRESHOLD_PX = 200     # max pixel distance to match same card across frames
CONFIDENCE_THRESHOLD = 0.3

# Corner-pairing constants (two bounding boxes per physical card)
PAIR_MIN_DISTANCE_PX = 10   # corners closer than this are treated as duplicates
PAIR_MAX_DISTANCE_PX = 400  # corners farther than this belong to different cards

# OpenCV capture resolution — camera hardware is forced to this resolution
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720


# ------------------------------------------------------------------
# Internal tracking dataclass
# ------------------------------------------------------------------

@dataclass
class _Candidate:
    """A card detection that has not yet been locked in."""
    label: str
    cx: float   # bounding box center x (pixels)
    cy: float   # bounding box center y (pixels)
    consecutive_frames: int = 1


# ------------------------------------------------------------------
# CV Pipeline
# ------------------------------------------------------------------

class CVPipeline:
    """
    Real-time card detection pipeline.

    Runs YOLO inference on a video source, assigns each detection to a
    spatial zone (dealer = top strip, players = horizontal bands along the
    bottom with player_1 at the right and player_N at the left), and uses
    frame-count debouncing to lock in a card only after it has been seen in
    the same location for LOCK_FRAMES consecutive frames.

    Once locked, a card is never re-evaluated until reset() is called.

    Args:
        num_players:      Number of player zones below the dealer zone.
        on_state_update:  Callback invoked each time a new card is locked in.
                          Receives a snapshot of the full game-state dict,
                          e.g. {"dealer": ["Ah"], "player_1": ["6s", "2d"]}.
        model_path:       Path to the YOLO .onnx or .pt model file.
        source:           Video source — 0 for default webcam, or a file path string.
        confidence:       Minimum YOLO confidence score to consider a detection.
        capture_width:    Camera hardware capture width in pixels.
        capture_height:   Camera hardware capture height in pixels.
    """

    def __init__(
        self,
        num_players: int,
        on_state_update: Callable[[dict[str, list[str]]], None],
        model_path: str = MODEL_PATH,
        source: int | str = 0,
        confidence: float = CONFIDENCE_THRESHOLD,
        capture_width: int = CAPTURE_WIDTH,
        capture_height: int = CAPTURE_HEIGHT,
    ) -> None:
        self.model = YOLO(model_path)
        self.num_players = num_players
        self.on_state_update = on_state_update
        self.source = source
        self.confidence = confidence
        self.capture_width = capture_width
        self.capture_height = capture_height

        self._game_state: dict[str, list[str]] = self._fresh_state()
        self._candidates: list[_Candidate] = []
        self._locked: list[tuple[str, float, float]] = []  # (label, cx, cy)

        # ----------------------------------------------------------
        # Webcam broadcast server (for Tkinter client)
        # ----------------------------------------------------------

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((BROADCAST_HOST, BROADCAST_PORT))
        self.server_socket.listen(1)

        print(f"Waiting for GUI client at {BROADCAST_HOST}:{BROADCAST_PORT}...")
        self.conn, addr = self.server_socket.accept()
        print(f"GUI client connected: {addr}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Start the pipeline using OpenCV for capture. Blocks until the source
        ends or the user presses 'q'.

        The camera hardware is forced to CAPTURE_WIDTH x CAPTURE_HEIGHT so that
        zone boundaries are computed against the true capture resolution.
        YOLO inference runs at imgsz=640 internally (faster), and bounding box
        coordinates are automatically rescaled back to the capture resolution.
        """
        cap = cv2.VideoCapture(self.source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.capture_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.capture_height)

        if not cap.isOpened():
            print("Error: Could not open video source.")
            return

        print("Starting Blackjack Analyzer... Press 'q' to quit.")

        try:
            while True:
                success, frame = cap.read()
                if not success:
                    print("Failed to grab frame.")
                    break

                frame_height, frame_width = frame.shape[:2]

                # Run YOLO inference on the captured frame
                results = self.model.predict(
                    source=frame,
                    imgsz=640,
                    verbose=False,
                    conf=self.confidence,
                )
                result = results[0]

                # Process detections for debouncing and zone assignment
                self._process_frame(result, frame_height, frame_width)

                # Draw YOLO annotations then our zone overlay on top
                annotated = result.plot()
                self._draw_debug_overlay(annotated, frame_height, frame_width)
                # broadcast frame to Tkinter GUI
                self._broadcast_frame(annotated)
                cv2.imshow("Blackjack Analyzer", annotated)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

            try:
                self.conn.close()
                self.server_socket.close()
            except Exception:
                pass

    print("Pipeline stopped.")

    def reset(self) -> None:
        """Clear all game state and tracking. Call this between hands."""
        self._game_state = self._fresh_state()
        self._candidates = []
        self._locked = []
        print("[RESET] Game state cleared.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fresh_state(self) -> dict[str, list[str]]:
        state: dict[str, list[str]] = {"dealer": []}
        for i in range(1, self.num_players + 1):
            state[f"player_{i}"] = []
        return state
    
    # For Broadcasting
    def _broadcast_frame(self, frame):
        """
        Send the annotated frame to the Tkinter GUI client.
        """
        try:
            _, jpeg = cv2.imencode('.jpg', frame)
            data = jpeg.tobytes()

            # send frame length first
            self.conn.sendall(struct.pack("!I", len(data)))
            self.conn.sendall(data)

        except Exception:
            # client disconnected
            pass

    def _zone_for(self, cy: float, cx: float, frame_height: int, frame_width: int) -> str:
        """
        Return the zone name for a card whose midpoint is at (cx, cy).

        Layout:
            Top DEALER_ZONE_RATIO of the frame (full width) → "dealer"
            Bottom (1 - DEALER_ZONE_RATIO) of the frame, divided into N equal
            vertical bands left-to-right → "player_N" ... "player_1"

            Player 1 is the rightmost band; Player N is the leftmost band.

        Example with 3 players (frame 1920×1080):
            ┌────────────────────────────────────────────────────┐  y = 0
            │                     dealer                         │
            ├──────────────────┬─────────────────┬───────────────┤  y = 378
            │    player_3      │    player_2     │   player_1    │
            └──────────────────┴─────────────────┴───────────────┘  y = 1080
             x = 0            x = 640           x = 1280       x = 1920
        """
        if cy / frame_height < DEALER_ZONE_RATIO:
            return "dealer"
        slot_width = frame_width / self.num_players
        idx_from_left = min(int(cx / slot_width), self.num_players - 1)
        player_num = self.num_players - idx_from_left  # rightmost slot = player_1
        return f"player_{player_num}"

    def _pair_corners(
        self, raw: list[tuple[str, float, float]], frame_height: int, frame_width: int
    ) -> list[tuple[str, float, float, str]]:
        """
        The YOLO model emits two bounding boxes per physical card — one for each
        corner index (rank/suit printed at opposite corners of the card).

        This method groups raw detections by label, pairs the two corners of each
        card by proximity, and returns one merged detection per card whose position
        is the midpoint of the two corners. Unpaired corners (only one corner
        visible) are discarded.

        Returns a list of (label, mid_cx, mid_cy, zone).
        """
        # Group raw detections by label: label -> [(index, cx, cy)]
        by_label: dict[str, list[tuple[int, float, float]]] = {}
        for i, (label, cx, cy) in enumerate(raw):
            by_label.setdefault(label, []).append((i, cx, cy))

        merged: list[tuple[str, float, float, str]] = []

        for label, points in by_label.items():
            used: set[int] = set()

            for j in range(len(points)):
                if j in used:
                    continue
                _, cx1, cy1 = points[j]
                best_k, best_dist = -1, float("inf")

                for k in range(len(points)):
                    if k == j or k in used:
                        continue
                    _, cx2, cy2 = points[k]
                    dist = ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5
                    if PAIR_MIN_DISTANCE_PX <= dist <= PAIR_MAX_DISTANCE_PX and dist < best_dist:
                        best_k, best_dist = k, dist

                if best_k == -1:
                    # Only one corner visible — not enough to confirm the card
                    continue

                used.add(j)
                used.add(best_k)
                _, cx2, cy2 = points[best_k]
                mid_cx = (cx1 + cx2) / 2
                mid_cy = (cy1 + cy2) / 2
                zone = self._zone_for(mid_cy, mid_cx, frame_height, frame_width)
                merged.append((label, mid_cx, mid_cy, zone))

        return merged

    def _draw_debug_overlay(self, frame, frame_height: int, frame_width: int) -> None:
        """
        Draw zone boundary lines and labels onto the frame in-place.

        Green horizontal line  — dealer / player boundary
        Green vertical lines   — player zone boundaries
        Zone labels            — printed in the top-left corner of each zone
        """
        color = (0, 255, 0)
        font = cv2.FONT_HERSHEY_SIMPLEX

        dealer_y = int(DEALER_ZONE_RATIO * frame_height)
        slot_width = frame_width / self.num_players

        # Horizontal dealer boundary
        cv2.line(frame, (0, dealer_y), (frame_width, dealer_y), color, 2)

        # Vertical player zone boundaries
        for i in range(1, self.num_players):
            x = int(slot_width * i)
            cv2.line(frame, (x, dealer_y), (x, frame_height), color, 2)

        # Dealer label
        cv2.putText(frame, "DEALER", (10, max(dealer_y - 10, 20)), font, 0.8, color, 2)

        # Player labels — rightmost slot = player_1
        for i in range(self.num_players):
            player_num = self.num_players - i
            x_label = int(slot_width * i) + 10
            cv2.putText(frame, f"PLAYER {player_num}", (x_label, dealer_y + 30), font, 0.8, color, 2)

    def _is_locked(self, label: str, cx: float, cy: float) -> bool:
        """
        Return True if a locked card with the same label already exists within
        MATCH_THRESHOLD_PX of (cx, cy).

        Using position rather than label alone allows multiple physical cards of
        the same rank/suit (multi-deck games) to each be detected and locked
        independently, as long as they sit at different locations on the table.
        """
        for locked_label, locked_cx, locked_cy in self._locked:
            if locked_label != label:
                continue
            dist = ((cx - locked_cx) ** 2 + (cy - locked_cy) ** 2) ** 0.5
            if dist < MATCH_THRESHOLD_PX:
                return True
        return False

    def _process_frame(self, result, frame_height: int, frame_width: int) -> None:
        # --- Parse raw YOLO boxes into (label, cx, cy) ---------------------
        raw: list[tuple[str, float, float]] = []
        for box in result.boxes:
            if float(box.conf[0]) < self.confidence:
                continue
            label = result.names[int(box.cls[0])]
            cx, cy = float(box.xywh[0][0]), float(box.xywh[0][1])
            raw.append((label, cx, cy))

        # --- Pair corners → one merged detection per physical card ---------
        # Zone is assigned from the midpoint, not the individual corners
        paired = self._pair_corners(raw, frame_height, frame_width)

        # --- Skip detections that match an already-locked card by position --
        detections: list[tuple[str, float, float, str]] = [
            (label, cx, cy, zone)
            for label, cx, cy, zone in paired
            if not self._is_locked(label, cx, cy)
        ]

        # --- Match existing candidates to detections in this frame ---------
        used: set[int] = set()      # detection indices already claimed
        surviving: list[_Candidate] = []

        for candidate in self._candidates:
            best_idx, best_dist = -1, float("inf")

            for i, (label, cx, cy, _) in enumerate(detections):
                if i in used or label != candidate.label:
                    continue
                dist = ((cx - candidate.cx) ** 2 + (cy - candidate.cy) ** 2) ** 0.5
                if dist < MATCH_THRESHOLD_PX and dist < best_dist:
                    best_idx, best_dist = i, dist

            if best_idx == -1:
                # Card not seen this frame — consecutive streak broken, drop it
                continue

            used.add(best_idx)
            label, cx, cy, zone = detections[best_idx]
            candidate.cx, candidate.cy = cx, cy
            candidate.consecutive_frames += 1

            if candidate.consecutive_frames >= LOCK_FRAMES:
                # Lock the card in by position — add to game state, never track again
                self._locked.append((label, candidate.cx, candidate.cy))
                self._game_state[zone].append(label)

                #send to kafka
                send_card_detection(label, zone, time.time())

                print(f"[LOCKED] {label} -> {zone} | state: {self._game_state}")
                self.on_state_update({k: list(v) for k, v in self._game_state.items()})
            else:
                surviving.append(candidate)

        # --- Spawn new candidates for detections that had no match ---------
        for i, (label, cx, cy, _) in enumerate(detections):
            if i not in used:
                surviving.append(_Candidate(label=label, cx=cx, cy=cy))

        self._candidates = surviving


# ------------------------------------------------------------------
# Callback and entry point
# ------------------------------------------------------------------

def _on_state_update(state: dict[str, list[str]]) -> None:
    """Default callback — prints the full game state whenever a card locks in."""
    print(f"[STATE UPDATE] {state}")


if __name__ == "__main__":
    pipeline = CVPipeline(
        num_players=1,
        on_state_update=_on_state_update,
        source=0,       # 0 = default webcam; pass a file path string for a video file
    )
    pipeline.run()
