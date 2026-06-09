"""114_trampoline_surge — Color-Match Trampoline Acrobatics.

Side-view trampoline game where the player bounces and aims for same-color zones
to build COMBO chains. Aerial flips add bonus multipliers. COMBO>=4 triggers
SUPER BOUNCE.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import pyxel


# ---------------------------------------------------------------------------
# Color constants (raw ints for headless test compatibility)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Zone:
    """A color-coded zone on the trampoline bed."""

    x: int  # left edge x
    w: int  # width
    color: int  # 0-3: 8=RED, 3=GREEN, 5=DARK_BLUE, 9=ORANGE


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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    TRAMPOLINE_Y = 200  # top surface of trampoline bed
    GROUND_Y = 210  # bottom of trampoline

    ZONE_COUNT = 5
    ZONE_LEFT = 40
    ZONE_RIGHT = 280

    zone_colors: tuple[int, ...] = (RED, GREEN, DARK_BLUE, ORANGE)

    # Physics
    GRAVITY: float = 0.4
    BOUNCE_POWER: float = 8.0
    BOUNCE_DECAY: float = 0.92
    AIR_CONTROL: float = 0.3

    # Heat
    MAX_HEAT: float = 100.0
    HEAT_DECAY: float = 0.3
    HEAT_WRONG: float = 20.0

    # Super mode
    SUPER_COMBO_REQ: int = 4
    SUPER_DURATION: int = 150  # frames (5s at 30fps)

    # Timer
    GAME_DURATION: int = 1800  # 60 seconds

    def __init__(self) -> None:
        self.phase: int = 0  # 0=TITLE, 1=PLAYING, 2=GAME_OVER
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.game_timer: int = self.GAME_DURATION

        self.player_x: float = 160.0
        self.player_y: float = self.TRAMPOLINE_Y - 50.0
        self.player_vy: float = 0.0
        self.player_vx: float = 0.0
        self.player_w: int = 16
        self.player_h: int = 20
        self.rotation: int = 0
        self.rotation_timer: int = 0
        self.on_bed: bool = False
        self.flip_bonus: int = 0
        self.flip_count: int = 0
        self.space_pressed: bool = False
        self.frame: int = 0

        self.zones: list[Zone] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        self._last_zone_color: int = -1
        self._consecutive_bounces: int = 0

        self._init_zones()

        # BDF font
        font_path = Path(__file__).with_name("k8x12.bdf")
        if font_path.exists():
            pyxel.load(str(font_path), False, False, False, False)

    # ------------------------------------------------------------------
    # Zone generation
    # ------------------------------------------------------------------
    def _init_zones(self) -> None:
        """Generate 5 random zones spanning 40..280 (total width 240)."""
        self.zones.clear()
        total_width = self.ZONE_RIGHT - self.ZONE_LEFT  # 240
        widths: list[int] = []
        remaining = total_width
        for i in range(self.ZONE_COUNT - 1):
            min_w = 36
            max_w = min(64, remaining - (self.ZONE_COUNT - 1 - i) * 36)
            w = random.randint(min_w, max_w)
            widths.append(w)
            remaining -= w
        widths.append(remaining)

        x = self.ZONE_LEFT
        for w in widths:
            color = random.choice(self.zone_colors)
            self.zones.append(Zone(x=x, w=w, color=color))
            x += w

    def _refresh_zones(self) -> None:
        self._init_zones()

    def _get_zone_at(self, px: float) -> Zone | None:
        for z in self.zones:
            if z.x <= px < z.x + z.w:
                return z
        return None

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.phase = 1  # PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.game_timer = self.GAME_DURATION
        self.player_x = 160.0
        self.player_y = self.TRAMPOLINE_Y - 50.0
        self.player_vy = 0.0
        self.player_vx = 0.0
        self.rotation = 0
        self.rotation_timer = 0
        self.on_bed = False
        self.flip_bonus = 0
        self.flip_count = 0
        self.space_pressed = False
        self.frame = 0
        self._last_zone_color = -1
        self._consecutive_bounces = 0
        self.particles.clear()
        self.floating_texts.clear()
        self._init_zones()

    # ------------------------------------------------------------------
    # Physics
    # ------------------------------------------------------------------
    def _update_physics(self) -> None:
        self.player_vy += self.GRAVITY
        self.player_x += self.player_vx
        self.player_y += self.player_vy

        if not self.on_bed:
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                self.player_vx -= self.AIR_CONTROL
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                self.player_vx += self.AIR_CONTROL

        self.player_vx *= 0.95

        # Clamp x
        hw = self.player_w / 2
        if self.player_x < hw:
            self.player_x = hw
            self.player_vx = abs(self.player_vx) * 0.3
        elif self.player_x > self.SCREEN_W - hw:
            self.player_x = self.SCREEN_W - hw
            self.player_vx = -abs(self.player_vx) * 0.3

    def _check_trampoline(self) -> None:
        """Check trampoline contact and handle bounce."""
        if self.on_bed:
            # Already on bed; check if we lifted off
            if self.player_y < self.TRAMPOLINE_Y:
                self.on_bed = False
            return

        if self.player_y >= self.TRAMPOLINE_Y and self.player_vy > 0:
            zone = self._get_zone_at(self.player_x)
            matched = False

            if self.super_mode:
                # SUPER mode: all zones match
                matched = True
                self.combo += 1
            elif zone is not None:
                if self._last_zone_color >= 0 and zone.color == self._last_zone_color:
                    self.combo += 1
                    matched = True
                else:
                    self.combo = 0
                    self.heat += self.HEAT_WRONG
            else:
                # No zone (shouldn't happen normally)
                self.combo = 0
                self.heat += self.HEAT_WRONG

            if matched:
                points = self.combo * 10
                self.score += points
                self.score += self.flip_bonus
                self._add_floating_text(
                    self.player_x,
                    self.TRAMPOLINE_Y - 8,
                    f"+{points}",
                    WHITE,
                )
                self._spawn_land_particles(self.player_x, self.TRAMPOLINE_Y, zone.color if zone else WHITE)
            else:
                self._spawn_land_particles(self.player_x, self.TRAMPOLINE_Y, GRAY)

            if self.combo > self.max_combo:
                self.max_combo = self.combo

            # SUPER BOUNCE check
            if self.combo >= self.SUPER_COMBO_REQ and not self.super_mode:
                self.super_mode = True
                self.super_timer = self.SUPER_DURATION
                self._add_floating_text(self.player_x, self.TRAMPOLINE_Y - 16, "SUPER!", YELLOW)

            # Bounce physics
            decay = self.BOUNCE_DECAY ** self._consecutive_bounces
            self.player_vy = -(self.BOUNCE_POWER * decay)
            self.player_y = float(self.TRAMPOLINE_Y)
            self.on_bed = True
            self._consecutive_bounces += 1

            # Track last zone color for next landing
            if zone is not None:
                self._last_zone_color = zone.color

            # Reset flip tracking
            self.flip_bonus = 0
            self.flip_count = 0

            # Refresh zones
            self._refresh_zones()

        # Check lift-off
        if self.player_y < self.TRAMPOLINE_Y:
            self.on_bed = False

    # ------------------------------------------------------------------
    # Rotation / Flip
    # ------------------------------------------------------------------
    def _update_rotation(self) -> None:
        if not self.on_bed:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.rotation = (self.rotation + 1) % 4
                self.flip_count += 1
                self.flip_bonus = self.flip_count * 50
                self._add_floating_text(
                    self.player_x,
                    self.player_y - 8,
                    f"FLIP x{self.flip_count}",
                    CYAN,
                )

    # ------------------------------------------------------------------
    # Heat
    # ------------------------------------------------------------------
    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self.phase = 2  # GAME_OVER
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    # ------------------------------------------------------------------
    # Super mode
    # ------------------------------------------------------------------
    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------
    def _spawn_land_particles(self, x: float, y: float, color: int) -> None:
        n = 8 if self.super_mode else 5
        for _ in range(n):
            vx = random.uniform(-1.5, 1.5)
            vy = random.uniform(-3.0, -0.5)
            life = random.randint(8, 18)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    def _update_effects(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        for ft in self.floating_texts:
            ft.y -= 0.6
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ------------------------------------------------------------------
    # Input (title / game over)
    # ------------------------------------------------------------------
    def _handle_title_input(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    def _handle_gameover_input(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = 0  # TITLE
            # prepare for next start
            self.score = 0
            self.combo = 0
            self.max_combo = 0
            self.heat = 0.0
            self.super_mode = False
            self.super_timer = 0
            self.game_timer = self.GAME_DURATION
            self.player_x = 160.0
            self.player_y = self.TRAMPOLINE_Y - 50.0
            self.player_vy = 0.0
            self.player_vx = 0.0
            self.rotation = 0
            self.on_bed = False
            self.flip_bonus = 0
            self.flip_count = 0
            self._last_zone_color = -1
            self._consecutive_bounces = 0
            self.particles.clear()
            self.floating_texts.clear()
            self._init_zones()

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def update(self) -> None:
        self.frame = pyxel.frame_count

        if self.phase == 0:
            self._handle_title_input()
            return

        if self.phase == 2:
            self._handle_gameover_input()
            return

        # PLAYING
        self._update_physics()
        self._check_trampoline()
        self._update_rotation()
        self._update_heat()
        self._update_super()
        self._update_effects()

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = 2  # GAME_OVER

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(80, 60, "TRAMPOLINE SURGE", WHITE)
        pyxel.text(70, 80, "SPACE: Bounce / Rotate", LIGHT_BLUE)
        pyxel.text(58, 92, "LEFT/RIGHT: Move in air", LIGHT_BLUE)
        pyxel.text(40, 104, "Land on same color to COMBO!", LIME)
        pyxel.text(55, 116, "COMBO x4 = SUPER BOUNCE!", YELLOW)
        pyxel.text(95, 140, "Press SPACE to start", WHITE)

    def _draw_playing(self) -> None:
        pyxel.cls(NAVY)

        # Trampoline bed background
        pyxel.rect(self.ZONE_LEFT, self.TRAMPOLINE_Y, self.ZONE_RIGHT - self.ZONE_LEFT, self.GROUND_Y - self.TRAMPOLINE_Y, GRAY)

        # Draw zones
        for z in self.zones:
            c = z.color
            if self.super_mode:
                # Pulsing rainbow in super mode
                pulse = (self.frame // 5) % 4
                sc = self.zone_colors[pulse]
                pyxel.rect(z.x, self.TRAMPOLINE_Y, z.w, self.GROUND_Y - self.TRAMPOLINE_Y, sc)
            else:
                pyxel.rect(z.x, self.TRAMPOLINE_Y, z.w, self.GROUND_Y - self.TRAMPOLINE_Y, c)

        # Draw particles
        for p in self.particles:
            alpha = p.life / 18
            col = p.color if alpha > 0.5 else GRAY
            pyxel.pset(int(p.x), int(p.y), col)

        # Draw player
        px = int(self.player_x)
        py = int(self.player_y)
        player_color = PINK if self.super_mode else WHITE
        pyxel.rect(
            px - self.player_w // 2,
            py - self.player_h,
            self.player_w,
            self.player_h,
            player_color,
        )

        # Rotation indicator
        if self.rotation > 0:
            rots = self.rotation
            for i in range(rots):
                xo = (i % 2) * 6 - 3
                yo = (i // 2) * 6 - 3
                pyxel.circ(px + xo, py - self.player_h // 2 + yo, 2, YELLOW)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 30
            # Fade: use WHITE when alpha > 0.5
            col = ft.color if alpha > 0.5 else GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, col)

        # HUD
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(230, 4, f"COMBO: x{self.combo}", WHITE)

        # Heat bar
        bar_w = 60
        heat_ratio = self.heat / self.MAX_HEAT
        pyxel.rect(4, 16, bar_w, 6, GRAY)
        pyxel.rect(4, 16, int(bar_w * heat_ratio), 6, RED)

        # Timer bar
        time_ratio = self.game_timer / self.GAME_DURATION
        timer_w = int(100 * time_ratio)
        pyxel.rect(110, 4, 100, 6, GRAY)
        if time_ratio > 0.3:
            pyxel.rect(110, 4, timer_w, 6, LIME)
        else:
            pyxel.rect(110, 4, timer_w, 6, RED)

        # SUPER indicator
        if self.super_mode:
            pulse = (self.frame // 8) % 2
            col = YELLOW if pulse else PINK
            pyxel.text(130, 20, "SUPER!", col)
            # Remaining super time bar
            super_ratio = self.super_timer / self.SUPER_DURATION
            pyxel.rect(180, 22, 60, 4, GRAY)
            pyxel.rect(180, 22, int(60 * super_ratio), 4, YELLOW)

    def _draw_gameover(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(110, 70, "GAME OVER", RED)
        pyxel.text(100, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(85, 102, f"MAX COMBO: x{self.max_combo}", LIME)
        pyxel.text(90, 130, "Press SPACE to retry", LIGHT_BLUE)

    def draw(self) -> None:
        if self.phase == 0:
            self._draw_title()
        elif self.phase == 1:
            self._draw_playing()
        elif self.phase == 2:
            self._draw_gameover()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    game = Game()
    pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="Trampoline Surge", display_scale=2)
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
