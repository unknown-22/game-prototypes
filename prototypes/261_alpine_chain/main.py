"""ALPINE CHAIN - Top-down ski slalom color-match game.

The most fun moment: Weaving through same-color gates at high speed while
COMBO grows, then hitting SUPER SKI and blazing through everything in
rainbow mode.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Screen ---
SCREEN_W = 320
SCREEN_H = 240

# --- Pyxel Color Constants ---
RED = 8
GREEN = 3
LIME = 3
DARK_BLUE = 5
LIGHT_BLUE = 6
WHITE = 7
ORANGE = 9
YELLOW = 10
CYAN = 12
GRAY = 13
BLACK = 0
NAVY = 1

PLAYER_COLORS: list[int] = [RED, LIME, DARK_BLUE, YELLOW]

# --- Phase Machine ---
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# --- Data Classes ---
@dataclass
class Gate:
    x: float
    y: float
    color: int
    passed: bool = False


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
    vy: float = -1.0


@dataclass
class TrailDot:
    x: float
    y: float


# --- Game Class ---
class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_x: float = SCREEN_W / 2
        self.player_y: float = SCREEN_H - 60
        self.player_color: int = RED
        self.player_color_timer: int = 20
        self.player_color_idx: int = 0
        self.gates: list[Gate] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.best_score: int = 0
        self.super_timer: int = 0
        self.heat: float = 0.0
        self.game_timer: int = 1800
        self.gate_spawn_timer: int = 0
        self.gate_spawn_interval: int = 60
        self.shake_frames: int = 0
        self.scroll_offset: float = 0.0
        self.best_trail: list[TrailDot] = []
        self.current_trail: list[TrailDot] = []
        self.trail_record_timer: int = 0
        self._rng: random.Random = random.Random()
        self.game_over_reason: str = ""
        self._bg_dots: list[tuple[float, float]] = []
        self._init_bg_dots()

    def _init_bg_dots(self) -> None:
        rng = random.Random(42)
        self._bg_dots = [
            (rng.uniform(0, SCREEN_W), rng.uniform(0, SCREEN_H))
            for _ in range(60)
        ]

    # -- Reset --
    def reset(self) -> None:
        self.player_x = SCREEN_W / 2
        self.player_y = SCREEN_H - 60
        self.player_color = RED
        self.player_color_timer = 20
        self.player_color_idx = 0
        self.gates.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_timer = 0
        self.heat = 0.0
        self.game_timer = 1800
        self.gate_spawn_timer = 0
        self.gate_spawn_interval = 60
        self.shake_frames = 0
        self.scroll_offset = 0.0
        self.current_trail.clear()
        self.trail_record_timer = 0
        self.game_over_reason = ""

    # -- Difficulty helpers --
    def _gate_scroll_speed(self) -> float:
        t = 1.0 - (self.game_timer / 1800.0)
        return 1.5 + (4.0 - 1.5) * t

    def _spawn_interval(self) -> int:
        t = 1.0 - (self.game_timer / 1800.0)
        return int(60.0 - (60.0 - 25.0) * t)

    # -- Run finalisation --
    def _finalize_run(self) -> None:
        if self.score > self.best_score:
            self.best_score = self.score
            self.best_trail = [TrailDot(d.x, d.y) for d in self.current_trail]

    # -- Phase dispatchers --
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_gameover()

    def draw(self) -> None:
        pyxel.cls(WHITE)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_gameover()

    # ================================================================
    #   TITLE
    # ================================================================
    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _draw_title(self) -> None:
        so = pyxel.frame_count * 0.4 % SCREEN_H
        for dx, dy in self._bg_dots:
            y = (dy + so) % SCREEN_H
            pyxel.pset(int(dx), int(y), DARK_BLUE)

        # Falling snow
        t = pyxel.frame_count * 0.7
        for i in range(12):
            sx = (i * 43 + 17) % SCREEN_W
            sy = (t + i * 31) % SCREEN_H
            pyxel.pset(sx, int(sy), WHITE)

        title = "ALPINE CHAIN"
        tx = SCREEN_W // 2 - len(title) * 4 // 2
        pyxel.text(tx, 50, title, RED)

        lines = [
            "Ski the slalom!",
            "Match colors, build COMBO chains!",
            "COMBO x4 = SUPER SKI (rainbow mode)",
            "",
            "Arrow keys to move",
            "",
            f"Best Score: {self.best_score}",
            "",
            "Press SPACE to Start",
        ]
        for i, line in enumerate(lines):
            lx = SCREEN_W // 2 - len(line) * 4 // 2
            if i == len(lines) - 1:
                col = YELLOW
            elif "Best Score" in line and self.best_score > 0:
                col = CYAN
            else:
                col = LIGHT_BLUE
            pyxel.text(lx, 90 + i * 12, line, col)

    # ================================================================
    #   GAME OVER
    # ================================================================
    def _update_gameover(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _draw_gameover(self) -> None:
        so = pyxel.frame_count * 0.3 % SCREEN_H
        for dx, dy in self._bg_dots:
            y = (dy + so) % SCREEN_H
            pyxel.pset(int(dx), int(y), DARK_BLUE)

        reason = self.game_over_reason
        rx = SCREEN_W // 2 - len(reason) * 4 // 2
        pyxel.text(rx, 40, reason, RED)

        lines = [
            f"Score: {self.score}",
            f"Best Score: {self.best_score}",
            f"Max COMBO: {self.max_combo}",
            "",
            "Press SPACE to Restart",
        ]
        for i, line in enumerate(lines):
            lx = SCREEN_W // 2 - len(line) * 4 // 2
            col = YELLOW if i == len(lines) - 1 else WHITE
            pyxel.text(lx, 80 + i * 14, line, col)

    # ================================================================
    #   PLAYING — Update
    # ================================================================
    def _update_playing(self) -> None:
        # Record trail position every 5 frames (before movement)
        self.trail_record_timer += 1
        if self.trail_record_timer >= 5:
            self.trail_record_timer = 0
            self.current_trail.append(TrailDot(self.player_x, self.player_y))

        # Player movement
        speed = 3.0
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player_x -= speed
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player_x += speed
        if pyxel.btn(pyxel.KEY_UP):
            self.player_y -= speed
        if pyxel.btn(pyxel.KEY_DOWN):
            self.player_y += speed
        self.player_x = max(10.0, min(310.0, self.player_x))
        self.player_y = max(40.0, min(220.0, self.player_y))

        # Colour cycle
        self.player_color_timer -= 1
        if self.player_color_timer <= 0:
            self.player_color_timer = 20
            self.player_color_idx = (self.player_color_idx + 1) % 4
            self.player_color = PLAYER_COLORS[self.player_color_idx]

        # Spawn gates
        self.gate_spawn_timer -= 1
        if self.gate_spawn_timer <= 0:
            self.gate_spawn_timer = self._spawn_interval()
            color = self._rng.choice(PLAYER_COLORS)
            x = float(self._rng.randint(60, 260))
            self.gates.append(Gate(x=x, y=-10.0, color=color))

        # Scroll gates
        scroll_speed = self._gate_scroll_speed()
        for gate in self.gates:
            gate.y += scroll_speed

        # Check gate passes / misses
        for gate in self.gates:
            if gate.passed:
                continue
            if abs(self.player_x - gate.x) < 20 and abs(self.player_y - gate.y) < 12:
                gate.passed = True
                if self.super_timer > 0:
                    self._handle_super_pass(gate)
                elif self.player_color == gate.color:
                    self._handle_match(gate)
                else:
                    self._handle_mismatch(gate)
            elif gate.y > 250:
                gate.passed = True
                if self.super_timer == 0:
                    self.heat += 5
                self.combo = 0
                self.floating_texts.append(
                    FloatingText(gate.x, gate.y, "MISS", 25, GRAY)
                )

        # Remove resolved gates
        self.gates = [g for g in self.gates if not g.passed]

        # SUPER SKI timer
        if self.super_timer > 0:
            self.super_timer -= 1

        # HEAT decay (frozen during SUPER)
        if self.super_timer == 0:
            self.heat = max(0.0, self.heat - 0.03)

        # Particles
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        # Floating texts
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

        # Game timer
        self.game_timer -= 1

        # Screen shake
        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Virtual scroll for cosmetics
        self.scroll_offset += scroll_speed

        # Game-over checks
        if self.heat >= 100:
            self._finalize_run()
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "WIPEOUT!"
        elif self.game_timer <= 0:
            self._finalize_run()
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "TIME'S UP!"

    # ----------------------------------------------------------------
    #   Gate-pass handlers
    # ----------------------------------------------------------------
    def _handle_match(self, gate: Gate) -> None:
        self.combo += 1
        points = 100 * self.combo
        self.score += points
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        for _ in range(8):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-3.0, -0.5)
            life = self._rng.randint(15, 25)
            self.particles.append(
                Particle(gate.x, gate.y, vx, vy, life, gate.color)
            )

        self.floating_texts.append(
            FloatingText(gate.x, gate.y, f"+{points}", 30, gate.color)
        )
        if self.combo >= 2:
            x = self.player_x
            y = self.player_y - 12
            self.floating_texts.append(
                FloatingText(x, y, f"COMBO x{self.combo}", 25, CYAN)
            )

        if self.combo >= 4 and self.super_timer == 0:
            self.super_timer = 300
            self.floating_texts.append(
                FloatingText(SCREEN_W / 2, SCREEN_H / 2, "SUPER SKI!", 45, YELLOW, vy=-0.5)
            )

    def _handle_mismatch(self, gate: Gate) -> None:
        self.combo = 0
        self.heat += 15
        self.shake_frames = 8

        for _ in range(4):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-2.0, -0.5)
            life = self._rng.randint(15, 25)
            self.particles.append(
                Particle(gate.x, gate.y, vx, vy, life, GRAY)
            )

        x = self.player_x
        y = self.player_y - 12
        self.floating_texts.append(
            FloatingText(x, y, "WRONG!", 25, GRAY)
        )

    def _handle_super_pass(self, gate: Gate) -> None:
        self.combo += 1
        points = 100 * self.combo * 3
        self.score += points
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        for _ in range(15):
            vx = self._rng.uniform(-2.5, 2.5)
            vy = self._rng.uniform(-3.5, -0.5)
            color = self._rng.choice(PLAYER_COLORS)
            life = self._rng.randint(15, 25)
            self.particles.append(
                Particle(gate.x, gate.y, vx, vy, life, color)
            )

        self.floating_texts.append(
            FloatingText(gate.x, gate.y, f"+{points}", 30, YELLOW)
        )
        x = self.player_x
        y = self.player_y - 12
        self.floating_texts.append(
            FloatingText(x, y, f"COMBO x{self.combo}", 25, CYAN)
        )

    # ================================================================
    #   PLAYING — Draw
    # ================================================================
    def _draw_playing(self) -> None:
        sx = sy = 0
        if self.shake_frames > 0:
            sx = self._rng.randint(-3, 3)
            sy = self._rng.randint(-3, 3)

        # Scrolling background dots
        so = self.scroll_offset % SCREEN_H
        for dx, dy in self._bg_dots:
            y = (dy + so) % SCREEN_H
            pyxel.pset(int(dx), int(y), DARK_BLUE)

        # Slope trees (cosmetic edges)
        tree_xs = [15, int(SCREEN_W - 15)]
        for tx in tree_xs:
            for toff in range(-30, SCREEN_H + 30, 55):
                ty = (toff + self.scroll_offset * 1.1) % (SCREEN_H + 60) - 30
                pyxel.tri(tx, int(ty), tx - 4, int(ty + 10), tx + 4, int(ty + 10), GREEN)

        # Ghost trail (best run)
        if self.best_trail:
            tsx = sx
            tsy = sy
            for dot in self.best_trail:
                pyxel.pset(int(dot.x + tsx), int(dot.y + tsy), CYAN)
                pyxel.pset(int(dot.x + tsx + 1), int(dot.y + tsy), CYAN)

        # Gates
        for gate in self.gates:
            gx = int(gate.x + sx)
            gy = int(gate.y + sy)
            # Poles
            pyxel.line(gx - 20, gy - 10, gx - 20, gy + 10, LIGHT_BLUE)
            pyxel.line(gx + 20, gy - 10, gx + 20, gy + 10, LIGHT_BLUE)
            # Banner
            if not gate.passed:
                pyxel.rect(gx - 18, gy - 2, 36, 5, gate.color)

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x + sx), int(p.y + sy), p.color)

        # Floating texts
        for ft in self.floating_texts:
            col = ft.color
            if ft.text == "SUPER SKI!":
                col = PLAYER_COLORS[pyxel.frame_count % 4]
            tx = int(ft.x + sx - len(ft.text) * 4 / 2)
            pyxel.text(tx, int(ft.y + sy), ft.text, col)

        # Skier
        px = int(self.player_x + sx)
        py = int(self.player_y + sy)
        if self.super_timer > 0:
            super_color = PLAYER_COLORS[pyxel.frame_count % 4]
            pyxel.tri(px, py + 8, px - 7, py - 8, px + 7, py - 8, super_color)
            aura_color = PLAYER_COLORS[(pyxel.frame_count + 2) % 4]
            pyxel.circb(px, py, 9, aura_color)
        else:
            pyxel.tri(px, py + 6, px - 5, py - 6, px + 5, py - 6, self.player_color)

        # ============================================================
        #   HUD (no shake offset)
        # ============================================================
        # Score
        pyxel.text(4, 2, f"Score: {self.score}", BLACK)
        # Combo
        combo_col = self.player_color if self.combo > 0 else BLACK
        pyxel.text(120, 2, f"x{self.combo}", combo_col)
        # Timer
        seconds = self.game_timer // 30
        ts = f"Time: {seconds}s"
        pyxel.text(SCREEN_W - len(ts) * 4 - 4, 2, ts, BLACK if seconds > 10 else RED)

        # HEAT bar
        bar_y = 12
        pyxel.rect(0, bar_y, SCREEN_W, 4, BLACK)
        bar_w = int((self.heat / 100.0) * SCREEN_W)
        if bar_w > 0:
            if self.heat < 25:
                hcol = GREEN
            elif self.heat < 50:
                hcol = YELLOW
            elif self.heat < 75:
                hcol = ORANGE
            else:
                hcol = RED
            pyxel.rect(0, bar_y, bar_w, 4, hcol)

        # SUPER SKI timer bar
        if self.super_timer > 0:
            sup_w = int((self.super_timer / 300.0) * SCREEN_W)
            pyxel.rect(0, bar_y + 5, sup_w, 3, YELLOW)


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="ALPINE CHAIN", fps=30)
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
