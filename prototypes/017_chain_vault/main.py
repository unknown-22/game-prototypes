"""CHAIN VAULT — Color-chain platformer prototype.

Reinterpreted from game idea #1 (score 31.55):
  Original: hacking auto-shooter with chain propagation + one-color constraint
  Reinterpreted as: platformer where chaining same-colored platforms
  triggers a cascading SHATTER for massive score.

Core fun: "Chain 3+ same-color platforms, trigger a screen-shaking
SHATTER, and get launched upward in a cascade of particles and points."

Engine: Pyxel 2.x, 256x256, 60fps, single-file.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pyxel

# ── Config ────────────────────────────────────────────────────────────────
SCREEN_W = 256
SCREEN_H = 256
GRAVITY = 0.35
JUMP_VEL = -7.0
SHATTER_JUMP_VEL = -8.5  # launched upward on shatter
MOVE_SPEED = 2.2
PLAYER_W = 10
PLAYER_H = 12
PLATFORM_H = 5
PLATFORM_W_MIN = 44
PLATFORM_W_MAX = 80
PLATFORM_GAP_MIN = 32
PLATFORM_GAP_MAX = 52
CHAIN_THRESHOLD = 3
CAMERA_FOLLOW = 0.06
HEAT_DECAY = 0.12
HEAT_PER_CHAIN = 12.0
HEAT_OVERLOAD = 85.0
MAX_PLATFORMS = 35
STAR_COUNT = 40

# Pyxel palette colors used
RED = pyxel.COLOR_RED       # 8
BLUE = pyxel.COLOR_CYAN     # 12
GREEN = pyxel.COLOR_LIME    # 11
PLATFORM_COLORS = (RED, BLUE, GREEN)


# ── Data ───────────────────────────────────────────────────────────────────
@dataclass
class Platform:
    x: int
    y: float
    w: int
    color: int
    alive: bool = True
    crumbling: int = 0  # frames until it breaks (0 = stable)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ── Game ───────────────────────────────────────────────────────────────────
class Game:
    """Color-chain platformer.  Climb, chain, shatter, repeat."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHAIN VAULT", fps=60)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── reset ──────────────────────────────────────────────────────────
    def reset(self) -> None:
        self.player_x: float = SCREEN_W / 2 - PLAYER_W / 2
        self.player_y: float = SCREEN_H - 60.0
        self.player_vy: float = 0.0
        self.player_on_ground: bool = False

        self.platforms: list[Platform] = []
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []

        self.chain_color: int | None = None
        self.chain_count: int = 0
        self.heat: float = 0.0

        self.score: int = 0
        self.high_score: int = 0
        self.max_height: float = self.player_y
        self.combo_bonus: float = 1.0

        self.game_over: bool = False
        self.game_over_timer: int = 0
        self.win_count: int = 0  # count of shatters this run

        self.camera_y: float = 0.0
        self.shake_timer: int = 0
        self.shake_mag: int = 0

        self._generate_initial()

    # ── generation ──────────────────────────────────────────────────────
    def _generate_initial(self) -> None:
        y = SCREEN_H - 24.0
        for _ in range(22):
            self._spawn_platform(y)
            y -= random.uniform(PLATFORM_GAP_MIN, PLATFORM_GAP_MAX)

    def _spawn_platform(self, y: float) -> Platform:
        w = random.randint(PLATFORM_W_MIN, PLATFORM_W_MAX)
        x = random.randint(4, SCREEN_W - w - 4)
        color = random.choice(PLATFORM_COLORS)
        p = Platform(x=x, y=y, w=w, color=color)
        self.platforms.append(p)
        return p

    def _cull_and_fill(self) -> None:
        # Remove platforms far below camera
        bottom = self.camera_y + SCREEN_H + 120
        self.platforms = [p for p in self.platforms if p.y < bottom]
        # Find highest platform
        if not self.platforms:
            self._spawn_platform(self.camera_y - 40)
            return
        top = min(p.y for p in self.platforms)
        # Generate upwards
        while top > self.camera_y - 120 and len(self.platforms) < MAX_PLATFORMS:
            top -= random.uniform(PLATFORM_GAP_MIN, PLATFORM_GAP_MAX)
            self._spawn_platform(top)

    # ── update ──────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.game_over:
            self._update_game_over()
            return

        self._update_input()
        self._update_physics()
        self._update_collision()
        self._update_camera()
        self._update_heat()
        self._update_particles()
        self._update_float_texts()
        self._update_crumbling()
        self._update_shake()
        self._check_death()
        self._cull_and_fill()

    def _update_game_over(self) -> None:
        self.game_over_timer += 1
        if self.game_over_timer > 30 and (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.KEY_Z)
        ):
            self.reset()

    def _update_input(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_x -= MOVE_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_x += MOVE_SPEED
        # Jump
        if self.player_on_ground and (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_UP)
            or pyxel.btnp(pyxel.KEY_W)
        ):
            self.player_vy = JUMP_VEL
            self.player_on_ground = False

    def _update_physics(self) -> None:
        self.player_vy += GRAVITY
        self.player_y += self.player_vy
        # Horizontal bounds
        self.player_x = max(0.0, min(float(SCREEN_W - PLAYER_W), self.player_x))

    def _update_collision(self) -> None:
        self.player_on_ground = False
        p_bottom = self.player_y + PLAYER_H
        p_cx = self.player_x + PLAYER_W / 2
        p_prev_bottom = p_bottom - self.player_vy

        for plat in self.platforms:
            if not plat.alive:
                continue
            # Player falling onto platform top
            if (
                self.player_vy >= 0
                and p_bottom >= plat.y
                and p_prev_bottom <= plat.y + 3
                and p_cx > plat.x
                and p_cx < plat.x + plat.w
            ):
                self.player_y = plat.y - PLAYER_H
                self.player_vy = 0.0
                self.player_on_ground = True
                self._on_land(plat)
                break

    def _on_land(self, plat: Platform) -> None:
        """Handle landing on a platform — chain tracking and shatter check."""
        # If platform is crumbling, don't count it (it breaks)
        if plat.crumbling > 0:
            return

        if self.chain_color == plat.color:
            self.chain_count += 1
        else:
            self.chain_color = plat.color
            self.chain_count = 1

        # Shatter check
        if self.chain_count >= CHAIN_THRESHOLD:
            self._trigger_shatter(plat)

    def _trigger_shatter(self, current_plat: Platform) -> None:
        """Shatter all platforms of the chained color.  Player gets launched upward."""
        color = self.chain_color
        assert color is not None
        shattered = 0

        for p in self.platforms:
            if p.alive and p.color == color:
                if p is current_plat:
                    # Current platform crumbles after a delay (player needs to react)
                    p.crumbling = 18
                else:
                    p.alive = False
                    shattered += 1
                    self._burst_particles(p)

        # Always give at least some particles
        if shattered == 0 and current_plat.crumbling > 0:
            self._burst_particles(current_plat)

        # Score
        multiplier = self.chain_count - CHAIN_THRESHOLD + 1  # 1x, 2x, 3x...
        points = (shattered + 1) * 50 * multiplier
        self.score += points
        self.win_count += 1

        # Floating text
        self.float_texts.append(
            FloatText(
                x=self.player_x + PLAYER_W / 2,
                y=self.player_y - 6,
                text=f"+{points}",
                life=40,
                color=color,
            )
        )

        # Launch player upward
        self.player_vy = SHATTER_JUMP_VEL - (self.chain_count - CHAIN_THRESHOLD) * 0.5
        self.player_on_ground = False

        # Shake
        self.shake_timer = 8
        self.shake_mag = min(5, 2 + shattered // 3)

        # Heat
        self.heat = min(100.0, self.heat + HEAT_PER_CHAIN + self.chain_count * 2)

        # Reset chain
        self.chain_color = None
        self.chain_count = 0

    def _update_camera(self) -> None:
        target = self.player_y - SCREEN_H * 0.55
        self.camera_y += (target - self.camera_y) * CAMERA_FOLLOW
        # Track highest point reached
        if self.player_y < self.max_height:
            self.max_height = self.player_y

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)
        # Overload: random platform crumbles
        if self.heat >= HEAT_OVERLOAD and random.random() < 0.008:
            alive = [p for p in self.platforms if p.alive and p.crumbling == 0]
            if alive:
                victim = random.choice(alive)
                victim.crumbling = 30

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_float_texts(self) -> None:
        for ft in self.float_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]

    def _update_crumbling(self) -> None:
        for p in self.platforms:
            if p.crumbling > 0:
                p.crumbling -= 1
                if p.crumbling == 0:
                    p.alive = False
                    self._burst_particles(p)

    def _update_shake(self) -> None:
        if self.shake_timer > 0:
            self.shake_timer -= 1

    def _check_death(self) -> None:
        if self.player_y > self.camera_y + SCREEN_H + 60:
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score

    # ── particles ───────────────────────────────────────────────────────
    def _burst_particles(self, p: Platform) -> None:
        count = 8
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 3.5)
            self.particles.append(
                Particle(
                    x=p.x + random.uniform(2, p.w - 2),
                    y=p.y + PLATFORM_H / 2,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.5,
                    life=random.randint(12, 30),
                    color=p.color,
                )
            )

    # ── draw ────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        # Camera shake offset
        sx = 0
        sy = 0
        if self.shake_timer > 0:
            sx = random.randint(-self.shake_mag, self.shake_mag)
            sy = random.randint(-self.shake_mag, self.shake_mag)

        cam_y = int(self.camera_y) + sy
        shake_x = sx

        self._draw_stars(cam_y)
        self._draw_platforms(cam_y, shake_x)
        self._draw_player(cam_y, shake_x)
        self._draw_particles(cam_y, shake_x)
        self._draw_float_texts(cam_y, shake_x)
        self._draw_ui()
        if self.game_over:
            self._draw_game_over()

    def _draw_stars(self, cam_y: int) -> None:
        for i in range(STAR_COUNT):
            sx = (i * 53 + 17) % SCREEN_W
            sy = (i * 37 + int(cam_y * 0.25)) % SCREEN_H
            pyxel.pset(sx, sy, pyxel.COLOR_NAVY)

    def _draw_platforms(self, cam_y: int, sx: int) -> None:
        for p in self.platforms:
            if not p.alive:
                continue
            sy = int(p.y - cam_y)
            if sy < -10 or sy > SCREEN_H + 10:
                continue
            # Crumbling platforms flicker
            if p.crumbling > 0 and p.crumbling % 4 < 2:
                continue
            base_x = p.x + sx
            pyxel.rect(base_x, sy, p.w, PLATFORM_H, p.color)
            # Top highlight
            hl_color = pyxel.COLOR_WHITE if p.color != pyxel.COLOR_WHITE else pyxel.COLOR_GRAY
            pyxel.rect(base_x, sy, p.w, 1, hl_color)

    def _draw_player(self, cam_y: int, sx: int) -> None:
        px = int(self.player_x) + sx
        py = int(self.player_y - cam_y)
        # Body
        pyxel.rect(px, py, PLAYER_W, PLAYER_H, pyxel.COLOR_WHITE)
        # Eyes
        if self.player_vy < -1:  # jumping up → look up
            eye_y = py + 2
        elif self.player_vy > 2:  # falling → look down
            eye_y = py + 5
        else:
            eye_y = py + 3
        pyxel.pset(px + 2, eye_y, pyxel.COLOR_BLACK)
        pyxel.pset(px + 7, eye_y, pyxel.COLOR_BLACK)

    def _draw_particles(self, cam_y: int, sx: int) -> None:
        for p in self.particles:
            px = int(p.x) + sx
            py = int(p.y - cam_y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, p.color)

    def _draw_float_texts(self, cam_y: int, sx: int) -> None:
        for ft in self.float_texts:
            fx = int(ft.x - len(ft.text) * 2) + sx
            fy = int(ft.y - cam_y)
            pyxel.text(fx, fy, ft.text, ft.color)

    def _draw_ui(self) -> None:
        # Chain counter (top-left)
        if self.chain_count > 0 and self.chain_color is not None:
            chain_text = f"CHAIN:{self.chain_count}"
            pyxel.text(5, 5, chain_text, self.chain_color)
            # "READY" flash when one away from shatter
            if self.chain_count == CHAIN_THRESHOLD - 1 and pyxel.frame_count % 20 < 10:
                pyxel.text(5, 13, "NEXT!", pyxel.COLOR_YELLOW)

        # Score (top-right)
        score_text = f"{self.score:06d}"
        pyxel.text(SCREEN_W - 42, 5, score_text, pyxel.COLOR_WHITE)

        # Shatter count
        pyxel.text(SCREEN_W - 56, 15, f"SHATTER:{self.win_count}", pyxel.COLOR_ORANGE)

        # Heat bar (left side)
        heat_h = int(self.heat / 100 * 40)
        bar_x = 2
        bar_y = SCREEN_H - 44
        pyxel.rect(bar_x, bar_y, 6, 40, pyxel.COLOR_NAVY)
        heat_color = pyxel.COLOR_RED if self.heat >= HEAT_OVERLOAD else pyxel.COLOR_ORANGE
        pyxel.rect(bar_x, bar_y + 40 - heat_h, 6, heat_h, heat_color)
        pyxel.text(bar_x + 1, bar_y - 7, "HEAT", pyxel.COLOR_GRAY)

        # High score (bottom-left)
        if self.high_score > 0:
            pyxel.text(12, SCREEN_H - 9, f"BEST:{self.high_score:06d}", pyxel.COLOR_GRAY)

        # Height
        h_m = int((SCREEN_H - self.max_height + self.camera_y) / 10)
        pyxel.text(SCREEN_W - 50, SCREEN_H - 9, f"H:{h_m}m", pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        # Semi-transparent overlay (dither)
        for y in range(0, SCREEN_H, 3):
            for x in range(0, SCREEN_W, 3):
                if pyxel.pget(x, y) != pyxel.COLOR_BLACK:
                    pyxel.pset(x, y, pyxel.COLOR_BLACK)

        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        pyxel.text(cx - 24, cy - 16, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(cx - 32, cy - 2, f"SCORE: {self.score:06d}", pyxel.COLOR_WHITE)
        pyxel.text(cx - 28, cy + 10, f"SHATTERS: {self.win_count}", pyxel.COLOR_ORANGE)
        if self.game_over_timer > 30:
            pyxel.text(cx - 44, cy + 26, "SPACE TO RETRY", pyxel.COLOR_GRAY)


# ── Entry ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game()
