from __future__ import annotations

import random as random_module
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Hold:
    col: int
    row: int
    color: int
    x: float = 0.0
    y: float = 0.0
    grabbed: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


SCREEN_W: int = 320
SCREEN_H: int = 240
CELL: int = 24
GRID_OFFSET_X: int = 36
GRID_OFFSET_Y: int = 24
GRID_COLS: int = 10
GRID_ROWS: int = 8
REACH_RADIUS: float = 36.0
HOLD_RADIUS: int = 10
MAX_HOLDS: int = 30
SPAWN_INTERVAL_INITIAL: int = 60
SPAWN_INTERVAL_MIN: int = 30
COLOR_CYCLE_INITIAL: int = 90
COLOR_CYCLE_MIN: int = 40
GAME_DURATION: int = 60 * 30
SUPER_DURATION: int = 300
HEAT_MAX: float = 100.0
HEAT_DECAY: float = 0.02
HEAT_MISMATCH: float = 15.0
HEAT_FALL: float = 25.0
STUN_MISMATCH: int = 10
STUN_FALL: int = 20
COLORS: tuple[int, int, int, int] = (8, 11, 5, 10)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "LIME", "DARK_BLUE", "YELLOW")
SHAKE_FRAMES: int = 15


class Game:
    def __init__(self) -> None:
        self._rng = random_module.Random()
        self._pre_init()
        pyxel.init(SCREEN_W, SCREEN_H, title="CLIMB SURGE", display_scale=2)
        pyxel.run(self._update, self._draw)

    def _pre_init(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_col: int = 0
        self.player_row: int = 0
        self.grip_color_index: int = 0
        self.grip_color: int = COLORS[0]
        self.color_timer: int = COLOR_CYCLE_INITIAL
        self.color_cycle_interval: int = COLOR_CYCLE_INITIAL
        self.holds: list[Hold] = []
        self.spawn_timer: int = 0
        self.spawn_interval: int = SPAWN_INTERVAL_INITIAL
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.stun_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self.ghost_path: list[tuple[int, int]] = []
        self.best_score: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.player_col = GRID_COLS // 2
        self.player_row = GRID_ROWS - 1
        self.grip_color_index = 0
        self.grip_color = COLORS[0]
        self.color_timer = COLOR_CYCLE_INITIAL
        self.color_cycle_interval = COLOR_CYCLE_INITIAL
        self.holds = []
        self.spawn_timer = 0
        self.spawn_interval = SPAWN_INTERVAL_INITIAL
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.stun_timer = 0
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.ghost_path = []
        self._initial_spawn()

    def _initial_spawn(self) -> None:
        self.holds = []
        occupied: set[tuple[int, int]] = set()
        start_col = GRID_COLS // 2
        start_row = GRID_ROWS - 1
        start_hold = Hold(col=start_col, row=start_row, color=self.grip_color)
        start_hold.x = GRID_OFFSET_X + start_hold.col * CELL + CELL // 2
        start_hold.y = GRID_OFFSET_Y + start_hold.row * CELL + CELL // 2
        self.holds.append(start_hold)
        occupied.add((start_col, start_row))

        for _ in range(14):
            col = self._rng.randint(0, GRID_COLS - 1)
            row = self._rng.randint(0, GRID_ROWS - 1)
            if (col, row) in occupied:
                continue
            color = self._rng.choice(COLORS)
            h = Hold(col=col, row=row, color=color)
            h.x = GRID_OFFSET_X + col * CELL + CELL // 2
            h.y = GRID_OFFSET_Y + row * CELL + CELL // 2
            self.holds.append(h)
            occupied.add((col, row))

    def _hold_at(self, col: int, row: int) -> Hold | None:
        for h in self.holds:
            if h.col == col and h.row == row:
                return h
        return None

    def _holds_in_reach(self) -> list[Hold]:
        px = GRID_OFFSET_X + self.player_col * CELL + CELL // 2
        py = GRID_OFFSET_Y + self.player_row * CELL + CELL // 2
        result: list[Hold] = []
        for h in self.holds:
            if h.col == self.player_col and h.row == self.player_row:
                continue
            dx = h.x - px
            dy = h.y - py
            if dx * dx + dy * dy <= REACH_RADIUS * REACH_RADIUS:
                result.append(h)
        return result

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _move_to_hold(self, hold: Hold) -> None:
        self.player_col = hold.col
        self.player_row = hold.row
        hold.grabbed = True
        px = hold.x
        py = hold.y

        if self._is_super() or hold.color == self.grip_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            super_mult = 3 if self._is_super() else 1
            points = 10 * self.combo * super_mult
            self.score += points
            self.ghost_path.append((hold.col, hold.row))
            count = self._rng.randint(15, 20) if self._is_super() else self._rng.randint(8, 12)
            particle_color = hold.color
            if self._is_super():
                particle_color = self._rng.choice(COLORS)
            self._add_particles(px, py, particle_color, count, self._is_super())
            self._add_floating_text(px, py - 8, f"+{points}", 7 if not self._is_super() else 10, 30)
            if self.combo >= 2 and not self._is_super():
                self._add_floating_text(px, py - 20, f"COMBO x{self.combo}", 10, 40)
            if self.combo >= 4 and not self._is_super():
                self._activate_super()
        else:
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self.stun_timer = STUN_MISMATCH
            self._add_particles(px, py, 13, 4, False)
            self._add_floating_text(px, py - 8, "MISS!", 8, 20)

    def _check_fall(self) -> None:
        if self.stun_timer > 0:
            return
        in_reach = self._holds_in_reach()
        if in_reach:
            return
        self.heat = min(HEAT_MAX, self.heat + HEAT_FALL)
        self.stun_timer = STUN_FALL
        self.combo = 0
        nearest = self._find_nearest_hold()
        px = GRID_OFFSET_X + self.player_col * CELL + CELL // 2
        py = GRID_OFFSET_Y + self.player_row * CELL + CELL // 2
        self._add_particles(px, py, 8, 10, False)
        self._add_floating_text(px, py - 8, "FALL!", 8, 20)
        if nearest is not None:
            self.player_col = nearest.col
            self.player_row = nearest.row

    def _find_nearest_hold(self) -> Hold | None:
        px = GRID_OFFSET_X + self.player_col * CELL + CELL // 2
        py = GRID_OFFSET_Y + self.player_row * CELL + CELL // 2
        best: Hold | None = None
        best_dist = float("inf")
        for h in self.holds:
            if h.col == self.player_col and h.row == self.player_row:
                continue
            dx = h.x - px
            dy = h.y - py
            d = dx * dx + dy * dy
            if d < best_dist:
                best_dist = d
                best = h
        return best

    def _try_move(self, dcol: int, drow: int) -> None:
        target_col = self.player_col + dcol
        target_row = self.player_row + drow
        if 0 <= target_col < GRID_COLS and 0 <= target_row < GRID_ROWS:
            target = self._hold_at(target_col, target_row)
            if target is not None:
                self._move_to_hold(target)

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        px = GRID_OFFSET_X + self.player_col * CELL + CELL // 2
        py = GRID_OFFSET_Y + self.player_row * CELL + CELL // 2
        self._add_particles(px, py, self._rng.choice(COLORS), 20, True)
        self._add_floating_text(px, py - 32, "SUPER GRIP!", 10, 60)

    def _update_color_cycle(self) -> None:
        if self._is_super():
            return
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = self.color_cycle_interval
            self.grip_color_index = (self.grip_color_index + 1) % 4
            self.grip_color = COLORS[self.grip_color_index]

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= HEAT_MAX:
            self._end_game()

    def _update_difficulty(self) -> None:
        elapsed_ratio = 1.0 - (self.game_timer / GAME_DURATION)
        self.spawn_interval = int(
            SPAWN_INTERVAL_INITIAL - (SPAWN_INTERVAL_INITIAL - SPAWN_INTERVAL_MIN) * elapsed_ratio
        )
        self.color_cycle_interval = int(
            COLOR_CYCLE_INITIAL - (COLOR_CYCLE_INITIAL - COLOR_CYCLE_MIN) * elapsed_ratio
        )

    def _spawn_hold(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = max(1, self.spawn_interval)
            if len(self.holds) >= MAX_HOLDS:
                return
            occupied = {(h.col, h.row) for h in self.holds}
            empty: list[tuple[int, int]] = []
            for r in range(GRID_ROWS):
                for c in range(GRID_COLS):
                    if (c, r) not in occupied:
                        empty.append((c, r))
            if not empty:
                return
            weights = [(GRID_ROWS - r) for (c, r) in empty]
            total = sum(weights)
            rnd = self._rng.uniform(0, total)
            acc = 0.0
            chosen = empty[0]
            for i, (c, r) in enumerate(empty):
                acc += weights[i]
                if rnd <= acc:
                    chosen = (c, r)
                    break
            col, row = chosen
            color = self._rng.choice(COLORS)
            h = Hold(col=col, row=row, color=color)
            h.x = GRID_OFFSET_X + col * CELL + CELL // 2
            h.y = GRID_OFFSET_Y + row * CELL + CELL // 2
            self.holds.append(h)

    def _add_particles(self, x: float, y: float, color: int, count: int, is_super: bool) -> None:
        for _ in range(count):
            c = self._rng.choice(COLORS) if is_super else color
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=self._rng.uniform(-2.0, 2.0),
                    vy=self._rng.uniform(-2.0, 2.0),
                    life=self._rng.randint(15, 25),
                    color=c,
                )
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [f for f in self.floating_texts if f.life > 0]

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        self.shake_frames = SHAKE_FRAMES
        if self.score > self.best_score:
            self.best_score = self.score

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        if self.stun_timer > 0:
            self.stun_timer -= 1
            self._update_particles()
            self._update_floating_texts()
            return

        self.game_timer -= 1
        if self.game_timer <= 0:
            self._end_game()
            return

        self._update_color_cycle()
        self._update_difficulty()
        self._spawn_hold()

        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self._try_move(-1, 0)
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self._try_move(1, 0)
        elif pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W):
            self._try_move(0, -1)
        elif pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
            self._try_move(0, 1)

        self._check_fall()
        self._update_super()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _draw(self) -> None:
        pyxel.cls(1)
        if self.shake_frames > 0:
            ox = self._rng.randint(-4, 4)
            oy = self._rng.randint(-4, 4)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(105, 50, "CLIMB SURGE", 7)
        pyxel.text(85, 75, "Vertical Rock Climbing!", 11)
        pyxel.text(75, 100, "Arrow/WASD: Move to holds", 6)
        pyxel.text(65, 114, "Match grip color for COMBO chain!", 13)
        pyxel.text(80, 128, "COMBO x4 = SUPER GRIP (3x, free grab!)", 11)
        pyxel.text(120, 150, "HEAT = Game Over", 8)
        pyxel.text(88, 180, "Press SPACE to start", 7)
        if self.best_score > 0:
            pyxel.text(105, 200, f"Best: {self.best_score}", 10)

    def _draw_game_over(self) -> None:
        pyxel.text(115, 70, "GAME OVER", 8)
        pyxel.text(110, 100, f"Score: {self.score}", 7)
        pyxel.text(100, 115, f"Max Combo: {self.max_combo}", 10)
        if self.best_score > 0:
            pyxel.text(105, 135, f"Best: {self.best_score}", 9)
        pyxel.text(95, 170, "Press R to restart", 13)

    def _draw_playing(self) -> None:
        self._draw_wall()
        self._draw_ghost_path()
        self._draw_holds()
        self._draw_player()
        self._draw_reach_indicator()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_wall(self) -> None:
        for row in range(GRID_ROWS + 1):
            py = GRID_OFFSET_Y + row * CELL
            pyxel.line(GRID_OFFSET_X, py, GRID_OFFSET_X + GRID_COLS * CELL, py, 13)
        for col in range(GRID_COLS + 1):
            px = GRID_OFFSET_X + col * CELL
            pyxel.line(px, GRID_OFFSET_Y, px, GRID_OFFSET_Y + GRID_ROWS * CELL, 13)

    def _draw_ghost_path(self) -> None:
        if not self.ghost_path:
            return
        for col, row in self.ghost_path:
            px = GRID_OFFSET_X + col * CELL + CELL // 2
            py = GRID_OFFSET_Y + row * CELL + CELL // 2
            pyxel.circ(px, py, 3, 12)

    def _draw_holds(self) -> None:
        for h in self.holds:
            px = int(h.x)
            py = int(h.y)
            color = h.color
            if h.grabbed:
                if pyxel.frame_count % 6 < 3:
                    color = 7
            pyxel.circ(px, py, HOLD_RADIUS, color)
            pyxel.circb(px, py, HOLD_RADIUS, 13)

    def _draw_player(self) -> None:
        px = int(GRID_OFFSET_X + self.player_col * CELL + CELL // 2)
        py = int(GRID_OFFSET_Y + self.player_row * CELL + CELL // 2)

        if self._is_super():
            color_idx = (pyxel.frame_count // 4) % 4
            color = COLORS[color_idx]
        else:
            color = self.grip_color

        pyxel.tri(px, py - 8, px - 6, py + 4, px + 6, py + 4, color)

        if self.stun_timer > 0:
            pyxel.text(px - 4, py - 16, "!", 8)

    def _draw_reach_indicator(self) -> None:
        px = GRID_OFFSET_X + self.player_col * CELL + CELL // 2
        py = GRID_OFFSET_Y + self.player_row * CELL + CELL // 2
        for h in self.holds:
            dx = h.x - px
            dy = h.y - py
            if dx * dx + dy * dy <= REACH_RADIUS * REACH_RADIUS:
                color = 10 if h.color == self.grip_color or self._is_super() else 13
                pyxel.line(px, py, int(h.x), int(h.y), color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)

        seconds = max(0, self.game_timer // 30)
        timer_color = 8 if seconds <= 10 else 7
        pyxel.text(120, 4, f"TIME: {seconds}", timer_color)

        combo_color = 7
        if self.combo >= 4:
            combo_color = 8
        elif self.combo >= 2:
            combo_color = 10
        pyxel.text(244, 4, f"COMBO: {self.combo}", combo_color)

        grip_name = COLOR_NAMES[self.grip_color_index]
        grip_color = COLORS[self.grip_color_index]
        if self._is_super():
            grip_name = "SUPER"
            grip_color = 10
        pyxel.text(4, 16, f"GRIP: {grip_name}", grip_color)

        bar_x = 4
        bar_y = 228
        bar_w = 312
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        fill_w = int(self.heat / HEAT_MAX * (bar_w - 2))
        heat_col = 3
        if self.heat > 30:
            heat_col = 11
        if self.heat > 60:
            heat_col = 10
        if self.heat > 80:
            heat_col = 8
        pyxel.rect(bar_x + 1, bar_y + 1, fill_w, bar_h - 2, heat_col)
        pyxel.text(4, bar_y - 7, f"HEAT {int(self.heat)}", 13)

        if self._is_super():
            super_sec = self.super_timer // 30
            rainbow_idx = (pyxel.frame_count // 4) % 4
            super_color = COLORS[rainbow_idx]
            pyxel.text(200, 16, f"SUPER GRIP {super_sec}s", super_color)

        if self.stun_timer > 0:
            pyxel.text(100, 28, f"STUNNED {self.stun_timer}", 8)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25
            if alpha > 0.1:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 3:
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
