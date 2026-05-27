"""CHROMA PRISM - レーザーを回して同色ターゲットを連続破壊する反射パズル"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import StrEnum

import pyxel

# ---- Constants ----
SCREEN_W = 320
SCREEN_H = 240
PRISM_X = SCREEN_W // 2
PRISM_Y = SCREEN_H // 2
TARGET_SIZE = 12
FPS = 30
HEAT_MAX = 10
ECHO_DURATION = 5 * FPS
COMBO_ECHO_THRESHOLD = 3
HEAT_COOLDOWN = 3 * FPS
MAX_TARGETS = 8
MIN_SPAWN_DIST = 40
SPAWN_MARGIN = 16

GAME_COLORS: list[int] = [
    pyxel.COLOR_RED,
    pyxel.COLOR_GREEN,
    pyxel.COLOR_DARK_BLUE,
    pyxel.COLOR_YELLOW,
]
COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]

DIR_UP = 0
DIR_RIGHT = 1
DIR_DOWN = 2
DIR_LEFT = 3


# ---- Enum ----
class Phase(StrEnum):
    TITLE = "TITLE"
    PLAYING = "PLAYING"
    GAME_OVER = "GAME_OVER"


# ---- Data Classes ----
@dataclass
class Target:
    x: float
    y: float
    color: int
    hp: int = 1
    active: bool = True


@dataclass
class EchoBeam:
    direction: int
    color: int
    timer: int
    hit_this_frame: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ---- Module-level helpers ----
def _line_rect_intersect(
    x1: float, y1: float, x2: float, y2: float,
    rx: float, ry: float, rw: float, rh: float,
) -> bool:
    if abs(x2 - x1) < 0.1:
        if rx <= x1 <= rx + rw:
            line_min = min(y1, y2)
            line_max = max(y1, y2)
            return not (ry + rh < line_min or ry > line_max)
        return False
    else:
        if ry <= y1 <= ry + rh:
            line_min = min(x1, x2)
            line_max = max(x1, x2)
            return not (rx + rw < line_min or rx > line_max)
        return False


def _center_dist(t: Target) -> float:
    return math.hypot(t.x + TARGET_SIZE / 2 - PRISM_X, t.y + TARGET_SIZE / 2 - PRISM_Y)


# ---- Game Class ----
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA PRISM", fps=FPS)
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.prism_angle: int = 0
        self.active_color_idx: int = 0
        self.targets: list[Target] = []
        self.echo_beams: list[EchoBeam] = []
        self.echo_timer: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.heat_timer: int = 0
        self.score: int = 0
        self.game_timer: int = 0
        self.particles: list[Particle] = []
        self.last_hits: list[tuple[int, int]] = []
        self.targets_destroyed: int = 0
        self.wave: int = 0
        self.rng: random.Random = random.Random()

    def reset(self) -> None:
        self._init_state()
        self.phase = Phase.PLAYING
        self._next_wave()

    @property
    def active_color(self) -> int:
        return GAME_COLORS[self.active_color_idx]

    # ---- Beam Direction ----
    def _get_beam_direction(self, color_idx: int) -> int:
        """Cardinal direction (0-3) for a color at current prism rotation."""
        return ((color_idx * 90 + self.prism_angle) % 360) // 90

    def _active_beam_direction(self) -> int:
        return self._get_beam_direction(self.active_color_idx)

    @staticmethod
    def _target_dist_along_beam(target: Target, direction: int) -> float:
        cx = target.x + TARGET_SIZE / 2
        cy = target.y + TARGET_SIZE / 2
        if direction == DIR_UP:
            return PRISM_Y - cy
        elif direction == DIR_DOWN:
            return cy - PRISM_Y
        elif direction == DIR_RIGHT:
            return cx - PRISM_X
        else:
            return PRISM_X - cx

    # ---- Wave / Spawning ----
    def _next_wave(self) -> None:
        self.wave += 1
        self.targets.clear()
        self.echo_beams.clear()
        self.echo_timer = 0
        self.combo = 0
        self.last_hits.clear()

        if self.wave == 1:
            count = 4
            self.game_timer = 60 * FPS
        elif self.wave == 2:
            count = 6
            self.game_timer = 50 * FPS + 10 * FPS
        else:
            count = min(MAX_TARGETS, 4 + self.wave * 2)
            self.game_timer = 45 * FPS + 10 * FPS

        self._spawn_targets(count)

    def _spawn_targets(self, count: int) -> None:
        max_hp = 1 if self.wave == 1 else (2 if self.wave == 2 else 3)
        positions = self._generate_target_positions(count)
        for x, y in positions:
            hp = self.rng.randint(1, max_hp)
            color = self.rng.choice(GAME_COLORS)
            self.targets.append(Target(x=x, y=y, color=color, hp=hp))

    def _generate_target_positions(self, count: int) -> list[tuple[float, float]]:
        positions: list[tuple[float, float]] = []
        margin = SPAWN_MARGIN
        max_attempts = 200

        for _ in range(count):
            for _ in range(max_attempts):
                side = self.rng.randint(0, 3)
                if side == 0:
                    x = self.rng.uniform(margin, SCREEN_W - margin - TARGET_SIZE)
                    y = margin
                elif side == 1:
                    x = SCREEN_W - margin - TARGET_SIZE
                    y = self.rng.uniform(margin, SCREEN_H - margin - TARGET_SIZE)
                elif side == 2:
                    x = self.rng.uniform(margin, SCREEN_W - margin - TARGET_SIZE)
                    y = SCREEN_H - margin - TARGET_SIZE
                else:
                    x = margin
                    y = self.rng.uniform(margin, SCREEN_H - margin - TARGET_SIZE)

                cx = x + TARGET_SIZE / 2
                cy = y + TARGET_SIZE / 2
                if math.hypot(cx - PRISM_X, cy - PRISM_Y) < MIN_SPAWN_DIST:
                    continue

                overlap = any(
                    abs(x - px) < TARGET_SIZE and abs(y - py) < TARGET_SIZE
                    for px, py in positions
                )
                if overlap:
                    continue

                positions.append((x, y))
                break

        return positions

    # ---- Hit Detection ----
    def _check_beam_hits(self) -> None:
        direction = self._active_beam_direction()
        beam_color = self.active_color
        beam_seg = self._beam_segment(direction)

        closest_target, closest_dist = self._find_closest_target(beam_seg)
        if closest_target is not None:
            if closest_target.color == beam_color:
                self._handle_hit(closest_target, direction, beam_color, is_echo=False)
            else:
                self._handle_miss()
            return

        for echo in self.echo_beams:
            if echo.hit_this_frame:
                continue
            echo_seg = self._beam_segment(echo.direction)
            echo_target, _ = self._find_closest_target(echo_seg)
            if echo_target is not None:
                echo.hit_this_frame = True
                echo_target.hp -= 1
                if echo_target.hp <= 0:
                    echo_target.active = False
                    self._on_target_destroyed(echo_target, is_echo=True)
                else:
                    self._spawn_particles(
                        echo_target.x + TARGET_SIZE / 2,
                        echo_target.y + TARGET_SIZE / 2,
                        echo.color,
                    )
                break

    def _beam_segment(self, direction: int) -> tuple[float, float, float, float]:
        if direction == DIR_UP:
            return (PRISM_X, PRISM_Y, PRISM_X, 0)
        elif direction == DIR_RIGHT:
            return (PRISM_X, PRISM_Y, SCREEN_W, PRISM_Y)
        elif direction == DIR_DOWN:
            return (PRISM_X, PRISM_Y, PRISM_X, SCREEN_H)
        else:
            return (PRISM_X, PRISM_Y, 0, PRISM_Y)

    def _find_closest_target(
        self, beam_seg: tuple[float, float, float, float]
    ) -> tuple[Target | None, float]:
        x1, y1, x2, y2 = beam_seg
        direction = self._seg_direction(x1, y1, x2, y2)
        closest: Target | None = None
        closest_dist = float("inf")

        for target in self.targets:
            if not target.active:
                continue
            if _line_rect_intersect(x1, y1, x2, y2, target.x, target.y, TARGET_SIZE, TARGET_SIZE):
                dist = self._target_dist_along_beam(target, direction)
                if dist < closest_dist:
                    closest_dist = dist
                    closest = target

        return closest, closest_dist

    @staticmethod
    def _seg_direction(x1: float, y1: float, x2: float, y2: float) -> int:
        if abs(x2 - x1) < 0.1:
            return DIR_UP if y2 < y1 else DIR_DOWN
        return DIR_RIGHT if x2 > x1 else DIR_LEFT

    def _handle_hit(
        self, target: Target, direction: int, beam_color: int, *, is_echo: bool
    ) -> None:
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        target.hp -= 1
        if target.hp <= 0:
            target.active = False
            self._on_target_destroyed(target, is_echo=is_echo)
        else:
            self._spawn_particles(
                target.x + TARGET_SIZE / 2, target.y + TARGET_SIZE / 2, beam_color
            )

        self.last_hits.append((direction, beam_color))
        if len(self.last_hits) > 3:
            self.last_hits.pop(0)

        if self.combo >= COMBO_ECHO_THRESHOLD and self.echo_timer <= 0:
            self._activate_echo()

    def _handle_miss(self) -> None:
        self._add_heat(1)
        self.combo = 0

    def _on_target_destroyed(self, target: Target, *, is_echo: bool) -> None:
        if is_echo:
            self._add_score(50, is_echo=True)
        else:
            self._add_score(100, is_echo=False)

        self.targets_destroyed += 1
        self._spawn_particles(
            target.x + TARGET_SIZE / 2, target.y + TARGET_SIZE / 2, target.color
        )

    # ---- Echo System ----
    def _activate_echo(self) -> None:
        self.echo_timer = ECHO_DURATION
        self.echo_beams.clear()
        for direction, color in self.last_hits:
            self.echo_beams.append(
                EchoBeam(direction=direction, color=color, timer=ECHO_DURATION)
            )

    def _update_echo_beams(self) -> None:
        if self.echo_timer > 0:
            self.echo_timer -= 1

        expired: list[EchoBeam] = []
        for echo in self.echo_beams:
            echo.timer -= 1
            echo.hit_this_frame = False
            if echo.timer <= 0:
                expired.append(echo)
        for e in expired:
            self.echo_beams.remove(e)

    # ---- Scoring ----
    def _add_score(self, base: int, *, is_echo: bool) -> None:
        if is_echo:
            self.score += base + self.combo * 25
        else:
            self.score += base + self.combo * 50

    # ---- Heat ----
    def _add_heat(self, amount: int) -> None:
        self.heat += amount
        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            self.phase = Phase.GAME_OVER

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat_timer += 1
            if self.heat_timer >= HEAT_COOLDOWN:
                self.heat_timer = 0
                self.heat -= 1

    # ---- Particles ----
    def _spawn_particles(self, x: float, y: float, color: int) -> None:
        count = self.rng.randint(8, 12)
        for _ in range(count):
            vx = self.rng.uniform(-2.0, 2.0)
            vy = self.rng.uniform(-2.0, 2.0)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=20, color=color)
            )

    def _update_particles(self) -> None:
        dead: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                dead.append(p)
        for p in dead:
            self.particles.remove(p)

    # ---- Update ----
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        self._handle_input()
        self._check_beam_hits()
        self._update_echo_beams()
        self._update_heat()
        self._update_particles()

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER

        if not any(t.active for t in self.targets):
            self.score += 500 * self.wave
            self._next_wave()

    def _handle_input(self) -> None:
        if pyxel.btnp(pyxel.KEY_LEFT):
            self.prism_angle = (self.prism_angle - 90) % 360
        if pyxel.btnp(pyxel.KEY_RIGHT):
            self.prism_angle = (self.prism_angle + 90) % 360
        if pyxel.btnp(pyxel.KEY_UP):
            self.active_color_idx = (self.active_color_idx + 1) % len(GAME_COLORS)
        if pyxel.btnp(pyxel.KEY_DOWN):
            self.active_color_idx = (self.active_color_idx - 1) % len(GAME_COLORS)
        for i, key in enumerate(
            [pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3, pyxel.KEY_4]
        ):
            if pyxel.btnp(key):
                self.active_color_idx = i

    # ---- Draw ----
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "CHROMA PRISM"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 30, title, pyxel.COLOR_WHITE)

        instructions = [
            "PRESS ENTER TO START",
            "",
            "LEFT/RIGHT: Rotate Prism (aim beam)",
            "UP/DOWN:   Cycle Active Color",
            "1-4:       Direct Color Select",
            "",
            "Match beam color to target color!",
            "Build COMBO (3+) for ECHO BEAM",
            "Wrong color hit = HEAT +1",
            "HEAT 10 = GAME OVER",
        ]
        y = 55
        for line in instructions:
            pyxel.text(SCREEN_W // 2 - len(line) * 2, y, line, pyxel.COLOR_WHITE)
            y += 10

        self._draw_prism()
        self._draw_beams()

    def _draw_game(self) -> None:
        self._draw_beams()
        self._draw_echo_beams()

        for target in self.targets:
            if target.active:
                self._draw_target(target)

        self._draw_prism()
        self._draw_particles()
        self._draw_hud()

    def _draw_prism(self) -> None:
        cx, cy = PRISM_X, PRISM_Y
        size = 10
        color = self.active_color if self.phase != Phase.TITLE else pyxel.COLOR_WHITE

        angle_rad = math.radians(self.prism_angle)
        pts: list[tuple[float, float]] = []
        for i in range(4):
            a = angle_rad + i * math.pi / 2
            pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))

        pyxel.tri(pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1], color)
        pyxel.tri(pts[0][0], pts[0][1], pts[2][0], pts[2][1], pts[3][0], pts[3][1], color)

        pyxel.circ(cx, cy, 4, pyxel.COLOR_BLACK)
        pyxel.circb(cx, cy, 5, color)

    def _draw_beams(self) -> None:
        cx, cy = PRISM_X, PRISM_Y

        for i in range(len(GAME_COLORS)):
            direction = self._get_beam_direction(i)
            color = GAME_COLORS[i]
            is_active = i == self.active_color_idx

            if not is_active and self.phase == Phase.PLAYING:
                color = pyxel.COLOR_GRAY

            if direction == DIR_UP:
                pyxel.line(cx, cy - 10, cx, 0, color)
            elif direction == DIR_RIGHT:
                pyxel.line(cx + 10, cy, SCREEN_W, cy, color)
            elif direction == DIR_DOWN:
                pyxel.line(cx, cy + 10, cx, SCREEN_H, color)
            else:
                pyxel.line(cx - 10, cy, 0, cy, color)

    def _draw_echo_beams(self) -> None:
        cx, cy = PRISM_X, PRISM_Y
        for echo in self.echo_beams:
            alpha = max(0.0, echo.timer / ECHO_DURATION)
            col = echo.color if alpha > 0.3 else pyxel.COLOR_GRAY

            if echo.direction == DIR_UP:
                self._draw_dotted_line(cx, cy - 10, cx, 0, col)
            elif echo.direction == DIR_RIGHT:
                self._draw_dotted_line(cx + 10, cy, SCREEN_W, cy, col)
            elif echo.direction == DIR_DOWN:
                self._draw_dotted_line(cx, cy + 10, cx, SCREEN_H, col)
            else:
                self._draw_dotted_line(cx - 10, cy, 0, cy, col)

    @staticmethod
    def _draw_dotted_line(
        x1: float, y1: float, x2: float, y2: float, col: int
    ) -> None:
        if abs(x2 - x1) < 0.1:
            for y in range(int(min(y1, y2)), int(max(y1, y2)), 4):
                pyxel.pset(int(x1), y, col)
        else:
            for x in range(int(min(x1, x2)), int(max(x1, x2)), 4):
                pyxel.pset(x, int(y1), col)

    def _draw_target(self, target: Target) -> None:
        x, y = int(target.x), int(target.y)
        pyxel.rect(x, y, TARGET_SIZE, TARGET_SIZE, target.color)
        pyxel.rectb(x, y, TARGET_SIZE, TARGET_SIZE, pyxel.COLOR_WHITE)
        if target.hp > 1:
            hp_text = str(target.hp)
            pyxel.text(
                x + TARGET_SIZE // 2 - 1,
                y + TARGET_SIZE // 2 - 3,
                hp_text,
                pyxel.COLOR_WHITE,
            )

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 20
            col = p.color if alpha > 0.5 else pyxel.COLOR_GRAY
            px, py2 = int(p.x), int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py2 < SCREEN_H:
                pyxel.rect(px, py2, 2, 2, col)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)

        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            combo_col = pyxel.COLOR_YELLOW if self.combo >= COMBO_ECHO_THRESHOLD else pyxel.COLOR_WHITE
            pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 4, combo_text, combo_col)

        heat_text = f"HEAT: {self.heat}/{HEAT_MAX}"
        heat_col = pyxel.COLOR_RED if self.heat >= 7 else pyxel.COLOR_WHITE
        pyxel.text(SCREEN_W - len(heat_text) * 4 - 4, 4, heat_text, heat_col)

        bar_x = SCREEN_W - 54
        bar_w = 50
        pyxel.rectb(bar_x, 14, bar_w, 5, pyxel.COLOR_WHITE)
        fill_w = int(bar_w * self.heat / HEAT_MAX)
        if self.heat < 5:
            hc = pyxel.COLOR_GREEN
        elif self.heat < 8:
            hc = pyxel.COLOR_YELLOW
        else:
            hc = pyxel.COLOR_RED
        pyxel.rect(bar_x, 14, fill_w, 5, hc)

        if self.echo_timer > 0:
            echo_sec = self.echo_timer // FPS
            echo_text = f"ECHO: {echo_sec}s"
            pyxel.text(
                SCREEN_W // 2 - len(echo_text) * 2,
                18,
                echo_text,
                pyxel.COLOR_YELLOW,
            )

        time_sec = self.game_timer // FPS
        timer_text = f"TIME: {time_sec}s"
        timer_col = pyxel.COLOR_RED if time_sec <= 10 else pyxel.COLOR_WHITE
        pyxel.text(SCREEN_W // 2 - len(timer_text) * 2, SCREEN_H - 22, timer_text, timer_col)

        wave_text = f"WAVE {self.wave}"
        pyxel.text(
            SCREEN_W // 2 - len(wave_text) * 2,
            SCREEN_H - 10,
            wave_text,
            pyxel.COLOR_GRAY,
        )

        color_name = COLOR_NAMES[self.active_color_idx]
        pyxel.text(4, SCREEN_H - 15, f"COLOR: {color_name}", self.active_color)

    def _draw_game_over(self) -> None:
        bx = SCREEN_W // 2 - 80
        by = SCREEN_H // 2 - 50
        bw = 160
        bh = 100
        pyxel.rect(bx, by, bw, bh, pyxel.COLOR_BLACK)
        pyxel.rectb(bx, by, bw, bh, pyxel.COLOR_WHITE)

        lines = [
            ("GAME OVER", pyxel.COLOR_RED),
            ("", pyxel.COLOR_WHITE),
            (f"SCORE: {self.score}", pyxel.COLOR_YELLOW),
            (f"MAX COMBO: {self.max_combo}", pyxel.COLOR_WHITE),
            (f"TARGETS: {self.targets_destroyed}", pyxel.COLOR_WHITE),
            ("", pyxel.COLOR_WHITE),
            ("PRESS ENTER TO RESTART", pyxel.COLOR_GRAY),
        ]
        y = SCREEN_H // 2 - 40
        for text, col in lines:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, col)
            y += 12


if __name__ == "__main__":
    Game()
