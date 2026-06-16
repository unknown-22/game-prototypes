"""SUMO SURGE - Top-down color-match sumo wrestling.

Push the AI opponent out of the ring using color-coded directional pushes.
Chain same-color pushes for COMBO -> SUPER SUMO (5s, 3x force, rainbow).
The most fun moment: building a 4-hit COMBO chain, triggering SUPER SUMO,
and blasting the opponent clean out of the ring in one massive rainbow push.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import ClassVar

import pyxel


# ============================================================
# Enums and Color Constants
# ============================================================


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    STUMBLE = auto()
    SUPER = auto()
    GAME_OVER = auto()


class PushColor(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2
    YELLOW = 3


PUSH_COLORS: tuple[int, int, int, int] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
RAINBOW: tuple[int, ...] = (8, 9, 10, 11, 12, 14, 15)
PUSH_KEYS: tuple[int, int, int, int] = (pyxel.KEY_Z, pyxel.KEY_X, pyxel.KEY_C, pyxel.KEY_V)
PUSH_NAMES: tuple[str, str, str, str] = ("Z:RED", "X:GRN", "C:BLU", "V:YEL")


# ============================================================
# Data Classes
# ============================================================


@dataclass
class Rikishi:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    radius: int = 12
    color: int = 8
    stumble_timer: float = 0.0


@dataclass
class Echo:
    x: float
    y: float
    life: float = 1.0
    color: int = 8


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: float
    color: int


# ============================================================
# Game Logic (pure, testable — no pyxel input calls)
# ============================================================


class Game:
    RING_CX: ClassVar[int] = 160
    RING_CY: ClassVar[int] = 120
    RING_RADIUS: ClassVar[int] = 100
    PUSH_FORCE: ClassVar[float] = 3.0
    SUPER_FORCE: ClassVar[float] = 9.0
    COMBO_THRESHOLD: ClassVar[int] = 4
    SUPER_DURATION: ClassVar[float] = 5.0
    STUMBLE_DURATION: ClassVar[float] = 2.0
    HEAT_MAX: ClassVar[float] = 100.0
    HEAT_PER_WRONG: ClassVar[float] = 15.0
    HEAT_DECAY: ClassVar[float] = 1.0
    PUSH_COOLDOWN: ClassVar[float] = 0.3
    FRICTION: ClassVar[float] = 0.95
    ECHO_LIFE: ClassVar[float] = 2.0
    MAX_ECHOS: ClassVar[int] = 10
    AI_PUSH_INTERVAL: ClassVar[float] = 0.8
    RECOIL_FACTOR: ClassVar[float] = 0.3
    SCREEN_W: ClassVar[int] = 320
    SCREEN_H: ClassVar[int] = 240

    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player: Rikishi = Rikishi(x=80.0, y=120.0)
        self.ai: Rikishi = Rikishi(x=240.0, y=120.0)
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.score: int = 0
        self.high_score: int = 0
        self.super_timer: float = 0.0
        self.stumble_timer: float = 0.0
        self.echos: list[Echo] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.push_cooldown: float = 0.0
        self.last_push_color: int = -1
        self._ai_timer: float = 0.0
        self._ai_color: int = 0
        self._result_display: str = ""
        self._result_reason: str = ""
        self.rng: random.Random = field(default_factory=random.Random)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.player = Rikishi(x=80.0, y=120.0)
        self.ai = Rikishi(x=240.0, y=120.0)
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.score = 0
        self.super_timer = 0.0
        self.stumble_timer = 0.0
        self.echos.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.push_cooldown = 0.0
        self.last_push_color = -1
        self._ai_timer = 0.0
        self._ai_color = 0
        self._result_display = ""
        self._result_reason = ""

    # --- Push System ---

    def _apply_push(self, color_idx: int, dx: float, dy: float) -> str:
        """Apply a push. Returns event string for floating text."""
        is_super = self.super_timer > 0.0
        color_match = is_super or (color_idx == self.last_push_color)

        if color_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            event = f"+COMBO x{self.combo}"
        else:
            if self.combo > 0:
                event = "COMBO BREAK"
            else:
                event = "MISS"
            self.combo = 0
            self.heat += self.HEAT_PER_WRONG
            if self.heat > self.HEAT_MAX:
                self.heat = self.HEAT_MAX

        self.last_push_color = color_idx

        force = self.SUPER_FORCE if is_super else self.PUSH_FORCE
        combo_bonus = 1.0 + (self.combo - 1) * 0.25 if self.combo > 0 else 1.0
        total_force = force * combo_bonus

        self.ai.vx += dx * total_force
        self.ai.vy += dy * total_force
        self.player.vx -= dx * total_force * self.RECOIL_FACTOR
        self.player.vy -= dy * total_force * self.RECOIL_FACTOR

        self._spawn_echo(self.player.x, self.player.y, PUSH_COLORS[color_idx])

        particle_color = PUSH_COLORS[color_idx]
        if is_super:
            particle_color = random.choice(RAINBOW)  # type: ignore[assignment]
        self._spawn_particles(self.ai.x, self.ai.y, dx, dy, particle_color, 8 if not is_super else 20)

        if is_super:
            self._add_floating_text(self.ai.x, self.ai.y - 10, "SUPER!", 1.0, 9)

        if color_match and self.combo >= self.COMBO_THRESHOLD and self.super_timer <= 0.0:
            self.super_timer = self.SUPER_DURATION
            self._add_floating_text(
                self.player.x, self.player.y - 20, "SUPER SUMO!", 1.5, 9
            )

        self.push_cooldown = self.PUSH_COOLDOWN
        return event

    def _can_push(self) -> bool:
        return (
            self.phase == Phase.PLAYING
            and self.push_cooldown <= 0.0
            and self.stumble_timer <= 0.0
        )

    # --- Ring-Out Detection ---

    def _check_ring_out(self) -> tuple[bool, bool]:
        """Return (player_out, ai_out)."""
        player_dist = math.hypot(
            self.player.x - self.RING_CX, self.player.y - self.RING_CY
        )
        ai_dist = math.hypot(
            self.ai.x - self.RING_CX, self.ai.y - self.RING_CY
        )
        player_out = player_dist > self.RING_RADIUS
        ai_out = ai_dist > self.RING_RADIUS
        return player_out, ai_out

    # --- Scoring ---

    def _calculate_score(self, is_win: bool) -> int:
        if not is_win:
            return 0
        base = 100
        multiplier = 1.0 + self.combo * 0.5
        if self.super_timer > 0.0:
            multiplier *= 2.0
        heat_penalty = 1.0 - self.heat / 200.0
        heat_penalty = max(0.5, heat_penalty)
        return int(base * multiplier * heat_penalty)

    # --- Echo System ---

    def _spawn_echo(self, x: float, y: float, color: int) -> None:
        self.echos.append(Echo(x=x, y=y, life=self.ECHO_LIFE, color=color))
        if len(self.echos) > self.MAX_ECHOS:
            self.echos.pop(0)

    def _check_echo_collect(self) -> None:
        for echo in list(self.echos):
            dist = math.hypot(self.player.x - echo.x, self.player.y - echo.y)
            if dist < self.player.radius + 5:
                self.heat = max(0.0, self.heat - 5.0)
                self._add_floating_text(echo.x, echo.y, "COOL -5", 0.8, 6)
                self.echos.remove(echo)

    # --- Physics ---

    def _update_physics(self, dt: float) -> None:
        for rikishi in (self.player, self.ai):
            rikishi.x += rikishi.vx
            rikishi.y += rikishi.vy
            rikishi.vx *= self.FRICTION
            rikishi.vy *= self.FRICTION

        dx = self.ai.x - self.player.x
        dy = self.ai.y - self.player.y
        dist = math.hypot(dx, dy)
        min_dist: float = self.player.radius + self.ai.radius + 2
        if dist < min_dist and dist > 0.0:
            overlap = min_dist - dist
            nx = dx / dist
            ny = dy / dist
            self.player.x -= nx * overlap * 0.5
            self.player.y -= ny * overlap * 0.5
            self.ai.x += nx * overlap * 0.5
            self.ai.y += ny * overlap * 0.5

    # --- AI ---

    def _update_ai(self, dt: float) -> None:
        if self.phase != Phase.PLAYING:
            return

        self._ai_timer += dt
        if self._ai_timer >= self.AI_PUSH_INTERVAL:
            self._ai_timer = 0.0
            self._ai_color = (self._ai_color + 1) % 4

            dx = self.player.x - self.ai.x
            dy = self.player.y - self.ai.y
            dist = math.hypot(dx, dy)
            if dist > 0.0:
                dx = dx / dist + self.rng.uniform(-0.3, 0.3)
                dy = dy / dist + self.rng.uniform(-0.3, 0.3)
                mag = math.hypot(dx, dy)
                if mag > 0.0:
                    dx /= mag
                    dy /= mag

                force = self.PUSH_FORCE * 0.8
                self.player.vx += dx * force
                self.player.vy += dy * force
                self.ai.vx -= dx * force * self.RECOIL_FACTOR
                self.ai.vy -= dy * force * self.RECOIL_FACTOR
                self.ai.color = PUSH_COLORS[self._ai_color]
                self._spawn_particles(
                    self.player.x, self.player.y, dx, dy,
                    PUSH_COLORS[self._ai_color], 5
                )

    # --- Timers ---

    def _update_timers(self, dt: float) -> None:
        if self.push_cooldown > 0.0:
            self.push_cooldown -= dt

        if self.super_timer > 0.0:
            self.super_timer -= dt
            if self.super_timer <= 0.0:
                self.super_timer = 0.0

        if self.stumble_timer > 0.0:
            self.stumble_timer -= dt
            if self.stumble_timer <= 0.0:
                self.stumble_timer = 0.0

        if self.heat >= self.HEAT_MAX and self.stumble_timer <= 0.0:
            self.stumble_timer = self.STUMBLE_DURATION
            self.heat = self.HEAT_MAX
            self._add_floating_text(
                self.player.x, self.player.y - 15, "STUMBLE!", 1.2, 8
            )
            self._spawn_particles(
                self.player.x, self.player.y, 0, -1,
                8, 5
            )

        if self.heat > 0.0 and self.stumble_timer <= 0.0:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY * dt)

    # --- Echos ---

    def _update_echos(self, dt: float) -> None:
        for echo in self.echos:
            echo.life -= dt / self.ECHO_LIFE
        self.echos = [e for e in self.echos if e.life > 0.0]

    # --- Particles ---

    def _spawn_particles(
        self, x: float, y: float, dx: float, dy: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=dx * self.rng.uniform(0.3, 1.5) + math.cos(angle) * speed * 0.5,
                    vy=dy * self.rng.uniform(0.3, 1.5) + math.sin(angle) * speed * 0.5,
                    life=self.rng.uniform(0.3, 1.0),
                    color=color,
                )
            )

    def _update_particles(self, dt: float) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= dt
        self.particles = [p for p in self.particles if p.life > 0.0]

    # --- Floating Text ---

    def _add_floating_text(
        self, x: float, y: float, text: str, life: float, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=life, color=color)
        )

    def _update_floating_texts(self, dt: float) -> None:
        for ft in self.floating_texts:
            ft.y -= 30.0 * dt
            ft.life -= dt
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0.0]

    # --- Phase Transitions ---

    def _check_phase_transitions(self) -> None:
        if self.phase not in (Phase.PLAYING, Phase.STUMBLE, Phase.SUPER):
            return

        player_out, ai_out = self._check_ring_out()

        if player_out and ai_out:
            self._on_defeat("Both fell out!")
        elif player_out:
            self._on_defeat("You were pushed out!")
        elif ai_out:
            self._on_victory()

    def _on_victory(self) -> None:
        self.score += self._calculate_score(True)
        if self.score > self.high_score:
            self.high_score = self.score
        self._result_display = "VICTORY!"
        self._result_reason = f"Score: {self.score}"
        self.phase = Phase.GAME_OVER
        self._spawn_particles(
            self.ai.x, self.ai.y, 0, -1,
            RAINBOW[0], 25
        )

    def _on_defeat(self, reason: str) -> None:
        self._result_display = "DEFEAT!"
        self._result_reason = reason
        self.phase = Phase.GAME_OVER
        self._spawn_particles(
            self.player.x, self.player.y, 0, -1,
            8, 25
        )

    # --- Main Update (called each frame) ---

    def update(self, dt: float) -> None:
        if self.phase == Phase.GAME_OVER:
            return

        self._update_timers(dt)
        self._update_ai(dt)
        self._update_physics(dt)
        self._update_echos(dt)
        self._update_particles(dt)
        self._update_floating_texts(dt)

        if self.phase in (Phase.PLAYING, Phase.STUMBLE, Phase.SUPER):
            self._check_echo_collect()
            self._check_phase_transitions()

            if self.stumble_timer > 0.0 and self.phase != Phase.STUMBLE:
                self.phase = Phase.STUMBLE
            elif self.stumble_timer <= 0.0 and self.phase == Phase.STUMBLE:
                self.phase = Phase.PLAYING

            if self.super_timer > 0.0 and self.phase != Phase.SUPER:
                self.phase = Phase.SUPER
            elif self.super_timer <= 0.0 and self.phase == Phase.SUPER:
                self.phase = Phase.PLAYING

    # --- Input Processing (called from App) ---

    def handle_push(self, color_idx: int) -> None:
        if not self._can_push():
            return

        directions = (
            (1.0, 0.0),   # RED -> RIGHT
            (0.0, -1.0),  # GREEN -> UP
            (-1.0, 0.0),  # BLUE -> LEFT
            (0.0, 1.0),   # YELLOW -> DOWN
        )
        dx, dy = directions[color_idx]
        event = self._apply_push(color_idx, dx, dy)
        if event and event not in ("MISS",):
            self._add_floating_text(
                self.ai.x, self.ai.y - 10, event, 0.8,
                PUSH_COLORS[color_idx]
            )


# ============================================================
# Pyxel App (handles drawing and input)
# ============================================================


class App:
    def __init__(self) -> None:
        pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="SUMO SURGE")
        self.game = Game()
        pyxel.run(self._update, self._draw)

    # --- Update ---

    def _update(self) -> None:
        game = self.game

        if game.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
            return

        if game.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                game.phase = Phase.TITLE
            return

        dt: float = 1.0 / 30.0

        for color_idx, key in enumerate(PUSH_KEYS):
            if pyxel.btnp(key):
                game.handle_push(color_idx)

        game.update(dt)

    # --- Draw ---

    def _draw(self) -> None:
        pyxel.cls(0)

        if self.game.phase == Phase.TITLE:
            self._draw_title()
        elif self.game.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_play()

    def _draw_title(self) -> None:
        game = self.game

        # Ring outline at center
        pyxel.circb(Game.RING_CX, Game.RING_CY, Game.RING_RADIUS, 7)

        title = "SUMO SURGE"
        title_w = len(title) * 4
        pyxel.text(Game.SCREEN_W // 2 - title_w // 2, 30, title, 7)

        subtitle = "Color-Match Sumo Wrestling"
        sub_w = len(subtitle) * 4
        pyxel.text(Game.SCREEN_W // 2 - sub_w // 2, 46, subtitle, 10)

        if game.high_score > 0:
            hs_text = f"HIGH SCORE: {game.high_score}"
            hs_w = len(hs_text) * 4
            pyxel.text(Game.SCREEN_W // 2 - hs_w // 2, 62, hs_text, 9)

        controls = [
            "Z - RED   Push RIGHT",
            "X - GREEN Push UP",
            "C - BLUE  Push LEFT",
            "V - YELLOW Push DOWN",
            "",
            "Same color x4 = SUPER SUMO!",
            "Wrong color = COMBO reset + HEAT",
            "HEAT >= 100 = STUMBLE (stunned)",
            "Step on echo trails to cool down",
            "",
            "Push the AI out of the ring!",
        ]
        y = 78
        for line in controls:
            pyxel.text(40, y, line, 7)
            y += 10

        if pyxel.frame_count % 60 < 40:
            prompt = "PRESS ENTER TO START"
            p_w = len(prompt) * 4
            pyxel.text(Game.SCREEN_W // 2 - p_w // 2, 200, prompt, 10)

    def _draw_game_over(self) -> None:
        game = self.game

        pyxel.circb(Game.RING_CX, Game.RING_CY, Game.RING_RADIUS, 6)

        result = game._result_display
        rw = len(result) * 4
        r_color = 9 if "VICTORY" in result else 8
        pyxel.text(Game.SCREEN_W // 2 - rw // 2, 40, result, r_color)

        reason = game._result_reason
        reason_w = len(reason) * 4
        pyxel.text(Game.SCREEN_W // 2 - reason_w // 2, 56, reason, 7)

        score_text = f"SCORE: {game.score}"
        sw = len(score_text) * 4
        pyxel.text(Game.SCREEN_W // 2 - sw // 2, 80, score_text, 7)

        combo_text = f"MAX COMBO: {game.max_combo}"
        cw = len(combo_text) * 4
        pyxel.text(Game.SCREEN_W // 2 - cw // 2, 96, combo_text, 10)

        if game.score >= game.high_score and game.score > 0:
            hs = "NEW HIGH SCORE!"
            hw = len(hs) * 4
            pyxel.text(Game.SCREEN_W // 2 - hw // 2, 120, hs, 9)
        elif game.high_score > 0:
            hs = f"HIGH SCORE: {game.high_score}"
            hw = len(hs) * 4
            pyxel.text(Game.SCREEN_W // 2 - hw // 2, 120, hs, 7)

        if pyxel.frame_count % 60 < 40:
            prompt = "PRESS ENTER TO RETRY"
            pw = len(prompt) * 4
            pyxel.text(Game.SCREEN_W // 2 - pw // 2, 200, prompt, 10)

    def _draw_play(self) -> None:
        game = self.game

        is_super = game.super_timer > 0.0
        is_stumble = game.stumble_timer > 0.0

        # Ring
        ring_color = 7
        if is_super:
            ring_color = RAINBOW[(pyxel.frame_count // 3) % len(RAINBOW)]
        pyxel.circb(Game.RING_CX, Game.RING_CY, Game.RING_RADIUS, ring_color)
        pyxel.circb(Game.RING_CX, Game.RING_CY, Game.RING_RADIUS + 1, 6)
        pyxel.circb(Game.RING_CX, Game.RING_CY, Game.RING_RADIUS - 1, 6)

        # Ring floor
        pyxel.circ(Game.RING_CX, Game.RING_CY, Game.RING_RADIUS - 2, 4)

        # Echos
        for echo in game.echos:
            alpha = max(1, int(echo.life * 3))
            size = int(alpha * 3)
            if size > 0:
                pyxel.circb(int(echo.x), int(echo.y), size, echo.color)

        # AI rikishi
        ai = game.ai
        ai_color = game.ai.color
        if ai.stumble_timer > 0.0 and pyxel.frame_count % 6 < 3:
            ai_color = 8
        pyxel.circ(int(ai.x), int(ai.y), ai.radius, ai_color)
        pyxel.circb(int(ai.x), int(ai.y), ai.radius, 7)

        # Player rikishi
        p = game.player
        p_color = p.color
        if is_super:
            p_color = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
        elif is_stumble and pyxel.frame_count % 6 < 3:
            p_color = 8
        pyxel.circ(int(p.x), int(p.y), p.radius, p_color)
        pyxel.circb(int(p.x), int(p.y), p.radius, 7)

        # Direction indicator (small line showing last push direction)
        if game.last_push_color >= 0:
            dirs = ((4, 0), (0, -4), (-4, 0), (0, 4))
            dx, dy = dirs[game.last_push_color]
            pyxel.line(
                int(p.x), int(p.y),
                int(p.x + dx * 3), int(p.y + dy * 3),
                PUSH_COLORS[game.last_push_color],
            )

        # Particles
        for pt in game.particles:
            alpha = pt.life
            size = max(1, int(3 * alpha))
            pyxel.circ(int(pt.x), int(pt.y), size, pt.color)

        # Floating texts
        for ft in game.floating_texts:
            alpha = min(1.0, ft.life)
            col = ft.color
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, col)

        # --- HUD ---

        # COMBO gauge (top-left)
        combo_text = f"COMBO: {game.combo}"
        if game.combo >= Game.COMBO_THRESHOLD:
            combo_color = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
        elif game.combo > 0:
            combo_color = 9
        else:
            combo_color = 7
        pyxel.text(4, 4, combo_text, combo_color)

        # MAX COMBO
        if game.max_combo > 0:
            mc_text = f"MAX: {game.max_combo}"
            pyxel.text(4, 12, mc_text, 12)

        # HEAT bar (top-right)
        bar_x = Game.SCREEN_W - 66
        bar_y = 4
        bar_w = 60
        bar_h = 6
        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, 7)
        heat_fill = int(bar_w * game.heat / Game.HEAT_MAX)
        if game.heat < 40:
            heat_color = 3
        elif game.heat < 70:
            heat_color = 9
        else:
            heat_color = 8
        if heat_fill > 0:
            pyxel.rect(bar_x, bar_y, heat_fill, bar_h, heat_color)
        pyxel.text(bar_x - 14, bar_y, "HEAT", 7)

        # Score (top-center)
        score_text = f"SCORE: {game.score}"
        sw = len(score_text) * 4
        pyxel.text(Game.SCREEN_W // 2 - sw // 2, 4, score_text, 7)

        # SUPER timer (center-top, below score)
        if is_super:
            super_text = f"SUPER SUMO {game.super_timer:.1f}s"
            super_w = len(super_text) * 4
            super_color = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            pyxel.text(Game.SCREEN_W // 2 - super_w // 2, 16, super_text, super_color)

        # STUMBLE indicator
        if is_stumble:
            st_text = f"STUMBLE {game.stumble_timer:.1f}s"
            st_w = len(st_text) * 4
            pyxel.text(Game.SCREEN_W // 2 - st_w // 2, 16, st_text, 8)

        # Cooldown indicator (bottom-left)
        if game.push_cooldown > 0.0:
            cd_text = f"COOL: {game.push_cooldown:.1f}s"
            pyxel.text(4, Game.SCREEN_H - 10, cd_text, 6)

        # Controls reminder (bottom-right)
        key_hints = "Z/X/C/V to Push"
        kh_w = len(key_hints) * 4
        pyxel.text(Game.SCREEN_W - kh_w - 4, Game.SCREEN_H - 10, key_hints, 12)


if __name__ == "__main__":
    App()
