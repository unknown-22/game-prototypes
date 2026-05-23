"""ECHO MEMORY — Memory sequence game with COMBO / ECHO CHAIN.

Core fun moment: same-color consecutive presses build COMBO, and at
COMBO >= 4 the ECHO CHAIN triggers to auto-complete the next 2
positions for bonus score — the screen erupts in particles.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 30

FONT_PATH = Path(__file__).with_name("k8x12.bdf")
FONT_W = 8
FONT_H = 12

# Colour palette
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

PANEL_COLORS: tuple[int, int, int, int] = (RED, GREEN, DARK_BLUE, YELLOW)
NUM_PANELS = 4

# Layout
HUD_H = 54
PANEL_AREA_Y = 68
PANEL_W = 105
PANEL_H = 62
PANEL_GAP = 10
LEFT_X = (SCREEN_W - PANEL_W * 2 - PANEL_GAP) // 2  # 50
RIGHT_X = LEFT_X + PANEL_W + PANEL_GAP  # 165

TOP_Y = PANEL_AREA_Y  # 68
BOTTOM_Y = TOP_Y + PANEL_H + PANEL_GAP  # 140

COMBO_Y = 218

# Panel positions: TL=RED, TR=GREEN, BL=DARK_BLUE, BR=YELLOW
PANEL_LAYOUT: tuple[tuple[int, int, int], ...] = (
    (LEFT_X, TOP_Y, RED),
    (RIGHT_X, TOP_Y, GREEN),
    (LEFT_X, BOTTOM_Y, DARK_BLUE),
    (RIGHT_X, BOTTOM_Y, YELLOW),
)

# Gameplay
MAX_LIVES = 3
ECHO_COMBO_THRESHOLD = 3
ECHO_AUTO_COUNT = 2

# Timings (frames)
FLASH_BASE_TOTAL = 28
MISS_ANIM_FRAMES = 35
ECHO_STEP_FRAMES = 14
CORRECT_FLASH_FRAMES = 8

# Sequence generation
REPEAT_BIAS = 0.38
COMBO_INJECT_CHANCE = 0.45  # per-round chance to inject a colour run


# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(IntEnum):
    TITLE = 0
    SHOW_SEQUENCE = 1
    PLAYER_TURN = 2
    ECHO_CHAIN = 3
    MISS_ANIM = 4
    GAME_OVER = 5


# ── Dataclasses ────────────────────────────────────────────────────────

@dataclass
class Panel:
    x: int
    y: int
    w: int
    h: int
    color: int

    def hit_test(self, mx: int, my: int) -> bool:
        return self.x <= mx < self.x + self.w and self.y <= my < self.y + self.h


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


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    """ECHO MEMORY — memory sequence game with combo/echo chain mechanics."""

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="ECHO MEMORY",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        self.font = pyxel.Font(str(FONT_PATH))
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State initialisation ─────────────────────────────────────────

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.lives: int = MAX_LIVES
        self.round_num: int = 1
        self.prev_color: int | None = None

        self.panels: list[Panel] = [
            Panel(x, y, PANEL_W, PANEL_H, color)
            for x, y, color in PANEL_LAYOUT
        ]

        self._sequence: list[int] = []
        self._seq_show_idx: int = 0      # index of note being shown
        self._seq_show_timer: int = 0    # timer for current flash on/off
        self._flash_on: bool = False     # whether current note is illuminated
        self._note_active: bool = False  # whether we are in ON phase of current note

        self._player_idx: int = 0        # player's position in sequence

        self._echo_left: int = 0         # remaining echo auto-completions
        self._echo_timer: int = 0        # pace echo auto-completions

        self._miss_timer: int = 0
        self._wrong_color: int = RED     # colour of panel that was wrongly pressed

        self._correct_flash_timer: int = 0
        self._correct_color: int = RED

        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self._shake_frames: int = 0
        self._sx: int = 0
        self._sy: int = 0

        self._generate_sequence()

    # ── Derived properties ───────────────────────────────────────────

    @property
    def _seq_length(self) -> int:
        return self.round_num + 2

    @property
    def _speed(self) -> float:
        if self.round_num <= 3:
            return 1.0
        elif self.round_num <= 6:
            return 1.3
        elif self.round_num <= 9:
            return 1.6
        else:
            return 2.0

    @property
    def _flash_duration(self) -> int:
        """Total frames per note (ON+OFF) at current speed."""
        return max(8, int(FLASH_BASE_TOTAL / self._speed))

    @property
    def _flash_on_frames(self) -> int:
        """Frames the note stays illuminated."""
        total = self._flash_duration
        return max(3, int(total * 0.6))

    @property
    def _flash_off_frames(self) -> int:
        """Frames between notes (off period)."""
        total = self._flash_duration
        return max(2, total - self._flash_on_frames)

    # ── Input helpers (pyxel-dependent) ──────────────────────────────

    @staticmethod
    def _read_mouse() -> tuple[int, int, bool]:
        """Return (mx, my, clicked)."""
        return pyxel.mouse_x, pyxel.mouse_y, pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

    @staticmethod
    def _read_click() -> bool:
        return pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

    # ── Update ───────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._read_click():
                self.reset()
                self._start_show_sequence()
            return

        if self.phase == Phase.GAME_OVER:
            if self._read_click():
                self.reset()
                self._start_show_sequence()
            return

        if self._correct_flash_timer > 0:
            self._correct_flash_timer -= 1

        self._update_particles()
        self._update_floating_texts()
        self._decay_shake()

        if self.phase == Phase.SHOW_SEQUENCE:
            self._update_show_sequence()

        elif self.phase == Phase.PLAYER_TURN:
            mx, my, clicked = self._read_mouse()
            if clicked:
                panel = self._find_panel_at(mx, my)
                if panel is not None:
                    self._handle_click(panel)

        elif self.phase == Phase.ECHO_CHAIN:
            self._update_echo_chain()

        elif self.phase == Phase.MISS_ANIM:
            self._miss_timer -= 1
            if self._miss_timer <= 0:
                if self.lives <= 0:
                    self.phase = Phase.GAME_OVER
                else:
                    self._start_show_sequence()

    # ── Pure-logic methods (testable, no pyxel calls) ────────────────

    def _generate_sequence(self) -> None:
        """Generate the sequence for the current round with combo bias."""
        seq: list[int] = []
        for _ in range(self._seq_length):
            if seq and self._rng.random() < REPEAT_BIAS:
                seq.append(seq[-1])
            else:
                seq.append(self._rng.choice(PANEL_COLORS))
        self._sequence = seq

    def _advance_sequence(self) -> None:
        """Move to the next note in the playback sequence."""
        pass

    def _find_panel_at(self, mx: int, my: int) -> Panel | None:
        """Find the panel at the given mouse coordinates."""
        for panel in self.panels:
            if panel.hit_test(mx, my):
                return panel
        return None

    def _check_click(self, panel_color: int) -> bool:
        """Check if the clicked colour matches the expected sequence position."""
        if self._player_idx >= len(self._sequence):
            return False
        return self._sequence[self._player_idx] == panel_color

    def _process_correct(self, panel_color: int) -> tuple[int, bool, bool]:
        """Process a correct click.

        Returns (bonus: int, round_complete: bool, echo_triggered: bool).
        """
        if not self._check_click(panel_color):
            return 0, False, False

        bonus = 10 + self.combo * 5
        self.score += bonus

        if self.prev_color == panel_color:
            self.combo += 1
        else:
            self.combo = 0
        self.prev_color = panel_color
        self.max_combo = max(self.max_combo, self.combo)

        self._correct_color = panel_color
        self._correct_flash_timer = CORRECT_FLASH_FRAMES

        self._player_idx += 1

        echo = self.combo >= ECHO_COMBO_THRESHOLD and self._player_idx < len(self._sequence)
        done = not echo and self._player_idx >= len(self._sequence)

        return bonus, done, echo

    def _process_wrong(self, panel_color: int) -> int:
        """Process a wrong click. Returns remaining lives."""
        self.lives -= 1
        self._wrong_color = panel_color
        self.combo = 0
        self.prev_color = None
        self._miss_timer = MISS_ANIM_FRAMES
        self._shake_frames = 12
        return self.lives

    def _start_echo_chain(self) -> int:
        """Start echo chain and return number of positions to skip."""
        remaining = min(ECHO_AUTO_COUNT, len(self._sequence) - self._player_idx)
        self._echo_left = remaining
        self._echo_timer = ECHO_STEP_FRAMES
        return remaining

    def _start_show_sequence(self) -> None:
        """Prepare show-sequence playback."""
        self._seq_show_idx = 0
        self._note_active = False
        self._flash_on = False
        self._seq_show_timer = self._flash_off_frames
        self.phase = Phase.SHOW_SEQUENCE

    # ── Score helpers ────────────────────────────────────────────────

    def _calc_echo_score(self, panel_color: int) -> int:
        _ = panel_color
        return 10 + self.combo * 10

    # ── Internal state transitions ───────────────────────────────────

    def _handle_click(self, panel: Panel) -> None:
        if self._player_idx >= len(self._sequence):
            return

        if self._check_click(panel.color):
            bonus, done, echo = self._process_correct(panel.color)
            self._spawn_correct_particles(panel)
            self._spawn_floating_text(
                float(panel.x + panel.w / 2),
                float(panel.y + panel.h / 2),
                f"+{bonus}",
                YELLOW,
            )
            if echo:
                self._start_echo_chain()
                self.phase = Phase.ECHO_CHAIN
                self._spawn_floating_text(
                    float(SCREEN_W / 2),
                    float(SCREEN_H / 2),
                    "ECHO CHAIN!",
                    PINK,
                )
                self._spawn_echo_particles()
            elif done:
                self._round_complete()
            # else: stay in PLAYER_TURN for next position
        else:
            self._spawn_wrong_particles(panel)
            self._process_wrong(panel.color)
            self.phase = Phase.MISS_ANIM
            self._spawn_floating_text(
                float(panel.x + panel.w / 2),
                float(panel.y + panel.h / 2),
                "MISS!",
                RED,
            )

    def _update_show_sequence(self) -> None:
        if self._seq_show_idx >= len(self._sequence):
            # Playback finished → player turn
            self._player_idx = 0
            self.phase = Phase.PLAYER_TURN
            return

        self._seq_show_timer -= 1
        if self._seq_show_timer <= 0:
            if not self._note_active:
                # Start next note
                self._note_active = True
                self._flash_on = True
                self._seq_show_timer = self._flash_on_frames
            else:
                # End current note, advance
                self._flash_on = False
                self._note_active = False
                self._seq_show_idx += 1
                if self._seq_show_idx < len(self._sequence):
                    self._seq_show_timer = self._flash_off_frames
                else:
                    self._seq_show_timer = self._flash_off_frames  # brief pause before player turn

    def _update_echo_chain(self) -> None:
        if self._echo_left <= 0:
            if self._player_idx >= len(self._sequence):
                self._round_complete()
            else:
                self.phase = Phase.PLAYER_TURN
            return

        self._echo_timer -= 1
        if self._echo_timer > 0:
            return

        if self._player_idx >= len(self._sequence):
            self._echo_left = 0
            self._round_complete()
            return

        echo_color = self._sequence[self._player_idx]
        bonus = self._calc_echo_score(echo_color)
        self.score += bonus

        self._correct_color = echo_color
        self._correct_flash_timer = CORRECT_FLASH_FRAMES

        self._spawn_floating_text(
            float(SCREEN_W / 2) + self._rng.uniform(-40, 40),
            float(SCREEN_H / 2) + self._rng.uniform(-20, 20),
            f"+{bonus}",
            PINK,
        )
        self._spawn_echo_particles()

        if self.prev_color == echo_color:
            self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)

        self._player_idx += 1
        self._echo_left -= 1

        if self._echo_left > 0 and self._player_idx < len(self._sequence):
            self._echo_timer = ECHO_STEP_FRAMES
        else:
            self._echo_left = 0

    def _round_complete(self) -> None:
        """Finish the current round, award bonus, advance to next."""
        self.score += self.round_num * 50
        self._spawn_floating_text(
            float(SCREEN_W / 2),
            float(30),
            f"ROUND {self.round_num} CLEAR! +{self.round_num * 50}",
            LIME,
        )
        self.round_num += 1
        self._player_idx = 0
        self.combo = 0
        self.prev_color = None
        self._generate_sequence()
        self._start_show_sequence()

    # ── Particles & effects ──────────────────────────────────────────

    def _spawn_correct_particles(self, panel: Panel) -> None:
        cx = float(panel.x + panel.w / 2)
        cy = float(panel.y + panel.h / 2)
        count = 4 + self.combo
        self._burst(cx, cy, panel.color, count)

    def _spawn_wrong_particles(self, panel: Panel) -> None:
        cx = float(panel.x + panel.w / 2)
        cy = float(panel.y + panel.h / 2)
        self._burst(cx, cy, RED, 8)

    def _spawn_echo_particles(self) -> None:
        cx = float(SCREEN_W / 2)
        cy = float(SCREEN_H / 2)
        colours = PANEL_COLORS
        for _ in range(6):
            col = self._rng.choice(colours)
            angle = self._rng.uniform(0, math.pi * 2)
            spd = self._rng.uniform(1.5, 4.0)
            self.particles.append(
                Particle(
                    x=cx, y=cy,
                    vx=math.cos(angle) * spd,
                    vy=math.sin(angle) * spd,
                    life=25 + self._rng.randint(0, 15),
                    color=col,
                )
            )

    def _burst(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            spd = self._rng.uniform(0.6, 2.8)
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=math.cos(angle) * spd,
                    vy=math.sin(angle) * spd,
                    life=14 + self._rng.randint(0, 10),
                    color=color,
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(
            FloatingText(x=x, y=y, text=text, life=30, color=color)
        )

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floats[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floats.remove(ft)

    def _decay_shake(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1
            if self._shake_frames > 0:
                self._sx = self._rng.randint(-3, 3)
                self._sy = self._rng.randint(-3, 3)
            else:
                self._sx = 0
                self._sy = 0

    def _apply_camera(self) -> None:
        if self._sx != 0 or self._sy != 0:
            try:
                pyxel.camera(self._sx, self._sy)
            except BaseException:
                pass
        else:
            try:
                pyxel.camera()
            except BaseException:
                pass

    # ── Text helpers ─────────────────────────────────────────────────

    def _text(self, x: int, y: int, s: str, col: int) -> None:
        pyxel.text(x, y, s, col, self.font)

    def _text_width(self, s: str) -> int:
        return len(s) * FONT_W

    def _text_center(self, cx: int, y: int, s: str, col: int) -> None:
        self._text(cx - self._text_width(s) // 2, y, s, col)

    # ── Draw ─────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)
        self._apply_camera()

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_background()
            self._draw_hud()
            self._draw_particles()
            self._draw_floats()
            self._draw_game_over()
            return

        self._draw_game_background()
        self._draw_hud()
        self._draw_panels()
        self._draw_particles()
        self._draw_floats()

        if self.phase == Phase.MISS_ANIM:
            self._draw_miss_feedback()

    # ── Screen drawing ───────────────────────────────────────────────

    def _draw_title(self) -> None:
        cx = SCREEN_W // 2
        self._text_center(cx, 44, "ECHO MEMORY", CYAN)
        self._text_center(cx, 64, "Memory Sequence Game", GRAY)

        y = 100
        self._text_center(cx, y, "4 colored panels play a sequence", GRAY)
        y += 14
        self._text_center(cx, y, "Click panels to reproduce the order", GRAY)
        y += 14
        self._text_center(cx, y, "Same-color hits build COMBO", GREEN)
        y += 14
        self._text_center(cx, y, "COMBO >= 3 = ECHO CHAIN!", PINK)
        y += 14
        self._text_center(cx, y, "Wrong click = lose 1 life (max 3)", RED)

        y = 192
        if (pyxel.frame_count // 18) % 2 == 0:
            self._text_center(cx, y, "CLICK TO START", YELLOW)

    def _draw_game_background(self) -> None:
        # Grid lines
        for x in range(0, SCREEN_W, 28):
            pyxel.line(x, 0, x, SCREEN_H, NAVY)
        for y in range(0, SCREEN_H, 28):
            pyxel.line(0, y, SCREEN_W, y, NAVY)

        # Panel area border
        pyxel.rectb(
            LEFT_X - 4, TOP_Y - 4,
            PANEL_W * 2 + PANEL_GAP + 8, PANEL_H * 2 + PANEL_GAP + 8,
            GRAY,
        )

    def _draw_hud(self) -> None:
        # Top HUD bar background
        pyxel.rect(0, 0, SCREEN_W, HUD_H, NAVY)

        # Score — left
        self._text(6, 4, "SCORE", GRAY)
        self._text(6, 16, f"{self.score:>6d}", WHITE)

        # Round — centre-left
        self._text(SCREEN_W // 2 - 40, 4, "ROUND", GRAY)
        self._text(SCREEN_W // 2 - 40, 16, f"{self.round_num}", WHITE)

        # Speed indicator
        speed_label = {1.0: "x1.0", 1.3: "x1.3", 1.6: "x1.6", 2.0: "x2.0"}[self._speed]
        self._text(SCREEN_W // 2 - 40, 30, f"SPD: {speed_label}", GRAY)

        # Lives — top-right
        self._text(SCREEN_W - 80, 4, "LIVES", GRAY)
        lives_x = SCREEN_W - 60
        for i in range(MAX_LIVES):
            if i < self.lives:
                self._text(lives_x + i * 16, 16, "o", RED)
            else:
                self._text(lives_x + i * 16, 16, "x", GRAY)

        # Step indicator
        shown = self._player_idx if self.phase == Phase.PLAYER_TURN else 0
        total = len(self._sequence)
        if self.phase == Phase.SHOW_SEQUENCE:
            step_label = "WATCH..."
        elif self.phase == Phase.PLAYER_TURN:
            step_label = f"STEP {shown + 1}/{total}"
        elif self.phase == Phase.ECHO_CHAIN:
            step_label = "ECHO!"
        elif self.phase == Phase.MISS_ANIM:
            step_label = "MISS"
        else:
            step_label = ""
        if step_label:
            self._text_center(SCREEN_W // 2 + 40, 16, step_label, YELLOW)

        # Combo — bottom
        if self.combo > 0:
            combo_col = PINK if self.combo >= ECHO_COMBO_THRESHOLD else YELLOW
            combo_str = f"COMBO x{self.combo}"
            self._text_center(SCREEN_W // 2, COMBO_Y, combo_str, combo_col)

    def _draw_panels(self) -> None:
        show_color = self._sequence[self._seq_show_idx] if (
            self.phase == Phase.SHOW_SEQUENCE
            and self._seq_show_idx < len(self._sequence)
        ) else None

        for panel in self.panels:
            px, py = panel.x, panel.y
            is_lit = self._flash_on and self.phase == Phase.SHOW_SEQUENCE and panel.color == show_color
            is_correct_flash = (
                self._correct_flash_timer > 0
                and panel.color == self._correct_color
                and self.phase in (Phase.PLAYER_TURN, Phase.ECHO_CHAIN)
            )
            is_wrong = self.phase == Phase.MISS_ANIM and panel.color == self._wrong_color

            if is_lit:
                fill = WHITE
                border = panel.color
            elif is_correct_flash:
                fill = LIME
                border = WHITE
            elif is_wrong:
                fill = RED
                border = WHITE
            else:
                fill = panel.color
                border = DARK_BLUE

            pyxel.rect(px, py, panel.w, panel.h, fill)
            pyxel.rectb(px, py, panel.w, panel.h, border)

            # Inner glow for highlighted panels
            if is_lit:
                pyxel.rectb(px + 2, py + 2, panel.w - 4, panel.h - 4, panel.color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            px_val = int(p.x)
            py_val = int(p.y)
            if 0 <= px_val < SCREEN_W and 0 <= py_val < SCREEN_H:
                pyxel.pset(px_val, py_val, p.color)

    def _draw_floats(self) -> None:
        for ft in self.floats:
            alpha = ft.life / 30.0
            if alpha > 0.1:
                tw = self._text_width(ft.text)
                self._text(
                    int(ft.x) - tw // 2,
                    int(ft.y),
                    ft.text,
                    ft.color,
                )

    def _draw_miss_feedback(self) -> None:
        blur = (pyxel.frame_count // 4) % 2
        if blur:
            pyxel.rect(0, 0, SCREEN_W, 18, RED)
            pyxel.rect(0, SCREEN_H - 18, SCREEN_W, 18, RED)

    def _draw_game_over(self) -> None:
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2

        # Dim overlay
        pyxel.rect(cx - 90, cy - 58, 180, 116, BLACK)
        pyxel.rectb(cx - 90, cy - 58, 180, 116, WHITE)

        self._text_center(cx, cy - 48, "GAME OVER", RED)
        self._text_center(cx, cy - 28, f"SCORE: {self.score}", WHITE)
        self._text_center(cx, cy - 14, f"MAX COMBO: {self.max_combo}", YELLOW)
        self._text_center(cx, cy, f"ROUNDS: {self.round_num}", WHITE)
        self._text_center(cx, cy + 28, "CLICK TO RESTART", GRAY)


# ── Entry point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
