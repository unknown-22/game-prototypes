"""Badminton Surge - Side-view badminton rally game.

Color-match consecutive rallies to build COMBO, trigger SUPER SMASH,
and survive 90 seconds against an AI that never misses.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240
NET_X = 160
NET_WIDTH = 4
PLAYER_X = 40
AI_X = 280
RACKET_W = 6
RACKET_H = 40
SHUTTLECOCK_R = 4
GRAVITY = 0.15
DRAG = 0.995
HIT_POWER_X = 3.5
HIT_POWER_Y_BASE = -4.0
COMBO_THRESHOLD = 4
SUPER_DURATION = 150
GAME_DURATION = 2700
HEAT_PER_MISS = 15
HEAT_PER_WRONG_COLOR = 10
HEAT_DECAY = 0.5
COLORS: tuple[int, int, int, int] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "BLUE", "YELLOW")
PLAYER_MIN_Y = 20
PLAYER_MAX_Y = SCREEN_H - RACKET_H - 10
AI_SPEED = 0.06
PLAYER_SPEED = 0.25
SWING_FRAMES = 6
RACKET_COLOR_CYCLE_FRAMES = 90
GHOST_TRAIL_LIFE = 120


# --- Phase ---
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# --- Data Classes ---
@dataclass
class Shuttlecock:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True


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


@dataclass
class GhostTrail:
    x: float
    y: float
    life: int
    color: int


# --- Game Class ---
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Badminton Surge", display_scale=2)
        pyxel.mouse(True)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # State initialization
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.player_y: float = SCREEN_H // 2
        self.player_racket_color: int = 0
        self.ai_y: float = SCREEN_H // 2
        self.shuttlecock: Shuttlecock | None = None
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.phase: Phase = Phase.TITLE
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_trail: list[GhostTrail] = []
        self.shake_frames: int = 0
        self.rally_count: int = 0
        self.last_hit_color: int = -1
        self._swing_timer: int = 0
        self._trail_record: list[tuple[float, float]] = []
        self._ghost_bonus_collected: bool = False
        self._serve_timer: int = 0
        self._racket_color_timer: int = RACKET_COLOR_CYCLE_FRAMES

    # ------------------------------------------------------------------
    # Pyxel callbacks
    # ------------------------------------------------------------------
    def update(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1
        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.GAME_OVER:
                self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(1)  # NAVY background
        # Screen shake
        ox = oy = 0
        if self.shake_frames > 0:
            intensity = max(1, self.shake_frames // 2)
            ox = self._rng.randrange(-intensity, intensity + 1)
            oy = self._rng.randrange(-intensity, intensity + 1)
        try:
            pyxel.camera(ox, oy)
        except BaseException:
            pass

        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING:
                self._draw_court()
                self._draw_net()
                self._draw_ghost_trail()
                self._draw_shuttlecock()
                self._draw_ai_racket()
                self._draw_player_racket()
                self._draw_particles()
                self._draw_floating_texts()
                self._draw_hud()
            case Phase.GAME_OVER:
                self._draw_court()
                self._draw_net()
                self._draw_ghost_trail()
                self._draw_shuttlecock()
                self._draw_ai_racket()
                self._draw_player_racket()
                self._draw_particles()
                self._draw_floating_texts()
                self._draw_hud()
                self._draw_game_over()

        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

    # ------------------------------------------------------------------
    # Phase: TITLE
    # ------------------------------------------------------------------
    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.PLAYING
            self._serve_shuttlecock()

    def _draw_title(self) -> None:
        # Court background
        self._draw_court()
        self._draw_net()
        # Title card
        pyxel.rect(60, 40, 200, 80, 0)
        pyxel.rectb(60, 40, 200, 80, 7)
        pyxel.text(85, 55, "BADMINTON SURGE", 7)
        pyxel.text(100, 68, "color-match rally!", 10)
        # Instructions
        pyxel.text(75, 140, "Mouse Y: move racket", 7)
        pyxel.text(75, 152, "Mouse Wheel: change color", 7)
        pyxel.text(75, 164, "Left Click: swing", 7)
        pyxel.text(100, 185, "Match racket color", 10)
        pyxel.text(95, 197, "to shuttlecock color!", 10)
        # Start prompt (blinking)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(115, 215, "Click to Start", 7)

    # ------------------------------------------------------------------
    # Phase: PLAYING
    # ------------------------------------------------------------------
    def _update_playing(self) -> None:
        if self.game_timer > 0:
            self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        self._update_heat()
        if self.heat >= 100:
            self.phase = Phase.GAME_OVER
            return

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.combo = 0

        # Racket color auto-cycle
        self._racket_color_timer -= 1
        if self._racket_color_timer <= 0:
            self._racket_color_timer = RACKET_COLOR_CYCLE_FRAMES
            self.player_racket_color = (self.player_racket_color + 1) % 4

        # Player input: racket position
        raw_y = pyxel.mouse_y
        target_y = max(PLAYER_MIN_Y, min(PLAYER_MAX_Y, float(raw_y)))
        self.player_y += (target_y - self.player_y) * PLAYER_SPEED

        # Player input: racket color change via mouse wheel
        wheel = pyxel.mouse_wheel
        if wheel != 0:
            self.player_racket_color = (self.player_racket_color + (1 if wheel > 0 else -1)) % 4

        # Swing timer
        if self._swing_timer > 0:
            self._swing_timer -= 1

        # Player input: swing
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._swing_timer = SWING_FRAMES
            if self._try_player_hit():
                pass
            else:
                self._add_floating_text(
                    PLAYER_X + 10, self.player_y + RACKET_H // 2,
                    "miss!", 8, 30,
                )

        # AI tracks shuttlecock
        self._update_ai()

        # Shuttlecock physics
        if self.shuttlecock is not None and self.shuttlecock.active:
            self._update_shuttlecock(self.shuttlecock)
            self._trail_record.append((self.shuttlecock.x, self.shuttlecock.y))
            if len(self._trail_record) > 300:
                self._trail_record.pop(0)

            # Ghost trail bonus check
            if not self._ghost_bonus_collected:
                self._check_ghost_bonus()

            # Player miss: shuttlecock off left edge
            if self.shuttlecock.x < -30:
                self._on_player_miss()
                return

            # Shuttlecock off right edge (shouldn't happen, ai never misses)
            if self.shuttlecock.x > SCREEN_W + 30:
                self._on_player_miss()
                return

        # Serve new shuttlecock after delay
        if self.shuttlecock is None or not self.shuttlecock.active:
            if self._serve_timer > 0:
                self._serve_timer -= 1
            else:
                self._serve_shuttlecock()

        self._update_particles()
        self._update_floating_texts()
        self._update_ghost_trail()

    # ------------------------------------------------------------------
    # Phase: GAME OVER
    # ------------------------------------------------------------------
    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._update_ghost_trail()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    # ------------------------------------------------------------------
    # Player hit logic (testable)
    # ------------------------------------------------------------------
    def _try_player_hit(self) -> bool:
        """Attempt to hit the shuttlecock. Returns True if successful."""
        sc = self.shuttlecock
        if sc is None or not sc.active:
            return False
        if sc.x > NET_X:
            return False  # shuttlecock on opponent side

        dist = self._dist_player_to_shuttlecock(sc)
        if dist > RACKET_H / 2 + SHUTTLECOCK_R + 4:
            return False

        self._on_player_hit(sc)
        return True

    def _on_player_hit(self, sc: Shuttlecock) -> None:
        """Process a successful player hit."""
        racket_matches = self.player_racket_color == sc.color

        if self.super_mode:
            self.combo += 1
            is_match = True
        elif racket_matches:
            if self.last_hit_color == sc.color:
                self.combo += 1
            else:
                self.combo = 1
            is_match = True
        else:
            self.combo = 0
            self.heat += HEAT_PER_WRONG_COLOR
            is_match = False

        self.last_hit_color = sc.color

        # Score
        base_score: int = 10
        combo_bonus: int = self.combo * 5
        total: int = base_score + combo_bonus
        if self.super_mode:
            total *= 3
        self.score += total

        # Advance racket color
        self.player_racket_color = (self.player_racket_color + 1) % 4
        self._racket_color_timer = RACKET_COLOR_CYCLE_FRAMES

        # Combo threshold -> SUPER SMASH
        if self.combo >= COMBO_THRESHOLD and not self.super_mode:
            self._activate_super_mode()
        self.max_combo = max(self.max_combo, self.combo)

        # Effects
        hit_x = sc.x
        hit_y = sc.y
        self._spawn_particles(hit_x, hit_y, COLORS[sc.color], 8)
        self._spawn_particles(
            PLAYER_X + RACKET_W, self.player_y + RACKET_H // 2,
            COLORS[self.player_racket_color - 1], 4,
        )
        self.shake_frames = max(self.shake_frames, 4)

        if is_match:
            self._add_floating_text(hit_x, hit_y - 8, f"+{total}", sc.color)
            if self.combo >= 2:
                self._add_floating_text(hit_x, hit_y - 18, f"{self.combo} COMBO!", 7)
            if self.combo >= COMBO_THRESHOLD:
                self._add_floating_text(hit_x, hit_y - 30, "SUPER!", 10)
        else:
            self._add_floating_text(hit_x, hit_y - 8, f"+{total}", 13)
            self._add_floating_text(hit_x, hit_y - 18, "WRONG!", 8)

        # Launch toward AI
        sc.vx = HIT_POWER_X
        sc.vy = HIT_POWER_Y_BASE + self._rng.uniform(-1.5, 1.5)

    def _dist_player_to_shuttlecock(self, sc: Shuttlecock) -> float:
        cx = PLAYER_X + RACKET_W / 2
        cy = self.player_y + RACKET_H / 2
        return math.sqrt((sc.x - cx) ** 2 + (sc.y - cy) ** 2)

    # ------------------------------------------------------------------
    # AI logic (testable)
    # ------------------------------------------------------------------
    def _update_ai(self) -> None:
        sc = self.shuttlecock
        if sc is None or not sc.active:
            return

        # Track shuttlecock Y
        target_y = sc.y
        self.ai_y += (target_y - self.ai_y) * AI_SPEED
        self.ai_y = max(PLAYER_MIN_Y, min(PLAYER_MAX_Y, self.ai_y))

        # AI returns shuttlecock when it's on AI side and moving toward AI
        if sc.x > NET_X + 20 and sc.vx > 0:
            self._ai_return(sc)

    def _ai_return(self, sc: Shuttlecock) -> None:
        """AI returns the shuttlecock with a random color."""
        dist = abs(sc.x - AI_X)
        if dist > RACKET_H + SHUTTLECOCK_R:
            return

        new_color = self._rng.randrange(0, 4)
        sc.color = new_color
        sc.vx = -HIT_POWER_X * 0.85
        sc.vy = HIT_POWER_Y_BASE + self._rng.uniform(-1.0, 1.0)
        self._spawn_particles(AI_X - RACKET_W, self.ai_y + RACKET_H // 2, COLORS[new_color], 3)

    # ------------------------------------------------------------------
    # Shuttlecock physics (testable)
    # ------------------------------------------------------------------
    def _update_shuttlecock(self, sc: Shuttlecock) -> None:
        sc.vy += GRAVITY
        sc.vx *= DRAG
        sc.vy *= DRAG
        sc.x += sc.vx
        sc.y += sc.vy

        # Bounce off top/bottom
        if sc.y < SHUTTLECOCK_R:
            sc.y = SHUTTLECOCK_R
            sc.vy = abs(sc.vy) * 0.6
        if sc.y > SCREEN_H - SHUTTLECOCK_R:
            sc.y = SCREEN_H - SHUTTLECOCK_R
            sc.vy = -abs(sc.vy) * 0.6

    # ------------------------------------------------------------------
    # Serve
    # ------------------------------------------------------------------
    def _serve_shuttlecock(self) -> None:
        color = self._rng.randrange(0, 4)
        self.shuttlecock = Shuttlecock(
            x=float(AI_X - 10),
            y=self.ai_y,
            vx=-HIT_POWER_X * 0.7,
            vy=HIT_POWER_Y_BASE + self._rng.uniform(-1.5, 1.5),
            color=color,
            active=True,
        )
        self._trail_record.clear()
        self._ghost_bonus_collected = False
        self._serve_timer = 40

    # ------------------------------------------------------------------
    # Miss handling (testable)
    # ------------------------------------------------------------------
    def _on_player_miss(self) -> None:
        self.heat += HEAT_PER_MISS
        self.combo = 0
        self.last_hit_color = -1
        self._add_floating_text(PLAYER_X + 10, self.player_y, "MISS!", 8, 40)

        # Convert trail record to ghost trail
        if self._trail_record:
            color = COLORS[self._rng.randrange(0, 4)]
            for x, y in self._trail_record[::4]:
                self.ghost_trail.append(GhostTrail(x=x, y=y, life=GHOST_TRAIL_LIFE, color=color))
        self._trail_record.clear()

        self.shuttlecock = None
        self._serve_timer = 25
        self.rally_count += 1

    # ------------------------------------------------------------------
    # Ghost trail bonus (testable)
    # ------------------------------------------------------------------
    def _check_ghost_bonus(self) -> None:
        sc = self.shuttlecock
        if sc is None:
            return
        for gt in self.ghost_trail:
            if gt.life <= 0:
                continue
            dx = sc.x - gt.x
            dy = sc.y - gt.y
            if dx * dx + dy * dy < 64:  # within 8px
                self._ghost_bonus_collected = True
                self.score += 25
                self._add_floating_text(sc.x, sc.y - 8, "+25 GHOST", 12, 30)
                self._spawn_particles(sc.x, sc.y, 12, 5)
                return

    # ------------------------------------------------------------------
    # SUPER SMASH (testable)
    # ------------------------------------------------------------------
    def _activate_super_mode(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.shake_frames = max(self.shake_frames, 12)
        self._add_floating_text(SCREEN_W // 2, SCREEN_H // 2 - 20, "SUPER SMASH!!", 10, 60)
        self._spawn_particles(SCREEN_W // 2, SCREEN_H // 2, 10, 30)

    # ------------------------------------------------------------------
    # HEAT (testable)
    # ------------------------------------------------------------------
    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ------------------------------------------------------------------
    # Effect systems
    # ------------------------------------------------------------------
    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            life = self._rng.randint(8, 20)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life, color=color,
            ))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
        self.particles = [p for p in self.particles if p.life > 0]

    def _add_floating_text(self, x: float, y: float, text: str, color: int, life: int = 25) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.life -= 1
            ft.y -= 0.7
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_ghost_trail(self) -> None:
        for gt in self.ghost_trail:
            gt.life -= 1
        self.ghost_trail = [gt for gt in self.ghost_trail if gt.life > 0]

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def _draw_court(self) -> None:
        # Floor
        pyxel.rect(0, SCREEN_H - 30, SCREEN_W, 30, 5)
        pyxel.rect(0, SCREEN_H - 30, SCREEN_W, 2, 7)
        pyxel.rect(0, SCREEN_H - 28, SCREEN_W, 1, 13)
        # Court lines
        pyxel.line(0, SCREEN_H - 30, SCREEN_W, SCREEN_H - 30, 7)
        pyxel.line(PLAYER_X, 0, PLAYER_X, SCREEN_H - 28, 13)
        pyxel.line(AI_X, 0, AI_X, SCREEN_H - 28, 13)

    def _draw_net(self) -> None:
        # Net pole
        pyxel.rect(NET_X, 20, NET_WIDTH, SCREEN_H - 50, 7)
        # Net cross-hatch
        for yy in range(24, SCREEN_H - 50, 6):
            for xx in range(NET_X - 2, NET_X + NET_WIDTH + 2, 2):
                if (xx + yy) % 4 == 0:
                    pyxel.pset(xx, yy, 6)

    def _draw_player_racket(self) -> None:
        rx = PLAYER_X
        ry = int(self.player_y)
        swing_offset = 0
        if self._swing_timer > 0:
            swing_offset = self._swing_timer % 3

        # Racket handle
        handle_color = 4  # BROWN
        pyxel.rect(rx + swing_offset, ry + RACKET_H // 2 - 2, RACKET_W, 4, handle_color)

        # Racket head
        color = COLORS[self.player_racket_color]
        if self.super_mode:
            color = (pyxel.frame_count // 4 + self.player_racket_color) % 16
        pyxel.rect(rx, ry, RACKET_W, RACKET_H, color)
        pyxel.rectb(rx, ry, RACKET_W, RACKET_H, 7)

        # Super mode glow
        if self.super_mode:
            glow_color = (pyxel.frame_count // 3) % 16
            pyxel.rectb(rx - 1, ry - 1, RACKET_W + 2, RACKET_H + 2, glow_color)

    def _draw_ai_racket(self) -> None:
        rx = AI_X - RACKET_W
        ry = int(self.ai_y)
        pyxel.rect(rx + RACKET_W // 2 - 1, ry + RACKET_H // 2 - 2, RACKET_W - 2, 4, 4)
        pyxel.rect(rx, ry, RACKET_W, RACKET_H, 13)
        pyxel.rectb(rx, ry, RACKET_W, RACKET_H, 7)

    def _draw_shuttlecock(self) -> None:
        sc = self.shuttlecock
        if sc is None or not sc.active:
            return
        sx = int(sc.x)
        sy = int(sc.y)
        color = COLORS[sc.color]

        # Tail (opposite direction of velocity)
        if abs(sc.vx) > 0.1 or abs(sc.vy) > 0.1:
            speed = math.sqrt(sc.vx ** 2 + sc.vy ** 2) + 0.001
            tx = -sc.vx / speed
            ty = -sc.vy / speed
            for i in range(1, 4):
                tx_i = sx + int(tx * i * 2)
                ty_i = sy + int(ty * i * 2)
                shade = 7 if i % 2 == 0 else color
                pyxel.pset(tx_i, ty_i, shade)

        # Shuttlecock head
        pyxel.circ(sx, sy, SHUTTLECOCK_R, color)
        pyxel.circb(sx, sy, SHUTTLECOCK_R, 7)

    def _draw_ghost_trail(self) -> None:
        for gt in self.ghost_trail:
            if gt.life <= 0:
                continue
            gx = int(gt.x)
            gy = int(gt.y)
            alpha = max(0.2, gt.life / GHOST_TRAIL_LIFE)
            if alpha > 0.5:
                pyxel.pset(gx, gy, gt.color)
            elif (gx + gy) % 3 == 0:
                pyxel.pset(gx, gy, gt.color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            px = int(p.x)
            py = int(p.y)
            pyxel.pset(px, py, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30
            if alpha <= 0:
                continue
            color = ft.color if alpha > 0.5 else 13
            offset = (len(ft.text) * 4) // 2
            pyxel.text(int(ft.x) - offset, int(ft.y), ft.text, color)

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 2, f"SCORE: {self.score}", 7)
        # Combo
        combo_text = f"COMBO: {self.combo}"
        if self.super_mode:
            combo_text += " SUPER!"
        combo_color = 7 if self.combo < COMBO_THRESHOLD else 10
        pyxel.text(120, 2, combo_text, combo_color)
        # Timer
        seconds = max(0, self.game_timer // 30)
        timer_color = 7 if seconds > 15 else 8
        pyxel.text(SCREEN_W - 55, 2, f"TIME: {seconds}s", timer_color)
        # Heat bar
        bar_x = 4
        bar_y = 10
        bar_w = 80
        bar_h = 5
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        fill = int(self.heat / 100 * (bar_w - 2))
        heat_color = 3 if self.heat < 50 else (10 if self.heat < 80 else 8)
        pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, heat_color)
        pyxel.text(4, 16, "HEAT", 13)
        # Super mode indicator
        if self.super_mode:
            super_remain = max(0, self.super_timer // 30)
            pyxel.text(SCREEN_W - 60, 20, f"SUPER:{super_remain}s", 10)

    def _draw_game_over(self) -> None:
        # Overlay
        pyxel.rect(40, 50, 240, 120, 0)
        pyxel.rectb(40, 50, 240, 120, 7)
        pyxel.text(110, 60, "GAME OVER", 8)
        pyxel.text(80, 80, f"Final Score: {self.score}", 7)
        pyxel.text(80, 92, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(80, 104, f"Rallies: {self.rally_count}", 7)
        cause = "TIME UP" if self.game_timer <= 0 else "OVERHEAT"
        pyxel.text(90, 116, f"Cause: {cause}", 8 if cause == "OVERHEAT" else 10)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(105, 140, "Click to Retry", 7)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
