from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ─── Color Constants ───────────────────────────────────────────────────────
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

REEL_COLORS: tuple[int, ...] = (RED, GREEN, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "BLUE", "YELLOW")

# ─── Constants ──────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
REEL_W = 60
REEL_H = 80
REEL_SPACING = 80
REEL_Y = 120
SPIN_DURATION = 60
SPIN_STAGGER = 18
MAX_SPINS = 20
MAX_HEAT = 10
HOLD_COST = 1
MISS_HEAT = 2
SUPER_COMBO_THRESHOLD = 4
SUPER_MULTIPLIER = 3
BIG_SCORE = 500
SMALL_SCORE = 100

# ─── Enums ──────────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SPINNING = auto()
    GAME_OVER = auto()


# ─── Data Classes ───────────────────────────────────────────────────────────


@dataclass
class Reel:
    x: int
    y: int
    color_idx: int = 0
    spinning: bool = False
    held: bool = False
    spin_timer: int = 0
    spin_speed: int = 0
    flash_frame: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    max_life: int = 20


# ─── Game Class ─────────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SPIN CHAIN", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.spins_remaining: int = MAX_SPINS
        self.super_spin: bool = False
        self.result_text: str = ""
        self.result_timer: int = 0
        self.shake_frames: int = 0
        self.last_match_color: int = -1
        self._init_reels()
        self.particles: list[Particle] = []
        self.high_score: int = 0

    def _init_reels(self) -> None:
        self.reels: list[Reel] = []
        for i in range(3):
            x = 80 + i * REEL_SPACING
            ci = self._rng.randint(0, 3)
            self.reels.append(Reel(x=x, y=REEL_Y, color_idx=ci))

    # ─── Phase Machine ──────────────────────────────────────────────────────

    def update(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.SPINNING:
            self._update_spinning()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        self._animate_demo_reels()
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _animate_demo_reels(self) -> None:
        if pyxel.frame_count % 6 == 0:
            for reel in self.reels:
                reel.color_idx = self._rng.randint(0, 3)

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.spins_remaining = MAX_SPINS
        self.super_spin = False
        self.result_text = ""
        self.result_timer = 0
        self.shake_frames = 0
        self.last_match_color = -1
        self.particles = []
        for reel in self.reels:
            reel.held = False
            reel.spinning = False
            reel.spin_timer = 0
            reel.color_idx = self._rng.randint(0, 3)

    def _update_playing(self) -> None:
        self._update_particles()
        if self.result_timer > 0:
            self.result_timer -= 1

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._spin_reels()
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            for i, reel in enumerate(self.reels):
                if self._is_mouse_over_reel(mx, my, reel):
                    self._toggle_hold(i)
                    break
            if self._is_mouse_over_spin_button(mx, my):
                self._spin_reels()

    def _is_mouse_over_reel(self, mx: int, my: int, reel: Reel) -> bool:
        return (
            mx > reel.x - REEL_W // 2
            and mx < reel.x + REEL_W // 2
            and my > reel.y - REEL_H // 2
            and my < reel.y + REEL_H // 2
        )

    def _is_mouse_over_spin_button(self, mx: int, my: int) -> bool:
        bx = SCREEN_W // 2 - 30
        by = SCREEN_H - 40
        return mx >= bx and mx < bx + 60 and my >= by and my < by + 20

    def _update_spinning(self) -> None:
        self._update_spin()
        self._update_particles()

    def _update_game_over(self) -> None:
        self._update_particles()
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            if self.score > self.high_score:
                self.high_score = self.score
            self.phase = Phase.TITLE

    # ─── Testable Logic ─────────────────────────────────────────────────────

    def _spin_reels(self) -> None:
        all_held = all(reel.held for reel in self.reels)
        if all_held:
            for reel in self.reels:
                reel.held = False

        for reel in self.reels:
            if reel.held:
                reel.spinning = False
                reel.spin_timer = 0
            else:
                reel.spinning = True
                reel.spin_timer = SPIN_DURATION
                reel.spin_speed = 4

        self.phase = Phase.SPINNING

    def _update_spin(self) -> None:
        all_stopped = True
        for i, reel in enumerate(self.reels):
            if not reel.spinning:
                continue
            all_stopped = False

            start_timer = SPIN_DURATION - i * SPIN_STAGGER
            if reel.spin_timer > start_timer:
                reel.spin_timer -= 1
                if pyxel.frame_count % reel.spin_speed == 0:
                    reel.color_idx = (reel.color_idx + 1) % 4
                continue

            reel.spin_timer -= 1
            if reel.spin_timer <= 0:
                reel.spinning = False
                reel.color_idx = self._rng.randint(0, 3)
                reel.spin_timer = 0
                continue

            progress = reel.spin_timer / max(start_timer, 1)
            speed = max(2, int(progress * 8 + 2))
            reel.spin_speed = speed
            if pyxel.frame_count % reel.spin_speed == 0:
                reel.color_idx = (reel.color_idx + 1) % 4

        if all_stopped:
            self._evaluate_result()

    def _evaluate_result(self) -> int:
        colors = [reel.color_idx for reel in self.reels]

        if colors[0] == colors[1] == colors[2]:
            match_count = 3
            match_color = colors[0]
        elif colors[0] == colors[1] or colors[1] == colors[2] or colors[0] == colors[2]:
            match_count = 2
            if colors[0] == colors[1]:
                match_color = colors[0]
            elif colors[1] == colors[2]:
                match_color = colors[1]
            else:
                match_color = colors[0]
        else:
            match_count = 0
            match_color = -1

        if self.super_spin and match_count == 0:
            match_count = 2
            match_color = self._rng.randint(0, 3)
            for reel in self.reels:
                reel.color_idx = match_color
            if self._rng.random() < 0.3:
                match_count = 3
                for reel in self.reels:
                    reel.color_idx = match_color

        was_super = self.super_spin

        if match_count == 0:
            self.combo = 0
            self.last_match_color = -1
            self.heat += MISS_HEAT
            self.result_text = "NO MATCH"
        else:
            multiplier = SUPER_MULTIPLIER if self.super_spin else 1

            if match_color == self.last_match_color and self.last_match_color >= 0:
                self.combo += 1
            else:
                self.combo = 1

            self.last_match_color = match_color
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            if match_count == 3:
                base = BIG_SCORE
                self.result_text = "BIG MATCH!"
                self.shake_frames = 8
                self._spawn_particles(SCREEN_W // 2, REEL_Y, 30, -1)
            else:
                base = SMALL_SCORE
                self.result_text = "SMALL MATCH"
                self._spawn_particles(SCREEN_W // 2, REEL_Y, 10, match_color)

            self.score += base * self.combo * multiplier

            if self.combo >= SUPER_COMBO_THRESHOLD and not self.super_spin:
                self.super_spin = True
                self.result_text = "SUPER SPIN!"
                self._spawn_particles(SCREEN_W // 2, 50, 20, -1)
                self.shake_frames = 12

        self.result_timer = 60

        if was_super and match_count > 0:
            self.super_spin = False

        self.spins_remaining -= 1

        if self.heat >= MAX_HEAT or self.spins_remaining <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score
        else:
            self.phase = Phase.PLAYING

        return match_count

    def _toggle_hold(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.reels):
            return
        reel = self.reels[idx]
        if reel.spinning:
            return
        if not reel.held:
            held_count = sum(1 for r in self.reels if r.held)
            if held_count >= 2:
                return
            reel.held = True
        else:
            reel.held = False
        self.heat = min(MAX_HEAT, self.heat + HOLD_COST)

    def _spawn_particles(self, x: int, y: int, count: int, color: int) -> None:
        for _ in range(count):
            c = color if color >= 0 else self._rng.choice(REEL_COLORS)
            self.particles.append(
                Particle(
                    x=float(x),
                    y=float(y),
                    vx=self._rng.uniform(-2, 2),
                    vy=self._rng.uniform(-5, -1),
                    life=self._rng.randint(20, 40),
                    color=c,
                    max_life=self._rng.randint(20, 40),
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ─── Drawing ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)
        self._apply_shake()

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_hud()
            self._draw_reels()
            self._draw_spin_button()
            self._draw_result_text()
        elif self.phase == Phase.SPINNING:
            self._draw_hud()
            self._draw_reels()
            self._draw_result_text()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        self._draw_particles()
        pyxel.camera()

    def _apply_shake(self) -> None:
        if self.shake_frames > 0:
            mag = 6 if self.shake_frames > 4 else 4
            sx = self._rng.randint(-mag, mag)
            sy = self._rng.randint(-mag, mag)
            try:
                pyxel.camera(sx, sy)
            except BaseException:
                pass

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 42, 30, "SPIN  CHAIN", CYAN)

        for reel in self.reels:
            self._draw_reel(
                reel,
                reel.color_idx,
                False,
                False,
            )

        pyxel.text(SCREEN_W // 2 - 68, 200, "[SPACE]  to  start", WHITE)
        pyxel.text(
            SCREEN_W // 2 - 62,
            212,
            "Match  3  colors  for  BIG  SCORE!",
            GRAY,
        )

        if self.high_score > 0:
            pyxel.text(
                SCREEN_W // 2 - 44,
                230,
                f"HIGH  SCORE: {self.high_score}",
                YELLOW,
            )

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)

        cx = SCREEN_W // 2 - 20
        combo_color = CYAN if self.super_spin or self.combo >= SUPER_COMBO_THRESHOLD else WHITE
        if self.combo >= SUPER_COMBO_THRESHOLD:
            combo_color = PINK
        pyxel.text(cx, 4, f"COMBO: x{self.combo}", combo_color)

        pyxel.text(4, 16, f"SPINS: {self.spins_remaining}/{MAX_SPINS}", GRAY)

        bar_x = SCREEN_W - 110
        bar_y = 4
        bar_w = 100
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * min(self.heat / MAX_HEAT, 1.0))
        if fill_w > 0:
            heat_c = RED if self.heat >= 7 else ORANGE
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_c)
        pyxel.text(bar_x - 22, 3, "HEAT", ORANGE)

        if self.super_spin:
            pyxel.text(bar_x, 14, "SUPER!", CYAN)

    def _draw_reels(self) -> None:
        for reel in self.reels:
            self._draw_reel(
                reel,
                reel.color_idx,
                reel.held,
                reel.spinning,
            )

    def _draw_reel(self, reel: Reel, color_idx: int, held: bool, spinning: bool) -> None:
        rx = reel.x - REEL_W // 2
        ry = reel.y - REEL_H // 2
        color = REEL_COLORS[color_idx]

        border_color = GRAY if held else WHITE
        if spinning and pyxel.frame_count % 4 < 2:
            border_color = CYAN

        pyxel.rect(rx, ry, REEL_W, REEL_H, color)
        pyxel.rectb(rx, ry, REEL_W, REEL_H, border_color)

        if held:
            pyxel.text(reel.x - 14, reel.y + REEL_H // 2 + 4, "HOLD", GRAY)

        label = COLOR_NAMES[color_idx]
        label_x = reel.x - len(label) * 2
        pyxel.text(label_x, reel.y - 2, label, BLACK)

    def _draw_spin_button(self) -> None:
        bx = SCREEN_W // 2 - 40
        by = SCREEN_H - 44
        bw = 80
        bh = 22

        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        hover = mx >= bx and mx < bx + bw and my >= by and my < by + bh
        btn_color = CYAN if hover else WHITE
        bg_color = DARK_BLUE if hover else BLACK

        pyxel.rect(bx, by, bw, bh, bg_color)
        pyxel.rectb(bx, by, bw, bh, btn_color)
        pyxel.text(bx + 24, by + 7, "SPIN", btn_color)

    def _draw_result_text(self) -> None:
        if self.result_timer <= 0:
            return
        if self.phase == Phase.SPINNING:
            return
        alpha = self.result_timer / 60
        color = YELLOW if "BIG" in self.result_text else WHITE
        if "SUPER" in self.result_text:
            color = PINK
        elif "NO MATCH" in self.result_text:
            color = RED

        if alpha > 0.5 or int(self.result_timer / 4) % 2 == 0:
            tx = SCREEN_W // 2 - len(self.result_text) * 2
            pyxel.text(tx, REEL_Y - REEL_H // 2 - 16, self.result_text, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / max(p.max_life, 1)
            if alpha > 0.6:
                pyxel.pset(int(p.x), int(p.y), p.color)
            elif alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), GRAY)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 30, 60, "GAME  OVER", RED)
        pyxel.text(SCREEN_W // 2 - 44, 88, f"Final  Score: {self.score}", WHITE)
        pyxel.text(
            SCREEN_W // 2 - 44,
            104,
            f"Max  Combo: x{self.max_combo}",
            ORANGE,
        )

        if self.score >= self.high_score and self.score > 0:
            pyxel.text(SCREEN_W // 2 - 50, 128, "NEW  HIGH  SCORE!", YELLOW)
        elif self.high_score > 0:
            pyxel.text(SCREEN_W // 2 - 44, 128, f"High: {self.high_score}", GRAY)

        pyxel.text(SCREEN_W // 2 - 50, 200, "[SPACE]  to  retry", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
