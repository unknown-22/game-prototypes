"""Scrum Chain - Color-match rugby passing game."""
import enum
import math
import random
from dataclasses import dataclass

import pyxel


class Phase(enum.Enum):
    TITLE = enum.auto()
    PLAYING = enum.auto()
    GAME_OVER = enum.auto()


@dataclass
class Teammate:
    x: int
    y: int
    color: int


@dataclass
class Defender:
    x: int
    y: int
    color: int
    stunned: int = 0


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


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    CELL = 20
    COLS = 16
    ROWS = 12

    COLOR_NAMES = ["RED", "LIME", "DARK_BLUE", "YELLOW"]
    COLOR_VALS = [8, 11, 5, 10]

    TRY_LINE_ROW = 1
    PLAYFIELD_TOP = 2
    PLAYER_START_ROW = 11
    PLAYER_START_COL = 8

    MAX_TEAMMATES = 8
    SUPER_DURATION = 300
    TRY_SCORE = 100
    HEAT_MAX = 100.0
    HEAT_DECAY = 0.02
    PASS_RANGE = 3
    GAME_DURATION = 3600
    DEFENDER_SPAWN_INTERVAL = 180

    def __init__(self) -> None:
        self._rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_x = self.PLAYER_START_COL
        self.player_y = self.PLAYER_START_ROW
        self.player_color = 0
        self.color_timer = 90
        self.ball_x = self.PLAYER_START_COL
        self.ball_y = self.PLAYER_START_ROW
        self.has_ball = True
        self.teammates: list[Teammate] = []
        self.defenders: list[Defender] = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.heat = 0.0
        self.game_timer = self.GAME_DURATION
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames = 0
        self.frame = 0
        self.stun_timer = 0
        self.defender_spawn_timer = 0

    def start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.player_x = self.PLAYER_START_COL
        self.player_y = self.PLAYER_START_ROW
        self.player_color = 0
        self.color_timer = 90
        self.ball_x = self.PLAYER_START_COL
        self.ball_y = self.PLAYER_START_ROW
        self.has_ball = True
        self.teammates = []
        self.defenders = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.heat = 0.0
        self.game_timer = self.GAME_DURATION
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.frame = 0
        self.stun_timer = 0
        self.defender_spawn_timer = self.DEFENDER_SPAWN_INTERVAL
        self._spawn_teammates()

    def _spawn_teammates(self) -> None:
        self.teammates.clear()
        for _ in range(self.MAX_TEAMMATES):
            x = self._rng.randint(0, self.COLS - 1)
            y = self._rng.randint(self.PLAYFIELD_TOP, self.PLAYER_START_ROW - 1)
            self.teammates.append(Teammate(x, y, self._rng.randint(0, 3)))

    def _find_nearest_teammate(self) -> Teammate | None:
        if self.stun_timer > 0:
            return None
        best: Teammate | None = None
        best_dist = float("inf")
        for t in self.teammates:
            d = abs(t.x - self.player_x) + abs(t.y - self.player_y)
            if d <= self.PASS_RANGE and d < best_dist:
                best_dist = d
                best = t
        return best

    def _pass_to(self, teammate: Teammate) -> tuple[int, int, bool]:
        matched = teammate.color == self.player_color or self.super_mode
        if matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = 3 if self.super_mode else 1
            gained = 10 * self.combo * multiplier
            self.score += gained
            self.player_x = teammate.x
            self.player_y = teammate.y
            self.ball_x = teammate.x
            self.ball_y = teammate.y
            px = teammate.x * self.CELL + self.CELL // 2
            py = teammate.y * self.CELL + self.CELL // 2
            self._spawn_particles(px, py, self.COLOR_VALS[teammate.color], 8, 10)
            self._spawn_floating_text(px, py, f"+{gained}", self.COLOR_VALS[teammate.color])
            if self.combo >= 4 and not self.super_mode:
                self.super_mode = True
                self.super_timer = self.SUPER_DURATION
                self._spawn_floating_text(px, py, "SUPER!", 7)
            return gained, self.combo, True

        self.combo = 0
        self.stun_timer = 15
        if not self.super_mode:
            self.heat = min(self.HEAT_MAX, self.heat + 15)
            px = self.ball_x * self.CELL + self.CELL // 2
            py = self.ball_y * self.CELL + self.CELL // 2
            self._spawn_particles(px, py, 8, 5, 8)
            self._spawn_floating_text(px, py, "MISS!", 8)
        return 0, self.combo, False

    def _update_defenders(self) -> None:
        speed = self._difficulty_speed()
        move_every = max(1, int(10 / speed))
        if self.frame % move_every != 0:
            return
        for d in self.defenders:
            if d.stunned > 0:
                d.stunned -= 1
                continue
            tx = self.player_x
            ty = self.player_y
            best_d = abs(tx - d.x) + abs(ty - d.y)
            for t in self.teammates:
                td = abs(t.x - d.x) + abs(t.y - d.y)
                if td < best_d:
                    best_d = td
                    tx = t.x
                    ty = t.y
            dx = tx - d.x
            dy = ty - d.y
            if dx != 0:
                d.x += 1 if dx > 0 else -1
            elif dy != 0:
                d.y += 1 if dy > 0 else -1

    def _check_tackle(self) -> bool:
        if self.super_mode or self.stun_timer > 0:
            return False
        for d in self.defenders:
            if d.stunned > 0:
                continue
            if d.x == self.player_x and d.y == self.player_y:
                self.combo = 0
                self.heat = min(self.HEAT_MAX, self.heat + 25)
                self.stun_timer = 15
                px = d.x * self.CELL + self.CELL // 2
                py = d.y * self.CELL + self.CELL // 2
                self._spawn_particles(px, py, 8, 5, 8)
                self._spawn_floating_text(px, py, "TACKLE!", 8)
                return True
        return False

    def _check_try(self) -> bool:
        return self.ball_y <= self.TRY_LINE_ROW

    def _score_try(self) -> None:
        gained = self.TRY_SCORE * max(1, self.combo)
        self.score += gained
        px = self.ball_x * self.CELL + self.CELL // 2
        py = self.ball_y * self.CELL + self.CELL // 2
        self._spawn_particles(px, py, 7, 20, 15)
        self._spawn_floating_text(px, py, f"TRY! +{gained}", 7)
        self.combo = 0
        self.player_x = self.PLAYER_START_COL
        self.player_y = self.PLAYER_START_ROW
        self.ball_x = self.PLAYER_START_COL
        self.ball_y = self.PLAYER_START_ROW
        self.has_ball = True
        self.shake_frames = 15
        self._spawn_teammates()

    def _update_heat(self) -> None:
        if not self.super_mode:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY)
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER

    def _spawn_defender(self) -> None:
        if len(self.defenders) >= self._max_defenders():
            return
        edge = self._rng.randint(0, 3)
        if edge == 0:
            x = self._rng.randint(0, self.COLS - 1)
            y = self.PLAYFIELD_TOP
        elif edge == 1:
            x = self._rng.randint(0, self.COLS - 1)
            y = self.PLAYER_START_ROW
        elif edge == 2:
            x = 0
            y = self._rng.randint(self.PLAYFIELD_TOP, self.PLAYER_START_ROW)
        else:
            x = self.COLS - 1
            y = self._rng.randint(self.PLAYFIELD_TOP, self.PLAYER_START_ROW)
        self.defenders.append(Defender(x, y, self._rng.randint(0, 3)))

    def _difficulty_speed(self) -> float:
        t = min(1.0, (self.GAME_DURATION - self.game_timer) / self.GAME_DURATION)
        return 1.0 + t * 2.5

    def _difficulty_cycle_interval(self) -> int:
        t = min(1.0, (self.GAME_DURATION - self.game_timer) / self.GAME_DURATION)
        return int(90 - t * 50)

    def _max_defenders(self) -> int:
        t = min(1.0, (self.GAME_DURATION - self.game_timer) / self.GAME_DURATION)
        return int(6 + t * 4)

    def _defender_spawn_interval(self) -> int:
        t = min(1.0, (self.GAME_DURATION - self.game_timer) / self.GAME_DURATION)
        return max(60, self.DEFENDER_SPAWN_INTERVAL - int(t * 120))

    def _spawn_particles(self, x: float, y: float, color: int, count: int, life: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            spd = self._rng.random() * 2.0 + 1.0
            self.particles.append(
                Particle(x, y, math.cos(angle) * spd, math.sin(angle) * spd, color, life)
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, color, 30))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.life -= 1
            ft.y -= 1.0
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.start_game()
            return

        self.frame += 1
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        if self.stun_timer > 0:
            self.stun_timer -= 1

        if self.stun_timer == 0:
            if pyxel.btnp(pyxel.KEY_UP) and self.player_y > self.TRY_LINE_ROW:
                self.player_y -= 1
                if self.has_ball:
                    self.ball_y = self.player_y
            if pyxel.btnp(pyxel.KEY_DOWN) and self.player_y < self.PLAYER_START_ROW:
                self.player_y += 1
                if self.has_ball:
                    self.ball_y = self.player_y
            if pyxel.btnp(pyxel.KEY_LEFT) and self.player_x > 0:
                self.player_x -= 1
                if self.has_ball:
                    self.ball_x = self.player_x
            if pyxel.btnp(pyxel.KEY_RIGHT) and self.player_x < self.COLS - 1:
                self.player_x += 1
                if self.has_ball:
                    self.ball_x = self.player_x

        if pyxel.btnp(pyxel.KEY_SPACE) and self.stun_timer == 0:
            tm = self._find_nearest_teammate()
            if tm is not None:
                self._pass_to(tm)

        self.color_timer -= 1
        if self.color_timer <= 0:
            self.player_color = (self.player_color + 1) % 4
            self.color_timer = self._difficulty_cycle_interval()

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

        if self._check_try():
            self._score_try()

        self._update_defenders()
        self._check_tackle()

        self.defender_spawn_timer -= 1
        if self.defender_spawn_timer <= 0:
            self.defender_spawn_timer = self._defender_spawn_interval()
            self._spawn_defender()

        self._update_heat()
        if self.phase == Phase.GAME_OVER:
            return

        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

    def draw(self) -> None:
        pyxel.cls(0)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "SCRUM CHAIN"
        pyxel.text(self.SCREEN_W // 2 - len(title) * 4 // 2, 60, title, 7)
        lines = [
            "Arrow Keys: Move",
            "SPACE: Pass",
            "",
            "Color Match COMBO -> SUPER TRY!",
            "",
            "Press SPACE to Start",
        ]
        y = 100
        for line in lines:
            pyxel.text(self.SCREEN_W // 2 - len(line) * 4 // 2, y, line, 7)
            y += 12

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 20, 80, "GAME OVER", 8)
        score_text = f"SCORE: {self.score}"
        pyxel.text(self.SCREEN_W // 2 - len(score_text) * 4 // 2, 110, score_text, 7)
        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(self.SCREEN_W // 2 - len(combo_text) * 4 // 2, 130, combo_text, 7)
        retry_text = "SPACE to Retry"
        pyxel.text(self.SCREEN_W // 2 - len(retry_text) * 4 // 2, 160, retry_text, 7)

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)
        pyxel.camera(shake_x, shake_y)

        self._draw_field()
        self._draw_teammates()
        self._draw_defenders()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()

        pyxel.camera(0, 0)
        self._draw_hud()

    def _draw_field(self) -> None:
        for col in range(self.COLS + 1):
            pyxel.line(col * self.CELL, 0, col * self.CELL, self.SCREEN_H, 5)
        for row in range(self.ROWS):
            pyxel.line(0, row * self.CELL, self.SCREEN_W, row * self.CELL, 5)
        pyxel.line(0, self.TRY_LINE_ROW * self.CELL, self.SCREEN_W, self.TRY_LINE_ROW * self.CELL, 8)

    def _draw_teammates(self) -> None:
        for t in self.teammates:
            px = t.x * self.CELL + self.CELL // 2
            py = t.y * self.CELL + self.CELL // 2
            col = self.COLOR_VALS[t.color]
            r = 6
            pyxel.tri(px, py - r, px - r, py, px, py + r, col)
            pyxel.tri(px, py - r, px + r, py, px, py + r, col)
            label = self.COLOR_NAMES[t.color][0]
            pyxel.text(px - 2, py - 2, label, 7)

    def _draw_defenders(self) -> None:
        for d in self.defenders:
            px = d.x * self.CELL + self.CELL // 2
            py = d.y * self.CELL + self.CELL // 2
            col = self.COLOR_VALS[d.color] if d.stunned == 0 else 7
            s = 6
            pyxel.line(px - s, py - s, px + s, py + s, col)
            pyxel.line(px + s, py - s, px - s, py + s, col)

    def _draw_player(self) -> None:
        px = self.player_x * self.CELL + self.CELL // 2
        py = self.player_y * self.CELL + self.CELL // 2
        col = self.COLOR_VALS[self.player_color] if self.stun_timer == 0 else 7
        pyxel.circ(px, py, 7, col)
        if self.has_ball:
            pyxel.circ(px, py, 3, 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        if self.super_mode:
            border_color = self.COLOR_VALS[self.frame % 4]
            pyxel.rectb(0, 0, self.SCREEN_W, self.SCREEN_H, border_color)

        combo_text = f"COMBO: {self.combo}"
        if self.super_mode:
            combo_color = self.COLOR_VALS[self.frame % 4]
        elif self.combo >= 4:
            combo_color = 11
        else:
            combo_color = 7
        pyxel.text(2, 2, combo_text, combo_color)

        score_text = f"SCORE: {self.score}"
        pyxel.text(self.SCREEN_W - len(score_text) * 4 - 2, 2, score_text, 7)

        seconds = max(0, self.game_timer) // 60
        timer_text = f"TIME: {seconds}"
        timer_color = 8 if seconds <= 10 and self.frame % 30 < 15 else 7
        pyxel.text(self.SCREEN_W // 2 - len(timer_text) * 2, 2, timer_text, timer_color)

        bw = self.SCREEN_W - 4
        bh = 4
        bx = 2
        by = self.SCREEN_H - 10
        pyxel.rect(bx, by, bw, bh, 5)
        hw = int(bw * self.heat / self.HEAT_MAX)
        hc = 8
        if self.heat > 50:
            hc = 9
        if self.heat > 75:
            hc = 10
        if hw > 0:
            pyxel.rect(bx, by, hw, bh, hc)
        pyxel.text(bx, by + 5, "HEAT", 6)

        cix = self.SCREEN_W // 2 - 30
        pyxel.rect(cix, self.SCREEN_H - 20, 8, 8, self.COLOR_VALS[self.player_color])
        pyxel.text(cix + 10, self.SCREEN_H - 18, f"PASS: {self.COLOR_NAMES[self.player_color]}", 7)

        if self.super_mode:
            st = f"SUPER TRY! {self.super_timer // 60}s"
            sc = self.COLOR_VALS[self.frame % 4]
            pyxel.text(self.SCREEN_W // 2 - len(st) * 2, self.SCREEN_H - 30, st, sc)


class App:
    def __init__(self) -> None:
        self.game = Game()
        pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="Scrum Chain")
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
