"""174_judo_surge - JUDO SURGE

Color-match judo throwing game. Player (auto-cycling 4-color belt) faces AI opponent.
Click the opponent to attempt a throw — must match your current belt color to the
opponent's vulnerable zone color. Same-color consecutive throws build COMBO chain
→ IPPON SUPER THROW.

面白い瞬間 (core fun moment):
Building a COMBO of 4+ same-color throws, triggering IPPON (SUPER THROW) that
instantly wins the round with rainbow particles and 3x score.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
DISPLAY_SCALE = 2

MAT_CX = 160
MAT_CY = 140
MAT_RADIUS = 100
PLAYER_RADIUS = 12
AI_RADIUS = 12

COLORS: tuple[int, ...] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "BLUE", "YELLOW")

HEAT_MAX = 100.0
HEAT_DECAY = 0.02
HEAT_MISMATCH = 20.0
HEAT_AI_HIT = 10.0
COMBO_THRESHOLD = 4
COMBO_SCORE_BASE = 100
COMBO_SCORE_PER = 50
IPPON_SCORE = 1000
GAME_TIME = 1800  # 60s at 30fps
IPPON_DURATION = 150  # 5s at 30fps
PLAYER_COLOR_INTERVAL = 90  # 3s at 30fps

# Pyxel 16-color palette
COL_BLACK = 0
COL_NAVY = 1
COL_PURPLE = 2
COL_GREEN = 3
COL_BROWN = 4
COL_DARK_BLUE = 5
COL_LIGHT_BLUE = 6
COL_WHITE = 7
COL_RED = 8
COL_ORANGE = 9
COL_YELLOW = 10
COL_LIME = 11
COL_CYAN = 12
COL_GRAY = 13
COL_PINK = 14
COL_PEACH = 15

RAINBOW_COLORS: tuple[int, ...] = (COL_RED, COL_ORANGE, COL_YELLOW, COL_GREEN, COL_CYAN, COL_PINK)

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


# ── Enums ──────────────────────────────────────────────────────────────────────
class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


# ── Data Classes ───────────────────────────────────────────────────────────────
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
    color: int
    life: int


# ── Game ───────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="JUDO SURGE",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        self._font: pyxel.Font | None = None
        if FONT_PATH.exists():
            self._font = pyxel.Font(str(FONT_PATH))
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── Reset / Init ───────────────────────────────────────────────────────
    def reset(self) -> None:
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.player_x: float = MAT_CX - 50
        self.player_y: float = MAT_CY
        self.ai_x: float = MAT_CX + 50
        self.ai_y: float = MAT_CY
        self.player_color_index: int = 0
        self.player_color_timer: int = PLAYER_COLOR_INTERVAL
        self.ai_color_index: int = 0
        self.ai_color_timer: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.ippon_timer: int = 0
        self.game_timer: int = GAME_TIME
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames: int = 0
        self._ai_attack_timer: int = 0
        self._ai_attacking: bool = False
        self._ai_attack_flash: int = 0
        self._frame_count: int = 0

    def _init_state(self) -> None:
        """Initialize state for a new round (callable from tests)."""
        self.phase = Phase.PLAYING
        self.player_x = MAT_CX - 50
        self.player_y = MAT_CY
        self.ai_x = MAT_CX + 50
        self.ai_y = MAT_CY
        self.player_color_index = 0
        self.player_color_timer = PLAYER_COLOR_INTERVAL
        self.ai_color_index = self._rng.randint(0, 3)
        self.ai_color_timer = self._rng.randint(120, 180)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.ippon_timer = 0
        self.game_timer = GAME_TIME
        self.particles.clear()
        self.floating_texts.clear()
        self._shake_frames = 0
        self._ai_attack_timer = self._rng.randint(180, 240)
        self._ai_attacking = False
        self._ai_attack_flash = 0
        self._frame_count = 0

    # ── Input ──────────────────────────────────────────────────────────────
    @staticmethod
    def _read_confirm() -> bool:
        return pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)

    @staticmethod
    def _read_click() -> bool:
        return pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

    # ── Core Logic ──────────────────────────────────────────────────────────
    def _player_color(self) -> int:
        return COLORS[self.player_color_index]

    def _ai_color(self) -> int:
        return COLORS[self.ai_color_index]

    def _attempt_throw(self, player_color: int, ai_color: int) -> tuple[bool, int]:
        """Returns (success, score_delta). Pure logic, testable."""
        is_ippon = self.ippon_timer > 0
        matched = is_ippon or (player_color == ai_color)

        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            base = COMBO_SCORE_BASE + self.combo * COMBO_SCORE_PER
            multiplier = 3 if is_ippon else 1
            score_delta = base * multiplier
            self.score += score_delta
            return True, score_delta

        self.combo = 0
        self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
        return False, 0

    def _trigger_ippon(self) -> None:
        """Activate IPPON super mode. Testable."""
        self.ippon_timer = IPPON_DURATION
        self.score += IPPON_SCORE

    def _update_heat(self) -> bool:
        """Decay heat. Returns True if game over from heat.
        Check threshold BEFORE decay so max heat reliably triggers game over."""
        is_game_over = self.heat >= HEAT_MAX
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)
        return is_game_over

    def _update_ippon(self) -> None:
        """Manage IPPON timer and state. Testable."""
        if self.ippon_timer > 0:
            self.ippon_timer -= 1
            if self.ippon_timer <= 0:
                self.ippon_timer = 0
                self.combo = 0

    def _update_ai(self) -> tuple[bool, int]:
        """Update AI color cycling and attack timing.
        Returns (is_attacking, current_ai_color). Testable."""
        self.ai_color_timer -= 1
        if self.ai_color_timer <= 0:
            self.ai_color_index = self._rng.randint(0, 3)
            self.ai_color_timer = self._rng.randint(120, 180)

        attacking = False
        if not self._ai_attacking:
            self._ai_attack_timer -= 1
            if self._ai_attack_timer <= 0:
                self._ai_attacking = True
                self._ai_attack_flash = 15
                self._ai_attack_timer = self._rng.randint(180, 240)
                attacking = True
        else:
            self._ai_attack_flash -= 1
            if self._ai_attack_flash <= 0:
                self._ai_attacking = False

        return attacking, self._ai_color()

    def _handle_ai_attack(self) -> str:
        """Handle AI attack: return 'hit' if player color doesn't match, 'defend' otherwise. Testable."""
        if self._player_color() != self._ai_color():
            self.heat = min(HEAT_MAX, self.heat + HEAT_AI_HIT)
            return "hit"
        return "defend"

    # ── Timer ───────────────────────────────────────────────────────────────
    def _update_timer(self) -> bool:
        """Decrement game timer. Returns True if time's up."""
        self.game_timer -= 1
        return self.game_timer <= 0

    # ── Particles ───────────────────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color,
                life=self._rng.randint(8, 20),
            ))

    def _spawn_ippon_particles(self) -> None:
        for _ in range(40):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(2.0, 5.0)
            self.particles.append(Particle(
                x=self.ai_x, y=self.ai_y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=self._rng.choice(RAINBOW_COLORS),
                life=self._rng.randint(15, 35),
            ))

    def _spawn_ai_attack_particles(self) -> None:
        for _ in range(8):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 2.5)
            self.particles.append(Particle(
                x=self.player_x, y=self.player_y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=COL_GRAY,
                life=self._rng.randint(5, 15),
            ))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int = 30) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    def _update_particles(self) -> None:
        survived: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survived.append(p)
        self.particles = survived

    def _update_floating_texts(self) -> None:
        survived: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.life -= 1
            if ft.life > 0:
                survived.append(ft)
        self.floating_texts = survived

    # ── Text Helpers ───────────────────────────────────────────────────────
    def _text_center(self, s: str, y: int, col: int) -> None:
        if self._font is not None:
            w = self._font.text_width(s)
            x = (SCREEN_W - w) // 2
            pyxel.text(x + 1, y + 1, s, COL_BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text((SCREEN_W - len(s) * 4) // 2, y, s, col)

    def _text(self, s: str, x: int, y: int, col: int) -> None:
        if self._font is not None:
            pyxel.text(x + 1, y + 1, s, COL_BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text(x, y, s, col)

    # ── Update ──────────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._read_confirm():
                self._init_state()
            return

        if self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            if self._read_confirm():
                self._init_state()
            return

        # ── PLAYING ──
        self._frame_count += 1

        # Player color auto-cycle (skip during IPPON — rainbow handles it)
        if self.ippon_timer == 0:
            self.player_color_timer -= 1
            if self.player_color_timer <= 0:
                self.player_color_index = (self.player_color_index + 1) % 4
                self.player_color_timer = PLAYER_COLOR_INTERVAL

        # Heat decay + game over check
        if self._update_heat():
            self.phase = Phase.GAME_OVER
            return

        # Timer countdown
        if self._update_timer():
            self.phase = Phase.GAME_OVER
            return

        # IPPON timer
        self._update_ippon()

        # AI behavior
        ai_attacking, ai_color = self._update_ai()
        if ai_attacking:
            result = self._handle_ai_attack()
            self._spawn_ai_attack_particles()
            if result == "hit":
                self._spawn_floating_text(
                    self.player_x, self.player_y - 20,
                    "HIT!", COL_RED, 30,
                )
            else:
                self._spawn_floating_text(
                    self.player_x, self.player_y - 20,
                    "DEFEND!", COL_CYAN, 30,
                )

        # Mouse click — attempt throw
        if self._read_click():
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            dist_to_ai = math.hypot(mx - self.ai_x, my - self.ai_y)
            dist_from_center = math.hypot(mx - MAT_CX, my - MAT_CY)
            if dist_from_center <= MAT_RADIUS and dist_to_ai <= AI_RADIUS + 10:
                success, score_delta = self._attempt_throw(self._player_color(), ai_color)

                if success:
                    self._spawn_particles(self.ai_x, self.ai_y, 12, self._player_color())
                    self._spawn_floating_text(
                        self.ai_x, self.ai_y - 20,
                        f"+{score_delta}", COL_WHITE, 30,
                    )
                    if self.combo > 1:
                        self._spawn_floating_text(
                            self.ai_x, self.ai_y - 35,
                            f"COMBO x{self.combo}!", COL_YELLOW, 35,
                        )

                    # Check IPPON trigger
                    if self.ippon_timer == 0 and self.combo >= COMBO_THRESHOLD:
                        self._trigger_ippon()
                        self._spawn_ippon_particles()
                        self._spawn_floating_text(
                            MAT_CX, MAT_CY - 40,
                            "IPPON!!", COL_CYAN, 60,
                        )
                        self._shake_frames = 20

                else:
                    self._spawn_floating_text(
                        self.ai_x, self.ai_y - 20,
                        "MISS!", COL_RED, 30,
                    )

        # Shake effect
        if self._shake_frames > 0:
            self._shake_frames -= 1

        # AI knockback recovery
        target_ax = MAT_CX + 50
        target_ay = MAT_CY
        self.ai_x += (target_ax - self.ai_x) * 0.02
        self.ai_y += (target_ay - self.ai_y) * 0.02

        self._update_particles()
        self._update_floating_texts()

    # ── Draw ────────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(COL_NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        # Shake offset
        ox = oy = 0
        if self._shake_frames > 0:
            ox = self._rng.randint(-4, 4)
            oy = self._rng.randint(-4, 4)

        self._draw_dojo(ox, oy)
        self._draw_fighters(ox, oy)
        self._draw_particles(ox, oy)
        self._draw_floating_texts(ox, oy)
        self._draw_hud()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        self._text_center("JUDO SURGE", 20, COL_CYAN)
        self._text_center("Color-Match Judo Throwing", 50, COL_WHITE)
        self._text_center("Match belt color to opponent", 75, COL_WHITE)
        self._text_center("vulnerable zone, CLICK to throw!", 88, COL_WHITE)
        self._text_center("COMBO x4 = IPPON SUPER THROW!", 120, COL_YELLOW)
        self._text_center("Rainbow mode / 3x score / 5 sec", 133, COL_CYAN)
        self._text_center("Wrong color adds HEAT", 165, COL_RED)
        self._text_center("HEAT 100 = Game Over", 178, COL_RED)
        self._text_center("TIME 60 sec", 200, COL_WHITE)
        self._text_center("SPACE to Start", 225, COL_LIME)

    def _draw_game_over(self) -> None:
        pyxel.rect(60, 60, 200, 90, COL_BLACK)
        pyxel.rectb(60, 60, 200, 90, COL_WHITE)
        self._text_center("GAME OVER", 75, COL_RED)
        self._text_center(f"SCORE: {self.score}", 100, COL_WHITE)
        self._text_center(f"MAX COMBO: x{self.max_combo}", 115, COL_YELLOW)
        self._text_center("SPACE to Retry", 135, COL_LIME)

    def _draw_dojo(self, ox: int, oy: int) -> None:
        cx = MAT_CX + ox
        cy = MAT_CY + oy
        pyxel.circ(cx, cy, MAT_RADIUS, COL_BROWN)
        pyxel.circ(cx, cy, MAT_RADIUS - 3, COL_PEACH)
        pyxel.circb(cx, cy, MAT_RADIUS, COL_BROWN)
        pyxel.circb(cx, cy, MAT_RADIUS - 3, COL_WHITE)

    def _draw_fighters(self, ox: int, oy: int) -> None:
        # Player
        px = int(self.player_x + ox)
        py = int(self.player_y + oy)
        player_c = self._player_color()
        if self.ippon_timer > 0:
            flash_idx = (self._frame_count // 4) % len(RAINBOW_COLORS)
            player_c = RAINBOW_COLORS[flash_idx]
        pyxel.circ(px, py, PLAYER_RADIUS, player_c)
        pyxel.circb(px, py, PLAYER_RADIUS, COL_BLACK)
        # Player label
        self._text("YOU", px - 8, py - PLAYER_RADIUS - 12, COL_WHITE)

        # AI
        ax = int(self.ai_x + ox)
        ay = int(self.ai_y + oy)
        pyxel.circ(ax, ay, AI_RADIUS, COL_GRAY)
        pyxel.circb(ax, ay, AI_RADIUS, COL_BLACK)
        # AI label
        self._text("CPU", ax - 8, ay - AI_RADIUS - 12, COL_WHITE)

        # Vulnerable zone dot above AI
        zone_c = self._ai_color()
        if self._ai_attacking:
            zone_c = COL_WHITE
        pyxel.circ(ax, ay - AI_RADIUS - 5, 3, zone_c)

    def _draw_particles(self, ox: int, oy: int) -> None:
        for p in self.particles:
            alpha = p.life / 20
            radius = max(1, int(3 * alpha))
            px = int(p.x + ox)
            py = int(p.y + oy)
            pyxel.circ(px, py, radius, p.color)

    def _draw_floating_texts(self, ox: int, oy: int) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30
            col = ft.color if alpha > 0.3 else COL_GRAY
            tx = int(ft.x + ox)
            ty = int(ft.y + oy)
            pyxel.text(tx, ty, ft.text, col)

    def _draw_hud(self) -> None:
        # Score top-left
        self._text(f"SCORE: {self.score}", 4, 4, COL_WHITE)

        # Combo top-center
        if self.ippon_timer > 0:
            flash_idx = (self._frame_count // 4) % len(RAINBOW_COLORS)
            combo_color = RAINBOW_COLORS[flash_idx]
            combo_text = "IPPON!"
        elif self.combo > 0:
            combo_color = COL_YELLOW if self.combo >= COMBO_THRESHOLD else COL_CYAN
            combo_text = f"COMBO x{self.combo}"
        else:
            combo_text = ""
            combo_color = COL_WHITE

        if combo_text:
            tw = len(combo_text) * 4
            self._text(combo_text, (SCREEN_W - tw) // 2, 4, combo_color)

        # HEAT bar top-right
        bar_x = SCREEN_W - 110
        bar_y = 4
        bar_w = 80
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, COL_WHITE)
        ratio = min(1.0, self.heat / HEAT_MAX)
        fill_w = int(bar_w * ratio)
        bar_col = COL_GREEN if ratio < 0.5 else (COL_YELLOW if ratio < 0.8 else COL_RED)
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_col)
        self._text(f"{self.heat:.0f}", bar_x + bar_w + 4, bar_y - 1, bar_col)

        # Timer
        sec = self.game_timer / FPS
        timer_col = COL_WHITE if sec > 10 else COL_RED
        self._text(f"TIME: {sec:.0f}s", SCREEN_W - 110, 14, timer_col)

        # Belt color indicator
        self._text("BELT:", 4, 18, COL_GRAY)
        belt_c = self._player_color()
        if self.ippon_timer > 0:
            flash_idx = (self._frame_count // 4) % len(RAINBOW_COLORS)
            belt_c = RAINBOW_COLORS[flash_idx]
        pyxel.rect(36, 18, 20, 6, belt_c)
        pyxel.rectb(36, 18, 20, 6, COL_WHITE)

        # IPPON timer
        if self.ippon_timer > 0:
            ippon_sec = self.ippon_timer / FPS
            flash_idx = (self._frame_count // 4) % len(RAINBOW_COLORS)
            self._text(f"IPPON: {ippon_sec:.1f}s", 4, 30, RAINBOW_COLORS[flash_idx])


# ── Make game (for tests) ────────────────────────────────────────────────────
def _make_game(rng: random.Random | None = None) -> Game:
    """Create a minimal Game instance for testing (no pyxel.init/run)."""
    g = Game.__new__(Game)
    g._font = None
    g._rng = rng if rng is not None else random.Random(42)
    g.reset()
    return g


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
