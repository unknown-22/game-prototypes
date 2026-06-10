from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Letter:
    char: str
    color: int
    x: float
    y: float
    speed: float
    life: int = 1
    glow_phase: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float = -1.5


SCREEN_W = 320
SCREEN_H = 240
MAX_HP = 5
MAX_HEAT = 100
GAME_DURATION = 90 * 60
COLORS: list[int] = [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW
COLORS_5: list[int] = [8, 3, 5, 10, 9]  # + ORANGE
SUPER_DURATION = 5 * 60
SUPER_COMBO_THRESHOLD = 4
HEAT_WRONG_KEY = 15.0
HEAT_MISS = 5.0
HEAT_DECAY = 0.05
LETTER_SPAWN_INTERVAL_INITIAL = 90
LETTER_SPAWN_INTERVAL_MIN = 30
LETTER_BASE_SPEED = 0.4
LETTER_SPEED_MAX = 1.25
STUN_DURATION = 2 * 60
SUPER_COOLDOWN_DURATION = 2 * 60
DANGER_Y = 200
KILL_Y = 230
HUD_TOP = 28
FONT_W = 4
FONT_H = 6


class Game:
    _COLOR_NAMES: ClassVar[dict[int, str]] = {8: "RED", 3: "GRN", 5: "BLU", 10: "YEL", 9: "ORG"}

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="TYPE SURGE", fps=60)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.hp: int = MAX_HP
        self.heat: float = 0.0
        self.timer: int = GAME_DURATION
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.super_cooldown: int = 0
        self.stun_timer: int = 0
        self.letters: list[Letter] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.spawn_timer: int = LETTER_SPAWN_INTERVAL_INITIAL
        self.current_color: int = -1
        self.last_key: str = ""
        self.shake_frames: int = 0
        self.shake_intensity: int = 0
        self._letters_destroyed: int = 0

    # ─── TITLE ────────────────────────────────────────────────

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hp = MAX_HP
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.super_mode = False
        self.super_cooldown = 0
        self.stun_timer = 0
        self.letters.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.spawn_timer = LETTER_SPAWN_INTERVAL_INITIAL
        self.current_color = -1
        self.last_key = ""
        self.shake_frames = 0
        self.shake_intensity = 0
        self._letters_destroyed = 0

    def _draw_title(self) -> None:
        pyxel.cls(1)
        pyxel.text(100, 40, "TYPE SURGE", 7)
        pyxel.text(70, 62, "Color-Match Typing Defense", 5)

        pyxel.text(50, 90, "Letters fall from the sky!", 7)
        pyxel.text(50, 104, "Type the matching KEY", 7)
        pyxel.text(50, 116, "to destroy them.", 7)

        pyxel.text(50, 134, "Same COLOR chain = COMBO UP", 3)
        pyxel.text(50, 148, "Wrong key or color = HEAT UP", 8)
        pyxel.text(50, 162, "COMBO x4 = SUPER TYPER!", 10)
        pyxel.text(50, 176, "(Auto-destroy all, 3x Score)", 11)

        pyxel.text(50, 200, "Survive 90s for max score!", 7)

        blink = (pyxel.frame_count // 20) % 2 == 0
        pyxel.text(90, 220, "Press SPACE to Start", 7 if blink else 0)

    # ─── PLAYING ──────────────────────────────────────────────

    def _update_playing(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._update_shake()

        if self.stun_timer > 0:
            self.stun_timer -= 1
            if self.stun_timer <= 0:
                self.stun_timer = 0
            # Skip input processing during stun, but still update game logic
            self._update_super()
            self._update_heat()
            self._update_letters()
            self._update_spawn()
            self._update_difficulty_scaling()
            self.timer -= 1
            self._check_game_end()
            return

        if self.super_mode:
            self._update_super()
            # During super, auto-destroy letters each frame
            self._super_tick()
        else:
            self._update_super()
            self._handle_all_keypresses()

        self._update_heat()
        self._update_letters()
        self._update_spawn()
        self._update_difficulty_scaling()
        self.timer -= 1
        self._check_game_end()

    def _update_super(self) -> None:
        if self.super_cooldown > 0:
            self.super_cooldown -= 1
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._deactivate_super()

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_super_activation_particles()
        ft = FloatingText(SCREEN_W / 2 - 30, SCREEN_H / 2 - 10, "SUPER TYPER!", 10, 60, vy=-1.0)
        self.floating_texts.append(ft)

    def _deactivate_super(self) -> None:
        self.super_mode = False
        self.super_timer = 0
        self.super_cooldown = SUPER_COOLDOWN_DURATION
        self.combo = 0
        self.current_color = -1

    def _super_tick(self) -> None:
        """During super mode, auto-destroy all letters each frame."""
        if not self.letters:
            return
        destroyed: list[Letter] = []
        for letter in self.letters:
            score_gain = self._compute_super_score()
            self.score += score_gain
            self._spawn_destroy_particles(letter, super_mode=True)
            ft = FloatingText(letter.x, letter.y, f"+{score_gain}", self._rainbow_color(), 30, vy=-0.8)
            self.floating_texts.append(ft)
            destroyed.append(letter)
            self._letters_destroyed += 1
        for lt in destroyed:
            self.letters.remove(lt)

    def _handle_all_keypresses(self) -> None:
        for key_code in range(pyxel.KEY_A, pyxel.KEY_Z + 1):
            if pyxel.btnp(key_code):
                char = chr(key_code)
                self.last_key = char
                self._process_keypress(char)
                return  # Only process one key per frame

    def _process_keypress(self, key: str) -> None:
        matching = [lt for lt in self.letters if lt.char == key.upper()]
        if not matching:
            self._on_wrong_key()
            return

        # Destroy the lowest one (highest y) — most urgent
        target = max(matching, key=lambda lt: lt.y)

        color_match = self.current_color == -1 or self.current_color == target.color

        if color_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            score_gain = self._compute_score()
            self.score += score_gain
            self._spawn_destroy_particles(target, super_mode=False)
            line = f"+{score_gain}"
            col = target.color
            if self.combo >= 3:
                line = f"+{score_gain} x{self.combo}"
            ft = FloatingText(target.x, target.y, line, col, 30, vy=-1.2)
            self.floating_texts.append(ft)
            self._letters_destroyed += 1

            if self.combo >= SUPER_COMBO_THRESHOLD:
                if not self.super_mode and self.super_cooldown <= 0:
                    self._activate_super()
        else:
            self.combo = 1
            score_gain = 10
            self.score += score_gain
            self.heat = min(MAX_HEAT, float(self.heat + HEAT_WRONG_KEY * 0.5))
            self._spawn_destroy_particles(target, super_mode=False)
            ft = FloatingText(target.x, target.y, "WRONG!", 8, 25, vy=-1.0)
            self.floating_texts.append(ft)
            self._trigger_shake(3)

        self.current_color = target.color
        self.letters.remove(target)

    def _on_wrong_key(self) -> None:
        self.heat = min(MAX_HEAT, float(self.heat + HEAT_WRONG_KEY))
        self._spawn_wrong_key_particles()
        self._trigger_shake(5)
        ft = FloatingText(SCREEN_W / 2 - 15, SCREEN_H - 40, "MISS!", 8, 25, vy=-1.0)
        self.floating_texts.append(ft)

    def _compute_score(self) -> int:
        return 10 + self.combo * 5

    def _compute_super_score(self) -> int:
        return 30 + self.combo * 15

    # ─── LETTER SPAWN & UPDATE ────────────────────────────────

    def _update_spawn(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            interval = self._get_spawn_interval()
            self.spawn_timer = interval
            self._spawn_letter()
            # At 30s+, occasional pairs
            elapsed = GAME_DURATION - self.timer
            if elapsed > 30 * 60 and self._rng.random() < 0.3:
                self._spawn_letter()

    def _spawn_letter(self) -> Letter:
        colors = COLORS_5 if self._get_active_colors_count() == 5 else COLORS
        color = self._rng.choice(colors)
        char = chr(self._rng.randint(65, 90))  # A-Z
        x = self._rng.uniform(20, 290)
        speed = self._get_letter_speed()
        # Offset overlapping letters slightly
        for lt in self.letters:
            if abs(lt.x - x) < 12 and lt.y < 30:
                x += self._rng.choice([-14, 14])
                x = max(20.0, min(290.0, x))
        letter = Letter(char=char, color=color, x=x, y=0.0, speed=speed)
        self.letters.append(letter)
        return letter

    def _update_letters(self) -> None:
        for letter in self.letters:
            letter.y += letter.speed
            letter.glow_phase += 0.1

        miss_letters = [lt for lt in self.letters if lt.y >= KILL_Y]
        for lt in miss_letters:
            self.hp -= 1
            self.heat = min(MAX_HEAT, float(self.heat + HEAT_MISS))
            self._spawn_miss_particles(lt)
            self.combo = 0
            self.current_color = -1
            self._trigger_shake(4)
            ft = FloatingText(lt.x, lt.y + 10, "-1 HP", 8, 30, vy=-0.5)
            self.floating_texts.append(ft)
        self.letters = [lt for lt in self.letters if lt.y < KILL_Y]

    # ─── DIFFICULTY SCALING ───────────────────────────────────

    def _get_spawn_interval(self) -> int:
        elapsed = GAME_DURATION - self.timer
        t = min(1.0, elapsed / GAME_DURATION)
        return int(LETTER_SPAWN_INTERVAL_INITIAL - (LETTER_SPAWN_INTERVAL_INITIAL - LETTER_SPAWN_INTERVAL_MIN) * t)

    def _get_letter_speed(self) -> float:
        elapsed = GAME_DURATION - self.timer
        t = min(1.0, elapsed / GAME_DURATION)
        return LETTER_BASE_SPEED + (LETTER_SPEED_MAX - LETTER_BASE_SPEED) * t

    def _get_active_colors_count(self) -> int:
        elapsed = GAME_DURATION - self.timer
        if elapsed > 60 * 60:
            return 5
        return 4

    def _update_difficulty_scaling(self) -> None:
        pass  # Difficulty handled in spawn/speed methods

    # ─── HEAT ─────────────────────────────────────────────────

    def _update_heat(self) -> None:
        if self.stun_timer > 0:
            return
        if self.heat >= MAX_HEAT:
            self._trigger_stun()
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _trigger_stun(self) -> None:
        self.stun_timer = STUN_DURATION
        self.heat = 50.0
        self._spawn_stun_particles()
        self._trigger_shake(8)
        ft = FloatingText(SCREEN_W / 2 - 20, SCREEN_H / 2, "STUN!", 8, 40, vy=-0.5)
        self.floating_texts.append(ft)

    # ─── PARTICLES ────────────────────────────────────────────

    def _spawn_destroy_particles(self, letter: Letter, super_mode: bool) -> None:
        count = self._rng.randint(8, 12) if super_mode else self._rng.randint(4, 8)
        for _ in range(count):
            angle = self._rng.uniform(0, 2 * math.pi)
            speed = self._rng.uniform(0.8, 3.0)
            color = self._rainbow_color() if super_mode else letter.color
            p = Particle(
                x=letter.x,
                y=letter.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color,
                life=self._rng.randint(15, 25),
                size=self._rng.randint(1, 3),
            )
            self.particles.append(p)

    def _spawn_wrong_key_particles(self) -> None:
        for _ in range(3):
            p = Particle(
                x=self._rng.uniform(140, 180),
                y=SCREEN_H - 30,
                vx=self._rng.uniform(-1.5, 1.5),
                vy=self._rng.uniform(-2.0, -0.5),
                color=8,
                life=self._rng.randint(10, 20),
                size=2,
            )
            self.particles.append(p)

    def _spawn_miss_particles(self, letter: Letter) -> None:
        for _ in range(5):
            p = Particle(
                x=letter.x,
                y=letter.y,
                vx=self._rng.uniform(-1.0, 1.0),
                vy=self._rng.uniform(-1.0, 0.5),
                color=8,
                life=self._rng.randint(10, 20),
                size=2,
            )
            self.particles.append(p)

    def _spawn_stun_particles(self) -> None:
        for _ in range(20):
            p = Particle(
                x=SCREEN_W / 2,
                y=SCREEN_H / 2,
                vx=self._rng.uniform(-2.5, 2.5),
                vy=self._rng.uniform(-2.5, 2.5),
                color=13,
                life=self._rng.randint(20, 35),
                size=self._rng.randint(1, 3),
            )
            self.particles.append(p)

    def _spawn_super_activation_particles(self) -> None:
        for _ in range(30):
            angle = self._rng.uniform(0, 2 * math.pi)
            speed = self._rng.uniform(1.5, 5.0)
            p = Particle(
                x=SCREEN_W / 2,
                y=SCREEN_H / 2,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=self._rainbow_color(),
                life=self._rng.randint(20, 40),
                size=self._rng.randint(1, 4),
            )
            self.particles.append(p)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ─── FLOATING TEXT ────────────────────────────────────────

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ─── SHAKE ────────────────────────────────────────────────

    def _trigger_shake(self, intensity: int) -> None:
        self.shake_frames = 8
        self.shake_intensity = intensity

    def _update_shake(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1

    # ─── GAME END ─────────────────────────────────────────────

    def _check_game_end(self) -> None:
        if self.hp <= 0 or self.timer <= 0:
            self.phase = Phase.GAME_OVER

    # ─── GAME OVER ────────────────────────────────────────────

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._update_shake()
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.TITLE
            self.reset()

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        if self.timer <= 0:
            pyxel.text(110, 30, "TIME'S UP!", 10)
        else:
            pyxel.text(115, 30, "GAME OVER", 8)

        pyxel.text(105, 55, f"Score: {self.score}", 7)
        pyxel.text(95, 72, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(95, 89, f"Letters Cleared: {self._letters_destroyed}", 7)

        blink = (pyxel.frame_count // 20) % 2 == 0
        pyxel.text(85, 130, "Press SPACE to Retry", 7 if blink else 0)

    # ─── DRAW ─────────────────────────────────────────────────

    def draw(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0 and self.shake_intensity > 0:
            shake_x = self._rng.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = self._rng.randint(-self.shake_intensity, self.shake_intensity)

        pyxel.camera(shake_x, shake_y)
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING | Phase.GAME_OVER:
                self._draw_game_background()
                if self.phase == Phase.PLAYING:
                    self._draw_letters()
                    self._draw_particles()
                    self._draw_floating_texts()
                    self._draw_hud()
                    self._draw_input_indicator()
                else:
                    self._draw_particles()
                    self._draw_floating_texts()
                    self._draw_game_over()
        pyxel.camera(0, 0)

    def _draw_game_background(self) -> None:
        # Dark gradient-ish background
        for y in range(SCREEN_H):
            c = 1 if y < SCREEN_H // 2 else 0
            pyxel.rect(0, y, SCREEN_W, 1, c)
        # HUD bar background
        pyxel.rect(0, 0, SCREEN_W, HUD_TOP, 0)
        # Floor line
        pyxel.rect(0, KILL_Y, SCREEN_W, 2, 8)
        # Danger zone
        danger_alpha = (pyxel.frame_count // 15) % 2
        if danger_alpha:
            pyxel.rect(0, DANGER_Y, SCREEN_W, KILL_Y - DANGER_Y, 5)

    def _draw_letters(self) -> None:
        for letter in self.letters:
            lx = int(letter.x)
            ly = int(letter.y)

            # Warning glow near danger zone
            if letter.y > DANGER_Y:
                blink = (pyxel.frame_count // 8) % 2
                if blink:
                    pyxel.text(lx - 1, ly, letter.char, 8)

            # Combo glow for current_color letters
            if letter.color == self.current_color and self.combo >= 3:
                glow_alpha = int(abs(math.sin(letter.glow_phase)) * 3)
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if dx == 0 and dy == 0:
                            continue
                        pyxel.text(lx + dx, ly + dy, letter.char, letter.color + glow_alpha % 16 if glow_alpha else letter.color)

            # Super mode rainbow flash
            if self.super_mode:
                color = self._rainbow_color()
                pyxel.text(lx, ly, letter.char, color)
                # Rainbow trail behind
                pyxel.text(lx, ly + 8, letter.char, self._rainbow_color(offset=4))
            else:
                # Main letter with white border
                pyxel.text(lx - 1, ly, letter.char, 7)
                pyxel.text(lx + 1, ly, letter.char, 7)
                pyxel.text(lx, ly - 1, letter.char, 7)
                pyxel.text(lx, ly + 1, letter.char, 7)
                pyxel.text(lx, ly, letter.char, letter.color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 0:
                alpha = (pyxel.frame_count // 3) % 2
                if p.life > 10 or alpha == 0:
                    px = int(p.x)
                    py_ = int(p.y)
                    if p.size <= 1:
                        pyxel.pset(px, py_, p.color)
                    else:
                        pyxel.rect(px, py_, p.size, p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                alpha = (pyxel.frame_count // 3) % 2
                if ft.life > 20 or alpha == 0:
                    tx = int(ft.x) - len(ft.text) * 2
                    ty = int(ft.y)
                    pyxel.text(max(0, tx), ty, ft.text, ft.color)

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 2, f"SC: {self.score:06d}", 7)
        # Combo
        combo_col = 10 if self.combo >= SUPER_COMBO_THRESHOLD else (3 if self.combo >= 2 else 7)
        pyxel.text(100, 2, f"COMBO: {self.combo}", combo_col)
        # HP with hearts
        hp_str = "".join("O" if i < self.hp else "-" for i in range(MAX_HP))
        hp_col = 8 if self.hp <= 2 else (3 if self.hp >= 4 else 10)
        pyxel.text(190, 2, f"HP: {hp_str}", hp_col)
        # Timer
        secs = self.timer // 60
        time_col = 8 if secs <= 15 else 7
        pyxel.text(265, 2, f"T:{secs:02d}", time_col)

        # HEAT bar (row 2)
        pyxel.text(4, 14, "HEAT", 7)
        heat_w = 60
        bar_x = 32
        pyxel.rectb(bar_x, 13, heat_w + 2, 8, 7)
        heat_fill = int(self.heat * heat_w / MAX_HEAT)
        if heat_fill > 0:
            heat_col = 8 if self.heat >= 70 else (9 if self.heat >= 30 else 3)
            pyxel.rect(bar_x + 1, 14, min(heat_fill, heat_w), 6, heat_col)

        # Super mode indicator
        if self.super_mode:
            super_secs = self.super_timer // 60 + 1
            pyxel.text(135, 14, f"!!! SUPER {super_secs}s !!!", self._rainbow_color())
        elif self.super_cooldown > 0:
            cd_secs = self.super_cooldown // 60 + 1
            pyxel.text(135, 14, f"Cool: {cd_secs}s", 13)

        # Stun indicator
        if self.stun_timer > 0:
            stun_secs = self.stun_timer // 60 + 1
            pyxel.text(240, 14, f"STUN {stun_secs}s", 8)

    def _draw_input_indicator(self) -> None:
        if self.last_key:
            blink = (pyxel.frame_count // 8) % 4
            if blink < 3:
                pyxel.text(SCREEN_W - 20, SCREEN_H - 10, f"[{self.last_key}]", 7)

    # ─── HELPERS ──────────────────────────────────────────────

    def _rainbow_color(self, offset: int = 0) -> int:
        idx = ((pyxel.frame_count // 4) + offset) % len(COLORS)
        return COLORS[idx]

    def update(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.GAME_OVER:
                self._update_game_over()

    # ─── TESTABLE INTERFACE (for pytest) ──────────────────────

    def _test_spawn_letter(self) -> Letter:
        return self._spawn_letter()

    def _test_get_spawn_interval(self) -> int:
        return self._get_spawn_interval()

    def _test_get_letter_speed(self) -> float:
        return self._get_letter_speed()


if __name__ == "__main__":
    Game()
