"""Claw Chain — UFO Catcher with Color-Match COMBO Chain."""
from __future__ import annotations

import random
from dataclasses import dataclass

import pyxel


@dataclass
class Prize:
    x: float
    y: float
    color: int
    size: int = 8
    vx: float = 0.0
    vy: float = 0.0
    alive: bool = True


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
class FloatText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    CLAW_Y = 30
    CLAW_SPEED = 3.0
    GRAB_RADIUS = 12
    SUPER_GRAB_RADIUS = 20
    PRIZE_COUNT = 20
    SUPER_DURATION = 300
    GAME_DURATION = 3600
    MAX_HEAT = 100
    HEAT_DECAY = 0.02
    HEAT_MISMATCH = 15
    COMBO_THRESHOLD = 4
    DROP_SPEED = 4
    RETRACT_SPEED = 3

    COLORS = [8, 11, 5, 10]
    COLOR_NAMES = ["RED", "LIME", "DARK_BLUE", "YELLOW"]
    RAINBOW_COLORS = [8, 9, 10, 11, 12, 14]

    BIN_TOP = 60
    BIN_BOTTOM = 220
    CLAW_LEFT_LIMIT = 20
    CLAW_RIGHT_LIMIT = 300

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="Claw Chain")
        self.best_score = 0
        self._reset()
        pyxel.run(self.update, self.draw)

    def _reset(self) -> None:
        self.phase = "TITLE"
        self.claw_x = 160.0
        self.claw_dropping = False
        self.claw_drop_y: float = self.CLAW_Y
        self.claw_retracting = False
        self.last_color: int | None = None
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.timer = self.GAME_DURATION
        self.super_timer = 0
        self.prizes: list[Prize] = []
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self.spawn_timer = 0
        self.spawn_interval = 60
        self._init_prizes()

    def _init_prizes(self) -> None:
        self.prizes.clear()
        for _ in range(self.PRIZE_COUNT):
            self.prizes.append(self._spawn_prize())

    def _spawn_prize(self) -> Prize:
        x = random.uniform(20, self.SCREEN_W - 20)
        y = random.uniform(self.BIN_TOP + 10, self.BIN_BOTTOM - 10)
        color = random.choice(self.COLORS)
        speed = self._drift_speed()
        vx = random.uniform(-speed, speed)
        vy = random.uniform(-speed * 0.7, speed * 0.7)
        return Prize(x=x, y=y, color=color, vx=vx, vy=vy)

    def _drift_speed(self) -> float:
        elapsed = self.GAME_DURATION - self.timer
        t = min(elapsed / self.GAME_DURATION, 1.0)
        return 0.3 + 0.4 * t

    def _spawn_interval_for_frame(self) -> int:
        elapsed = self.GAME_DURATION - self.timer
        seconds = elapsed // 120
        return max(25, 60 - seconds)

    def update(self) -> None:
        match self.phase:
            case "TITLE":
                self._update_title()
            case "PLAYING":
                self._update_playing()
            case "GAME_OVER":
                self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._reset()
            self.phase = "PLAYING"
            self._init_prizes()

    def _update_playing(self) -> None:
        self._update_heat()
        self.timer -= 1
        if self.timer <= 0:
            self._end_game()
            return

        if self.super_timer > 0:
            self.super_timer -= 1

        self._update_prizes()
        self._update_particles()
        self._update_float_texts()
        self._update_spawn_timer()

        if not self.claw_dropping and not self.claw_retracting:
            self._update_claw_input()
        elif self.claw_dropping and not self.claw_retracting:
            self._update_claw_drop()
        elif self.claw_retracting:
            self._update_claw_retract()

    def _update_claw_input(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT):
            self.claw_x -= self.CLAW_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.claw_x += self.CLAW_SPEED
        self.claw_x = max(self.CLAW_LEFT_LIMIT, min(self.claw_x, self.CLAW_RIGHT_LIMIT))
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.claw_dropping = True
            self.claw_drop_y = self.CLAW_Y

    def _update_claw_drop(self) -> None:
        self.claw_drop_y += self.DROP_SPEED
        if self.claw_drop_y >= self.BIN_TOP:
            prize = self._check_grab()
            if prize is not None:
                self._process_grab(prize)
                self._remove_prize(prize)
                self.claw_retracting = True
            elif self.claw_drop_y >= self.BIN_BOTTOM:
                self.claw_retracting = True

    def _update_claw_retract(self) -> None:
        self.claw_drop_y -= self.RETRACT_SPEED
        if self.claw_drop_y <= self.CLAW_Y:
            self.claw_drop_y = self.CLAW_Y
            self.claw_dropping = False
            self.claw_retracting = False

    def _check_grab(self) -> Prize | None:
        radius = self.SUPER_GRAB_RADIUS if self.super_timer > 0 else self.GRAB_RADIUS
        for prize in self.prizes:
            if not prize.alive:
                continue
            dx = self.claw_x - prize.x
            dy = self.claw_drop_y - prize.y
            if dx * dx + dy * dy < radius * radius:
                return prize
        return None

    def _process_grab(self, prize: Prize) -> int:
        if self.super_timer > 0 or self.last_color is None or prize.color == self.last_color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = 3 if self.super_timer > 0 else 1
            gained = 10 * self.combo * multiplier
            self.score += gained
            self.last_color = prize.color
            self._spawn_grab_particles(prize)
            self._spawn_score_text(prize.x, prize.y, gained)
            if self.combo >= self.COMBO_THRESHOLD and self.super_timer <= 0:
                self._activate_super()
            if self.combo >= 3:
                self._spawn_combo_text(self.combo)
        else:
            self.combo = 0
            self.last_color = prize.color
            self.heat += self.HEAT_MISMATCH
            self._spawn_miss_particles(prize)
            self._spawn_wrong_text(prize.x, prize.y)
            gained = 10
            self.score += gained
        return gained

    def _remove_prize(self, prize: Prize) -> None:
        prize.alive = False
        self.prizes = [p for p in self.prizes if p.alive]
        self.prizes.append(self._spawn_prize())

    def _activate_super(self) -> None:
        self.super_timer = self.SUPER_DURATION
        self.float_texts.append(FloatText(
            self.SCREEN_W // 2, self.CLAW_Y + 5, "SUPER CLAW!",
            random.choice(self.RAINBOW_COLORS), 60,
        ))

    def _spawn_grab_particles(self, prize: Prize) -> None:
        count = 16 if self.super_timer > 0 else 8
        life = 25 if self.super_timer > 0 else 15
        clr = prize.color if self.super_timer <= 0 else random.choice(self.RAINBOW_COLORS)
        for _ in range(count):
            self.particles.append(Particle(
                x=prize.x, y=prize.y,
                vx=random.uniform(-3, 3),
                vy=random.uniform(-3, 3),
                color=clr, life=life,
            ))

    def _spawn_miss_particles(self, prize: Prize) -> None:
        for _ in range(4):
            self.particles.append(Particle(
                x=prize.x, y=prize.y,
                vx=random.uniform(-2, 2),
                vy=random.uniform(-2, 2),
                color=8, life=10,
            ))

    def _spawn_score_text(self, x: float, y: float, gained: int) -> None:
        self.float_texts.append(FloatText(x, y, f"+{gained}", 7, 30))

    def _spawn_wrong_text(self, x: float, y: float) -> None:
        self.float_texts.append(FloatText(x, y, "WRONG!", 8, 30))

    def _spawn_combo_text(self, combo: int) -> None:
        color = self.RAINBOW_COLORS[combo % len(self.RAINBOW_COLORS)]
        self.float_texts.append(FloatText(
            self.SCREEN_W // 2, self.SCREEN_H // 2,
            f"COMBO x{combo}!", color, 45,
        ))

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self._end_game()
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_spawn_timer(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self._spawn_interval_for_frame()

    def _update_prizes(self) -> None:
        for prize in self.prizes:
            prize.x += prize.vx
            prize.y += prize.vy
            if prize.x < 15:
                prize.x = self.SCREEN_W - 15
            elif prize.x > self.SCREEN_W - 15:
                prize.x = 15
            if prize.y < self.BIN_TOP + 5:
                prize.y = self.BIN_BOTTOM - 5
            elif prize.y > self.BIN_BOTTOM - 5:
                prize.y = self.BIN_TOP + 5

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_float_texts(self) -> None:
        for ft in self.float_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]

    def _end_game(self) -> None:
        self.phase = "GAME_OVER"
        if self.score > self.best_score:
            self.best_score = self.score

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self._reset()
            self.phase = "TITLE"

    def draw(self) -> None:
        pyxel.cls(0)
        match self.phase:
            case "TITLE":
                self._draw_title()
            case "PLAYING":
                self._draw_playing()
            case "GAME_OVER":
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 40, 60, "CLAW CHAIN", 7)
        pyxel.text(self.SCREEN_W // 2 - 55, 90, "Color-Match COMBO!", 11)
        pyxel.text(self.SCREEN_W // 2 - 70, 130, "LEFT/RIGHT: Move claw", 7)
        pyxel.text(self.SCREEN_W // 2 - 70, 142, "SPACE/RETURN: Drop claw", 7)
        pyxel.text(self.SCREEN_W // 2 - 80, 160, "Match 4 colors -> SUPER CLAW!", 10)
        pyxel.text(self.SCREEN_W // 2 - 60, 200, "Press SPACE to start", 7)
        blink = (pyxel.frame_count // 30) % 2
        if blink:
            pyxel.text(self.SCREEN_W // 2 - 55, 200, "Press SPACE to start", 10)

    def _draw_playing(self) -> None:
        self._draw_bin()
        self._draw_prizes()
        self._draw_claw()
        self._draw_particles()
        self._draw_float_texts()
        self._draw_hud()

    def _draw_bin(self) -> None:
        pyxel.rectb(5, self.BIN_TOP - 5, self.SCREEN_W - 10, self.BIN_BOTTOM - self.BIN_TOP + 10, 13)

    def _draw_prizes(self) -> None:
        for prize in self.prizes:
            if not prize.alive:
                continue
            pyxel.circ(int(prize.x), int(prize.y), 6, prize.color)
            pyxel.circb(int(prize.x), int(prize.y), 6, 7)

    def _draw_claw(self) -> None:
        claw_x = int(self.claw_x)
        if self.claw_retracting or self.claw_dropping:
            claw_end = int(self.claw_drop_y)
        else:
            claw_end = self.CLAW_Y + 14

        if self.super_timer > 0:
            clr_idx = (pyxel.frame_count // 4) % len(self.RAINBOW_COLORS)
            clr = self.RAINBOW_COLORS[clr_idx]
        else:
            clr = 7

        pyxel.rect(claw_x - 6, self.CLAW_Y, 2, claw_end - self.CLAW_Y + 4, clr)
        pyxel.rect(claw_x + 4, self.CLAW_Y, 2, claw_end - self.CLAW_Y + 4, clr)
        pyxel.rect(claw_x - 1, self.CLAW_Y, 2, claw_end - self.CLAW_Y + 4, clr)

        pyxel.rect(claw_x - 8, self.CLAW_Y - 4, 16, 6, 7)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, self.SCREEN_W, 14, 1)
        pyxel.text(4, 4, f"SCORE:{self.score}", 7)
        pyxel.text(104, 4, f"COMBO:{self.combo}", 7)

        heat_bar_x = 200
        heat_fill = int(50 * (self.heat / self.MAX_HEAT))
        pyxel.text(heat_bar_x, 4, "HEAT", 8)
        pyxel.rect(heat_bar_x + 26, 2, 50, 8, 5)
        pyxel.rect(heat_bar_x + 26, 2, heat_fill, 8, 8)

        secs = max(0, self.timer // 60)
        pyxel.text(285, 4, f"{secs:2d}s", 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25
            if alpha > 0.3:
                pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)

    def _draw_float_texts(self) -> None:
        for ft in self.float_texts:
            alpha = ft.life / 60
            if alpha > 0.2:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 30, 60, "GAME OVER", 8)
        pyxel.text(self.SCREEN_W // 2 - 40, 90, f"SCORE: {self.score}", 7)
        pyxel.text(self.SCREEN_W // 2 - 45, 110, f"MAX COMBO: {self.max_combo}", 7)
        pyxel.text(self.SCREEN_W // 2 - 55, 130, f"BEST: {self.best_score}", 10)
        pyxel.text(self.SCREEN_W // 2 - 50, 170, "Press R to restart", 7)


if __name__ == "__main__":
    Game()
