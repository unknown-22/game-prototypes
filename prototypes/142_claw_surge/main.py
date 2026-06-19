import pyxel
import random
from dataclasses import dataclass
from enum import Enum, auto


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SUPER_ANIM = auto()
    GAME_OVER = auto()


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


COLORS = [8, 3, 10, 6]
BG_COLOR = 0
GRID_BG = 1
HEAT_COLOR = 8
SUPER_COLOR = 9
TEXT_COLOR = 7
GRID_LEFT = 40
GRID_TOP = 30
CELL = 30
COLS = 8
ROWS = 6


class Game:
    def __init__(self) -> None:
        pyxel.init(320, 240, display_scale=2, title="CLAW SURGE")
        pyxel.mouse(True)
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.grid: list[list[int]] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.last_color: int = -1
        self.heat: float = 0.0
        self.super_claw: bool = False
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.cursor_x: int = 0
        self.cursor_y: int = 0
        self.grab_x: int = 0
        self.grab_y: int = 0
        self.frame: int = 0
        self.game_over_reason: str = ""
        self._reset()
        pyxel.run(self._update, self._draw)

    def _reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.last_color = -1
        self.heat = 0.0
        self.super_claw = False
        self.super_timer = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.grab_x = 0
        self.grab_y = 0
        self.frame = 0
        self.game_over_reason = ""
        self.grid = [[self._rng.randint(0, 3) for _ in range(COLS)] for _ in range(ROWS)]

    def _update(self) -> None:
        self.frame += 1
        self.cursor_x = pyxel.mouse_x
        self.cursor_y = pyxel.mouse_y

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self._reset()
        elif self.phase == Phase.PLAYING:
            self._update_particles()
            self._update_floating_texts()
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._handle_click()
        elif self.phase == Phase.SUPER_ANIM:
            self._update_particles()
            self._update_floating_texts()
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.phase = Phase.PLAYING
                self.super_timer = 0
        elif self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.TITLE

    def _draw(self) -> None:
        pyxel.cls(BG_COLOR)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.SUPER_ANIM):
            self._draw_grid()
            self._draw_hud()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_cursor()
        elif self.phase == Phase.GAME_OVER:
            self._draw_grid()
            self._draw_hud()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "CLAW SURGE"
        pyxel.text(160 - len(title) * 4 // 2, 60, title, TEXT_COLOR)
        subtitle = "Color-Match Crane Game"
        pyxel.text(160 - len(subtitle) * 4 // 2, 85, subtitle, TEXT_COLOR)
        instructions = [
            "Click same-color prizes to build COMBO!",
            "COMBO x4 = SUPER CLAW (BFS burst!)",
            "Wrong color = HEAT + COMBO reset",
            "HEAT >= 100 = GAME OVER",
            "Press SPACE to start",
        ]
        y = 120
        for line in instructions:
            pyxel.text(160 - len(line) * 4 // 2, y, line, TEXT_COLOR)
            y += 15

    def _draw_game_over(self) -> None:
        pyxel.text(160 - 24, 60, "GAME OVER", HEAT_COLOR)
        pyxel.text(160 - 40, 90, f"Score: {self.score}", TEXT_COLOR)
        pyxel.text(160 - 48, 110, f"Max Combo: x{self.max_combo}", TEXT_COLOR)
        reason = self.game_over_reason if self.game_over_reason else "Overheated!"
        pyxel.text(160 - len(reason) * 4 // 2, 140, reason, TEXT_COLOR)
        pyxel.text(160 - 56, 180, "Press SPACE to retry", TEXT_COLOR)

    def _draw_grid(self) -> None:
        for row in range(ROWS):
            for col in range(COLS):
                x = GRID_LEFT + col * CELL
                y = GRID_TOP + row * CELL
                color_idx = self.grid[row][col]
                if color_idx >= 0:
                    prize_color = COLORS[color_idx]
                    pyxel.rect(x + 2, y + 2, CELL - 4, CELL - 4, prize_color)
                    pyxel.rectb(x + 2, y + 2, CELL - 4, CELL - 4, TEXT_COLOR)
                    if self.super_claw and self.phase in (Phase.PLAYING, Phase.SUPER_ANIM):
                        if (self.frame // 15) % 2 == 0:
                            pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, SUPER_COLOR)
                else:
                    pyxel.rect(x + 2, y + 2, CELL - 4, CELL - 4, GRID_BG)

    def _draw_hud(self) -> None:
        score_text = f"SCORE:{self.score:>6}"
        combo_text = f"COMBO:x{self.combo}"
        heat_blocks = int(self.heat / 5)
        heat_str = "#" * heat_blocks + "_" * (20 - heat_blocks)
        hud_text = f"{score_text}  {combo_text}  HEAT:[{heat_str}]"
        pyxel.text(4, 4, hud_text, TEXT_COLOR)

        if self.super_claw and (self.frame // 10) % 2 == 0:
            super_text = "!!! SUPER CLAW READY !!!"
            pyxel.text(160 - len(super_text) * 4 // 2, 15, super_text, SUPER_COLOR)

    def _draw_cursor(self) -> None:
        cx = self.cursor_x
        cy = self.cursor_y
        pyxel.line(cx - 5, cy, cx - 2, cy, TEXT_COLOR)
        pyxel.line(cx + 2, cy, cx + 5, cy, TEXT_COLOR)
        pyxel.line(cx, cy - 5, cx, cy - 2, TEXT_COLOR)
        pyxel.line(cx, cy + 2, cx, cy + 5, TEXT_COLOR)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _handle_click(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        col = (mx - GRID_LEFT) // CELL
        row = (my - GRID_TOP) // CELL

        if col < 0 or col >= COLS or row < 0 or row >= ROWS or self.grid[row][col] == -1:
            self.heat = min(100.0, self.heat + 5.0)
            self._spawn_floating_text(mx, my, "MISS", HEAT_COLOR)
            self._check_game_over()
            return

        color = self.grid[row][col]
        self.grab_x = col
        self.grab_y = row
        gx = GRID_LEFT + col * CELL + CELL // 2
        gy = GRID_TOP + row * CELL + CELL // 2

        if self.super_claw:
            cluster = self._bfs_cluster(col, row, color)
            cluster_size = len(cluster)
            for c, r in cluster:
                self.grid[r][c] = -1
                self._spawn_particles_at(GRID_LEFT + c * CELL + CELL // 2, GRID_TOP + r * CELL + CELL // 2, color, 5)

            base_score = cluster_size * 100
            combo_bonus = self.combo if self.combo > 0 else 1
            score_add = base_score * combo_bonus
            self.score += score_add
            self.combo += cluster_size - 1
            self.last_color = color
            self.super_claw = False
            self.heat = max(0.0, self.heat - cluster_size * 3.0)

            self._spawn_floating_text(gx, gy - 10, f"SUPER! x{cluster_size}", SUPER_COLOR)
            self._spawn_floating_text(gx, gy + 10, f"+{score_add}", TEXT_COLOR)
        else:
            if self.last_color == -1 or color == self.last_color:
                self.combo += 1
                score_add = 10 + self.combo * 5
            else:
                self.combo = 1
                score_add = 10
                self.heat = min(100.0, self.heat + 10.0)
            self.last_color = color
            self.score += score_add
            self.grid[row][col] = -1

            self._spawn_particles_at(gx, gy, color, 12)
            if self.combo >= 2:
                self._spawn_floating_text(gx, gy - 5, f"+{score_add}", TEXT_COLOR)
                self._spawn_floating_text(gx + 20, gy - 15, f"x{self.combo}", SUPER_COLOR)
            else:
                self._spawn_floating_text(gx, gy - 5, f"+{score_add}", TEXT_COLOR)

            if self.combo >= 4:
                self.super_claw = True
                self._spawn_floating_text(160, 200, "SUPER CLAW READY!", SUPER_COLOR)

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        self._apply_gravity()
        self._check_game_over()
        # Decay heat AFTER game over check (pitfall: decay-before-check blocks game over)
        self.heat = max(0.0, self.heat - 2.0)

    def _bfs_cluster(self, start_col: int, start_row: int, color: int) -> set[tuple[int, int]]:
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(start_col, start_row)]
        visited.add((start_col, start_row))
        while queue:
            c, r = queue.pop(0)
            for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if (nc, nr) not in visited and self.grid[nr][nc] == color:
                        visited.add((nc, nr))
                        queue.append((nc, nr))
        return visited

    def _apply_gravity(self) -> None:
        for col in range(COLS):
            values: list[int] = []
            for row in range(ROWS - 1, -1, -1):
                if self.grid[row][col] != -1:
                    values.append(self.grid[row][col])
            for row in range(ROWS):
                idx = ROWS - 1 - row
                if idx < len(values):
                    self.grid[row][col] = values[idx]
                else:
                    self.grid[row][col] = -1
            for row in range(ROWS):
                if self.grid[row][col] == -1:
                    self.grid[row][col] = self._rng.randint(0, 3)

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _spawn_particles_at(self, x: float, y: float, color_idx: int, count: int) -> None:
        prize_color = COLORS[color_idx]
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 2.0)
            life = self._rng.randint(10, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=prize_color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=45, color=color))

    def _check_game_over(self) -> None:
        if self.heat >= 100.0:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "Overheated!"
            return
        all_empty = True
        for row in range(ROWS):
            for col in range(COLS):
                if self.grid[row][col] != -1:
                    all_empty = False
                    break
            if not all_empty:
                break
        if all_empty:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "All prizes collected!"


if __name__ == "__main__":
    Game()
