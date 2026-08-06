from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30

GRID_COLS = 8
GRID_ROWS = 6
CELL_SIZE = 32
GRID_OFFSET_X = (SCREEN_W - GRID_COLS * CELL_SIZE) // 2
GRID_OFFSET_Y = (SCREEN_H - GRID_ROWS * CELL_SIZE) // 2

GAME_DURATION = 60.0
MAX_TIER = 4
HEAT_PER_PLACE = 5
HEAT_DECAY_PER_TICK = 2
HEAT_MAX = 100
TICK_INTERVAL = 1.0
CA_PROPAGATE_CHANCE = 0.25
SURGE_COMBO_THRESHOLD = 4
SURGE_DURATION = 5.0
ANIM_SYNTH_DURATION = 0.8
ANIM_SURGE_DURATION = 1.2
CRACK_SCORE_PENALTY = -20
PLACE_SCORE_PER_TIER = 10
SYNTH_SCORE_PER_TIER_MULT = 20
SURGE_SCORE_PER_CELL = 50
NUM_GLASS_COLORS = 4

GLASS_COLORS: dict[int, int] = {1: 8, 2: 5, 3: 10, 4: 3}
GLASS_NAMES: dict[int, str] = {1: "RED", 2: "BLUE", 3: "YELLOW", 4: "GREEN"}
TIER_BRIGHTNESS: dict[int, int] = {1: 6, 2: 10, 3: 13, 4: 15}


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    ANIM_SYNTH = auto()
    ANIM_SURGE = auto()
    GAME_OVER = auto()


@dataclass
class Cell:
    color: int  # 0=empty, 1-4
    tier: int  # 0=empty, 1-4


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Stained Glass Builder", fps=FPS, display_scale=2)
        self._rng = random.Random()
        self.best_score: int = 0
        self.reset()
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        best = self.best_score
        self.phase: Phase = Phase.TITLE
        self.grid: list[list[Cell]] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.game_timer: float = GAME_DURATION
        self.surge_timer: float = 0.0
        self.surge_color: int = 0
        self.mouse_grid_x: int = -1
        self.mouse_grid_y: int = -1
        self.selected_color: int = 1
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.anim_timer: float = 0.0
        self.cells_to_anim: list[tuple[int, int]] = []
        self._tick_timer: float = 0.0
        self._rng = random.Random()
        self.best_score = best
        self._init_grid()

    def _init_grid(self) -> None:
        self.grid = [[Cell(color=0, tier=0) for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

    def _cell_at(self, mx: int, my: int) -> tuple[int, int] | None:
        if mx < GRID_OFFSET_X or my < GRID_OFFSET_Y:
            return None
        col = (mx - GRID_OFFSET_X) // CELL_SIZE
        row = (my - GRID_OFFSET_Y) // CELL_SIZE
        if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
            return col, row
        return None

    def _get_connected(self, c: int, r: int) -> set[tuple[int, int]]:
        color = self.grid[r][c].color
        if color == 0:
            return set()
        visited: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = [(c, r)]
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        while stack:
            cc, rr = stack.pop()
            if (cc, rr) in visited:
                continue
            visited.add((cc, rr))
            for dx, dy in directions:
                nc, nr = cc + dx, rr + dy
                if 0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS:
                    if (nc, nr) not in visited and self.grid[nr][nc].color == color:
                        stack.append((nc, nr))
        return visited

    def _place_glass(self, col: int, row: int) -> int:
        cell = self.grid[row][col]
        if cell.color != 0:
            return 0
        color = self.selected_color
        cell.color = color
        cell.tier = 1
        gain = PLACE_SCORE_PER_TIER
        neighbors = self._adjacent_positions(col, row)
        has_same_color_neighbor = any(
            self.grid[nr][nc].color == color for nc, nr in neighbors
        )
        if has_same_color_neighbor:
            cluster = self._get_connected(col, row)
            synth_gain = self._synthesize(cluster)
            gain += synth_gain
        return gain

    def _synthesize(self, cluster: set[tuple[int, int]]) -> int:
        total_score = 0
        for c, r in cluster:
            cell = self.grid[r][c]
            if cell.color == 0:
                continue
            if cell.tier < MAX_TIER:
                cell.tier += 1
                total_score += cell.tier * cell.tier * SYNTH_SCORE_PER_TIER_MULT
        return total_score

    def _adjacent_positions(self, col: int, row: int) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS:
                result.append((nc, nr))
        return result

    def _ca_propagate(self) -> int:
        spread_count = 0
        new_cells: list[tuple[int, int, int]] = []
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = self.grid[r][c]
                if cell.color == 0 or cell.tier == 0:
                    continue
                for nc, nr in self._adjacent_positions(c, r):
                    if self.grid[nr][nc].color == 0:
                        if self._rng.random() < CA_PROPAGATE_CHANCE * self._ca_multiplier():
                            new_cells.append((nc, nr, cell.color))
                            spread_count += 1
        already_set: set[tuple[int, int]] = set()
        for nc, nr, color in new_cells:
            if (nc, nr) not in already_set:
                self.grid[nr][nc].color = color
                self.grid[nr][nc].tier = 1
                already_set.add((nc, nr))
        return spread_count

    def _ca_multiplier(self) -> float:
        if self.surge_timer > 0 and self.surge_color > 0:
            return 2.0
        return 1.0

    def _trigger_surge(self, color: int) -> int:
        total_score = 0
        visited: set[tuple[int, int]] = set()
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c].color == color and (c, r) not in visited:
                    cluster = self._get_connected(c, r)
                    visited.update(cluster)
                    for cc, rr in cluster:
                        self.grid[rr][cc].tier = MAX_TIER
        connected_count = visited
        total_score = len(connected_count) * SURGE_SCORE_PER_CELL
        self.surge_timer = SURGE_DURATION
        self.surge_color = color
        return total_score

    def _crack_glass(self) -> int:
        non_empty: list[tuple[int, int]] = []
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c].color != 0:
                    non_empty.append((c, r))
        if not non_empty:
            return 0
        c, r = self._rng.choice(non_empty)
        self.grid[r][c].color = 0
        self.grid[r][c].tier = 0
        self._add_particles(
            GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE / 2,
            GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE / 2,
            7, 8,
        )
        self.floating_texts.append(
            FloatingText(
                x=GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE / 2,
                y=GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE / 2,
                text=f"{CRACK_SCORE_PENALTY:+.0f}",
                life=30,
                color=8,
            )
        )
        return CRACK_SCORE_PENALTY

    def _add_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(10, 25),
                    color=color,
                    size=self._rng.randint(1, 3),
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_tick(self) -> None:
        self._ca_propagate()
        self.heat = max(0.0, self.heat - HEAT_DECAY_PER_TICK)
        self.game_timer = max(0.0, self.game_timer - TICK_INTERVAL)
        if self.surge_timer > 0:
            self.surge_timer = max(0.0, self.surge_timer - TICK_INTERVAL)
            if self.surge_timer <= 0:
                self.surge_color = 0

    def _do_placement(self, col: int, row: int) -> None:
        gain = self._place_glass(col, row)
        if gain == 0:
            return
        self.score += gain
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self.heat = min(HEAT_MAX, self.heat + HEAT_PER_PLACE)
        if self.heat >= HEAT_MAX:
            crack_penalty = self._crack_glass()
            self.score += crack_penalty
            self.heat = 0.0
            self.combo = 0

        cx = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE / 2
        cy = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE / 2
        self._add_particles(cx, cy, GLASS_COLORS[self.selected_color], 6)
        self.floating_texts.append(
            FloatingText(
                x=cx, y=cy,
                text=f"+{gain}",
                life=25, color=GLASS_COLORS[self.selected_color],
            )
        )

        has_same_color_neighbor = any(
            self.grid[nr][nc].color == self.selected_color
            for nc, nr in self._adjacent_positions(col, row)
        )
        if has_same_color_neighbor:
            cluster = self._get_connected(col, row)
            self.cells_to_anim = list(cluster)
            self.phase = Phase.ANIM_SYNTH
            self.anim_timer = ANIM_SYNTH_DURATION
            if self.combo >= SURGE_COMBO_THRESHOLD:
                surge_score = self._trigger_surge(self.selected_color)
                self.score += surge_score
                self.floating_texts.append(
                    FloatingText(
                        x=SCREEN_W / 2, y=SCREEN_H / 2,
                        text=f"SURGE! +{surge_score}",
                        life=40, color=10,
                    )
                )
                self.phase = Phase.ANIM_SURGE
                self.anim_timer = ANIM_SURGE_DURATION
                visited: set[tuple[int, int]] = set()
                for r in range(GRID_ROWS):
                    for c in range(GRID_COLS):
                        if self.grid[r][c].color == self.selected_color and (c, r) not in visited:
                            sur_cluster = self._get_connected(c, r)
                            visited.update(sur_cluster)
                self.cells_to_anim = list(visited)
                self._add_particles(SCREEN_W / 2, SCREEN_H / 2, 10, 16)
        else:
            self.phase = Phase.PLAYING

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.ANIM_SYNTH:
            self._update_anim_synth()
        elif self.phase == Phase.ANIM_SURGE:
            self._update_anim_surge()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        self._update_particles()
        self._update_floating_texts()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_1):
            self.selected_color = 1
        if pyxel.btnp(pyxel.KEY_2):
            self.selected_color = 2
        if pyxel.btnp(pyxel.KEY_3):
            self.selected_color = 3
        if pyxel.btnp(pyxel.KEY_4):
            self.selected_color = 4

        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        cell = self._cell_at(mx, my)
        if cell is not None:
            self.mouse_grid_x, self.mouse_grid_y = cell
        else:
            self.mouse_grid_x = -1
            self.mouse_grid_y = -1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self.selected_color = (self.selected_color % NUM_GLASS_COLORS) + 1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.mouse_grid_x >= 0 and self.mouse_grid_y >= 0:
                self._do_placement(self.mouse_grid_x, self.mouse_grid_y)

        self._tick_timer += 1.0 / FPS
        while self._tick_timer >= TICK_INTERVAL:
            self._tick_timer -= TICK_INTERVAL
            self._update_tick()

        if self.game_timer <= 0:
            if self.score > self.best_score:
                self.best_score = self.score
            self.phase = Phase.GAME_OVER

    def _update_anim_synth(self) -> None:
        self._tick_timer += 1.0 / FPS
        while self._tick_timer >= TICK_INTERVAL:
            self._tick_timer -= TICK_INTERVAL
            self._update_tick()
        self.anim_timer = max(0.0, self.anim_timer - 1.0 / FPS)
        if self.anim_timer <= 0:
            self.phase = Phase.PLAYING
            if self.game_timer <= 0:
                if self.score > self.best_score:
                    self.best_score = self.score
                self.phase = Phase.GAME_OVER

    def _update_anim_surge(self) -> None:
        self._tick_timer += 1.0 / FPS
        while self._tick_timer >= TICK_INTERVAL:
            self._tick_timer -= TICK_INTERVAL
            self._update_tick()
        self.anim_timer = max(0.0, self.anim_timer - 1.0 / FPS)
        if self.anim_timer <= 0:
            self.phase = Phase.PLAYING
            if self.game_timer <= 0:
                if self.score > self.best_score:
                    self.best_score = self.score
                self.phase = Phase.GAME_OVER

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()

    def draw(self) -> None:
        pyxel.cls(1)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.ANIM_SYNTH, Phase.ANIM_SURGE):
            self._draw_grid()
            self._draw_glass()
            self._draw_hover()
            self._draw_hud()
            self._draw_particles_and_texts()
            if self.phase == Phase.ANIM_SYNTH:
                self._draw_synth_anim()
            elif self.phase == Phase.ANIM_SURGE:
                self._draw_surge_anim()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "STAINED GLASS"
        x = (SCREEN_W - len(title) * 4) // 2
        pyxel.text(x, 80, title, 7)
        subtitle = "Click to place, chain same colors"
        sx = (SCREEN_W - len(subtitle) * 4) // 2
        pyxel.text(sx, 110, subtitle, 13)
        hint = "Press SPACE to start"
        hx = (SCREEN_W - len(hint) * 4) // 2
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(hx, 150, hint, 10)
        controls = "Left-click: Place / Right-click: Cycle color"
        cx = (SCREEN_W - len(controls) * 4) // 2
        pyxel.text(cx, 175, controls, 13)
        keys_hint = "Keys 1-4: Select color directly"
        kx = (SCREEN_W - len(keys_hint) * 4) // 2
        pyxel.text(kx, 190, keys_hint, 13)
        if self.best_score > 0:
            best_text = f"Best: {self.best_score}"
            bx = (SCREEN_W - len(best_text) * 4) // 2
            pyxel.text(bx, 205, best_text, 10)

    def _draw_grid(self) -> None:
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x = GRID_OFFSET_X + c * CELL_SIZE
                y = GRID_OFFSET_Y + r * CELL_SIZE
                pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 13)

    def _draw_glass(self) -> None:
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = self.grid[r][c]
                if cell.color == 0 or cell.tier == 0:
                    continue
                x = GRID_OFFSET_X + c * CELL_SIZE + 1
                y = GRID_OFFSET_Y + r * CELL_SIZE + 1
                w = CELL_SIZE - 2
                h = CELL_SIZE - 2
                base_color = GLASS_COLORS[cell.color]
                brightness = TIER_BRIGHTNESS[cell.tier]
                pyxel.rect(x, y, w, h, base_color)
                pyxel.rectb(x, y, w, h, brightness)
                inner = w // 4
                ix = x + (w - inner) // 2
                iy = y + (h - inner) // 2
                pyxel.rect(ix, iy, inner, inner, brightness)
                if cell.tier == MAX_TIER:
                    sparkle = (pyxel.frame_count // 8 + c + r) % 4
                    if sparkle == 0:
                        pyxel.pset(x + w * 3 // 4, y + h // 4, 7)
                    elif sparkle == 2:
                        pyxel.pset(x + w // 4, y + h * 3 // 4, 7)

    def _draw_hover(self) -> None:
        if self.phase == Phase.PLAYING and self.mouse_grid_x >= 0 and self.mouse_grid_y >= 0:
            c, r = self.mouse_grid_x, self.mouse_grid_y
            if self.grid[r][c].color == 0:
                x = GRID_OFFSET_X + c * CELL_SIZE
                y = GRID_OFFSET_Y + r * CELL_SIZE
                pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 7)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, GRID_OFFSET_Y, 1)
        pyxel.rect(0, SCREEN_H - GRID_OFFSET_Y, SCREEN_W, GRID_OFFSET_Y, 1)
        pyxel.text(2, 2, f"SCORE: {self.score}", 7)
        pyxel.text(2, 10, f"COMBO: {self.combo}", 10)
        time_color = 7 if self.game_timer > 10 else 8
        pyxel.text(SCREEN_W - 52, 2, f"TIME: {self.game_timer:.0f}", time_color)
        bar_width = 80
        bar_x = SCREEN_W - bar_width - 4
        bar_y = 12
        pyxel.rectb(bar_x, bar_y, bar_width, 5, 13)
        heat_ratio = self.heat / HEAT_MAX
        fill_w = int(bar_width * heat_ratio)
        heat_color = 11 if heat_ratio < 0.5 else (9 if heat_ratio < 0.8 else 8)
        if fill_w > 0:
            pyxel.rect(bar_x + 1, bar_y + 1, fill_w - 1 if fill_w > 1 else 0, 3, heat_color)
        pyxel.text(bar_x, bar_y + 6, "HEAT", 13)
        for i, (color_idx, pyxel_color) in enumerate(GLASS_COLORS.items()):
            sx = GRID_OFFSET_X + i * 24
            sy = SCREEN_H - GRID_OFFSET_Y + 4
            sw = 18 if self.selected_color == color_idx else 10
            sh = 18 if self.selected_color == color_idx else 10
            pyxel.rect(sx, sy, sw, sh, pyxel_color)

    def _draw_synth_anim(self) -> None:
        if self.anim_timer > 0:
            for c, r in self.cells_to_anim:
                x = GRID_OFFSET_X + c * CELL_SIZE
                y = GRID_OFFSET_Y + r * CELL_SIZE
                flash_alpha = self.anim_timer / ANIM_SYNTH_DURATION
                if int(flash_alpha * 4) % 2 == 0:
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 7)

    def _draw_surge_anim(self) -> None:
        if self.anim_timer > 0:
            for c, r in self.cells_to_anim:
                x = GRID_OFFSET_X + c * CELL_SIZE
                y = GRID_OFFSET_Y + r * CELL_SIZE
                hue = (pyxel.frame_count // 4 + c + r) % 4
                colors = [8, 10, 11, 12]
                pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, colors[hue])

    def _draw_particles_and_texts(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)
        for ft in self.floating_texts:
            alpha = ft.life / 40
            if alpha > 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_game_over(self) -> None:
        go_text = "GAME OVER"
        gx = (SCREEN_W - len(go_text) * 4) // 2
        pyxel.text(gx, 70, go_text, 8)
        score_text = f"Score: {self.score}"
        sx = (SCREEN_W - len(score_text) * 4) // 2
        pyxel.text(sx, 100, score_text, 7)
        combo_text = f"Max Combo: {self.max_combo}"
        cx = (SCREEN_W - len(combo_text) * 4) // 2
        pyxel.text(cx, 115, combo_text, 10)
        if self.score >= self.best_score and self.score > 0:
            new_best = "NEW BEST!"
            nx = (SCREEN_W - len(new_best) * 4) // 2
            if (pyxel.frame_count // 15) % 2 == 0:
                pyxel.text(nx, 135, new_best, 10)
        else:
            best_text = f"Best: {self.best_score}"
            bx = (SCREEN_W - len(best_text) * 4) // 2
            pyxel.text(bx, 135, best_text, 13)
        retry = "Press SPACE to retry"
        rx = (SCREEN_W - len(retry) * 4) // 2
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(rx, 170, retry, 7)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
