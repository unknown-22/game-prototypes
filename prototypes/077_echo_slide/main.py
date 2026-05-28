"""ECHO SLIDE - 色合わせカーリング/シャッフルボードゲーム"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30
RINK_TOP = 40
RINK_BOTTOM = 190
TARGET_CX = 160
TARGET_CY = 210
LAUNCH_Y = 55
PUCK_RADIUS = 8
FRICTION = 0.94
STOP_THRESHOLD = 0.3
MAX_POWER = 10.0
POWER_SCALE = 0.12
MIN_DRAG = 8
PUCKS_PER_ROUND = 10
PARTICLE_LIFE = 25
FLOAT_TEXT_LIFE = 40
GHOST_RECORD_INTERVAL = 4
ECHO_OVERLAP_DIST = 15

RING_OUTER_R = 50
RING_MID_R = 30
RING_CENTER_R = 10
RING_SHRINK_PER_ROUND = 5

SCORE_OUTER = 100
SCORE_MID = 200
SCORE_CENTER = 300

ECHO_BONUS_MULT = 1.5
TRAIL_BONUS_MULT = 1.25
SUPER_SLIDE_MULT = 2
SUPER_SLIDE_COMBO = 3

COLORS: list[int] = [8, 6, 11, 10]
COLOR_DIM: dict[int, int] = {8: 4, 6: 1, 11: 3, 10: 9}


class Phase(StrEnum):
    TITLE = "TITLE"
    AIMING = "AIMING"
    SLIDING = "SLIDING"
    SCORING = "SCORING"
    GAME_OVER = "GAME_OVER"


@dataclass
class Puck:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    color: int = 0
    active: bool = True
    landed: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="ECHO SLIDE", fps=FPS, display_scale=2)
        font_path = str(Path(__file__).with_name("k8x12.bdf"))
        pyxel.load(font_path, exclude_images=True, exclude_sounds=True, exclude_musics=True)
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.round: int = 1
        self.pucks_remaining: int = PUCKS_PER_ROUND
        self.current_color: int = 0
        self.threshold: int = 500
        self.puck: Puck | None = None
        self.puck_path: list[tuple[float, float]] = []
        self.ghost_path: list[tuple[float, float]] = []
        self.ghost_landing_dist: float = -1.0
        self.ghost_color: int = 0
        self.super_slide: bool = False
        self.super_slide_frames: int = 0
        self._path_record_counter: int = 0

        self.aiming: bool = False
        self.aim_origin: tuple[int, int] = (0, 0)
        self.aim_end: tuple[int, int] = (0, 0)

        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.rng: random.Random = random.Random()

    def reset(self) -> None:
        self._init_state()
        self.phase = Phase.AIMING
        self.rng = random.Random()

    def _pick_color(self) -> int:
        return self.rng.choice(COLORS)

    def _ring_outer_r(self) -> int:
        return max(10, RING_OUTER_R - (self.round - 1) * RING_SHRINK_PER_ROUND)

    def _ring_mid_r(self) -> int:
        return max(5, RING_MID_R - (self.round - 1) * RING_SHRINK_PER_ROUND)

    def _ring_center_r(self) -> int:
        return max(3, RING_CENTER_R - (self.round - 1) * RING_SHRINK_PER_ROUND)

    def _dist_to_target(self, x: float, y: float) -> float:
        return math.hypot(x - TARGET_CX, y - TARGET_CY)

    def _score_ring(self, dist: float) -> int:
        if dist <= self._ring_center_r():
            return SCORE_CENTER
        if dist <= self._ring_mid_r():
            return SCORE_MID
        if dist <= self._ring_outer_r():
            return SCORE_OUTER
        return 0

    def _ring_name(self, dist: float) -> str:
        if dist <= self._ring_center_r():
            return "BULLSEYE"
        if dist <= self._ring_mid_r():
            return "MIDDLE"
        if dist <= self._ring_outer_r():
            return "OUTER"
        return "MISS"

    def _check_echo_bonus(
        self, landing_dist: float
    ) -> tuple[bool, bool]:
        echo = False
        trail = False
        if self.ghost_landing_dist < 0:
            return False, False
        if landing_dist < self.ghost_landing_dist:
            echo = True
        if self.ghost_path and self.puck_path:
            for gx, gy in self.ghost_path:
                for px, py in self.puck_path:
                    if math.hypot(gx - px, gy - py) < ECHO_OVERLAP_DIST:
                        trail = True
                        break
                if trail:
                    break
        return echo, trail

    def _compute_score(
        self, ring_score: int, combo: int, *, echo: bool, trail: bool, super_slide: bool
    ) -> int:
        score = ring_score * max(1, combo)
        if echo:
            score = int(score * ECHO_BONUS_MULT)
        if trail:
            score = int(score * TRAIL_BONUS_MULT)
        if super_slide:
            score *= SUPER_SLIDE_MULT
        return score

    def _launch_puck(self) -> None:
        ox, oy = self.aim_origin
        ex, ey = self.aim_end
        dx = ex - ox
        dy = ey - oy
        dist = math.hypot(dx, dy)
        if dist < MIN_DRAG:
            self.aiming = False
            return
        power = min(dist * POWER_SCALE, MAX_POWER)
        vx = dx / dist * power
        vy = dy / dist * power
        self.puck = Puck(
            x=float(ox),
            y=float(oy),
            vx=vx,
            vy=vy,
            color=self.current_color,
        )
        self.puck_path = [(float(ox), float(oy))]
        self._path_record_counter = 0
        self.aiming = False
        self.phase = Phase.SLIDING

    def _update_puck(self) -> None:
        if self.puck is None or not self.puck.active:
            return
        p = self.puck
        p.x += p.vx
        p.y += p.vy
        p.vx *= FRICTION
        p.vy *= FRICTION
        self._path_record_counter += 1
        if self._path_record_counter >= GHOST_RECORD_INTERVAL:
            self._path_record_counter = 0
            self.puck_path.append((p.x, p.y))
        speed = math.hypot(p.vx, p.vy)
        if speed < STOP_THRESHOLD:
            p.active = False
            p.landed = True
            self.puck_path.append((p.x, p.y))
            self._handle_landing()
        elif p.x < -PUCK_RADIUS or p.x > SCREEN_W + PUCK_RADIUS:
            p.active = False
            p.landed = False
            self._handle_miss()
        elif p.y < RINK_TOP - PUCK_RADIUS or p.y > SCREEN_H + PUCK_RADIUS:
            p.active = False
            p.landed = False
            self._handle_miss()

    def _handle_landing(self) -> None:
        if self.puck is None:
            return
        p = self.puck
        dist = self._dist_to_target(p.x, p.y)
        ring_score = self._score_ring(dist)

        if ring_score == 0:
            self._handle_miss()
            return

        prev_color = self.ghost_color if self.ghost_landing_dist >= 0 else -1
        same_color = p.color == prev_color

        if same_color:
            self.combo += 1
        else:
            self.combo = 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        super_slide = False
        if self.combo >= SUPER_SLIDE_COMBO:
            super_slide = True
            self.super_slide = True
            self.super_slide_frames = 60
        else:
            self.super_slide = False

        echo, trail = self._check_echo_bonus(dist)
        gained = self._compute_score(
            ring_score, self.combo, echo=echo, trail=trail, super_slide=super_slide
        )
        self.score += gained

        self.ghost_path = list(self.puck_path)
        self.ghost_landing_dist = dist
        self.ghost_color = p.color

        ring_name = self._ring_name(dist)
        self._spawn_landing_particles(p.x, p.y, p.color)
        self._spawn_floating_text(p.x, p.y - 10, f"+{gained}", pyxel.COLOR_YELLOW)
        self._spawn_floating_text(
            p.x, p.y - 20, ring_name, p.color if ring_score > 0 else pyxel.COLOR_RED
        )
        if self.combo > 1:
            self._spawn_floating_text(
                p.x, p.y - 30, f"COMBO x{self.combo}", pyxel.COLOR_LIME
            )
        if echo:
            self._spawn_floating_text(p.x, p.y - 40, "ECHO!", pyxel.COLOR_ORANGE)
        if trail:
            self._spawn_floating_text(p.x, p.y - 50, "TRAIL!", pyxel.COLOR_CYAN)
        if super_slide:
            self._spawn_floating_text(
                p.x, p.y - 60, "SUPER SLIDE!", pyxel.COLOR_WHITE
            )

        self.phase = Phase.SCORING

    def _handle_miss(self) -> None:
        self.combo = 0
        self.super_slide = False
        if self.puck is not None and self.puck.color is not None:
            self.ghost_color = self.puck.color
        self.ghost_path = list(self.puck_path)
        if self.puck is not None:
            self.ghost_landing_dist = self._dist_to_target(self.puck.x, self.puck.y)
        if self.puck is not None:
            self._spawn_floating_text(
                self.puck.x, self.puck.y - 10, "MISS", pyxel.COLOR_RED
            )
        self.phase = Phase.SCORING

    def _next_puck(self) -> None:
        self.pucks_remaining -= 1
        self.puck = None
        self.puck_path = []
        self._path_record_counter = 0

        if self.super_slide_frames > 0:
            self._spawn_super_slide_particles()

        if self.pucks_remaining <= 0:
            if self.score >= self.threshold:
                self.round += 1
                self.pucks_remaining = PUCKS_PER_ROUND
                self.threshold = (self.round - 0) * 500
                self.current_color = self._pick_color()
                self.phase = Phase.AIMING
                self._spawn_floating_text(
                    SCREEN_W // 2,
                    SCREEN_H // 2,
                    f"ROUND {self.round}",
                    pyxel.COLOR_WHITE,
                )
            else:
                self.phase = Phase.GAME_OVER
        else:
            self.current_color = self._pick_color()
            self.phase = Phase.AIMING

    def _spawn_landing_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(12):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=color,
                    life=PARTICLE_LIFE,
                )
            )

    def _spawn_super_slide_particles(self) -> None:
        if self.puck is None:
            return
        for _ in range(6):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.3, 1.0)
            self.particles.append(
                Particle(
                    x=self.puck.x,
                    y=self.puck.y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=pyxel.COLOR_YELLOW,
                    life=PARTICLE_LIFE // 2,
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=FLOAT_TEXT_LIFE, color=color)
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

    def _update_floating_texts(self) -> None:
        dead: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                dead.append(ft)
        for ft in dead:
            self.floating_texts.remove(ft)

    # ---- Update ----
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            return

        if self.super_slide_frames > 0:
            self.super_slide_frames -= 1
            if self.super_slide_frames <= 0:
                self.super_slide = False

        self._update_particles()
        self._update_floating_texts()

        if self.phase == Phase.AIMING:
            self._update_aiming(
                is_click=pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT),
                is_held=pyxel.btn(pyxel.MOUSE_BUTTON_LEFT),
                is_released=pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT),
                mouse_x=pyxel.mouse_x,
                mouse_y=pyxel.mouse_y,
            )
        elif self.phase == Phase.SLIDING:
            self._update_puck()
        elif self.phase == Phase.SCORING:
            self._update_scoring()

    def _update_aiming(
        self,
        *,
        is_click: bool,
        is_held: bool,
        is_released: bool,
        mouse_x: int,
        mouse_y: int,
    ) -> None:
        if is_click and not self.aiming:
            origin_y = min(mouse_y, RINK_BOTTOM - PUCK_RADIUS)
            self.aim_origin = (mouse_x, origin_y)
            self.aim_end = (mouse_x, origin_y)
            self.aiming = True
            if self.puck is not None:
                self.puck = None
                self.puck_path = []
            return

        if is_held and self.aiming:
            self.aim_end = (mouse_x, min(mouse_y, RINK_BOTTOM - PUCK_RADIUS))
            return

        if is_released and self.aiming:
            self._launch_puck()
            return

    def _update_scoring(self) -> None:
        self._next_puck()

    # ---- Draw ----
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()
        else:
            self._draw_game()

    def _draw_title(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY)
        title = "ECHO SLIDE"
        w = len(title) * 4
        pyxel.text(SCREEN_W // 2 - w // 2, 30, title, pyxel.COLOR_WHITE)

        lines = [
            "CLICK TO START",
            "",
            "CLICK-DRAG-RELEASE to aim and slide pucks",
            "Land in colored rings to score",
            "Same-color consecutive hits build COMBO",
            "Trace the ghost for ECHO/TRAIL bonuses",
            "COMBO >= 3 = SUPER SLIDE (2x score)",
            "",
            "10 pucks per round. Beat the threshold!",
            "Round " + str(self.round) + " threshold: " + str(self.threshold),
            "",
            "R = restart  |  Click = start",
        ]
        y = 55
        for line in lines:
            pyxel.text(SCREEN_W // 2 - len(line) * 2, y, line, pyxel.COLOR_GRAY)
            y += 10

        self._draw_sample_puck()
        self._draw_rings_static()

    def _draw_sample_puck(self) -> None:
        pyxel.circ(160, LAUNCH_Y + 5, PUCK_RADIUS, COLORS[0])
        pyxel.circb(160, LAUNCH_Y + 5, PUCK_RADIUS, pyxel.COLOR_WHITE)
        pyxel.text(160 - len("PUCK") * 2, LAUNCH_Y + 18, "PUCK", pyxel.COLOR_WHITE)

    def _draw_rings_static(self) -> None:
        pyxel.circb(TARGET_CX, TARGET_CY, RING_OUTER_R, pyxel.COLOR_WHITE)
        pyxel.circb(TARGET_CX, TARGET_CY, RING_MID_R, pyxel.COLOR_GRAY)
        pyxel.circb(TARGET_CX, TARGET_CY, RING_CENTER_R, pyxel.COLOR_ORANGE)

    def _draw_game(self) -> None:
        self._draw_rink()
        self._draw_rings()
        self._draw_ghost_trail()
        self._draw_puck()
        self._draw_aim_arrow()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_rink(self) -> None:
        pyxel.rect(0, RINK_TOP, SCREEN_W, RINK_BOTTOM - RINK_TOP, pyxel.COLOR_CYAN)
        pyxel.line(0, RINK_TOP, SCREEN_W, RINK_TOP, pyxel.COLOR_WHITE)
        pyxel.line(0, RINK_BOTTOM, SCREEN_W, RINK_BOTTOM, pyxel.COLOR_WHITE)
        pyxel.rect(0, RINK_BOTTOM, SCREEN_W, SCREEN_H - RINK_BOTTOM, pyxel.COLOR_DARK_BLUE)

    def _draw_rings(self) -> None:
        rr = self._ring_outer_r()
        mr = self._ring_mid_r()
        cr = self._ring_center_r()
        pulse = 1.0
        if self.super_slide_frames > 0:
            pulse = 1.0 + 0.5 * math.sin(pyxel.frame_count * 0.3)
        outer_r = int(rr * pulse)
        mid_r = int(mr * pulse)
        center_r = int(cr * pulse)

        outer_color = pyxel.COLOR_WHITE
        mid_color = pyxel.COLOR_GRAY
        center_color = pyxel.COLOR_ORANGE
        if self.super_slide_frames > 0:
            outer_color = pyxel.COLOR_YELLOW
            mid_color = pyxel.COLOR_YELLOW

        pyxel.circb(TARGET_CX, TARGET_CY, outer_r, outer_color)
        pyxel.circb(TARGET_CX, TARGET_CY, mid_r, mid_color)
        pyxel.circb(TARGET_CX, TARGET_CY, center_r, center_color)

    def _draw_ghost_trail(self) -> None:
        if not self.ghost_path or len(self.ghost_path) < 2:
            return
        color = COLOR_DIM.get(self.ghost_color, pyxel.COLOR_GRAY)
        if self.super_slide:
            color = self.ghost_color
        for i in range(len(self.ghost_path) - 1):
            x1, y1 = self.ghost_path[i]
            x2, y2 = self.ghost_path[i + 1]
            px1, py1 = int(x1), int(y1)
            px2, py2 = int(x2), int(y2)
            if px1 == px2 and py1 == py2:
                pyxel.pset(px1, py1, color)
            else:
                pyxel.line(px1, py1, px2, py2, color)

    def _draw_puck(self) -> None:
        if self.puck is None or not self.puck.active:
            return
        p = self.puck
        px, py = int(p.x), int(p.y)
        pyxel.circ(px, py, PUCK_RADIUS, p.color)
        pyxel.circb(px, py, PUCK_RADIUS, pyxel.COLOR_WHITE)
        if self.super_slide and self.puck.active:
            glow = 1 if pyxel.frame_count % 20 < 10 else 0
            if glow:
                pyxel.circb(px, py, PUCK_RADIUS + 2, pyxel.COLOR_YELLOW)

    def _draw_aim_arrow(self) -> None:
        if not self.aiming:
            return
        ox, oy = self.aim_origin
        ex, ey = self.aim_end
        dx = ex - ox
        dy = ey - oy
        dist = math.hypot(dx, dy)
        if dist < MIN_DRAG:
            pyxel.circ(ox, oy, 3, pyxel.COLOR_WHITE)
            return
        color = COLORS[COLORS.index(self.current_color)] if self.current_color in COLORS else pyxel.COLOR_WHITE
        if self.current_color in COLORS:
            idx = COLORS.index(self.current_color)
            color = COLORS[idx]
        else:
            color = pyxel.COLOR_WHITE

        steps = int(dist / 4)
        for i in range(steps):
            t = i / max(steps, 1)
            px = int(ox + dx * t)
            py = int(oy + dy * t)
            pyxel.pset(px, py, color)

        pyxel.circ(ox, oy, 3, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            px, py = int(p.x), int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                size = max(1, p.life // 6)
                pyxel.rect(px, py, size, size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            x = int(ft.x - len(ft.text) * 2)
            y = int(ft.y)
            pyxel.text(x, y, ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(4, 14, f"ROUND: {self.round}", pyxel.COLOR_WHITE)
        pyxel.text(4, 24, f"THRESHOLD: {self.threshold}", pyxel.COLOR_GRAY)

        pucks_text = f"PUCKS: {self.pucks_remaining}/{PUCKS_PER_ROUND}"
        pyxel.text(
            SCREEN_W // 2 - len(pucks_text) * 2, 4, pucks_text, pyxel.COLOR_WHITE
        )

        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            combo_color = pyxel.COLOR_YELLOW if self.combo >= SUPER_SLIDE_COMBO else pyxel.COLOR_WHITE
            pyxel.text(
                SCREEN_W // 2 - len(combo_text) * 2,
                14,
                combo_text,
                combo_color,
            )

        color_x = SCREEN_W - 44
        pyxel.text(color_x, 4, "NEXT:", pyxel.COLOR_GRAY)
        if self.phase in (Phase.AIMING, Phase.SLIDING):
            pyxel.circ(color_x + 28, 10, PUCK_RADIUS // 2, self.current_color)
            pyxel.circb(color_x + 28, 10, PUCK_RADIUS // 2, pyxel.COLOR_WHITE)

        if self.super_slide:
            ss_text = "SUPER SLIDE!"
            pyxel.text(
                SCREEN_W // 2 - len(ss_text) * 2,
                24,
                ss_text,
                pyxel.COLOR_YELLOW,
            )

        pyxel.text(4, SCREEN_H - 8, "R: Restart", pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        bx = SCREEN_W // 2 - 80
        by = SCREEN_H // 2 - 55
        bw = 160
        bh = 120
        pyxel.rect(bx, by, bw, bh, pyxel.COLOR_BLACK)
        pyxel.rectb(bx, by, bw, bh, pyxel.COLOR_WHITE)

        lines = [
            ("GAME OVER", pyxel.COLOR_RED),
            ("", pyxel.COLOR_WHITE),
            (f"SCORE: {self.score}", pyxel.COLOR_YELLOW),
            (f"ROUND: {self.round}", pyxel.COLOR_WHITE),
            (f"MAX COMBO: {self.max_combo}", pyxel.COLOR_WHITE),
            (f"THRESHOLD: {self.threshold}", pyxel.COLOR_RED),
            ("", pyxel.COLOR_WHITE),
            ("CLICK OR ENTER TO RETRY", pyxel.COLOR_GRAY),
        ]
        y = SCREEN_H // 2 - 45
        for text, col in lines:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, col)
            y += 12


if __name__ == "__main__":
    Game()
