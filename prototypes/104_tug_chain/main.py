from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Color Constants ──────────────────────────────────────────────────────────
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

SEGMENT_COLORS = [RED, GREEN, LIGHT_BLUE, YELLOW]
RAINBOW_COLORS = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]

# ── Enums / Data ─────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class RopeSegment:
    x: float
    y: float
    color: int
    width: int = 32
    height: int = 12


@dataclass
class GhostTrail:
    x: float
    y: float
    color: int
    life: int
    width: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Game ─────────────────────────────────────────────────────────────────────


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    GAME_DURATION = 3600  # 60 seconds
    PULL_WINDOW = 90  # frames to match color
    AI_PULL_MIN = 120
    AI_PULL_MAX = 180
    COLOR_CYCLE_INTERVAL = 60
    PULL_COLOR_CYCLE_INTERVAL = 120
    SUPER_DURATION = 300
    GHOST_LIFE = 60
    MAX_HEAT = 10
    WIN_THRESHOLD = 40.0
    LOSE_THRESHOLD = 200.0
    SEGMENT_COUNT = 8
    SEGMENT_WIDTH = 32
    SEGMENT_HEIGHT = 12
    ROPE_Y = 120

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, "TUG CHAIN", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.timer = self.GAME_DURATION
        self.rope_x = 100.0
        self.rope_y = self.ROPE_Y
        self.pull_color = SEGMENT_COLORS[0]
        self.pull_timer = self.PULL_WINDOW
        self.super_mode = False
        self.super_timer = 0
        self.ai_pull_timer = self._rng.randint(self.AI_PULL_MIN, self.AI_PULL_MAX)
        self.ai_pull_color = SEGMENT_COLORS[0]
        self.game_over_reason = ""
        self.shake_frames = 0
        self.grip_zone_index = 3
        self.ghost_bonus = 0
        self.color_index = 0
        self._color_cycle_timer = 0
        self.segments: list[RopeSegment] = []
        self.ghosts: list[GhostTrail] = []
        self.particles: list[Particle] = []
        self._create_segments()
        self._update_segments()

    def _create_segments(self) -> list[RopeSegment]:
        self.segments = []
        x = self.rope_x
        for i in range(self.SEGMENT_COUNT):
            color = self._rng.choice(SEGMENT_COLORS)
            self.segments.append(
                RopeSegment(x=x, y=self.rope_y, color=color, width=self.SEGMENT_WIDTH, height=self.SEGMENT_HEIGHT)
            )
            x += self.SEGMENT_WIDTH
        return self.segments

    def _update_segments(self) -> None:
        x = self.rope_x
        for i, seg in enumerate(self.segments):
            seg.x = x + self.SEGMENT_WIDTH / 2
            seg.y = self.rope_y
            x += self.SEGMENT_WIDTH

    def _update_rope_colors(self) -> None:
        self._color_cycle_timer += 1
        if self._color_cycle_timer >= self.COLOR_CYCLE_INTERVAL:
            self._color_cycle_timer = 0
            for seg in self.segments:
                seg.color = self._rng.choice(SEGMENT_COLORS)

    def _cycle_pull_color(self) -> None:
        self._color_cycle_timer += 1
        if self._color_cycle_timer >= self.PULL_COLOR_CYCLE_INTERVAL:
            self._color_cycle_timer = 0
            self.color_index = (self.color_index + 1) % len(SEGMENT_COLORS)

    def _ai_pull(self) -> None:
        self.ai_pull_timer -= 1
        if self.ai_pull_timer <= 0:
            self.ai_pull_timer = self._rng.randint(self.AI_PULL_MIN, self.AI_PULL_MAX)
            self._advance_rope(toward_player=-4.0)

    def compute_pull_force(self) -> float:
        base = 6.0
        bonus = self.ghost_bonus * 2.0
        multiplier = 3.0 if self.super_mode else 1.0
        return (base + bonus) * multiplier

    def _pull_success(self) -> None:
        force = self.compute_pull_force()
        self._advance_rope(toward_player=force)
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self.score += self.combo * 10
        self.pull_timer = self.PULL_WINDOW

        grip = self.get_grip_segment()
        if grip:
            gx = grip.x
            gy = grip.y
            self.ghosts.append(
                GhostTrail(x=gx, y=gy, color=grip.color, life=self.GHOST_LIFE, width=self.SEGMENT_WIDTH)
            )
            self._spawn_particles(gx, gy, grip.color, 8)

        if self.combo >= 4 and not self.super_mode:
            self.super_mode = True
            self.super_timer = self.SUPER_DURATION
            self.shake_frames = 10
            if grip:
                self._spawn_particles(grip.x, grip.y, grip.color, 20)

    def _pull_fail(self, reason: str) -> None:
        self.combo = 0
        self.heat += 2
        if reason == "wrong":
            self.heat += 3
        self.pull_timer = self.PULL_WINDOW
        self._advance_rope(toward_player=-3.0)

    def _try_pull(self, matched: bool) -> None:
        if matched:
            self._pull_success()
        else:
            self._pull_fail("wrong")

    def get_grip_segment(self) -> RopeSegment | None:
        if 0 <= self.grip_zone_index < len(self.segments):
            return self.segments[self.grip_zone_index]
        return None

    def _advance_rope(self, toward_player: float) -> None:
        self.rope_x -= toward_player
        self.rope_x = max(20.0, min(240.0, self.rope_x))
        self._update_segments()

    def _update_ghosts(self) -> None:
        for ghost in self.ghosts:
            ghost.life -= 1
        self.ghosts = [g for g in self.ghosts if g.life > 0]
        self.ghost_bonus = len(self.ghosts)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        colors = RAINBOW_COLORS if self.super_mode else [color]
        for _ in range(count):
            vx = self._rng.uniform(-3, 3)
            vy = self._rng.uniform(-5, -1)
            life = self._rng.randint(15, 30)
            c = self._rng.choice(colors)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=c))

    def _update_timers(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.pull_timer > 0:
            self.pull_timer -= 1
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

    def _check_win_lose(self) -> Phase | None:
        if self.rope_x < self.WIN_THRESHOLD:
            self.game_over_reason = "WIN!"
            return Phase.GAME_OVER
        if self.rope_x > self.LOSE_THRESHOLD:
            self.game_over_reason = "PULLED AWAY!"
            return Phase.GAME_OVER
        if self.heat >= self.MAX_HEAT:
            self.game_over_reason = "OVERHEAT!"
            return Phase.GAME_OVER
        if self.timer <= 0:
            self.game_over_reason = "TIME UP!"
            return Phase.GAME_OVER
        return None

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.GAME_OVER:
                self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._update_timers()
        self._update_rope_colors()
        self._cycle_pull_color()
        self._ai_pull()
        self._update_ghosts()
        self._update_particles()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if pyxel.btnp(pyxel.KEY_SPACE):
            grip = self.get_grip_segment()
            if grip:
                matched = grip.color == self.pull_color
                self._try_pull(matched)

        if self.pull_timer <= 0:
            self._pull_fail("timeout")

        result = self._check_win_lose()
        if result is not None:
            self.phase = result
            if self.game_over_reason == "WIN!":
                self._spawn_particles(self.SCREEN_W / 2, self.SCREEN_H / 2, YELLOW, 30)

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.TITLE

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.shake_frames > 0:
            sx = self._rng.randint(-4, 4)
            sy = self._rng.randint(-4, 4)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING:
                self._draw_playing()
            case Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(110, 60, "TUG CHAIN", WHITE)
        pyxel.text(82, 76, "Tug of War with Color Chains", GRAY)
        blink = (pyxel.frame_count // 30) % 2 == 0
        if blink:
            pyxel.text(105, 120, "Press SPACE to start", YELLOW)

        # decorative rope
        for i in range(10):
            rx = 30 + i * 28
            ry = 200
            c = SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            pyxel.rect(rx, ry, 26, 10, c)
            if i < 9:
                pyxel.line(rx + 26, ry + 5, rx + 28, ry + 5, GRAY)

    def _draw_playing(self) -> None:
        # rope segments
        prev_end_x: float | None = None
        prev_end_y: float | None = None
        for i, seg in enumerate(self.segments):
            left = seg.x - seg.width // 2
            top = seg.y - seg.height // 2
            pyxel.rect(left, top, seg.width, seg.height, seg.color)

            # grip zone highlight
            if i == self.grip_zone_index:
                pulse = int(4 + 4 * math.sin(pyxel.frame_count * 0.2))
                pyxel.rectb(left - 2, top - 2, seg.width + 4, seg.height + 4, YELLOW)
                pyxel.circ(seg.x, seg.y, 8 + pulse, YELLOW)

            # connect segments with line
            if prev_end_x is not None and prev_end_y is not None:
                pyxel.line(prev_end_x, prev_end_y, left, seg.y, GRAY)
            prev_end_x = left + seg.width
            prev_end_y = seg.y

        # ghost trails
        for ghost in self.ghosts:
            c = ghost.color if ghost.life > 30 else GRAY
            left = ghost.x - ghost.width // 2
            top = ghost.y - self.SEGMENT_HEIGHT // 2
            pyxel.rect(left, top, ghost.width, self.SEGMENT_HEIGHT, c)

        # particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # player stick figure (left)
        player_x = 30
        player_base_y = self.rope_y
        pyxel.rect(player_x - 4, player_base_y - 20, 8, 28, WHITE)  # body
        pyxel.rect(player_x - 8, player_base_y - 26, 16, 8, WHITE)  # head
        # arms reaching toward rope
        pyxel.rect(player_x + 4, player_base_y - 10, int(self.rope_x - player_x), 4, WHITE)

        # AI stick figure (right)
        ai_x = 280
        ai_base_y = self.rope_y
        pyxel.rect(ai_x - 4, ai_base_y - 20, 8, 28, GRAY)  # body
        pyxel.rect(ai_x - 8, ai_base_y - 26, 16, 8, GRAY)  # head
        # arms reaching toward rope
        rope_right = self.rope_x + self.SEGMENT_COUNT * self.SEGMENT_WIDTH
        pyxel.rect(int(rope_right), ai_base_y - 10, int(ai_x - rope_right), 4, GRAY)

        # HUD
        pyxel.text(4, 4, f"Score: {self.score}", WHITE)
        combo_color = YELLOW if self.combo >= 4 else WHITE
        pyxel.text(130, 4, f"COMBO x{self.combo}", combo_color)
        pyxel.text(200, 4, f"MAX: {self.max_combo}", GRAY)

        # HEAT bar (top-right)
        heat_x = 210
        heat_y = 16
        pyxel.rect(heat_x, heat_y, 100, 6, DARK_BLUE)
        heat_fill = int(100 * self.heat / self.MAX_HEAT)
        if heat_fill > 0:
            heat_color = YELLOW if self.heat >= 7 else RED
            pyxel.rect(heat_x, heat_y, heat_fill, 6, heat_color)
        pyxel.text(heat_x + 102, heat_y, "HEAT", GRAY)

        # pull color indicator
        pyxel.text(4, 18, "PULL:", GRAY)
        pyxel.rect(32, 18, 16, 8, self.pull_color)

        # grip zone color indicator
        grip = self.get_grip_segment()
        if grip:
            pyxel.text(4, 30, "GRIP:", GRAY)
            pyxel.rect(32, 30, 16, 8, grip.color)

        # match indicator
        if grip and grip.color == self.pull_color:
            pyxel.text(56, 24, "MATCH!", LIME)
        elif grip:
            pyxel.text(56, 24, "NO MATCH", RED)

        # SUPER MODE indicator
        if self.super_mode:
            rainbow_idx = (pyxel.frame_count // 4) % len(RAINBOW_COLORS)
            pyxel.text(110, 35, "SUPER PULL!", RAINBOW_COLORS[rainbow_idx])

        # Timer bar (bottom)
        bar_w = 300
        bar_h = 8
        bar_x = 10
        bar_y = self.SCREEN_H - 16
        fill = int(bar_w * self.timer / self.GAME_DURATION)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        if fill > 0:
            timer_color = CYAN
            if self.timer < 600:
                timer_color = RED
            elif self.timer < 1200:
                timer_color = YELLOW
            pyxel.rect(bar_x, bar_y, fill, bar_h, timer_color)
        pyxel.text(bar_x + bar_w // 2 - 14, bar_y + 2, f"TIME: {self.timer // 60}", WHITE)

        # pull timer gauge (small bar under grip zone)
        grip = self.get_grip_segment()
        if grip:
            pyxel.text(grip.x - 14, grip.y + 20, f"{self.pull_timer}", WHITE)

    def _draw_game_over(self) -> None:
        pyxel.text(120, 50, "GAME OVER", WHITE)
        pyxel.text(110, 65, self.game_over_reason, YELLOW)
        pyxel.text(90, 90, f"Score: {self.score}", WHITE)
        pyxel.text(90, 105, f"Max COMBO: {self.max_combo}", YELLOW)
        blink = (pyxel.frame_count // 30) % 2 == 0
        if blink:
            pyxel.text(95, 140, "Press SPACE to retry", WHITE)

        # particles for win celebration
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2
            p.life -= 1
            if p.life > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)
        self.particles = [p for p in self.particles if p.life > 0]


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
