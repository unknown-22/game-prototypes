"""CHROMA CROSS — Color-match lane crossing game.

Reinterpreted from game_idea_factory #1 (Score 32.0, alchemy synthesis deckbuilder):
  "synthesis/compression" → COMBO chain → SYNTHESIS super mode
  "split/converge across paths" → crossing lanes with branching obstacles

Core mechanic: Cross colored lanes; matching-color obstacles are safe (build COMBO).
COMBO >= 5 triggers SYNTHESIS: all colors safe, 3x score for 3 seconds.
Reach the top to level up. Wrong-color hits cost HP.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel

# ── Constants ──
SCREEN_W = 256
SCREEN_H = 256
LANE_H = 32
LANE_COUNT = 8
PLAYER_W = 12
PLAYER_H = 12
PLAYER_SPEED = 2
OBSTACLE_H = 18
OBSTACLE_MIN_W = 28
OBSTACLE_MAX_W = 52
OBSTACLE_MIN_GAP = 36  # minimum gap between obstacles in same lane

# Color indices for obstacles/player (raw ints — pyxel.COLOR_* used only in draw)
# RED=8, GREEN=3, YELLOW=10, LIGHT_BLUE=6
COLOR_VALS: tuple[int, ...] = (8, 3, 10, 6)
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "YELLOW", "BLUE")
NUM_COLORS = len(COLOR_VALS)

COMBO_THRESHOLD = 5  # combos needed to activate SYNTHESIS
SUPER_DURATION = 180  # frames (3 sec at 60fps)
COMBO_TIMEOUT = 90  # frames before combo resets (1.5 sec)
DAMAGE_COOLDOWN = 30  # invincibility frames after taking damage


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Obstacle:
    """A colored obstacle block moving horizontally in a lane."""

    x: float
    y: int  # top of the lane this obstacle lives in
    w: int
    color_idx: int
    speed: float  # px/frame; positive = right, negative = left

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def color_val(self) -> int:
        return COLOR_VALS[self.color_idx]


@dataclass
class Particle:
    """Visual particle for effects."""

    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    """Floating score/combo text."""

    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    """Color-match lane crossing game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA CROSS")
        self._rng: random.Random = random.Random()
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        """Initialize all mutable state (called by __init__ and headless tests)."""
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.player_x: float = SCREEN_W / 2
        self.player_y: float = SCREEN_H - LANE_H / 2
        self.player_color_idx: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.combo_timer: int = 0
        self.hp: int = 5
        self.max_hp: int = 5
        self.level: int = 1
        self.damage_cooldown: int = 0
        self.obstacles: list[Obstacle] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.super_mode: bool = False
        self.super_timer: int = 0

    # ── Properties ──

    @property
    def player_color(self) -> int:
        return COLOR_VALS[self.player_color_idx]

    # ── Geometry helpers ──

    @staticmethod
    def _player_rect(
        px: float, py: float
    ) -> tuple[float, float, float, float]:
        """Returns (left, top, right, bottom)."""
        hw = PLAYER_W / 2
        hh = PLAYER_H / 2
        return (px - hw, py - hh, px + hw, py + hh)

    @staticmethod
    def _rects_overlap(
        a: tuple[float, float, float, float],
        b: tuple[float, float, float, float],
    ) -> bool:
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]

    # ── Lane spawning ──

    def _spawn_lanes(self) -> None:
        """Fill all lanes with obstacles."""
        self.obstacles.clear()
        num_per_lane = min(1 + self.level // 3, 4)
        speed_scale = 1.0 + self.level * 0.15

        for lane in range(LANE_COUNT):
            lane_y = lane * LANE_H
            count = self._rng.randint(num_per_lane, num_per_lane + 1)
            attempts = 0
            spawned: list[Obstacle] = []
            while len(spawned) < count and attempts < 30:
                attempts += 1
                w = self._rng.randint(OBSTACLE_MIN_W, OBSTACLE_MAX_W)
                x = self._rng.uniform(0, SCREEN_W - w)
                # Check gap against already-spawned obstacles in this lane
                too_close = False
                for existing in spawned:
                    gap = abs(x - existing.x) - (w + existing.w) / 2
                    if gap < OBSTACLE_MIN_GAP:
                        too_close = True
                        break
                if too_close:
                    continue
                color_idx = self._rng.randint(0, NUM_COLORS - 1)
                spd = self._rng.uniform(0.8, 1.5) * speed_scale
                if self._rng.random() < 0.5:
                    spd = -spd
                spawned.append(
                    Obstacle(x=x, y=lane_y, w=w, color_idx=color_idx, speed=spd)
                )
            self.obstacles.extend(spawned)

    # ── Effects ──

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int = 8
    ) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            spd = self._rng.uniform(1, 3)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * spd,
                    vy=math.sin(angle) * spd,
                    life=15 + self._rng.randint(0, 10),
                    color=color,
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=40, color=color)
        )

    # ── Super mode ──

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_particles(self.player_x, self.player_y, pyxel.COLOR_WHITE, 16)
        self._spawn_floating_text(
            self.player_x, self.player_y - 12, "SYNTHESIS!", pyxel.COLOR_YELLOW
        )

    def _deactivate_super(self) -> None:
        self.super_mode = False
        self.super_timer = 0

    # ── Damage ──

    def _take_damage(self) -> None:
        if self.super_mode or self.damage_cooldown > 0:
            return
        self.hp -= 1
        self.combo = 0
        self.combo_timer = 0
        self.damage_cooldown = DAMAGE_COOLDOWN
        self._spawn_particles(self.player_x, self.player_y, pyxel.COLOR_RED, 8)
        self._spawn_floating_text(
            self.player_x, self.player_y - 12, "-1 HP", pyxel.COLOR_RED
        )
        if self.hp <= 0:
            self.phase = Phase.GAME_OVER
            self._spawn_particles(
                self.player_x, self.player_y, pyxel.COLOR_ORANGE, 20
            )

    # ── Update ──

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._init_state()
                self.phase = Phase.PLAYING
                self._spawn_lanes()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._init_state()
                self.phase = Phase.PLAYING
                self._spawn_lanes()
            return

        # ── PLAYING ──
        self._update_player()
        self._update_obstacles()
        self._update_collisions()
        self._update_timers()
        self._update_particles()
        self._update_floating_texts()
        self._check_goal()

    def _update_player(self) -> None:
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = PLAYER_SPEED

        # Diagonal normalization
        if dx != 0 and dy != 0:
            inv = 1.0 / math.sqrt(2.0)
            dx *= inv
            dy *= inv

        self.player_x += dx
        self.player_y += dy

        # Clamp within screen
        hw = PLAYER_W / 2
        hh = PLAYER_H / 2
        self.player_x = max(hw, min(SCREEN_W - hw, self.player_x))
        self.player_y = max(hh, min(SCREEN_H - hh, self.player_y))

        # Color cycling
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.player_color_idx = (self.player_color_idx + 1) % NUM_COLORS

    def _update_obstacles(self) -> None:
        for obs in self.obstacles:
            obs.x += obs.speed
            # Wrap around the screen
            if obs.speed > 0 and obs.x > SCREEN_W:
                obs.x = -float(obs.w)
            elif obs.speed < 0 and obs.x < -obs.w:
                obs.x = float(SCREEN_W)

    def _update_collisions(self) -> None:
        p_rect = self._player_rect(self.player_x, self.player_y)
        hit_matching = False
        hit_wrong = False

        for obs in self.obstacles:
            obs_rect = (obs.x, obs.y + 2, obs.x + obs.w, obs.y + OBSTACLE_H - 2)
            if self._rects_overlap(p_rect, obs_rect):
                if self.super_mode or obs.color_idx == self.player_color_idx:
                    hit_matching = True
                else:
                    hit_wrong = True

        if hit_wrong:
            self._take_damage()
        elif hit_matching:
            self.combo += 1
            self.combo_timer = COMBO_TIMEOUT
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()

    def _update_timers(self) -> None:
        if self.combo > 0:
            self.combo_timer -= 1
            if self.combo_timer <= 0:
                self.combo = 0

        if self.damage_cooldown > 0:
            self.damage_cooldown -= 1

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._deactivate_super()

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _check_goal(self) -> None:
        """Check if player reached top lane."""
        if self.player_y < LANE_H / 2:
            base = 100
            combo_bonus = self.combo * 20
            super_mult = 3 if self.super_mode else 1
            points = (base + combo_bonus) * super_mult
            self.score += points
            self.level += 1
            self.player_y = SCREEN_H - LANE_H / 2
            self._spawn_lanes()
            self._spawn_particles(
                self.player_x, self.player_y, pyxel.COLOR_YELLOW, 12
            )
            self._spawn_floating_text(
                self.player_x,
                LANE_H / 2,
                f"+{points}",
                pyxel.COLOR_YELLOW,
            )

    # ── Draw ──

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_lane_lines()
        self._draw_obstacles()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        pyxel.text(cx - 44, cy - 30, "CHROMA CROSS", pyxel.COLOR_WHITE)
        pyxel.text(cx - 60, cy, "Arrow/WASD: Move", pyxel.COLOR_GRAY)
        pyxel.text(cx - 60, cy + 12, "SPACE: Cycle Color", pyxel.COLOR_GRAY)
        pyxel.text(cx - 70, cy + 28, "Match color = safe + COMBO", pyxel.COLOR_GREEN)
        pyxel.text(cx - 70, cy + 40, "Wrong color = -1 HP", pyxel.COLOR_RED)
        pyxel.text(cx - 70, cy + 52, "Reach top to LEVEL UP", pyxel.COLOR_YELLOW)
        pyxel.text(cx - 48, cy + 74, "PRESS SPACE TO START", pyxel.COLOR_YELLOW)

    def _draw_lane_lines(self) -> None:
        for i in range(1, LANE_COUNT):
            y = i * LANE_H
            pyxel.line(0, y, SCREEN_W, y, pyxel.COLOR_NAVY)

    def _draw_obstacles(self) -> None:
        for obs in self.obstacles:
            if self.super_mode:
                color = COLOR_VALS[(pyxel.frame_count // 4) % NUM_COLORS]
            else:
                color = obs.color_val
            x = int(obs.x)
            y = obs.y + 4
            pyxel.rect(x, y, obs.w, OBSTACLE_H, color)
            pyxel.rectb(x, y, obs.w, OBSTACLE_H, pyxel.COLOR_WHITE)

    def _draw_player(self) -> None:
        px = int(self.player_x - PLAYER_W // 2)
        py = int(self.player_y - PLAYER_H // 2)

        if self.super_mode:
            # Rainbow aura
            aura_c = COLOR_VALS[(pyxel.frame_count // 3) % NUM_COLORS]
            pyxel.rect(px - 2, py - 2, PLAYER_W + 4, PLAYER_H + 4, aura_c)

        # Damage invincibility blink
        if self.damage_cooldown > 0 and (pyxel.frame_count // 4) % 2 == 0:
            pyxel.rectb(px, py, PLAYER_W, PLAYER_H, pyxel.COLOR_WHITE)
            return

        pyxel.rect(px, py, PLAYER_W, PLAYER_H, self.player_color)
        pyxel.rectb(px, py, PLAYER_W, PLAYER_H, pyxel.COLOR_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40.0
            if alpha > 0.2:
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 9, pyxel.COLOR_NAVY)

        # Score
        pyxel.text(2, 1, f"SC:{self.score}", pyxel.COLOR_WHITE)

        # Level
        pyxel.text(SCREEN_W // 2 - 16, 1, f"LV:{self.level}", pyxel.COLOR_YELLOW)

        # Combo
        combo_color = pyxel.COLOR_WHITE
        if self.combo >= COMBO_THRESHOLD:
            combo_color = pyxel.COLOR_YELLOW
        elif self.combo >= 3:
            combo_color = pyxel.COLOR_ORANGE
        pyxel.text(SCREEN_W - 56, 1, f"CMB:{self.combo}", combo_color)

        # HP hearts at bottom
        for i in range(self.max_hp):
            hx = 2 + i * 10
            hy = SCREEN_H - 9
            if i < self.hp:
                pyxel.rect(hx, hy, 8, 6, pyxel.COLOR_RED)
            else:
                pyxel.rectb(hx, hy, 8, 6, pyxel.COLOR_GRAY)

        # Color indicator
        cname = COLOR_NAMES[self.player_color_idx]
        pyxel.text(SCREEN_W - 60, SCREEN_H - 24, f"[{cname}]", self.player_color)

        # Super mode bar
        if self.super_mode:
            remaining = self.super_timer / SUPER_DURATION
            bar_w = 80
            bar_h = 4
            bar_x = SCREEN_W // 2 - bar_w // 2
            bar_y = 10
            pyxel.rectb(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_WHITE)
            fill_w = int(bar_w * remaining)
            if fill_w > 0:
                fill_color = COLOR_VALS[(pyxel.frame_count // 6) % NUM_COLORS]
                pyxel.rect(bar_x, bar_y, fill_w, bar_h, fill_color)

    def _draw_game_over_overlay(self) -> None:
        # Checkerboard dim
        for y in range(SCREEN_H):
            if y % 4 < 2:
                for x in range(SCREEN_W):
                    if (x // 4 + y // 4) % 2 == 0:
                        pyxel.pset(x, y, pyxel.COLOR_BLACK)

        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        pyxel.text(cx - 28, cy - 24, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(cx - 36, cy - 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(cx - 44, cy + 8, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_YELLOW)
        pyxel.text(cx - 32, cy + 20, f"LEVEL: {self.level}", pyxel.COLOR_GRAY)
        pyxel.text(cx - 52, cy + 40, "PRESS SPACE TO RETRY", pyxel.COLOR_YELLOW)


if __name__ == "__main__":
    Game()
