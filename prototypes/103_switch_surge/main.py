"""103_switch_surge -- Train Dispatching Color-Match Puzzle Prototype

The most fun moment:
    連続で同じ色の列車を駅に送り込み、COMBOが光って
    SURGEで一気に全列車が3倍スコアで流れ込む瞬間
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240

# pyxel palette ints
BLACK = 0
NAVY = 1
PURPLE = 2
GREEN = 3
BROWN = 4
DARK_BLUE = 5
LIGHT_BLUE = 6
WHITE = 7
RED = 8
ORANGE = 9
YELLOW = 10
LIME = 11
CYAN = 12
GRAY = 13
PINK = 14
PEACH = 15

COLORS = (RED, GREEN, DARK_BLUE, YELLOW)
COLOR_NAMES = ("RED", "GREEN", "BLUE", "YELLOW")

STATION_COLORS = (GREEN, DARK_BLUE, YELLOW, RED)  # GL, BL, YL, RD

# Track network nodes
# 0-3: stations (GL, BL, YL, RD)
# 4-5: entrances (L, R)
# 6-9: junctions (J0, J1, J2, J3)
# 10-14: waypoints (W0, W1, W2, W3, W4)
NODES: list[tuple[int, int]] = [
    (40, 60),    # 0: GL station (top-left)
    (280, 60),   # 1: BL station (top-right)
    (40, 180),   # 2: YL station (bottom-left)
    (280, 180),  # 3: RD station (bottom-right)
    (0, 120),    # 4: L entrance
    (320, 120),  # 5: R entrance
    (80, 60),    # 6: J0 junction
    (160, 60),   # 7: J1 junction
    (80, 180),   # 8: J2 junction
    (160, 180),  # 9: J3 junction
    (240, 60),   # 10: W0 waypoint
    (240, 180),  # 11: W1 waypoint
    (80, 120),   # 12: W2 waypoint
    (160, 120),  # 13: W3 waypoint
    (240, 120),  # 14: W4 waypoint
]

NUM_NODES = len(NODES)

# Edges: (node_a, node_b) for each track segment
EDGES: list[tuple[int, int]] = [
    # Horizontal y=60
    (0, 6),    # 0:  GL - J0
    (6, 7),    # 1:  J0 - J1
    (7, 10),   # 2:  J1 - W0
    (10, 1),   # 3:  W0 - BL
    # Horizontal y=120
    (4, 12),   # 4:  L entrance - W2
    (12, 13),  # 5:  W2 - W3
    (13, 14),  # 6:  W3 - W4
    (14, 5),   # 7:  W4 - R entrance
    # Horizontal y=180
    (2, 8),    # 8:  YL - J2
    (8, 9),    # 9:  J2 - J3
    (9, 11),   # 10: J3 - W1
    (11, 3),   # 11: W1 - RD
    # Vertical x=80
    (6, 12),   # 12: J0 - W2
    (12, 8),   # 13: W2 - J2
    # Vertical x=160
    (7, 13),   # 14: J1 - W3
    (13, 9),   # 15: W3 - J3
    # Vertical x=240
    (10, 14),  # 16: W0 - W4
    (14, 11),  # 17: W4 - W1
]

# Junction index -> (junction_node_id, edge_a, edge_b, edge_c)
# state=0: edge_a <-> edge_b connected, edge_c blocked
# state=1: edge_a <-> edge_c connected, edge_b blocked
JUNCTION_DEFS: list[tuple[int, int, int, int]] = [
    (6, 0, 1, 12),   # J0: edges 0(GL), 1(J1), 12(W2 dn)
    (7, 1, 2, 14),   # J1: edges 1(J0), 2(W0), 14(W3 dn)
    (8, 8, 9, 13),   # J2: edges 8(YL), 9(J3), 13(W2 up)
    (9, 9, 10, 15),  # J3: edges 9(J2), 10(W1), 15(W3 up)
]

# Station index -> color (from COLORS)
STATION_COLOR_MAP: list[int] = [GREEN, DARK_BLUE, YELLOW, RED]  # GL=0, BL=1, YL=2, RD=3

# Node types
NODE_STATION = 0
NODE_ENTRANCE = 1
NODE_JUNCTION = 2
NODE_WAYPOINT = 3

NODE_TYPES: list[int] = [
    NODE_STATION,   # 0
    NODE_STATION,   # 1
    NODE_STATION,   # 2
    NODE_STATION,   # 3
    NODE_ENTRANCE,  # 4
    NODE_ENTRANCE,  # 5
    NODE_JUNCTION,  # 6
    NODE_JUNCTION,  # 7
    NODE_JUNCTION,  # 8
    NODE_JUNCTION,  # 9
    NODE_WAYPOINT,  # 10
    NODE_WAYPOINT,  # 11
    NODE_WAYPOINT,  # 12
    NODE_WAYPOINT,  # 13
    NODE_WAYPOINT,  # 14
]

# Junction node ID -> junction index in JUNCTION_DEFS
JUNCTION_NODE_TO_IDX: dict[int, int] = {6: 0, 7: 1, 8: 2, 9: 3}

# Game balance
TRAIN_SPEED_BASE = 1.2
TRAIN_W = 10
TRAIN_H = 6
BASE_SPAWN_INTERVAL = 90  # frames
MIN_SPAWN_INTERVAL = 20
SPAWN_INTERVAL_DEC = 2
GAME_DURATION = 90  # seconds
GAME_DURATION_FRAMES = GAME_DURATION * 60
SPEED_BUMP_INTERVAL = 15  # seconds
SPEED_BUMP = 0.15

COMBO_SUPER_THRESHOLD = 4
COMBO_MULTIPLIERS = (1.0, 1.5, 2.0, 2.5)  # combo 0,1,2,3+
SURGE_DURATION = 5 * 60  # 5 seconds
SURGE_SCORE_MULT = 3.0

MAX_HEAT = 100.0
HEAT_WARN = 80.0
HEAT_BLOCK = 100.0
HEAT_PER_WRONG = 15.0
HEAT_PER_QUEUE = 0.5
HEAT_BLOCK_DURATION = 3 * 60  # 3 seconds
HEAT_RESET_AFTER_BLOCK = 50.0
STATION_COOLDOWN = 15  # frames

SCORE_BASE = 100
WRONG_PENALTY = -10

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Train:
    color: int
    target_station: int     # station node index
    path: list[int] = field(default_factory=list)  # list of node IDs to visit
    path_idx: int = 0    # index in path of current segment destination
    progress: float = 0.0  # 0.0-1.0 along current segment
    queued: bool = False
    queued_frames: int = 0


@dataclass
class Junction:
    node_id: int
    state: int = 0  # 0=straight, 1=turned


@dataclass
class Station:
    node_id: int
    color: int
    cooldown: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------
class SwitchSurge:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SWITCH SURGE", display_scale=2, fps=60)
        self._rng = random.Random()
        self._init_state()
        pyxel.run(self.update, self.draw)

    # -------------------------------------------------------------------
    # State initialization
    # -------------------------------------------------------------------
    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_DURATION_FRAMES
        self.trains_dispatched: int = 0
        self.surge_timer: int = 0
        self.block_timer: int = 0
        self.blocked_junction: int = -1
        self._spawn_timer: int = 0
        self._spawn_interval: int = BASE_SPAWN_INTERVAL
        self._speed_mult: float = 1.0
        self._shake_frames: int = 0

        self.trains: list[Train] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_trains: list[list[tuple[float, float, int]]] = []

        # Track network state
        self.junctions: list[Junction] = []
        self.stations: list[Station] = []
        self._init_track_network()

    def _init_track_network(self) -> None:
        self.junctions = [Junction(node_id=nid) for nid, _, _, _ in JUNCTION_DEFS]
        self.stations = [
            Station(node_id=i, color=STATION_COLOR_MAP[i]) for i in range(4)
        ]

    # -------------------------------------------------------------------
    # Graph / pathfinding logic
    # -------------------------------------------------------------------
    def _edge_traversable(self, edge_id: int) -> bool:
        """Check if an edge is traversable given current junction states."""
        for j_node_id, e_a, e_b, e_c in JUNCTION_DEFS:
            if edge_id not in (e_a, e_b, e_c):
                continue
            jidx = JUNCTION_NODE_TO_IDX[j_node_id]
            state = self.junctions[jidx].state
            if state == 0:
                if edge_id not in (e_a, e_b):
                    return False
            else:
                if edge_id not in (e_a, e_c):
                    return False
        return True

    def _build_adjacency(self) -> list[list[int]]:
        """Build adjacency list for BFS based on current junction states."""
        adj: list[list[int]] = [[] for _ in range(NUM_NODES)]
        for eid, (a, b) in enumerate(EDGES):
            if self._edge_traversable(eid):
                adj[a].append(b)
                adj[b].append(a)
        return adj

    def _find_path(self, start_node: int, target_node: int) -> list[int] | None:
        """BFS to find shortest path from start_node to target_node."""
        if start_node == target_node:
            return [start_node]

        adj = self._build_adjacency()
        queue: deque[int] = deque([start_node])
        visited: dict[int, int | None] = {start_node: None}

        while queue:
            node = queue.popleft()
            if node == target_node:
                break
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited[neighbor] = node
                    queue.append(neighbor)

        if target_node not in visited:
            return None

        # Reconstruct path
        path: list[int] = []
        cur = target_node
        while cur is not None:
            path.append(cur)
            cur = visited[cur]
        path.reverse()
        return path

    def _get_next_node(self, train: Train) -> int | None:
        """Get the next node the train should head toward."""
        path = train.path
        if train.path_idx + 1 < len(path):
            return path[train.path_idx + 1]
        return None

    # -------------------------------------------------------------------
    # Train spawning
    # -------------------------------------------------------------------
    def _spawn_train(self) -> None:
        color = self._rng.choice(COLORS)
        entrance = self._rng.choice([4, 5])  # node 4 (left) or 5 (right)

        # Target: the station with matching color
        # STATION_COLOR_MAP = [GREEN, DARK_BLUE, YELLOW, RED]
        # COLORS = (RED, GREEN, DARK_BLUE, YELLOW)
        # Need to find station node whose color matches
        target_station = STATION_COLOR_MAP.index(color)

        path = self._find_path(entrance, target_station)
        if path is None:
            return  # no path available; skip spawn

        train = Train(
            color=color,
            target_station=target_station,
            path=path,
            path_idx=0,
            progress=0.0,
        )
        self.trains.append(train)

    # -------------------------------------------------------------------
    # Train movement and segment geometry
    # -------------------------------------------------------------------
    def _segment_endpoints(self, node_a: int, node_b: int) -> tuple[float, float, float, float]:
        """Return (x1, y1, x2, y2) for the segment between two nodes."""
        x1, y1 = NODES[node_a]
        x2, y2 = NODES[node_b]
        return x1, y1, x2, y2

    def _segment_length(self, node_a: int, node_b: int) -> float:
        x1, y1, x2, y2 = self._segment_endpoints(node_a, node_b)
        return math.hypot(x2 - x1, y2 - y1)

    def _train_position(self, train: Train) -> tuple[float, float]:
        """Get (x, y) position of a train along its current segment."""
        path = train.path
        idx = train.path_idx
        if idx >= len(path) - 1:
            # At final node
            nx, ny = NODES[path[-1]]
            return float(nx), float(ny)
        a, b = path[idx], path[idx + 1]
        x1, y1, x2, y2 = self._segment_endpoints(a, b)
        t = train.progress
        return x1 + (x2 - x1) * t, y1 + (y2 - y1) * t

    def _train_angle(self, train: Train) -> float:
        """Direction angle in radians of the train's current segment."""
        path = train.path
        idx = train.path_idx
        if idx >= len(path) - 1:
            return 0.0
        a, b = path[idx], path[idx + 1]
        x1, y1, x2, y2 = self._segment_endpoints(a, b)
        return math.atan2(y2 - y1, x2 - x1)

    # -------------------------------------------------------------------
    # Train arrival and scoring logic
    # -------------------------------------------------------------------
    def _handle_arrival(self, train: Train, station: Station) -> None:
        train_color = train.color
        station_color = station.color

        if self._is_surge():
            # SURGE mode: all arrivals count as correct, 3x score
            multiplier = COMBO_MULTIPLIERS[min(self.combo, len(COMBO_MULTIPLIERS) - 1)]
            points = int(SCORE_BASE * multiplier * SURGE_SCORE_MULT)
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.trains_dispatched += 1
            self.score += points
            self._spawn_arrival_particles(train, True)
            self._spawn_floating_text(train, f"+{points}", YELLOW)
            # Record ghost
            self._record_ghost(train)
            # Station cooldown
            station.cooldown = STATION_COOLDOWN
        elif train_color == station_color:
            # Correct match
            multiplier = COMBO_MULTIPLIERS[min(self.combo, len(COMBO_MULTIPLIERS) - 1)]
            points = int(SCORE_BASE * multiplier)
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.trains_dispatched += 1
            self.score += points
            self._spawn_arrival_particles(train, True)
            self._spawn_floating_text(train, f"+{points}", LIME)
            self._record_ghost(train)
            station.cooldown = STATION_COOLDOWN

            # Check SURGE trigger
            if self.combo >= COMBO_SUPER_THRESHOLD and self.surge_timer == 0:
                self.surge_timer = SURGE_DURATION
                self._spawn_floating_text(train, "SURGE!", YELLOW)
        else:
            # Wrong arrival
            self.score += WRONG_PENALTY
            self.heat = min(self.heat + HEAT_PER_WRONG, MAX_HEAT)
            self.combo = 0
            self._spawn_arrival_particles(train, False)
            self._spawn_floating_text(train, f"{WRONG_PENALTY}", RED)
            station.cooldown = STATION_COOLDOWN

    def _record_ghost(self, train: Train) -> None:
        """Record the train's path as a ghost trail."""
        points: list[tuple[float, float, int]] = []
        path = train.path
        for i in range(len(path)):
            nx, ny = NODES[path[i]]
            points.append((float(nx), float(ny), train.color))
        self.ghost_trains.append(points)
        if len(self.ghost_trains) > 3:
            self.ghost_trains.pop(0)

    def _spawn_arrival_particles(self, train: Train, success: bool) -> None:
        x, y = self._train_position(train)
        count = 8 if success else 4
        color = train.color if success else ORANGE
        for _ in range(count):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-1.5, 1.5)
            life = self._rng.randint(15, 30)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, max_life=life, color=color)
            )

    def _spawn_floating_text(self, train: Train, text: str, color: int) -> None:
        x, y = self._train_position(train)
        self.floating_texts.append(
            FloatingText(x=x, y=y - 8, text=text, life=45, color=color)
        )

    # -------------------------------------------------------------------
    # Update methods
    # -------------------------------------------------------------------
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._init_state()
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE):
            self._init_state()
            self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1

        self._update_timer()
        self._update_spawning()
        self._handle_input()
        self._update_trains()
        self._update_arrivals()
        self._update_surge()
        self._update_heat_block()
        self._update_particles()
        self._update_floating_texts()
        self._update_station_cooldowns()
        self._check_game_over()

    def _update_timer(self) -> None:
        self.timer -= 1
        elapsed = GAME_DURATION_FRAMES - self.timer
        bumps = elapsed // (SPEED_BUMP_INTERVAL * 60)
        self._speed_mult = 1.0 + bumps * SPEED_BUMP

    def _update_spawning(self) -> None:
        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            self._spawn_train()
            self._spawn_interval = max(MIN_SPAWN_INTERVAL, self._spawn_interval - SPAWN_INTERVAL_DEC)
            self._spawn_timer = self._spawn_interval

    def _handle_input(self) -> None:
        if self.block_timer > 0:
            return  # can't toggle during track block
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            for jn in self.junctions:
                jx, jy = NODES[jn.node_id]
                if math.hypot(mx - jx, my - jy) < 10:
                    jn.state = 1 - jn.state  # toggle 0<->1
                    self._recompute_all_paths()

    def _recompute_all_paths(self) -> None:
        """Recompute paths for all trains."""
        for train in self.trains:
            if train.queued:
                continue
            pos_node = train.path[train.path_idx]
            if train.progress > 0.5:
                pos_node = train.path[train.path_idx + 1] if train.path_idx + 1 < len(train.path) else pos_node
            new_path = self._find_path(pos_node, train.target_station)
            if new_path is not None:
                train.path = new_path
                train.path_idx = 0
                train.progress = 0.0

    def _update_trains(self) -> None:
        speed = TRAIN_SPEED_BASE * self._speed_mult

        for train in self.trains:
            if train.queued:
                train.queued_frames += 1
                self.heat = min(self.heat + HEAT_PER_QUEUE, MAX_HEAT)
                continue

            path = train.path
            if train.path_idx >= len(path) - 1:
                continue  # already at destination, waiting for arrival processing

            a = path[train.path_idx]
            b = path[train.path_idx + 1]
            seg_len = self._segment_length(a, b)
            if seg_len <= 0:
                train.path_idx += 1
                train.progress = 0.0
                continue

            train.progress += speed / seg_len

            if train.progress >= 1.0:
                # Overshoot handling
                overflow = train.progress - 1.0
                train.path_idx += 1
                train.progress = 0.0
                # Check next segment to apply overshoot
                if train.path_idx < len(path) - 1:
                    na = path[train.path_idx]
                    nb = path[train.path_idx + 1]
                    next_len = self._segment_length(na, nb)
                    if next_len > 0:
                        train.progress = min(1.0, overflow * speed / next_len)

    def _update_arrivals(self) -> None:
        """Check for trains that have reached the end of their path."""
        to_remove: list[int] = []

        for i, train in enumerate(self.trains):
            if train.queued:
                # Check if station cooldown expired
                last_node = train.path[-1]
                for stn in self.stations:
                    if stn.node_id == last_node:
                        if stn.cooldown <= 0:
                            self._handle_arrival(train, stn)
                            to_remove.append(i)
                        break
                continue

            path = train.path
            if train.path_idx >= len(path) - 1:
                last_node = path[-1]
                # Check if it's a station
                if NODE_TYPES[last_node] == NODE_STATION:
                    stn = self.stations[last_node]
                    if stn.cooldown > 0:
                        train.queued = True
                        train.queued_frames = 0
                        # Spawn waiting particles
                        wx, wy = NODES[last_node]
                        self.particles.append(
                            Particle(x=float(wx), y=float(wy), vx=0.0, vy=0.0,
                                     life=30, max_life=30, color=GRAY)
                        )
                    else:
                        self._handle_arrival(train, stn)
                        to_remove.append(i)
                else:
                    # Train reached a non-station endpoint (shouldn't happen)
                    to_remove.append(i)

        for i in reversed(to_remove):
            if i < len(self.trains):
                self.trains.pop(i)

    def _update_surge(self) -> None:
        if self.surge_timer > 0:
            self.surge_timer -= 1
            # Spawn rainbow particles during SURGE
            if self.surge_timer % 10 == 0:
                for _ in range(3):
                    rx = self._rng.uniform(0, SCREEN_W)
                    ry = self._rng.uniform(0, SCREEN_H)
                    rc = COLORS[self._rng.randint(0, 3)]
                    self.particles.append(
                        Particle(x=rx, y=ry, vx=0.0, vy=0.0,
                                 life=20, max_life=20, color=rc)
                    )

    def _update_heat_block(self) -> None:
        if self.block_timer > 0:
            self.block_timer -= 1
            if self.block_timer == 0:
                self.heat = HEAT_RESET_AFTER_BLOCK
                self.blocked_junction = -1
                self._recompute_all_paths()
            return

        if self.heat >= HEAT_BLOCK:
            self.block_timer = HEAT_BLOCK_DURATION
            self.blocked_junction = self._rng.choice([jn.node_id for jn in self.junctions])
            # Lock the blocked junction
            for jn in self.junctions:
                if jn.node_id == self.blocked_junction:
                    # Force a state that might cause issues, and block input
                    break
            self._recompute_all_paths()

    def _update_station_cooldowns(self) -> None:
        for stn in self.stations:
            if stn.cooldown > 0:
                stn.cooldown -= 1

    def _update_particles(self) -> None:
        new_particles: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.03  # slight gravity
            p.life -= 1
            if p.life > 0:
                new_particles.append(p)
        self.particles = new_particles

    def _update_floating_texts(self) -> None:
        new_texts: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                new_texts.append(ft)
        self.floating_texts = new_texts

    def _check_game_over(self) -> None:
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _is_surge(self) -> bool:
        return self.surge_timer > 0

    # -------------------------------------------------------------------
    # Draw methods
    # -------------------------------------------------------------------
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "SWITCH SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 40, title, YELLOW)

        subtitle = "Train Dispatching Puzzle"
        sw = len(subtitle) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 55, subtitle, WHITE)

        lines = [
            "Click junctions to switch tracks",
            "Route trains to same-color stations",
            "Chain same colors = COMBO up!",
            "COMBO x4 = SURGE (auto-match 3x!)",
            "Wrong arrival = score -10 + HEAT",
            "HEAT 100% = TRACK BLOCK",
            "",
            "SPACE or ENTER: Start",
            "R: Restart anytime",
        ]
        for i, line in enumerate(lines):
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, 90 + i * 14, line, GRAY)

    def _draw_playing(self) -> None:
        # Screen shake
        sx = 0
        sy = 0
        if self._shake_frames > 0:
            sx = self._rng.randint(-2, 2)
            sy = self._rng.randint(-2, 2)

        self._draw_tracks(sx, sy)
        self._draw_ghost_trains(sx, sy)
        self._draw_stations(sx, sy)
        self._draw_junctions(sx, sy)
        self._draw_trains(sx, sy)
        self._draw_particles(sx, sy)
        self._draw_floating_texts(sx, sy)
        self._draw_hud()
        self._draw_surge_overlay()

    def _draw_tracks(self, sx: int, sy: int) -> None:
        for eid, (a, b) in enumerate(EDGES):
            x1, y1 = NODES[a]
            x2, y2 = NODES[b]
            if self._edge_traversable(eid):
                col = GRAY
            else:
                col = NAVY  # blocked/untraversable
            pyxel.line(int(x1 + sx), int(y1 + sy), int(x2 + sx), int(y2 + sy), col)

    def _draw_ghost_trains(self, sx: int, sy: int) -> None:
        for ghost in self.ghost_trains:
            for i in range(len(ghost) - 1):
                x1, y1, col = ghost[i]
                x2, y2, _ = ghost[i + 1]
                # Draw faint dotted line
                if i % 2 == 0:
                    pyxel.line(int(x1 + sx), int(y1 + sy), int(x2 + sx), int(y2 + sy), NAVY)

    def _draw_stations(self, sx: int, sy: int) -> None:
        for stn in self.stations:
            nx, ny = NODES[stn.node_id]
            px = nx + sx
            py_ = ny + sy
            # Station square
            pyxel.rect(int(px) - 6, int(py_) - 6, 12, 12, stn.color)
            pyxel.rectb(int(px) - 6, int(py_) - 6, 12, 12, WHITE)
            # Cooldown indicator
            if stn.cooldown > 0:
                cd = stn.cooldown
                alpha = cd / STATION_COOLDOWN
                ring_radius = int(9 * (1.0 - alpha))
                pyxel.circb(int(px), int(py_), ring_radius, GRAY)

    def _draw_junctions(self, sx: int, sy: int) -> None:
        for jn in self.junctions:
            jx, jy = NODES[jn.node_id]
            px = jx + sx
            py_ = jy + sy
            # Junction circle
            if self.blocked_junction == jn.node_id and self.block_timer > 0:
                col = RED
            elif self._is_surge():
                col = YELLOW
            elif jn.state == 0:
                col = WHITE
            else:
                col = GRAY
            pyxel.circ(int(px), int(py_), 6, col)
            pyxel.circb(int(px), int(py_), 6, WHITE)

            # Draw a small indicator of state
            if jn.state == 0:
                pyxel.line(int(px) - 3, int(py_), int(px) + 3, int(py_), BLACK)
            else:
                pyxel.line(int(px), int(py_) - 3, int(px), int(py_) + 3, BLACK)

    def _draw_trains(self, sx: int, sy: int) -> None:
        for train in self.trains:
            if train.queued:
                continue
            px, py_ = self._train_position(train)
            angle = self._train_angle(train)
            dx = px + sx
            dy = py_ + sy

            # Train body
            col = train.color
            if self._is_surge():
                col = COLORS[(pyxel.frame_count // 8) % len(COLORS)]

            # Draw rotated rectangle approximation
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            hw = TRAIN_W / 2
            hh = TRAIN_H / 2

            # Four corners
            corners = [
                (-hw, -hh),
                (hw, -hh),
                (hw, hh),
                (-hw, hh),
            ]
            pts = []
            for cx, cy in corners:
                rx = cx * cos_a - cy * sin_a + dx
                ry = cx * sin_a + cy * cos_a + dy
                pts.append((int(rx), int(ry)))

            # Simple rectangle fill
            pyxel.tri(pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1], col)
            pyxel.tri(pts[0][0], pts[0][1], pts[2][0], pts[2][1], pts[3][0], pts[3][1], col)

            # Direction indicator
            fwd_x = dx + cos_a * hw * 0.6
            fwd_y = dy + sin_a * hw * 0.6
            pyxel.circ(int(fwd_x), int(fwd_y), 2, WHITE)

    def _draw_particles(self, sx: int, sy: int) -> None:
        for p in self.particles:
            alpha = p.life / max(p.max_life, 1)
            if alpha > 0.3:
                c = p.color
            else:
                c = GRAY
            pyxel.pset(int(p.x + sx), int(p.y + sy), c)

    def _draw_floating_texts(self, sx: int, sy: int) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                alpha = ft.life / 45.0
                if alpha > 0.3:
                    pyxel.text(
                        int(ft.x + sx) - len(ft.text) * 2,
                        int(ft.y + sy),
                        ft.text,
                        ft.color,
                    )

    def _draw_hud(self) -> None:
        # Timer
        seconds = self.timer // 60
        ttext = f"TIME:{seconds:02d}"
        pyxel.text(4, 2, ttext, WHITE)

        # Score
        stext = f"SCORE:{self.score}"
        pyxel.text(SCREEN_W - len(stext) * 4 - 4, 2, stext, YELLOW)

        # COMBO center-top
        if self.combo > 0:
            ctext = f"COMBO x{self.combo}"
            cw = len(ctext) * 4
            cc = LIME
            if self.combo >= COMBO_SUPER_THRESHOLD:
                cc = YELLOW
            pyxel.text(SCREEN_W // 2 - cw // 2, 2, ctext, cc)

        # HEAT bar bottom-left
        bar_x = 4
        bar_y = SCREEN_H - 10
        bar_w = 80
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        fill_w = int(bar_w * self.heat / MAX_HEAT)
        if self.heat >= HEAT_BLOCK:
            hc = RED
        elif self.heat >= HEAT_WARN:
            hc = ORANGE
        elif self.heat >= 50:
            hc = YELLOW
        else:
            hc = GREEN
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, hc)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", GRAY)

        # Block indicator
        if self.block_timer > 0:
            btext = f"BLOCK:{self.block_timer // 60}s"
            pyxel.text(bar_x + bar_w + 4, bar_y + 8, btext, RED)

        # Max combo
        mtext = f"BEST:{self.max_combo}"
        pyxel.text(SCREEN_W - len(mtext) * 4 - 4, SCREEN_H - 10, mtext, GRAY)

        # Trains dispatched
        dtext = f"TRAINS:{self.trains_dispatched}"
        pyxel.text(SCREEN_W // 2 - len(dtext) * 2, SCREEN_H - 10, dtext, WHITE)

    def _draw_surge_overlay(self) -> None:
        if self.surge_timer > 0:
            # Rainbow border
            ci = (pyxel.frame_count // 8) % len(COLORS)
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, COLORS[ci])
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, COLORS[(ci + 1) % len(COLORS)])

            # SURGE text
            stext = f"SURGE! {self.surge_timer // 60 + 1}s"
            sw2 = len(stext) * 4
            pyxel.text(SCREEN_W // 2 - sw2 // 2, 14, stext, YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 20, 50, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 30, 80, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 40, 95, f"MAX COMBO: {self.max_combo}", ORANGE)
        pyxel.text(SCREEN_W // 2 - 45, 110, f"TRAINS DISPATCHED: {self.trains_dispatched}", GRAY)
        surge_str = f"x{COMBO_SUPER_THRESHOLD}" if self.max_combo >= COMBO_SUPER_THRESHOLD else "NO"
        pyxel.text(SCREEN_W // 2 - 45, 125, f"SURGE REACHED: {surge_str}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 45, 160, "R or SPACE: Retry", GRAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    SwitchSurge()


if __name__ == "__main__":
    main()
