import pyxel
import random
import math
from dataclasses import dataclass
from collections import deque

SCREEN_W = 320
SCREEN_H = 240
COLS = 8
ROWS = 6
CELL_SIZE = 28
GRID_X = 36
GRID_Y = 60

BLACK = 0
NAVY = 1
GREEN = 3
DARK_BLUE = 5
WHITE = 7
RED = 8
YELLOW = 10
CYAN = 12
GRAY = 13
LIME = 11
ORANGE = 9
PURPLE = 2

DATA_COLORS: list[int] = [RED, GREEN, CYAN, YELLOW]
DATA_COLOR_NAMES = ["RED", "GREEN", "CYAN", "YELLOW"]
NUM_DATA_COLORS = len(DATA_COLORS)

ICE_COLOR = GRAY
FIREWALL_COLOR = DARK_BLUE

HACK_DURATION = 0.3
SURGE_DELAY = 0.08
TRACE_RATE = 1.0
TRACE_PENALTY = 5.0
ICE_TRACE_RATE = 0.3
SURGE_THRESHOLD = 4
TRACE_MAX = 100.0

PHASE_TITLE = 0
PHASE_PLAYING = 1
PHASE_SURGE_ANIM = 2
PHASE_GAME_OVER = 3
PHASE_VICTORY = 4

DIRECTIONS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


@dataclass
class Node:
    col: int
    row: int
    node_type: int  # 0=DATA, 1=ICE, 2=FIREWALL
    color: int  # 0-3 for DATA, -1 for ICE/FIREWALL
    hacked: bool = False
    hacking: bool = False
    hack_progress: float = 0.0

    @property
    def is_data(self) -> bool:
        return self.node_type == 0

    @property
    def is_ice(self) -> bool:
        return self.node_type == 1

    @property
    def is_firewall(self) -> bool:
        return self.node_type == 2


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    max_life: int = 20


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int
    max_life: int = 30


@dataclass
class SurgeStep:
    col: int
    row: int
    delay: float = 0.0


class Game:
    def __init__(self) -> None:
        self._rng = random.Random()
        self._init_state()
        pyxel.init(SCREEN_W, SCREEN_H, title="NETWORK SURGE", display_scale=2)
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase = PHASE_TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.trace = 0.0
        self.nodes_hacked = 0
        self.total_data_nodes = 0
        self.seed_val = 0
        self.grid: list[list[Node | None]] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.surge_queue: list[SurgeStep] = []
        self.surge_timer = 0.0
        self._shake_frames = 0
        self._shake_x = 0.0
        self._shake_y = 0.0
        self._hovered_col = -1
        self._hovered_row = -1
        self._hacking_node: tuple[int, int] | None = None
        self._hack_timer = 0.0
        self._surge_source_color: int = -1
        self._frame_count = 0

    def _generate_grid(self) -> None:
        self._rng.seed(self.seed_val)
        self.grid = [[None] * COLS for _ in range(ROWS)]

        positions = [(c, r) for r in range(ROWS) for c in range(COLS)]
        self._rng.shuffle(positions)

        num_ice = self._rng.randint(6, 8)
        num_firewall = self._rng.randint(4, 6)

        idx = 0
        for i in range(num_ice):
            if idx < len(positions):
                c, r = positions[idx]
                self.grid[r][c] = Node(col=c, row=r, node_type=1, color=-1)
                idx += 1

        for i in range(num_firewall):
            if idx < len(positions):
                c, r = positions[idx]
                self.grid[r][c] = Node(col=c, row=r, node_type=2, color=-1)
                idx += 1

        self.total_data_nodes = 0
        for i in range(idx, len(positions)):
            c, r = positions[i]
            color = self._rng.randint(0, NUM_DATA_COLORS - 1)
            self.grid[r][c] = Node(col=c, row=r, node_type=0, color=color)
            self.total_data_nodes += 1

    def update(self) -> None:
        self._frame_count += 1
        if self.phase == PHASE_TITLE:
            self._update_title()
        elif self.phase == PHASE_PLAYING:
            self._update_playing()
        elif self.phase == PHASE_SURGE_ANIM:
            self._update_surge_anim()
        elif self.phase == PHASE_GAME_OVER:
            self._update_game_over()
        elif self.phase == PHASE_VICTORY:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.trace = 0.0
        self.nodes_hacked = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.surge_queue.clear()
        self.surge_timer = 0.0
        self._shake_frames = 0
        self._hacking_node = None
        self._hack_timer = 0.0
        self._surge_source_color = -1
        self.phase = PHASE_PLAYING
        self._generate_grid()

    def _update_playing(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        self._hovered_col, self._hovered_row = self._get_grid_cell(mx, my)

        self.trace += TRACE_RATE * (1.0 / 60.0)
        for r in range(ROWS):
            for c in range(COLS):
                node = self.grid[r][c]
                if node is not None and node.is_ice:
                    self.trace += ICE_TRACE_RATE * (1.0 / 60.0)

        if self.trace >= TRACE_MAX:
            self.trace = TRACE_MAX
            self.phase = PHASE_GAME_OVER
            self._spawn_game_over_particles()
            return

        if self._hacking_node is not None:
            hc, hr = self._hacking_node
            node = self.grid[hr][hc]
            if node is not None:
                self._hack_timer -= 1.0 / 60.0
                node.hack_progress = max(0.0, self._hack_timer / HACK_DURATION)
                if self._hack_timer <= 0:
                    self._finish_hack(node)
                    self._hacking_node = None
            else:
                self._hacking_node = None
                self._hack_timer = 0.0
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(self._hovered_col, self._hovered_row)

        self._update_particles()
        self._update_floating_texts()
        self._update_shake()

    def _handle_click(self, col: int, row: int) -> None:
        if col < 0 or row < 0 or col >= COLS or row >= ROWS:
            return
        node = self.grid[row][col]
        if node is None or node.hacked:
            return

        if node.is_ice or node.is_firewall:
            self._add_floating_text(
                node.col * CELL_SIZE + GRID_X + CELL_SIZE // 2,
                node.row * CELL_SIZE + GRID_Y + CELL_SIZE // 2,
                "BLOCKED",
                RED,
            )
            self.trace = min(TRACE_MAX, self.trace + 2.0)
            return

        if node.is_data and not node.hacked:
            if self.combo > 0 and node.color != self._surge_source_color:
                self.combo = 0
                self.trace = min(TRACE_MAX, self.trace + TRACE_PENALTY)
                self._add_floating_text(
                    node.col * CELL_SIZE + GRID_X + CELL_SIZE // 2,
                    node.row * CELL_SIZE + GRID_Y + CELL_SIZE // 2,
                    "RESET +5%",
                    RED,
                )

            self._surge_source_color = node.color
            node.hacking = True
            self._hacking_node = (col, row)
            self._hack_timer = HACK_DURATION
            node.hack_progress = 0.0

    def _finish_hack(self, node: Node) -> None:
        node.hacked = True
        node.hacking = False
        node.hack_progress = 0.0
        self.nodes_hacked += 1
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        base_score = 100
        multiplier = max(1, self.combo)
        self.score += base_score * multiplier

        cx = node.col * CELL_SIZE + GRID_X + CELL_SIZE // 2
        cy = node.row * CELL_SIZE + GRID_Y + CELL_SIZE // 2

        self._spawn_particles(cx, cy, DATA_COLORS[node.color], 8)

        if self.combo >= SURGE_THRESHOLD:
            self._trigger_surge(node)
        else:
            self._add_floating_text(cx, cy, f"+{base_score * multiplier}", WHITE)
            if self._check_victory():
                self.phase = PHASE_VICTORY

    def _trigger_surge(self, source: Node) -> None:
        source_color = source.color
        visited: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int, int]] = deque()
        queue.append((source.col, source.row, 0))

        surge_steps: list[SurgeStep] = []
        while queue:
            c, r, dist = queue.popleft()
            key = (c, r)
            if key in visited:
                continue
            visited.add(key)
            node = self.grid[r][c]
            if node is None:
                continue
            if node.is_firewall:
                continue
            if node.is_ice:
                continue
            if key != (source.col, source.row) and node.is_data and not node.hacked and node.color == source_color:
                surge_steps.append(SurgeStep(col=c, row=r, delay=dist * SURGE_DELAY))

            for dc, dr in DIRECTIONS:
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    nkey = (nc, nr)
                    if nkey not in visited:
                        nn = self.grid[nr][nc]
                        if nn is not None and not nn.is_firewall:
                            queue.append((nc, nr, dist + 1))

        self.surge_queue = surge_steps
        self.surge_timer = 0.0
        self._shake_frames = 15
        self.phase = PHASE_SURGE_ANIM

    def _update_surge_anim(self) -> None:
        self.trace += TRACE_RATE * (1.0 / 60.0)
        for r in range(ROWS):
            for c in range(COLS):
                node = self.grid[r][c]
                if node is not None and node.is_ice:
                    self.trace += ICE_TRACE_RATE * (1.0 / 60.0)

        if self.trace >= TRACE_MAX:
            self.trace = TRACE_MAX
            self.phase = PHASE_GAME_OVER
            self._spawn_game_over_particles()
            return

        self.surge_timer += 1.0 / 60.0

        processed = 0
        for step in self.surge_queue:
            if step.delay <= self.surge_timer:
                node = self.grid[step.row][step.col]
                if node is not None and not node.hacked:
                    node.hacked = True
                    self.nodes_hacked += 1
                    self.combo += 1
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    cx = node.col * CELL_SIZE + GRID_X + CELL_SIZE // 2
                    cy = node.row * CELL_SIZE + GRID_Y + CELL_SIZE // 2
                    self._spawn_particles(cx, cy, DATA_COLORS[node.color], 5)
                    self._add_floating_text(
                        cx, cy, "+500", YELLOW,
                    )
                    self.score += 500
                    step.delay = -1.0
                    processed += 1

        if processed > 0:
            self._shake_frames = max(self._shake_frames, 5)

        all_done = all(s.delay < 0 for s in self.surge_queue)
        if all_done and self.surge_timer > 0.3:
            self.phase = PHASE_PLAYING
            self.surge_queue.clear()
            if self._check_victory():
                self.phase = PHASE_VICTORY

        self._update_particles()
        self._update_floating_texts()
        self._update_shake()

    def _check_victory(self) -> bool:
        for r in range(ROWS):
            for c in range(COLS):
                node = self.grid[r][c]
                if node is not None and node.is_data and not node.hacked:
                    return False
        return True

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._update_shake()
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.seed_val = self._rng.randint(0, 999999)
            self._start_game()

    def _get_grid_cell(self, mx: int, my: int) -> tuple[int, int]:
        col = (mx - GRID_X) // CELL_SIZE
        row = (my - GRID_Y) // CELL_SIZE
        if 0 <= col < COLS and 0 <= row < ROWS:
            return col, row
        return -1, -1

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.random() * 2.0 + 1.0
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, color=color, life=20, max_life=20))

    def _spawn_game_over_particles(self) -> None:
        for _ in range(40):
            x = self._rng.random() * SCREEN_W
            y = self._rng.random() * SCREEN_H
            self._spawn_particles(x, y, RED, 1)

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=30, max_life=30))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_shake(self) -> None:
        if self._shake_frames > 0:
            self._shake_x = self._rng.uniform(-3, 3)
            self._shake_y = self._rng.uniform(-3, 3)
            self._shake_frames -= 1
        else:
            self._shake_x = 0.0
            self._shake_y = 0.0

    def draw(self) -> None:
        pyxel.cls(BLACK)
        ox = int(self._shake_x)
        oy = int(self._shake_y)

        if self.phase == PHASE_TITLE:
            self._draw_title()
        else:
            self._draw_hud()
            self._draw_grid(ox, oy)
            self._draw_particles(ox, oy)
            self._draw_floating_texts(ox, oy)
            if self.phase == PHASE_GAME_OVER:
                self._draw_game_over(False)
            elif self.phase == PHASE_VICTORY:
                self._draw_game_over(True)

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 52, 50, "NETWORK SURGE", WHITE)
        pyxel.text(SCREEN_W // 2 - 56, 80, "Hack the grid. Build the chain.", GRAY)
        pyxel.text(SCREEN_W // 2 - 44, 120, "CLICK or SPACE to START", YELLOW)
        pyxel.text(SCREEN_W // 2 - 64, 150, "Same-color = COMBO", GREEN)
        pyxel.text(SCREEN_W // 2 - 56, 162, "COMBO 4+ = SURGE", CYAN)
        pyxel.text(SCREEN_W // 2 - 52, 174, "Wrong color = RESET + TRACE", RED)

        t = self._frame_count * 0.05
        for i in range(COLS * ROWS):
            fx = GRID_X + (i % COLS) * CELL_SIZE + CELL_SIZE // 2
            fy = GRID_Y + (i // COLS) * CELL_SIZE + CELL_SIZE // 2
            col_idx = i % len(DATA_COLORS)
            alpha = (math.sin(t + i * 0.5) + 1) * 0.5
            r = 6 + alpha * 6
            pyxel.circb(int(fx), int(fy), int(r), DATA_COLORS[col_idx])

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 14, f"COMBO: x{max(1, self.combo)}", YELLOW)
        pyxel.text(4, 24, f"MAX COMBO: {self.max_combo}", GREEN)
        pyxel.text(4, 34, f"NODES: {self.nodes_hacked}/{self.total_data_nodes}", CYAN)

        trace_bar_x = SCREEN_W - 34
        trace_bar_y = 6
        trace_bar_h = 220
        trace_bar_w = 24
        pyxel.rectb(trace_bar_x - 1, trace_bar_y - 1, trace_bar_w + 2, trace_bar_h + 2, GRAY)
        fill_h = int(trace_bar_h * (self.trace / TRACE_MAX))
        bar_color = GREEN if self.trace < 50 else YELLOW if self.trace < 80 else RED
        if self.trace > 80 and (self._frame_count // 10) % 2 == 0:
            bar_color = WHITE
        pyxel.rect(trace_bar_x, trace_bar_y + trace_bar_h - fill_h, trace_bar_w, fill_h, bar_color)
        pyxel.text(trace_bar_x - 2, trace_bar_y + trace_bar_h + 4, "TRACE", GRAY)

    def _draw_grid(self, ox: int, oy: int) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                node = self.grid[r][c]
                x = ox + GRID_X + c * CELL_SIZE
                y = oy + GRID_Y + r * CELL_SIZE

                if node is None:
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, NAVY)
                    continue

                is_hovered = (c == self._hovered_col and r == self._hovered_row)
                border_color = NAVY
                if is_hovered and self.phase == PHASE_PLAYING:
                    border_color = WHITE

                if node.is_ice:
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, border_color)
                    inner = 4
                    pyxel.rect(x + inner, y + inner, CELL_SIZE - inner * 2, CELL_SIZE - inner * 2, ICE_COLOR)
                    pyxel.text(x + 4, y + 8, "ICE", BLACK)
                elif node.is_firewall:
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, border_color)
                    inner = 4
                    pyxel.rect(x + inner, y + inner, CELL_SIZE - inner * 2, CELL_SIZE - inner * 2, FIREWALL_COLOR)
                    pyxel.text(x + 2, y + 8, "FW", WHITE)
                elif node.is_data:
                    fill_color = DATA_COLORS[node.color]
                    if node.hacked:
                        fill_color = NAVY
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, border_color if not node.hacked else NAVY)
                    pyxel.rect(x + 3, y + 3, CELL_SIZE - 6, CELL_SIZE - 6, fill_color)
                    if node.hacked:
                        pyxel.text(x + 8, y + 8, "OK", GREEN)
                    elif node.hacking and self._hacking_node == (c, r):
                        prog_w = int((CELL_SIZE - 8) * node.hack_progress)
                        pyxel.rect(x + 4, y + CELL_SIZE - 8, prog_w, 4, GREEN)

    def _draw_particles(self, ox: int, oy: int) -> None:
        for p in self.particles:
            alpha = p.life / p.max_life
            r = 2.0 * alpha
            px = int(ox + p.x)
            py_val = int(oy + p.y)
            pyxel.circ(px, py_val, max(1, int(r)), p.color)

    def _draw_floating_texts(self, ox: int, oy: int) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / ft.max_life
            color = ft.color if alpha > 0.5 else GRAY
            tx = int(ox + ft.x - len(ft.text) * 2)
            ty = int(oy + ft.y - 4)
            pyxel.text(tx, ty, ft.text, color)

    def _draw_game_over(self, victory: bool) -> None:
        overlay_color = GREEN if victory else RED
        pyxel.rect(0, SCREEN_H // 2 - 30, SCREEN_W, 60, BLACK)
        pyxel.rectb(0, SCREEN_H // 2 - 30, SCREEN_W, 60, overlay_color)

        if victory:
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 - 22, "NETWORK SECURED!", GREEN)
        else:
            pyxel.text(SCREEN_W // 2 - 24, SCREEN_H // 2 - 22, "DETECTED!", RED)

        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 8, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 + 2, f"MAX COMBO: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 + 12, f"NODES: {self.nodes_hacked}/{self.total_data_nodes}", CYAN)
        pyxel.text(SCREEN_W // 2 - 44, SCREEN_H // 2 + 24, "CLICK or R to retry", GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
