import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pyxel

SCREEN_W = 320
SCREEN_H = 240

CELL = 20
COLS = 12
ROWS = 9
OFFSET_X = 40
OFFSET_Y = 30

FPS = 60
GAME_TIME = FPS * 60
SUPER_DURATION = 300
MOVE_COOLDOWN = 8
HEAT_MAX = 100.0
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15.0
HEAT_CAUGHT = 25.0
COMBO_SUPER_THRESHOLD = 4
SPOT_COUNT_INITIAL = 17
MAX_SPOTS = 20
MIN_SPOTS = 3
SPOT_RESPAWN_BASE = 240
SPOT_RESPAWN_MIN = 120
SEEKER_COUNT = 3
SEEKER_SPEED_INITIAL = 30
SEEKER_SPEED_MIN = 8
SEEKER_AWARENESS_INITIAL = 60
SEEKER_AWARENESS_MIN = 30

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

SPOT_COLORS: list[int] = [RED, LIME, DARK_BLUE, YELLOW]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class HidingSpot:
    col: int
    row: int
    color: int
    respawn_timer: int = 0


@dataclass
class Seeker:
    col: int
    row: int
    awareness: set[tuple[int, int]]
    dir_x: int = 1
    dir_y: int = 0
    speed_frames: int = 30
    move_counter: int = 0
    awareness_counter: int = 0
    color: int = RED


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


class Game:
    phase: Phase
    player_col: int
    player_row: int
    player_color: int
    is_hidden: bool
    current_spot_color: Optional[int]
    spots: list[HidingSpot]
    seekers: list[Seeker]
    score: int
    combo: int
    max_combo: int
    super_mode: bool
    super_timer: int
    heat: float
    game_timer: int
    move_cooldown: int
    particles: list[Particle]
    floating_texts: list[FloatingText]
    rng: random.Random
    awareness_interval: int
    speed_frames_current: int
    respawn_interval: int
    frame: int
    elapsed_seconds: int

    def __init__(self) -> None:
        self.rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_col = COLS // 2
        self.player_row = ROWS // 2
        self.player_color = GREEN
        self.is_hidden = False
        self.current_spot_color = None
        self.spots = []
        self.seekers = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.heat = 0.0
        self.game_timer = GAME_TIME
        self.move_cooldown = 0
        self.particles = []
        self.floating_texts = []
        self.awareness_interval = SEEKER_AWARENESS_INITIAL
        self.speed_frames_current = SEEKER_SPEED_INITIAL
        self.respawn_interval = SPOT_RESPAWN_BASE
        self.frame = 0
        self.elapsed_seconds = 0

    def reset_playing(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING
        self._spawn_spots()
        self._spawn_seekers()

    def _spawn_spots(self) -> None:
        self.spots.clear()
        for _ in range(SPOT_COUNT_INITIAL):
            self._respawn_spot()

    def _respawn_spot(self) -> None:
        if len(self.spots) >= MAX_SPOTS:
            return
        occupied = {(s.col, s.row) for s in self.spots}
        occupied.add((self.player_col, self.player_row))
        empty: list[tuple[int, int]] = []
        for c in range(COLS):
            for r in range(ROWS):
                if (c, r) not in occupied:
                    empty.append((c, r))
        if not empty:
            return
        c, r = self.rng.choice(empty)
        color = self.rng.choice(SPOT_COLORS)
        self.spots.append(HidingSpot(c, r, color))

    def _spawn_seekers(self) -> None:
        self.seekers.clear()
        corners = [
            (0, 0), (COLS - 1, 0), (0, ROWS - 1),
            (COLS - 1, ROWS - 1),
            (COLS // 2, 0), (0, ROWS // 2),
            (COLS - 1, ROWS // 2), (COLS // 2, ROWS - 1),
        ]
        chosen = self.rng.sample(corners, min(len(corners), SEEKER_COUNT))
        for i, (c, r) in enumerate(chosen):
            color = SPOT_COLORS[i % len(SPOT_COLORS)]
            seeker = Seeker(
                col=c, row=r,
                awareness=set(),
                dir_x=self.rng.choice([-1, 1]),
                dir_y=self.rng.choice([-1, 0, 1]),
                speed_frames=self.speed_frames_current,
                move_counter=self.rng.randint(0, self.speed_frames_current),
                awareness_counter=self.rng.randint(0, self.awareness_interval),
                color=color,
            )
            if seeker.dir_y == 0 and seeker.dir_x == 0:
                seeker.dir_x = 1
            self.seekers.append(seeker)

    def _try_hide(self, spot_color: int) -> int:
        if self.is_hidden:
            self.is_hidden = False
            self.current_spot_color = None
            return 0
        if self.current_spot_color is None or spot_color == self.current_spot_color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = 3 if self.super_mode else 1
            gained = 10 * self.combo * multiplier
            self.score += gained
            self.is_hidden = True
            self.current_spot_color = spot_color
            if self.combo >= COMBO_SUPER_THRESHOLD and not self.super_mode:
                self._trigger_super()
            return gained
        self.combo = 0
        self._update_heat(HEAT_MISMATCH)
        self._add_floating_text(
            self.player_col * CELL + OFFSET_X + CELL // 2,
            self.player_row * CELL + OFFSET_Y,
            "MISMATCH!",
            RED,
        )
        self._spawn_particles(
            self.player_col * CELL + OFFSET_X + CELL // 2,
            self.player_row * CELL + OFFSET_Y + CELL // 2,
            RED,
            10,
        )
        self.is_hidden = True
        self.current_spot_color = spot_color
        return 0

    def _trigger_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        cx = self.player_col * CELL + OFFSET_X + CELL // 2
        cy = self.player_row * CELL + OFFSET_Y + CELL // 2
        self._spawn_particles(cx, cy, WHITE, 25)
        self._add_floating_text(cx, cy - 10, "SUPER HIDE!", WHITE)

    def _update_seekers(self) -> None:
        for seeker in self.seekers:
            seeker.move_counter += 1
            if seeker.move_counter >= seeker.speed_frames:
                seeker.move_counter = 0
                self._move_seeker(seeker)
            seeker.awareness_counter += 1
            if seeker.awareness_counter >= self.awareness_interval:
                seeker.awareness_counter = 0
                self._expand_awareness(seeker)

    def _move_seeker(self, seeker: Seeker) -> None:
        new_col = seeker.col + seeker.dir_x
        new_row = seeker.row + seeker.dir_y
        if new_col < 0 or new_col >= COLS:
            seeker.dir_x *= -1
            new_col = seeker.col + seeker.dir_x
        if new_row < 0 or new_row >= ROWS:
            seeker.dir_y *= -1
            new_row = seeker.row + seeker.dir_y
        new_col = max(0, min(COLS - 1, new_col))
        new_row = max(0, min(ROWS - 1, new_row))
        if self.rng.random() < 0.3 or (new_col, new_row) == (seeker.col, seeker.row):
            seeker.dir_x = self.rng.choice([-1, 1])
            seeker.dir_y = self.rng.choice([-1, 0, 1])
            if seeker.dir_y == 0 and seeker.dir_x == 0:
                seeker.dir_x = 1
            new_col = seeker.col + seeker.dir_x
            new_row = seeker.row + seeker.dir_y
            new_col = max(0, min(COLS - 1, new_col))
            new_row = max(0, min(ROWS - 1, new_row))
        seeker.col = new_col
        seeker.row = new_row

    def _expand_awareness(self, seeker: Seeker) -> None:
        seeker.awareness.add((seeker.col, seeker.row))
        new_cells: set[tuple[int, int]] = set()
        for ac, ar in seeker.awareness:
            for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nc, nr = ac + dc, ar + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if self.rng.random() < 0.5:
                        new_cells.add((nc, nr))
        seeker.awareness |= new_cells
        if len(seeker.awareness) > 50:
            seeker.awareness = set(self.rng.sample(
                sorted(seeker.awareness), 50))

    def _check_caught(self) -> bool:
        if self.is_hidden:
            return False
        if self.super_mode:
            return False
        player_pos = (self.player_col, self.player_row)
        for seeker in self.seekers:
            if player_pos == (seeker.col, seeker.row):
                self._update_heat(HEAT_CAUGHT)
                self.combo = 0
                cx = self.player_col * CELL + OFFSET_X + CELL // 2
                cy = self.player_row * CELL + OFFSET_Y + CELL // 2
                self._spawn_particles(cx, cy, RED, 15)
                self._add_floating_text(cx, cy - 10, "CAUGHT!", RED)
                return True
            if player_pos in seeker.awareness:
                self._home_seeker(seeker, player_pos)
        return False

    def _home_seeker(self, seeker: Seeker, target: tuple[int, int]) -> None:
        tc, tr = target
        if seeker.move_counter >= seeker.speed_frames - 1:
            seeker.move_counter = seeker.speed_frames - 1

    def _update_heat(self, amount: float) -> None:
        self.heat = min(HEAT_MAX, self.heat + amount)
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER

    def _update_super_mode(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0
                self.combo = 0

    def _update_difficulty(self) -> None:
        elapsed = (GAME_TIME - self.game_timer) // FPS
        if elapsed != self.elapsed_seconds:
            self.elapsed_seconds = elapsed
            self.speed_frames_current = max(
                SEEKER_SPEED_MIN,
                SEEKER_SPEED_INITIAL - elapsed // 12,
            )
            self.awareness_interval = max(
                SEEKER_AWARENESS_MIN,
                SEEKER_AWARENESS_INITIAL - (elapsed * 30) // 60,
            )
            self.respawn_interval = max(
                SPOT_RESPAWN_MIN,
                SPOT_RESPAWN_BASE - (elapsed * 120) // 60,
            )
            for seeker in self.seekers:
                seeker.speed_frames = self.speed_frames_current

    def _update_player(self) -> None:
        if self.move_cooldown > 0:
            self.move_cooldown -= 1
            return
        moved = False
        new_col = self.player_col
        new_row = self.player_row
        if pyxel.btn(pyxel.KEY_UP):
            new_row -= 1
            moved = True
        elif pyxel.btn(pyxel.KEY_DOWN):
            new_row += 1
            moved = True
        elif pyxel.btn(pyxel.KEY_LEFT):
            new_col -= 1
            moved = True
        elif pyxel.btn(pyxel.KEY_RIGHT):
            new_col += 1
            moved = True
        if moved:
            new_col = max(0, min(COLS - 1, new_col))
            new_row = max(0, min(ROWS - 1, new_row))
            if new_col != self.player_col or new_row != self.player_row:
                self.player_col = new_col
                self.player_row = new_row
                self.move_cooldown = MOVE_COOLDOWN
                if self.is_hidden:
                    self.is_hidden = False
                    self.current_spot_color = None
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._attempt_hide()

    def _attempt_hide(self) -> None:
        for i, spot in enumerate(self.spots):
            if spot.col == self.player_col and spot.row == self.player_row:
                gained = self._try_hide(spot.color)
                if gained > 0:
                    cx = spot.col * CELL + OFFSET_X + CELL // 2
                    cy = spot.row * CELL + OFFSET_Y + CELL // 2
                    self._add_floating_text(
                        cx, cy, f"+{gained}", spot.color,
                    )
                    count = 15 if self.super_mode else 8
                    self._spawn_particles(cx, cy, spot.color, count)
                self.spots[i].respawn_timer = self.rng.randint(
                    self.respawn_interval, self.respawn_interval + 120
                )
                return

    def _update_spots(self) -> None:
        new_spots: list[HidingSpot] = []
        for spot in self.spots:
            if spot.respawn_timer > 0:
                spot.respawn_timer -= 1
                if spot.respawn_timer <= 0:
                    self._respawn_spot()
                    continue
            new_spots.append(spot)
        self.spots = new_spots
        if len(self.spots) < MIN_SPOTS:
            for _ in range(MIN_SPOTS - len(self.spots)):
                self._respawn_spot()

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

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self.rng.randint(10, 20)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color))

    def _update_playing(self) -> None:
        self.frame += 1
        self.game_timer -= 1

        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        self.heat = max(0.0, self.heat - HEAT_DECAY)

        self._update_player()
        self._update_spots()
        self._update_seekers()
        self._check_caught()
        self._update_super_mode()
        self._update_difficulty()
        self._update_particles()
        self._update_floating_texts()

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self.frame += 1
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset_playing()
            return

        if self.phase == Phase.GAME_OVER:
            self.frame += 1
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset_playing()
            return

        if self.phase == Phase.PLAYING:
            self._update_playing()

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 36, 30, "HIDE SURGE", WHITE)
        pyxel.text(SCREEN_W // 2 - 56, 48, "Hide from the seekers!", GRAY)
        pyxel.text(SCREEN_W // 2 - 72, 70, "Match same-color spots to build COMBO!", LIME)
        pyxel.text(SCREEN_W // 2 - 60, 85, "COMBO x4 = SUPER HIDE!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 72, 105, "Arrow keys: Move  SPACE: Hide", GRAY)

        for i, c in enumerate(SPOT_COLORS):
            cx = SCREEN_W // 2 - 28 + i * 16
            pyxel.rect(cx, 120, 10, 10, c)

        if (self.frame // 15) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - 52, 200, "PRESS SPACE TO START", WHITE)

        self._draw_particles()

    def _draw_playing(self) -> None:
        self._draw_grid()
        self._draw_spots()
        self._draw_awareness()
        self._draw_seekers()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_grid(self) -> None:
        for c in range(COLS + 1):
            x = OFFSET_X + c * CELL
            pyxel.line(x, OFFSET_Y, x, OFFSET_Y + ROWS * CELL, GRAY)
        for r in range(ROWS + 1):
            y = OFFSET_Y + r * CELL
            pyxel.line(OFFSET_X, y, OFFSET_X + COLS * CELL, y, GRAY)

    def _draw_spots(self) -> None:
        for spot in self.spots:
            if spot.respawn_timer > 0:
                continue
            x = OFFSET_X + spot.col * CELL + 2
            y = OFFSET_Y + spot.row * CELL + 2
            pyxel.rect(x, y, CELL - 4, CELL - 4, spot.color)
            pyxel.rectb(x, y, CELL - 4, CELL - 4, BLACK)

    def _draw_awareness(self) -> None:
        for seeker in self.seekers:
            for ac, ar in seeker.awareness:
                x = OFFSET_X + ac * CELL + 5
                y = OFFSET_Y + ar * CELL + 5
                pyxel.rect(x, y, CELL - 10, CELL - 10, seeker.color)

    def _draw_seekers(self) -> None:
        for seeker in self.seekers:
            cx = OFFSET_X + seeker.col * CELL + CELL // 2
            cy = OFFSET_Y + seeker.row * CELL + CELL // 2
            pyxel.circ(cx, cy, 7, seeker.color)
            pyxel.circb(cx, cy, 7, WHITE)

    def _draw_player(self) -> None:
        cx = OFFSET_X + self.player_col * CELL + CELL // 2
        cy = OFFSET_Y + self.player_row * CELL + CELL // 2
        if self.super_mode:
            idx = (self.frame // 4) % len(SPOT_COLORS)
            color = SPOT_COLORS[idx]
            pyxel.circ(cx, cy, 8, color)
            pyxel.circb(cx, cy, 8, WHITE)
            pulse = 4 + (self.frame % 8) // 2
            pyxel.circb(cx, cy, 8 + pulse, WHITE)
            pyxel.circb(cx, cy, 8 + pulse + 2, YELLOW)
        elif self.is_hidden:
            pyxel.circ(cx, cy, 5, DARK_BLUE)
            pyxel.circb(cx, cy, 5, WHITE)
        else:
            pyxel.circ(cx, cy, 8, GREEN)
            pyxel.circb(cx, cy, 8, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 20.0
            color = p.color
            if alpha < 0.3 and color > 0:
                color = GRAY
            pyxel.pset(int(p.x), int(p.y), color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            color = ft.color if alpha >= 0.3 else GRAY
            pyxel.text(int(ft.x) - 16, int(ft.y), ft.text, color)

    def _draw_hud(self) -> None:
        time_sec = max(0, self.game_timer // FPS)
        time_color = RED if time_sec < 15 else WHITE
        pyxel.text(8, 8, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 24, 8, f"COMBO: x{self.combo}", YELLOW)
        pyxel.text(SCREEN_W - 50, 8, f"{time_sec}s", time_color)

        status = self._status_text()
        pyxel.text(8, 20, status, GREEN if self.is_hidden else ORANGE)

        if self.super_mode:
            super_sec = self.super_timer // FPS
            idx = (self.frame // 4) % len(SPOT_COLORS)
            pyxel.text(
                SCREEN_W // 2 - 50, SCREEN_H - 40,
                f"SUPER HIDE! {super_sec}s", SPOT_COLORS[idx],
            )

        self._draw_heat_bar()

    def _status_text(self) -> str:
        if self.super_mode:
            return "SUPER"
        if self.is_hidden:
            return "HIDDEN"
        return "EXPOSED"

    def _draw_heat_bar(self) -> None:
        bar_w = 120
        bar_h = 6
        bar_x = SCREEN_W - bar_w - 8
        bar_y = SCREEN_H - 18
        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, GRAY)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, BLACK)
        fill_w = int(bar_w * self.heat / HEAT_MAX)
        heat_color = RED if self.heat > 70 else (YELLOW if self.heat > 40 else LIME)
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_color)
        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, WHITE)
        pyxel.text(bar_x - 30, bar_y - 2, "HEAT", GRAY)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 28, 30, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 52, 60, f"Score: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 52, 80, f"Max Combo: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 40, 100, f"Heat: {self.heat:.0f}", ORANGE)
        survived = (GAME_TIME - self.game_timer) // FPS
        pyxel.text(SCREEN_W // 2 - 40, 120, f"Time: {survived}s", LIME)
        if (self.frame // 15) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - 56, 190, "PRESS SPACE TO RETRY", WHITE)


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="Hide Surge", fps=FPS)
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
