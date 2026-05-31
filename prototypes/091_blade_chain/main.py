from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ─── Color Constants ───────────────────────────────────────────────────────────
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

BLADE_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
BLADE_COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]
BLADE_COLOR_LABELS: list[str] = ["R", "G", "B", "Y"]

FENCER_RADIUS = 12
BLADE_REACH = 60
LUNGE_FRAMES = 8
ECHO_LIFE = 60
PARTICLE_LIFE_MIN = 15
PARTICLE_LIFE_MAX = 25
FLOAT_LIFE = 20
SHAKE_FRAMES = 10
SUPER_LUNGE_THRESHOLD = 4
MATCH_DURATION = 90 * 30  # 2700 frames
ARENA_LEFT = 10
ARENA_TOP = 18
ARENA_RIGHT = 310
ARENA_BOTTOM = 232


# ─── Data Classes ──────────────────────────────────────────────────────────────


@dataclass
class Fencer:
    x: float
    y: float
    color: int
    hp: int = 10


@dataclass
class Echo:
    x: float
    y: float
    angle: float
    life: int
    color: int


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


# ─── Phase Enum ────────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    LUNGING = auto()
    AI_TURN = auto()
    GAME_OVER = auto()


# ─── Game Class ────────────────────────────────────────────────────────────────


class Game:
    BLADE_COLORS: ClassVar[list[int]] = [RED, GREEN, DARK_BLUE, YELLOW]

    def __init__(self) -> None:
        pyxel.init(320, 240, title="Blade Chain", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.timer: int = MATCH_DURATION
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.player: Fencer = Fencer(x=60.0, y=120.0, color=RED, hp=10)
        self.ai: Fencer = Fencer(x=260.0, y=120.0, color=GREEN, hp=10)
        self.player_color: int = 0
        self.last_player_color: int | None = None
        self.lunging_frame: int = 0
        self.lunge_start_x: float = 0.0
        self.lunge_start_y: float = 0.0
        self.lunge_angle: float = 0.0
        self.ai_cooldown: int = 0
        self.ai_lunging: bool = False
        self.ai_lunge_frame: int = 0
        self.ai_lunge_angle: float = 0.0
        self.echoes: list[Echo] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.shake_frames: int = 0
        self.super_lunge_active: bool = False
        self.hit_result: str = ""
        self.hit_result_timer: int = 0

    # ── Pure Functions ─────────────────────────────────────────────────────────

    @staticmethod
    def _is_blade_hitting(
        lunger_x: float,
        lunger_y: float,
        angle: float,
        target_x: float,
        target_y: float,
        target_r: float,
        reach: float,
    ) -> bool:
        end_x = lunger_x + math.cos(angle) * reach
        end_y = lunger_y + math.sin(angle) * reach
        dx = target_x - lunger_x
        dy = target_y - lunger_y
        bdx = end_x - lunger_x
        bdy = end_y - lunger_y
        denom = bdx * bdx + bdy * bdy
        if denom == 0:
            return math.hypot(dx, dy) <= target_r
        t = (dx * bdx + dy * bdy) / denom
        t = max(0.0, min(1.0, t))
        closest_x = lunger_x + bdx * t
        closest_y = lunger_y + bdy * t
        return math.hypot(closest_x - target_x, closest_y - target_y) <= target_r

    def _check_lunge_hit(self, lunger: Fencer, target: Fencer, angle: float) -> bool:
        return self._is_blade_hitting(
            lunger.x, lunger.y, angle,
            target.x, target.y, FENCER_RADIUS, BLADE_REACH,
        )

    def _compute_combo(self, hit_color: int) -> int:
        if self.last_player_color is not None and hit_color == self.last_player_color:
            self.combo += 1
        else:
            self.combo = 1
        self.last_player_color = hit_color
        self.super_lunge_active = self.combo >= SUPER_LUNGE_THRESHOLD
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        return self.combo

    # ── Player Actions ──────────────────────────────────────────────────────────

    def _swap_color(self, direction: int) -> None:
        self.player_color = (self.player_color + direction) % 4
        self.player.color = self.BLADE_COLORS[self.player_color]

    def _lunge(self) -> tuple[bool, str]:
        hit = self._check_lunge_hit(self.player, self.ai, self.lunge_angle)
        hit_color = self.BLADE_COLORS[self.player_color]
        if hit:
            self._compute_combo(hit_color)
            base_damage = 2 if self.super_lunge_active else 1
            damage = int(base_damage * (1 + self.combo * 0.5))
            self.score += damage
            self.ai.hp -= damage
            target_x = self.player.x + math.cos(self.lunge_angle) * BLADE_REACH * 0.5
            target_y = self.player.y + math.sin(self.lunge_angle) * BLADE_REACH * 0.5
            if self.super_lunge_active:
                self._add_particles(target_x, target_y, 20, PINK)
                self.shake_frames = SHAKE_FRAMES
                self._add_float(target_x, target_y - 10, f"SUPER x{self.combo}", PINK)
                self.hit_result = f"SUPER x{self.combo}!"
                return (True, "SUPER")
            else:
                self._add_particles(target_x, target_y, 8, hit_color)
                self._add_float(target_x, target_y - 10, f"COMBO x{self.combo}", hit_color)
                self.hit_result = f"HIT x{self.combo}"
                return (True, "HIT")
        else:
            self.combo = 0
            self.super_lunge_active = False
            end_x = self.player.x + math.cos(self.lunge_angle) * BLADE_REACH
            end_y = self.player.y + math.sin(self.lunge_angle) * BLADE_REACH
            self._add_particles(end_x, end_y, 4, GRAY)
            self.hit_result = "MISS"
            return (False, "MISS")

    # ── AI ──────────────────────────────────────────────────────────────────────

    def _set_ai_cooldown(self) -> None:
        progress = 1.0 - (self.timer / MATCH_DURATION)
        min_cd = int(40 - 20 * progress)
        max_cd = int(60 - 20 * progress)
        self.ai_cooldown = self._rng.randint(min_cd, max_cd)

    def _ai_lunge_execute(self) -> None:
        self.ai_lunging = True
        self.ai_lunge_frame = LUNGE_FRAMES
        dx = self.player.x - self.ai.x
        dy = self.player.y - self.ai.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.ai_lunge_angle = math.atan2(dy, dx)
        else:
            self.ai_lunge_angle = 0.0
        # AI picks a color — sometimes counters player's last used color
        if self.last_player_color is not None and self._rng.random() < 0.4:
            # Pick a random color different from player's last
            available = [c for c in self.BLADE_COLORS if c != self.last_player_color]
            self.ai.color = self._rng.choice(available) if available else self._rng.choice(self.BLADE_COLORS)
        else:
            self.ai.color = self._rng.choice(self.BLADE_COLORS)
        self._add_echo(self.ai.x, self.ai.y, self.ai_lunge_angle, self.ai.color)

    # ── Effects ─────────────────────────────────────────────────────────────────

    def _add_echo(self, x: float, y: float, angle: float, color: int) -> None:
        self.echoes.append(Echo(x=x, y=y, angle=angle, life=ECHO_LIFE, color=color))

    def _add_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 3.0)
            life = self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX)
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=life, color=color,
                )
            )

    def _add_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=FLOAT_LIFE, color=color))

    def _update_echoes(self) -> None:
        self.echoes = [e for e in self.echoes if e.life > 0]
        for e in self.echoes:
            e.life -= 1

    def _update_particles(self) -> None:
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1

    def _update_floats(self) -> None:
        self.floats = [f for f in self.floats if f.life > 0]
        for f in self.floats:
            f.y -= 1
            f.life -= 1

    def _tick_effects(self) -> None:
        self._update_echoes()
        self._update_particles()
        self._update_floats()

        if self.hit_result_timer > 0:
            self.hit_result_timer -= 1
            if self.hit_result_timer == 0:
                self.hit_result = ""

    # ── Update ──────────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.LUNGING:
            self._update_lunging()
        elif self.phase == Phase.AI_TURN:
            self._update_ai_turn()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.timer -= 1
        if self.ai_cooldown > 0:
            self.ai_cooldown -= 1
        self._tick_effects()
        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.heat >= 10 or self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        wheel = pyxel.mouse_wheel
        if wheel != 0:
            self._swap_color(1 if wheel > 0 else -1)

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.LUNGING
            self.lunging_frame = LUNGE_FRAMES
            self.lunge_start_x = self.player.x
            self.lunge_start_y = self.player.y
            self.lunge_angle = math.atan2(
                pyxel.mouse_y - self.player.y,
                pyxel.mouse_x - self.player.x,
            )
            self._add_echo(self.player.x, self.player.y, self.lunge_angle, self.BLADE_COLORS[self.player_color])
            self._lunge()
            self.hit_result_timer = 20

    def _update_lunging(self) -> None:
        self.lunging_frame -= 1
        self._tick_effects()
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.lunging_frame <= 0:
            self.phase = Phase.AI_TURN

    def _update_ai_turn(self) -> None:
        self._tick_effects()
        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.ai_lunging:
            self.ai_lunge_frame -= 1
            if self.ai_lunge_frame <= 0:
                hit = self._check_lunge_hit(self.ai, self.player, self.ai_lunge_angle)
                if hit:
                    self.heat += 1
                    px = (self.ai.x + self.player.x) / 2
                    py = (self.ai.y + self.player.y) / 2
                    self._add_particles(px, py, 8, ORANGE)
                    self._add_float(px, py - 10, "HIT!", ORANGE)
                    self.combo = 0
                    self.super_lunge_active = False
                else:
                    end_x = self.ai.x + math.cos(self.ai_lunge_angle) * BLADE_REACH
                    end_y = self.ai.y + math.sin(self.ai_lunge_angle) * BLADE_REACH
                    self._add_particles(end_x, end_y, 4, GRAY)
                self.ai_lunging = False
                self._set_ai_cooldown()
                self.phase = Phase.PLAYING
        else:
            if self.ai_cooldown <= 0:
                self._ai_lunge_execute()
            else:
                self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        self._tick_effects()
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    # ── Draw ────────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        # Screen shake
        if self.shake_frames > 0:
            sx = self._rng.randint(-3, 3)
            sy = self._rng.randint(-3, 3)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        self._draw_arena()
        self._draw_echoes()
        self._draw_blades()
        self._draw_fencers()
        self._draw_particles()
        self._draw_floats()
        self._draw_hud()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

        pyxel.camera(0, 0)

    def _draw_title(self) -> None:
        # Title
        title = "BLADE CHAIN"
        tw = len(title) * 4
        pyxel.text(160 - tw // 2, 60, title, WHITE)

        # Subtitle
        sub = "Color-Match Fencing Duel"
        sw = len(sub) * 4
        pyxel.text(160 - sw // 2, 78, sub, CYAN)

        # Instructions
        pyxel.text(50, 110, "Aim with MOUSE", WHITE)
        pyxel.text(50, 122, "CLICK to lunge", WHITE)
        pyxel.text(50, 134, "SCROLL to swap blade color", WHITE)
        pyxel.text(50, 150, "Match colors for COMBO", YELLOW)
        pyxel.text(50, 162, "x4 combo = SUPER LUNGE", PINK)

        # Start prompt
        prompt = "CLICK or SPACE to start"
        pw = len(prompt) * 4
        pyxel.text(160 - pw // 2, 200, prompt, WHITE)

        # Color legend
        pyxel.text(50, 185, "Colors:", WHITE)
        for i, (c, n) in enumerate(zip(BLADE_COLORS, BLADE_COLOR_LABELS)):
            pyxel.text(120 + i * 20, 185, n, c)

    def _draw_arena(self) -> None:
        pyxel.rect(ARENA_LEFT, ARENA_TOP, ARENA_RIGHT - ARENA_LEFT, ARENA_BOTTOM - ARENA_TOP, GRAY)
        pyxel.rectb(ARENA_LEFT, ARENA_TOP, ARENA_RIGHT - ARENA_LEFT, ARENA_BOTTOM - ARENA_TOP, WHITE)

    def _draw_echoes(self) -> None:
        for e in self.echoes:
            alpha = e.life / ECHO_LIFE
            end_x = e.x + math.cos(e.angle) * BLADE_REACH * alpha
            end_y = e.y + math.sin(e.angle) * BLADE_REACH * alpha
            # Fade echo by using darker shade based on life
            fade_color = CYAN if alpha > 0.5 else GRAY
            pyxel.line(int(e.x), int(e.y), int(end_x), int(end_y), fade_color)

    def _draw_blades(self) -> None:
        # Player lunge blade
        if self.phase == Phase.LUNGING and self.lunging_frame > 0:
            progress = 1.0 - (self.lunging_frame / LUNGE_FRAMES)
            length = BLADE_REACH * (1.0 - abs(progress - 0.5) * 2.0)
            end_x = self.player.x + math.cos(self.lunge_angle) * length
            end_y = self.player.y + math.sin(self.lunge_angle) * length
            blade_color = PINK if self.super_lunge_active else self.BLADE_COLORS[self.player_color]
            pyxel.line(
                int(self.player.x), int(self.player.y),
                int(end_x), int(end_y),
                blade_color,
            )

        # AI lunge blade
        if self.phase == Phase.AI_TURN and self.ai_lunging and self.ai_lunge_frame > 0:
            progress = 1.0 - (self.ai_lunge_frame / LUNGE_FRAMES)
            length = BLADE_REACH * (1.0 - abs(progress - 0.5) * 2.0)
            end_x = self.ai.x + math.cos(self.ai_lunge_angle) * length
            end_y = self.ai.y + math.sin(self.ai_lunge_angle) * length
            pyxel.line(
                int(self.ai.x), int(self.ai.y),
                int(end_x), int(end_y),
                self.ai.color,
            )

    def _draw_fencers(self) -> None:
        # Player fencer
        px, py = int(self.player.x), int(self.player.y)
        pyxel.circ(px, py, FENCER_RADIUS, self.player.color)
        pyxel.circb(px, py, FENCER_RADIUS, WHITE)
        # Aim line (always show direction to mouse)
        if self.phase in (Phase.PLAYING, Phase.LUNGING):
            aim_angle = math.atan2(pyxel.mouse_y - py, pyxel.mouse_x - px)
            aim_x = px + math.cos(aim_angle) * (FENCER_RADIUS + 4)
            aim_y = py + math.sin(aim_angle) * (FENCER_RADIUS + 4)
            pyxel.circ(int(aim_x), int(aim_y), 2, WHITE)

        # AI fencer
        ax, ay = int(self.ai.x), int(self.ai.y)
        pyxel.circ(ax, ay, FENCER_RADIUS, self.ai.color)
        pyxel.circb(ax, ay, FENCER_RADIUS, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / PARTICLE_LIFE_MAX
            size = max(1, int(3 * alpha))
            if size == 1:
                pyxel.pset(int(p.x), int(p.y), p.color)
            else:
                pyxel.circ(int(p.x), int(p.y), size, p.color)

    def _draw_floats(self) -> None:
        for f in self.floats:
            alpha = f.life / FLOAT_LIFE
            draw_color = f.color if alpha > 0.3 else GRAY
            text_width = len(f.text) * 4
            pyxel.text(int(f.x) - text_width // 2, int(f.y), f.text, draw_color)

    def _draw_hud(self) -> None:
        # Background bar
        pyxel.rect(0, 0, 320, 17, NAVY)
        pyxel.line(0, 17, 320, 17, WHITE)

        # Score (left)
        pyxel.text(4, 4, f"SCORE:{self.score:05d}", WHITE)

        # Combo (below score, left side)
        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}"
            combo_color = PINK if self.super_lunge_active else YELLOW
            pyxel.text(4, 20, combo_text, combo_color)

        # Hit result
        if self.hit_result and self.hit_result_timer > 0:
            c = PINK if "SUPER" in self.hit_result else (RED if "MISS" in self.hit_result else YELLOW)
            tw = len(self.hit_result) * 4
            pyxel.text(160 - tw // 2, 20, self.hit_result, c)

        # Timer (center)
        seconds = self.timer // 30
        timer_text = f"TIME:{seconds:02d}"
        pyxel.text(140, 4, timer_text, WHITE if seconds > 10 else RED)

        # Heat bar (right)
        heat_label = "HEAT"
        pyxel.text(260, 4, heat_label, ORANGE)
        bar_x = 296
        bar_w = 20
        bar_h = 8
        bar_y = 4
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        fill = int((self.heat / 10) * (bar_w - 2))
        if fill > 0:
            heat_color = RED if self.heat >= 8 else ORANGE
            pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, heat_color)

        # Color indicator
        color_label = f"BLADE: {BLADE_COLOR_LABELS[self.player_color]}"
        pyxel.text(4, 32, color_label, self.BLADE_COLORS[self.player_color])

    def _draw_game_over_overlay(self) -> None:
        # Semi-transparent overlay
        for y in range(40, 200, 2):
            pyxel.line(60, y, 260, y, BLACK)

        # Game Over text
        go_text = "GAME OVER"
        gw = len(go_text) * 4
        pyxel.text(160 - gw // 2, 70, go_text, RED)

        # Score
        score_text = f"SCORE: {self.score}"
        sw = len(score_text) * 4
        pyxel.text(160 - sw // 2, 95, score_text, WHITE)

        # Max combo
        combo_text = f"MAX COMBO: x{self.max_combo}"
        cw = len(combo_text) * 4
        pyxel.text(160 - cw // 2, 110, combo_text, YELLOW)

        # Cause of death
        if self.heat >= 10:
            cause = "Overheated!"
        else:
            cause = "Time Up!"
        cause_w = len(cause) * 4
        pyxel.text(160 - cause_w // 2, 130, cause, ORANGE if self.heat >= 10 else CYAN)

        # Retry
        retry = "CLICK or SPACE to retry"
        rw = len(retry) * 4
        pyxel.text(160 - rw // 2, 155, retry, WHITE)


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game()
