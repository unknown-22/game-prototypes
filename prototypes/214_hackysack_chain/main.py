"""214_hackysack_chain -- Hacky Sack Color-Match Combo Chain

The most fun moment:
  同じ色のサックを連続で蹴り続けてCOMBOを積み、SUPER KICKが発動した瞬間が最高に気持ちいい
  (Chain same-color kicks to build COMBO, then unleash SUPER KICK rainbow burst)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCREEN_W = 320
SCREEN_H = 240

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

SACK_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
SACK_COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]

SACK_RADIUS = 6
SACK_COLOR_CYCLE_FRAMES = 45
PLAYER_W = 40
PLAYER_H = 8
PLAYER_Y = 210
PLAYER_SPEED = 4
PLAYER_FRICTION = 0.85
FOOT_W = 20
FOOT_H = 6

GRAVITY = 0.3
AIR_FRICTION = 0.995
WALL_RESTITUTION = 0.7
CEILING_RESTITUTION = 0.6
KICK_POWER_MIN = 6.0
SPEED_CLAMP_X = 5.0
SPEED_CLAMP_Y = 10.0

HEAT_CAP = 100
HEAT_MISS = 20
HEAT_OOB = 5
HEAT_DECAY = 0.03

SUPER_COMBO_THRESHOLD = 5
SUPER_DURATION = 300

GAME_TIME = 60 * 60  # 60 seconds at 60fps

STUCK_THRESHOLD = 30


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Sack:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # 0-3 index into SACK_COLORS
    radius: int = SACK_RADIUS
    stuck_frames: int = 0


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


@dataclass
class EchoGhost:
    x: float
    y: float
    life: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H
    SACK_RADIUS = SACK_RADIUS
    PLAYER_W = PLAYER_W
    PLAYER_H = PLAYER_H
    PLAYER_Y = PLAYER_Y
    GRAVITY = GRAVITY
    KICK_POWER_MIN = KICK_POWER_MIN
    HEAT_CAP = HEAT_CAP
    SUPER_DURATION = SUPER_DURATION
    GAME_TIME = GAME_TIME

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Hacky Sack Chain", display_scale=2)
        pyxel.mouse(True)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self._update, self._draw)

    # ------------------------------------------------------------------
    # State initialization
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_x: float = SCREEN_W / 2
        self.player_vx: float = 0.0
        self.sack: Sack = Sack(x=SCREEN_W / 2, y=60.0, vx=1.0, vy=0.0, color=0, stuck_frames=0)
        self.sack_color_timer: int = 0

        self.combo_count: int = 0
        self.current_combo_color: int = -1
        self.max_combo: int = 0
        self.score: int = 0

        self.heat: float = 0.0
        self.super_active: bool = False
        self.super_timer: int = 0
        self.time_remaining: int = GAME_TIME

        self._kicked_this_frame: bool = False
        self._prev_sack_x: float = 0.0
        self._prev_sack_y: float = 0.0

        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_recording: list[tuple[float, float]] = []
        self.ghost_playback: list[EchoGhost] = []

        self.screen_shake: int = 0

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _update(self) -> None:
        space_pressed = pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)

        if self.phase == Phase.TITLE:
            self._update_title(space_pressed)
        elif self.phase == Phase.PLAYING:
            self._update_playing(space_pressed)
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over(space_pressed)

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _update_title(self, space_pressed: bool) -> None:
        if space_pressed:
            self.reset()
            self.phase = Phase.PLAYING

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)

        title = "HACKY SACK CHAIN"
        title_w = len(title) * 4
        pyxel.text(SCREEN_W // 2 - title_w // 2, 50, title, WHITE)

        lines = [
            "",
            "KICK the falling sack!",
            "",
            "Match SAME COLOR = COMBO",
            "COMBO x5 = SUPER KICK!",
            "",
            "Miss = HEAT up = Game Over",
            "",
            "LEFT/RIGHT or Mouse to move",
            "",
            "[SPACE] to START",
        ]
        for i, line in enumerate(lines):
            lw = len(line) * 4
            color = YELLOW if i == 0 else WHITE
            if line.startswith("[SPACE]") and pyxel.frame_count % 60 < 30:
                color = ORANGE
            pyxel.text(SCREEN_W // 2 - lw // 2, 82 + i * 10, line, color)

    # ------------------------------------------------------------------
    # Playing screen
    # ------------------------------------------------------------------

    def _update_playing(self, space_pressed: bool) -> None:
        self._handle_input()
        self._update_player()
        self._update_sack_physics()
        self._update_sack_color_timer()
        self._update_particles()
        self._update_floating_texts()
        self._update_echo_ghosts()
        self._update_super_mode()
        self._update_heat_decay()
        self._update_timer()
        self._update_screen_shake()

        if self.heat >= HEAT_CAP or self.time_remaining <= 0:
            self.phase = Phase.GAME_OVER

    def _handle_input(self) -> None:
        target_vx = 0.0

        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            target_vx = -PLAYER_SPEED
        elif pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            target_vx = PLAYER_SPEED

        mouse_x = pyxel.mouse_x
        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            diff = mouse_x - self.player_x
            target_vx = max(-PLAYER_SPEED, min(PLAYER_SPEED, diff * 0.3))

        self.player_vx += (target_vx - self.player_vx) * 0.3

    def _update_player(self) -> None:
        self.player_x += self.player_vx
        self.player_x = max(PLAYER_W / 2, min(SCREEN_W - PLAYER_W / 2, self.player_x))

    def _update_sack_physics(self) -> None:
        self._kicked_this_frame = False
        self._prev_sack_x = self.sack.x
        self._prev_sack_y = self.sack.y

        self.sack.vy += GRAVITY
        self.sack.vx *= AIR_FRICTION
        self.sack.vy *= AIR_FRICTION

        self.sack.x += self.sack.vx
        self.sack.y += self.sack.vy

        # Wall bounce left/right
        if self.sack.x - self.sack.radius <= 0:
            self.sack.x = float(self.sack.radius)
            self.sack.vx = abs(self.sack.vx) * WALL_RESTITUTION
            self.heat = min(HEAT_CAP, self.heat + HEAT_OOB)
        elif self.sack.x + self.sack.radius >= SCREEN_W:
            self.sack.x = float(SCREEN_W - self.sack.radius)
            self.sack.vx = -abs(self.sack.vx) * WALL_RESTITUTION
            self.heat = min(HEAT_CAP, self.heat + HEAT_OOB)

        # Ceiling bounce
        if self.sack.y - self.sack.radius <= 0:
            self.sack.y = float(self.sack.radius)
            self.sack.vy = abs(self.sack.vy) * CEILING_RESTITUTION

        # Speed clamp
        self.sack.vx = max(-SPEED_CLAMP_X, min(SPEED_CLAMP_X, self.sack.vx))
        self.sack.vy = max(-SPEED_CLAMP_Y, min(SPEED_CLAMP_Y, self.sack.vy))

        # Corner stuck detection
        if self.sack.y < 10 and abs(self.sack.vy) < 0.5:
            self.sack.stuck_frames += 1
            if self.sack.stuck_frames >= STUCK_THRESHOLD:
                self.sack.vy = -4.0
                self.sack.vx = self._rng.uniform(-2.0, 2.0)
                self.sack.stuck_frames = 0
        else:
            self.sack.stuck_frames = 0

        # Check foot collision
        if self._check_foot_collision(self.player_x) and not self._kicked_this_frame:
            self._resolve_kick(self.player_vx)

        # Check ground miss
        if self.sack.y >= SCREEN_H and not self._kicked_this_frame:
            self._update_heat_from_miss()

        # Ghost recording
        if self._kicked_this_frame:
            self.ghost_recording.append((self._prev_sack_x, self._prev_sack_y))
        elif not self.ghost_recording and self.sack.vy < 0:
            self.ghost_recording.append((self.sack.x, self.sack.y))

    def _update_sack_color_timer(self) -> None:
        self.sack_color_timer += 1
        if self.sack_color_timer >= SACK_COLOR_CYCLE_FRAMES:
            self.sack_color_timer = 0
            self.sack.color = (self.sack.color + 1) % len(SACK_COLORS)

    # ------------------------------------------------------------------
    # Testable logic methods
    # ------------------------------------------------------------------

    def _check_foot_collision(self, player_x: float) -> bool:
        foot_top = PLAYER_Y - FOOT_H
        foot_left = player_x - FOOT_W / 2
        foot_right = player_x + FOOT_W / 2

        if not (foot_left <= self.sack.x <= foot_right):
            return False
        if not (foot_top - self.sack.radius <= self.sack.y <= PLAYER_Y):
            return False

        return self.sack.vy > 0

    def _resolve_kick(self, player_vx: float) -> None:
        self._kicked_this_frame = True

        downward_speed = self.sack.vy
        kick_power = max(KICK_POWER_MIN, min(9.0, downward_speed * 1.2))
        self.sack.vy = -kick_power
        self.sack.vx += player_vx * 0.5
        self.sack.y = PLAYER_Y - FOOT_H - self.sack.radius

        # Combo logic
        if self.sack.color == self.current_combo_color:
            self.combo_count += 1
            points = int(10 * (1 + self.combo_count * 0.5))
        else:
            self.combo_count = 1
            self.current_combo_color = self.sack.color
            points = 10

        self.max_combo = max(self.max_combo, self.combo_count)

        multiplier = 3.0 if self.super_active else 1.0
        points = int(points * multiplier)
        self.score += points

        # Floating text
        text = f"+{points}"
        text_color = SACK_COLORS[self.sack.color]
        if self.combo_count >= 3:
            text = f"COMBO x{self.combo_count}"
            text_color = ORANGE
        if self.combo_count >= SUPER_COMBO_THRESHOLD and not self.super_active:
            self._activate_super()
        elif self.super_active:
            self.super_timer = SUPER_DURATION

        self.floating_texts.append(
            FloatingText(self.sack.x, PLAYER_Y - FOOT_H - 10, text, 30, text_color)
        )

        # Particles on kick
        num_particles = 20 if self.super_active else 8
        for _ in range(num_particles):
            angle = self._rng.uniform(0, math.pi)
            speed = self._rng.uniform(1.0, 3.0)
            pcolor = self._rng.choice(SACK_COLORS) if self.super_active else SACK_COLORS[self.sack.color]
            self.particles.append(
                Particle(
                    x=self.sack.x,
                    y=PLAYER_Y - FOOT_H,
                    vx=math.cos(angle) * speed * self._rng.choice([-1, 1]),
                    vy=math.sin(angle) * speed * -1,
                    life=20 + self._rng.randint(0, 10),
                    color=pcolor,
                    size=2,
                )
            )

        # Release ghost playback
        self.ghost_playback = [EchoGhost(x=p[0], y=p[1], life=90) for p in self.ghost_recording]
        self.ghost_recording.clear()

    def _activate_super(self) -> None:
        self.super_active = True
        self.super_timer = SUPER_DURATION
        self.floating_texts.append(
            FloatingText(SCREEN_W / 2, SCREEN_H / 2, "SUPER!", 60, YELLOW)
        )

    def _update_heat_from_miss(self) -> None:
        self.heat = min(HEAT_CAP, self.heat + HEAT_MISS)
        self.combo_count = 0
        self.current_combo_color = -1
        self.super_active = False
        self.super_timer = 0
        self.ghost_recording.clear()
        self.ghost_playback.clear()
        self.screen_shake = 10

        # Miss particles
        for _ in range(12):
            angle = self._rng.uniform(0, math.pi)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=self.sack.x,
                    y=SCREEN_H - 2,
                    vx=math.cos(angle) * speed * self._rng.choice([-1, 1]),
                    vy=-math.sin(angle) * speed,
                    life=25,
                    color=GRAY,
                    size=2,
                )
            )
        self.floating_texts.append(
            FloatingText(self.sack.x, SCREEN_H - 10, "MISS!", 30, RED)
        )

        # Respawn sack
        self.sack.x = self._rng.uniform(40, SCREEN_W - 40)
        self.sack.y = 30.0
        self.sack.vx = self._rng.uniform(-2.0, 2.0)
        self.sack.vy = 2.0
        self.sack.color = self._rng.randint(0, 3)
        self.sack.stuck_frames = 0

    # ------------------------------------------------------------------
    # Particle / FloatingText / EchoGhost updates
    # ------------------------------------------------------------------

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_echo_ghosts(self) -> None:
        for g in self.ghost_playback:
            g.life -= 1
        self.ghost_playback = [g for g in self.ghost_playback if g.life > 0]

    # ------------------------------------------------------------------
    # Heat / Super / Timer / Shake updates
    # ------------------------------------------------------------------

    def _update_heat_decay(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super_mode(self) -> None:
        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False
                self.super_timer = 0

    def _update_timer(self) -> None:
        self.time_remaining = max(0, self.time_remaining - 1)

    def _update_screen_shake(self) -> None:
        if self.screen_shake > 0:
            self.screen_shake -= 1

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_playing(self) -> None:
        # Screen shake offset
        shake_x = self._rng.randint(-2, 2) if self.screen_shake > 0 else 0
        shake_y = self._rng.randint(-2, 2) if self.screen_shake > 0 else 0

        # SUPER border glow
        if self.super_active and pyxel.frame_count % 8 < 4:
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, YELLOW)
            pyxel.rectb(2, 2, SCREEN_W - 4, SCREEN_H - 4, ORANGE)

        # Background
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, NAVY)

        # Ground line
        pyxel.rect(0, SCREEN_H - 2, SCREEN_W, 2, BROWN)

        # Echo ghosts
        for ghost in self.ghost_playback:
            alpha = max(0, ghost.life / 90)
            color = DARK_BLUE if self.super_active else GRAY
            pyxel.pset(int(ghost.x + shake_x), int(ghost.y + shake_y), color)

        # Particles
        for p in self.particles:
            alpha = p.life / 25
            if alpha > 0.2:
                pyxel.pset(int(p.x + shake_x), int(p.y + shake_y), p.color)

        # Player (stick figure)
        px = int(self.player_x + shake_x)
        py = PLAYER_Y + shake_y

        # Legs
        pyxel.line(px, py, px - 6, py + 15, WHITE)
        pyxel.line(px, py, px + 6, py + 15, WHITE)
        # Body
        pyxel.line(px, py, px, py - 15, WHITE)
        # Arms
        pyxel.line(px, py - 10, px - 8, py - 5, WHITE)
        pyxel.line(px, py - 10, px + 8, py - 5, WHITE)
        # Head
        pyxel.circ(px, py - 18, 3, PEACH)

        # Foot (colored paddle)
        foot_color = SACK_COLORS[self.current_combo_color] if self.current_combo_color >= 0 else WHITE
        foot_left = int(px - FOOT_W / 2)
        foot_top = int(py - FOOT_H)
        pyxel.rect(foot_left, foot_top, FOOT_W, FOOT_H, foot_color)
        if self.super_active:
            pyxel.rectb(foot_left - 1, foot_top - 1, FOOT_W + 2, FOOT_H + 2, YELLOW)

        # Sack
        sack_x = int(self.sack.x + shake_x)
        sack_y = int(self.sack.y + shake_y)
        sack_color = SACK_COLORS[self.sack.color]

        if self.super_active and pyxel.frame_count % 6 < 3:
            sack_color = SACK_COLORS[(pyxel.frame_count // 6) % len(SACK_COLORS)]

        # Shadow
        pyxel.ellib(sack_x - 2, sack_y + 2, sack_x + 2, sack_y + 5, DARK_BLUE)

        # Sack body
        pyxel.circ(sack_x, sack_y, self.sack.radius, sack_color)
        pyxel.circb(sack_x, sack_y, self.sack.radius, BLACK)

        # Color indicator ring
        if not self.super_active:
            pyxel.circb(sack_x, sack_y, self.sack.radius + 2, SACK_COLORS[self.sack.color])

        # Floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x + shake_x) - len(ft.text) * 2, int(ft.y + shake_y), ft.text, ft.color)

        # HUD
        self._draw_hud()

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)

        # Combo (top-center)
        combo_text = f"COMBO: {self.combo_count}"
        if self.combo_count >= SUPER_COMBO_THRESHOLD:
            combo_color = YELLOW
        elif self.combo_count >= 3:
            combo_color = ORANGE
        else:
            combo_color = WHITE
        combo_w = len(combo_text) * 4
        pyxel.text(SCREEN_W // 2 - combo_w // 2, 4, combo_text, combo_color)

        # HEAT bar (top-right)
        heat_text = "HEAT"
        pyxel.text(SCREEN_W - 80, 4, heat_text, RED)
        bar_w = 60
        pyxel.rect(SCREEN_W - 80, 12, bar_w, 6, DARK_BLUE)
        heat_fill = int(bar_w * (self.heat / HEAT_CAP))
        heat_bar_color = RED if self.heat > 60 else ORANGE
        if heat_fill > 0:
            pyxel.rect(SCREEN_W - 80, 12, heat_fill, 6, heat_bar_color)
        pyxel.rectb(SCREEN_W - 80, 12, bar_w, 6, WHITE)

        # Timer
        seconds = self.time_remaining // 60
        timer_text = f"TIME: {seconds}"
        timer_color = RED if seconds <= 10 else WHITE
        timer_w = len(timer_text) * 4
        pyxel.text(SCREEN_W // 2 - timer_w // 2, 18, timer_text, timer_color)

        # SUPER indicator
        if self.super_active:
            super_left = self.super_timer // 60
            super_text = f"SUPER {super_left}s"
            pyxel.text(4, 18, super_text, YELLOW)

    # ------------------------------------------------------------------
    # Game Over screen
    # ------------------------------------------------------------------

    def _update_game_over(self, space_pressed: bool) -> None:
        if space_pressed:
            self.reset()
            self.phase = Phase.PLAYING

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)

        header = "GAME OVER"
        hw = len(header) * 4
        pyxel.text(SCREEN_W // 2 - hw // 2, 60, header, RED)

        reason = "TIME UP!" if self.time_remaining <= 0 else "HEAT OVERLOAD!"
        rw = len(reason) * 4
        pyxel.text(SCREEN_W // 2 - rw // 2, 78, reason, ORANGE)

        lines = [
            f"SCORE: {self.score}",
            f"MAX COMBO: {self.max_combo}",
            "",
            "[SPACE] to RETRY",
        ]
        for i, line in enumerate(lines):
            lw = len(line) * 4
            color = GREEN if i == 0 else (YELLOW if i == 1 else WHITE)
            if line.startswith("[SPACE]") and pyxel.frame_count % 60 < 30:
                color = ORANGE
            pyxel.text(SCREEN_W // 2 - lw // 2, 100 + i * 12, line, color)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> None:
        pass  # pyxel.run is called in __init__


if __name__ == "__main__":
    Game()
