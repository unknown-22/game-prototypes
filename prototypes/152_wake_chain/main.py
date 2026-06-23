"""WAKE CHAIN — Side-scrolling wakeboarding game."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ============================================================
# Constants
# ============================================================
SCREEN_W = 320
SCREEN_H = 240
PLAYER_X = 80
PLAYER_MIN_Y = 40
PLAYER_MAX_Y = 200
PLAYER_SPEED_PER_FRAME = 200.0 / 60.0  # 200 px/sec at 60fps
BUOY_SPEED_PER_FRAME = 120.0 / 60.0  # 120 px/sec at 60fps
BUOY_RADIUS = 8
COLLECT_RADIUS: float = 14.0
MAX_HEAT: float = 5.0
SUPER_DURATION: int = 300  # frames (5 seconds)
GAME_DURATION: int = 3600  # frames (60 seconds)
COMBO_THRESHOLD: int = 4
INITIAL_SPAWN_INTERVAL: int = 48  # frames (0.8s)
MIN_SPAWN_INTERVAL: int = 15  # frames (0.25s)
DIFFICULTY_INTERVAL: int = 600  # frames (10 seconds)
SPAWN_INTERVAL_DECREASE: int = 5
SHAKE_FRAMES: int = 5

BUOY_COLORS: tuple[int, ...] = (8, 3, 6, 10)  # RED, GREEN, LIGHT_BLUE, YELLOW

# ============================================================
# Enums
# ============================================================
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ============================================================
# Data Classes
# ============================================================
@dataclass
class Buoy:
    x: float
    y: float
    color: int  # 0-3 index into BUOY_COLORS
    collected: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


# ============================================================
# Game
# ============================================================
class Game:
    """Side-scrolling wakeboarding game. Pass through same-color buoys to build combos."""

    # Pre-initialized state (required for Game.__new__ bypass in tests)
    phase: Phase = Phase.TITLE
    score: int = 0
    high_score: int = 0
    combo: int = 0
    max_combo: int = 0
    heat: float = 0.0
    game_timer: int = GAME_DURATION
    super_timer: int = 0
    player_y: float = 120.0
    player_color: int = 0  # 0-3 index into BUOY_COLORS
    buoys: list[Buoy] = []
    particles: list[Particle] = []
    wake_trail: list[Particle] = []
    _rng: random.Random = random.Random()
    _spawn_timer: int = INITIAL_SPAWN_INTERVAL
    _spawn_interval: int = INITIAL_SPAWN_INTERVAL
    _shake_frames: int = 0
    last_color: int = 0  # index for wake trail color
    _title_buoys: list[Buoy] = []
    _title_spawn_timer: int = 0
    _title_wave_offset: float = 0.0
    _elapsed_frames: int = 0

    def __init__(self) -> None:
        self.buoys = []
        self.particles = []
        self.wake_trail = []
        self._title_buoys = []
        pyxel.init(SCREEN_W, SCREEN_H, title="WAKE CHAIN", display_scale=2, fps=60)
        pyxel.run(self.update, self.draw)

    # ============================================================
    # Main Loop
    # ============================================================
    def update(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1
            pyxel.camera(random.randint(-2, 2), random.randint(-2, 2))
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(5)  # DARK_BLUE background
        self._draw_water_background()

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ============================================================
    # Phase Updates
    # ============================================================
    def _update_title(self) -> None:
        self._title_wave_offset = (self._title_wave_offset + 0.5) % 40.0
        self._title_spawn_timer -= 1
        if self._title_spawn_timer <= 0:
            self._title_spawn_timer = 30
            color_idx = random.randint(0, 3)
            y = random.uniform(50, 190)
            self._title_buoys.append(Buoy(x=330.0, y=y, color=color_idx))

        for b in self._title_buoys:
            b.x -= BUOY_SPEED_PER_FRAME
        self._title_buoys = [b for b in self._title_buoys if b.x > -20]

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._elapsed_frames += 1

        # Player movement
        if pyxel.btn(pyxel.KEY_UP):
            self.player_y -= PLAYER_SPEED_PER_FRAME
        if pyxel.btn(pyxel.KEY_DOWN):
            self.player_y += PLAYER_SPEED_PER_FRAME
        self._clamp_player()

        # Spawn buoys
        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            self._spawn_buoy()
            self._spawn_timer = self._spawn_interval

        # Move buoys
        self._move_buoys()

        # Check collisions
        self._check_buoy_collision()

        # Update super mode
        self._update_super()

        # Spawn wake trail particles
        if self._elapsed_frames % 2 == 0:
            self._spawn_wake_particles(random.randint(1, 2))

        # Heat warning particles
        if self.heat >= 4.0:
            self._spawn_wake_particles(1)

        # Update particles
        self._update_particles()

        # Update game timer
        self.game_timer -= 1
        if self.game_timer <= 0:
            self._trigger_game_over()

        # Update difficulty
        self._update_difficulty()

        # Check heat game over
        if self.phase == Phase.PLAYING and self.heat >= MAX_HEAT:
            self._trigger_game_over()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.TITLE

    # ============================================================
    # Phase Draws
    # ============================================================
    def _draw_water_background(self) -> None:
        """Draw water surface wave lines and boat."""
        offset = int(self._title_wave_offset) if self.phase == Phase.TITLE else 0
        # Water surface wave lines
        for i in range(8):
            wave_y = 30 + i * 3
            for x in range(0, SCREEN_W, 20):
                wx = x + offset + (i % 2) * 10
                pyxel.pset(wx % SCREEN_W, wave_y, 13)  # GRAY

        # Deep water shading
        pyxel.rect(0, 210, SCREEN_W, SCREEN_H - 210, 1)  # NAVY

        # Boat at left
        pyxel.tri(5, 50, 25, 40, 25, 60, 4)  # BROWN boat triangle
        pyxel.rect(0, 48, 8, 4, 4)

    def _draw_title(self) -> None:
        # Background buoys
        for b in self._title_buoys:
            color_int = BUOY_COLORS[b.color]
            pyxel.circ(int(b.x), int(b.y), BUOY_RADIUS, color_int)
            pyxel.circb(int(b.x), int(b.y), BUOY_RADIUS, 7)

        # Title
        title = "WAKE CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 80, title, 7)

        # Instructions
        inst1 = "ARROW KEYS: Move"
        pyxel.text(SCREEN_W // 2 - len(inst1) * 2, 110, inst1, 7)
        inst2 = "MATCH COLORS: Chain"
        pyxel.text(SCREEN_W // 2 - len(inst2) * 2, 122, inst2, 7)
        inst3 = "SUPER: 4x Combo!"
        pyxel.text(SCREEN_W // 2 - len(inst3) * 2, 134, inst3, 10)

        start = "PRESS SPACE TO START"
        pyxel.text(SCREEN_W // 2 - len(start) * 2, 170, start, 7)

        # High score
        if self.high_score > 0:
            hs = f"HIGH SCORE: {self.high_score}"
            pyxel.text(SCREEN_W // 2 - len(hs) * 2, 190, hs, 10)

    def _draw_playing(self) -> None:
        is_super = self._is_super()
        rainbow_idx = pyxel.frame_count % len(BUOY_COLORS)

        # Rope from boat to player
        pyxel.line(15, 50, PLAYER_X, int(self.player_y), 7)

        # Wake trail particles
        for p in self.wake_trail:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Other particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Buoys
        for b in self.buoys:
            if b.collected:
                continue
            color_int = BUOY_COLORS[b.color]
            pyxel.circ(int(b.x), int(b.y), BUOY_RADIUS, color_int)
            pyxel.circb(int(b.x), int(b.y), BUOY_RADIUS // 2, 7)

        # Player
        player_render_color = BUOY_COLORS[rainbow_idx] if is_super else 7  # WHITE
        px = PLAYER_X - 4
        py2 = int(self.player_y) - 6
        pyxel.rect(px, py2, 8, 12, player_render_color)
        # Wakeboard
        pyxel.rect(px - 2, py2 + 12, 12, 3, 4)  # BROWN

        # HUD
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)

        combo_text = f"COMBO: {self.combo}"
        pyxel.text(SCREEN_W - len(combo_text) * 4 - 4, 4, combo_text, 7)

        secs = max(0, self.game_timer // 60)
        timer_text = f"TIME: {secs}"
        pyxel.text(SCREEN_W // 2 - len(timer_text) * 2, 4, timer_text, 7)

        if is_super:
            super_color = BUOY_COLORS[rainbow_idx]
            pyxel.text(SCREEN_W - 56, 14, "SUPER WAKE!", super_color)

        # Heat bar at bottom
        bar_w = 100
        bar_h = 6
        bar_x = (SCREEN_W - bar_w) // 2
        bar_y = SCREEN_H - 14
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 13)  # GRAY background

        heat_ratio = min(1.0, self.heat / MAX_HEAT)
        fill_w = int(bar_w * heat_ratio)
        if fill_w > 0:
            if heat_ratio < 0.5:
                heat_color = 3  # GREEN
            elif heat_ratio < 0.8:
                heat_color = 10  # YELLOW
            else:
                heat_color = 8  # RED
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_color)

        label = "HEAT"
        pyxel.text(bar_x - 22, bar_y - 1, label, 7)

    def _draw_game_over(self) -> None:
        go_text = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go_text) * 2, 60, go_text, 8)

        score_text = f"FINAL SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 85, score_text, 7)

        max_combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(max_combo_text) * 2, 100, max_combo_text, 7)

        if self.score >= self.high_score > 0:
            nhs = "NEW HIGH SCORE!"
            pyxel.text(SCREEN_W // 2 - len(nhs) * 2, 120, nhs, 10)
        elif self.high_score > 0:
            hs = f"HIGH SCORE: {self.high_score}"
            pyxel.text(SCREEN_W // 2 - len(hs) * 2, 120, hs, 7)

        inst = "PRESS SPACE TO RETRY"
        pyxel.text(SCREEN_W // 2 - len(inst) * 2, 155, inst, 7)

    # ============================================================
    # Game Logic (Testable — no pyxel input calls)
    # ============================================================
    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.game_timer = GAME_DURATION
        self.super_timer = 0
        self.player_y = 120.0
        self.player_color = 0
        self.buoys.clear()
        self.particles.clear()
        self.wake_trail.clear()
        self._spawn_timer = 0  # Spawn immediately on start
        self._spawn_interval = INITIAL_SPAWN_INTERVAL
        self._shake_frames = 0
        self.last_color = 0
        self._title_buoys.clear()
        self._title_spawn_timer = 0
        self._title_wave_offset = 0.0
        self._elapsed_frames = 0

    def _trigger_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        self._shake_frames = SHAKE_FRAMES
        if self.score > self.high_score:
            self.high_score = self.score

    def _move_buoys(self) -> None:
        for b in self.buoys:
            b.x -= BUOY_SPEED_PER_FRAME
        # Remove off-screen buoys
        self.buoys = [b for b in self.buoys if b.x > -20]

    def _spawn_buoy(self) -> None:
        color_idx = random.randint(0, 3)
        y = random.uniform(50, 190)
        self.buoys.append(Buoy(x=330.0, y=y, color=color_idx))

    def _check_buoy_collision(self) -> None:
        is_super = self._is_super()
        for b in self.buoys:
            if b.collected:
                continue
            dist = math.hypot(b.x - PLAYER_X, b.y - self.player_y)
            if dist <= COLLECT_RADIUS:
                if is_super or b.color == self.player_color:
                    # Same color (or super mode): combo up, score
                    self.combo += 1
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    self._add_score(10)
                    b.collected = True
                    self._spawn_collect_particles(b.x, b.y, b.color, random.randint(5, 8))

                    if is_super:
                        self._spawn_collect_particles(b.x, b.y, (b.color + 1) % 4, random.randint(5, 8))

                    # Activate super at threshold
                    if self.combo >= COMBO_THRESHOLD and not is_super:
                        self._activate_super()
                else:
                    # Wrong color: combo reset, heat up, change player color
                    self.combo = 0
                    self.player_color = b.color
                    if not is_super:
                        self.heat += 1.0
                    b.collected = True
                    self._spawn_wrong_particles(b.x, b.y, b.color)

                self.last_color = b.color
                break  # Only collect one buoy per frame for clarity

    def _add_score(self, base: int) -> int:
        multiplier = 3 if self._is_super() else 1
        points = base * self.combo * multiplier
        self.score += points
        return points

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._shake_frames = SHAKE_FRAMES
        # Super burst particles
        for _ in range(random.randint(30, 40)):
            color = random.choice(BUOY_COLORS)
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.randint(20, 40)
            self.particles.append(
                Particle(
                    x=float(PLAYER_X),
                    y=self.player_y,
                    vx=vx,
                    vy=vy,
                    life=life,
                    color=color,
                    size=random.randint(1, 3),
                )
            )

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _spawn_wake_particles(self, n: int) -> None:
        for _ in range(n):
            color = BUOY_COLORS[self.last_color]
            life = random.randint(15, 30)
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(-0.3, 0.3)
            self.wake_trail.append(
                Particle(
                    x=float(PLAYER_X),
                    y=self.player_y,
                    vx=vx,
                    vy=vy,
                    life=life,
                    color=color,
                    size=random.randint(1, 3),
                )
            )

    def _spawn_collect_particles(self, x: float, y: float, color_idx: int, count: int) -> None:
        color = BUOY_COLORS[color_idx]
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 3)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 1.0
            life = random.randint(10, 20)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color, size=random.randint(1, 2))
            )

    def _spawn_wrong_particles(self, x: float, y: float, color_idx: int) -> None:
        color = BUOY_COLORS[color_idx]
        for _ in range(random.randint(4, 6)):
            vx = random.uniform(-1.5, 1.5)
            vy = random.uniform(-1.5, 1.5)
            life = random.randint(8, 15)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color, size=1)
            )

    def _update_particles(self) -> None:
        for p in self.wake_trail:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.wake_trail = [p for p in self.wake_trail if p.life > 0]

        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _clamp_player(self) -> None:
        if self.player_y < PLAYER_MIN_Y:
            self.player_y = PLAYER_MIN_Y
        if self.player_y > PLAYER_MAX_Y:
            self.player_y = PLAYER_MAX_Y

    def _update_difficulty(self) -> None:
        if self._elapsed_frames > 0 and self._elapsed_frames % DIFFICULTY_INTERVAL == 0:
            self._spawn_interval = max(MIN_SPAWN_INTERVAL, self._spawn_interval - SPAWN_INTERVAL_DECREASE)


# ============================================================
# Entry Point
# ============================================================
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
