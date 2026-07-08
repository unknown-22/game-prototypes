import math
import random
from dataclasses import dataclass

import pyxel

SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 216
PLAYER_W = 16
PLAYER_H = 32
BOUNCE_HEIGHT = 80
BOUNCE_SPEED = 3.0
MOVE_SPEED = 2.5
GEM_SIZE = 8
MAX_GEMS = 12
GEM_SPAWN_INTERVAL = 45
SUPER_DURATION = 300
GAME_TIME = 3600
HEAT_MAX = 100
HEAT_PER_MISS = 15
HEAT_DECAY = 0.03
COMBO_SUPER_THRESHOLD = 5
NUM_COLORS = 4

RED = 8
GREEN = 3
DARK_BLUE = 5
YELLOW = 10
COLORS = [RED, GREEN, DARK_BLUE, YELLOW]
COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW"]


@dataclass
class Gem:
    x: float
    y: float
    color: int
    wobble_phase: float = 0.0
    alive: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        self._init_state()
        self.phase = "TITLE"

    def _init_state(self) -> None:
        self.player_x: float = SCREEN_W // 2
        self.player_y: float = float(GROUND_Y)
        self.bounce_phase: float = 0.0
        self.bounce_direction: int = -1
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.gems_collected: int = 0
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.game_timer: int = GAME_TIME
        self.active_color: int = 0
        self.gems: list[Gem] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.spawn_timer: int = 0
        self.shake_frames: int = 0
        self.frame: int = 0
        self.rng: random.Random = random.Random()

    def reset(self) -> None:
        self._init_state()
        self.phase = "PLAYING"
        self.active_color = self.rng.randint(0, NUM_COLORS - 1)
        self.rng = random.Random()

    def _update_bounce(self) -> None:
        self.bounce_phase += BOUNCE_SPEED * (-self.bounce_direction)
        if self.bounce_phase >= BOUNCE_HEIGHT:
            self.bounce_phase = float(BOUNCE_HEIGHT)
            self.bounce_direction = 1
        elif self.bounce_phase <= 0:
            self.bounce_phase = 0.0
            self.bounce_direction = -1
        self.player_y = float(GROUND_Y) - self.bounce_phase

    def _update_player(self, left: bool, right: bool) -> None:
        if left:
            self.player_x -= MOVE_SPEED
        if right:
            self.player_x += MOVE_SPEED
        self.player_x = max(float(PLAYER_W), min(float(SCREEN_W - PLAYER_W), self.player_x))

    def _spawn_gem(self) -> None:
        if len(self.gems) >= MAX_GEMS:
            return
        x = self.rng.uniform(GEM_SIZE * 2, SCREEN_W - GEM_SIZE * 2)
        color = self.rng.randint(0, NUM_COLORS - 1)
        self.gems.append(Gem(x=x, y=0.0, color=color))

    def _update_gems(self) -> None:
        for gem in self.gems:
            if gem.y < 40:
                gem.y += 1.0
            elif gem.y < 60:
                gem.y += 0.3
            gem.wobble_phase += 0.03
            gem.x += math.sin(gem.wobble_phase) * 0.5

    def _check_gem_collisions(self) -> list[Gem]:
        player_top = float(GROUND_Y) - self.bounce_phase - PLAYER_H / 2
        hits: list[Gem] = []
        for gem in self.gems:
            if not gem.alive:
                continue
            dist = (gem.x - self.player_x) ** 2 + (gem.y - player_top) ** 2
            if dist < (GEM_SIZE + 10) ** 2:
                hits.append(gem)
        return hits

    def _collect_gem(self, gem: Gem) -> None:
        gem.alive = False
        if self.super_mode or gem.color == self.active_color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self._add_score(10)
            self._spawn_particles(gem.x, gem.y, COLORS[gem.color], 8)
            self._add_floating_text(
                gem.x, gem.y - 4,
                f"+{int(10 * (1 + self.combo * 0.5) * (3 if self.super_mode else 1))}",
                COLORS[gem.color],
            )
            if self.combo >= COMBO_SUPER_THRESHOLD and not self.super_mode:
                self._activate_super()
        else:
            self.combo = 0
            self.heat = min(float(HEAT_MAX), self.heat + HEAT_PER_MISS)
            self._spawn_particles(gem.x, gem.y, 13, 4)
            self._add_floating_text(gem.x, gem.y - 4, "MISS!", 8)
        if not self.super_mode:
            self.active_color = gem.color
        self.gems_collected += 1

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        for gem in self.gems:
            if gem.alive:
                self._collect_gem(gem)
        self._spawn_particles(self.player_x, self.player_y, 7, 20)
        self._add_floating_text(self.player_x, self.player_y - 20, "SUPER!", 10)

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0
                self.combo = 0

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _add_score(self, base: int) -> None:
        multiplier = 1.0 + self.combo * 0.5
        if self.super_mode:
            multiplier *= 3
        self.score += int(base * multiplier)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self.rng.uniform(-2.0, 2.0)
            vy = self.rng.uniform(-3.0, -1.0)
            life = self.rng.randint(15, 30)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color)
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x - len(text) * 2, y=y, text=text, life=30, color=color)
        )

    def update(self) -> None:
        self.frame += 1
        if self.phase == "PLAYING":
            self._update_playing()
        elif self.phase == "GAME_OVER":
            self._update_particles()
            self._update_floating_texts()

    def _update_playing(self) -> None:
        left = pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A)
        right = pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D)

        self._update_bounce()
        self._update_player(left, right)
        self._update_gems()
        self._update_super()

        self.spawn_timer += 1
        if self.spawn_timer >= GEM_SPAWN_INTERVAL:
            self.spawn_timer = 0
            self._spawn_gem()

        hits = self._check_gem_collisions()
        for gem in hits:
            self._collect_gem(gem)
        self.gems = [g for g in self.gems if g.alive]

        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

        self.game_timer -= 1

        if self.player_y > SCREEN_H + 50:
            self.phase = "GAME_OVER"
        elif self.heat >= HEAT_MAX:
            self.phase = "GAME_OVER"
        elif self.game_timer <= 0:
            self.phase = "GAME_OVER"

        if self.heat > 60:
            self.shake_frames = max(1, int((self.heat - 60) / 5))
        elif self.shake_frames > 0:
            self.shake_frames -= 1

        self._update_particles()
        self._update_floating_texts()

    def draw(self) -> None:
        pyxel.cls(0)
        if self.phase == "TITLE":
            self._draw_title()
        elif self.phase == "PLAYING":
            self._draw_playing()
        elif self.phase == "GAME_OVER":
            self._draw_game_over()

    def _draw_title(self) -> None:
        for i in range(SCREEN_H):
            c = 1 if i < SCREEN_H * 2 // 3 else 5
            pyxel.line(0, i, SCREEN_W, i, c)

        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, 5)

        title = "POGO CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 40, title, 7)

        lines = [
            "Bounce through same-color gems!",
            "COMBO x5 = SUPER BOUNCE!",
            "",
            "Arrow keys / A,D to move",
            "Match colors for COMBO chain",
            "Wrong color = HEAT + MISS",
            "HEAT 100 = GAME OVER",
            "",
            "PRESS ENTER TO START",
        ]
        for i, line in enumerate(lines):
            if line and (self.frame // 30) % 2 == 0 and i == len(lines) - 1:
                pyxel.text(SCREEN_W // 2 - len(line) * 2, 80 + i * 14, line, 10)
            elif line:
                pyxel.text(SCREEN_W // 2 - len(line) * 2, 80 + i * 14, line, 7)

    def _draw_playing(self) -> None:
        if self.shake_frames > 0:
            sx = self.rng.randint(-self.shake_frames, self.shake_frames)
            sy = self.rng.randint(-self.shake_frames // 2, self.shake_frames // 2)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        for i in range(SCREEN_H):
            c = 1
            pyxel.line(0, i, SCREEN_W, i, c)

        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, 5)
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, 7)

        self._draw_gems()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_gems(self) -> None:
        for gem in self.gems:
            if not gem.alive:
                continue
            gx = int(gem.x)
            gy = int(gem.y)
            c = COLORS[gem.color]
            s = GEM_SIZE
            pyxel.tri(gx, gy - s, gx - s, gy, gx, gy + s, c)
            pyxel.tri(gx, gy - s, gx + s, gy, gx, gy + s, c)
            pyxel.line(gx - s, gy, gx, gy + s, 13)
            pyxel.line(gx + s, gy, gx, gy + s, 13)
            pyxel.line(gx, gy - s, gx - s, gy, 13)
            pyxel.line(gx, gy - s, gx + s, gy, 13)
            highlight = 7 if c != 7 else 10
            pyxel.line(gx, gy - s, gx - s // 2, gy - s // 2, highlight)
            pyxel.line(gx, gy - s, gx + s // 2, gy - s // 2, highlight)

    def _draw_player(self) -> None:
        px = int(self.player_x)
        py = int(self.player_y)
        head_y = py - PLAYER_H + 8
        spring_top = head_y + 6
        spring_bottom = py

        if self.super_mode:
            rainbow = [8, 10, 3, 6]
            c_idx = (self.frame // 4) % 4
            body_color = rainbow[c_idx]
            head_color = rainbow[(c_idx + 1) % 4]
        else:
            body_color = 7
            head_color = 7

        pyxel.circ(px, head_y, 5, head_color)
        pyxel.rect(px - 2, head_y + 4, 4, spring_top - head_y - 4, body_color)
        pyxel.rect(px - 1, head_y + 4, 2, spring_top - head_y - 4, 7)
        pyxel.rect(px - 3, head_y + 5, 2, 2, body_color)

        compressed = int(self.bounce_phase * 3 / BOUNCE_HEIGHT)
        coil_count = max(1, 4 - compressed)
        seg_h = (spring_bottom - spring_top) / coil_count
        for i in range(coil_count):
            coil_y = int(spring_top + seg_h * i)
            coil_x = px - 4 if i % 2 == 0 else px + 1
            pyxel.rect(coil_x, coil_y, 3, max(1, int(seg_h) - 1), body_color)

        pyxel.rect(px - 3, py - 2, 6, 2, 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 0:
                size = max(1, p.life // 10)
                pyxel.rect(int(p.x), int(p.y), size, size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 30, 0)
        pyxel.line(0, 30, SCREEN_W, 30, 5)

        pyxel.text(4, 4, f"SCORE {self.score}", 7)

        combo_color = 7
        if self.combo >= 3:
            combo_color = 10
        if self.combo >= COMBO_SUPER_THRESHOLD:
            combo_color = 8
        pyxel.text(4, 14, f"COMBO x{self.combo}", combo_color)

        secs = max(0, self.game_timer) // 60 + 1
        time_text = f"TIME {secs}s"
        pyxel.text(SCREEN_W - 60, 4, time_text, 7)

        bar_x = SCREEN_W - 64
        bar_y = 16
        bar_w = 56
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 13)
        fill = int(self.heat / HEAT_MAX * bar_w)
        heat_color = 9 if self.heat < 50 else (10 if self.heat < 80 else 8)
        if fill > 0:
            pyxel.rect(bar_x, bar_y, fill, bar_h, heat_color)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 7)
        pyxel.text(bar_x - 15, bar_y - 1, "HT", 7)

        ax = 4
        ay = 24
        pyxel.rect(ax, ay, 6, 6, COLORS[self.active_color])
        pyxel.rect(ax, ay, 6, 6, 7)

        if self.super_mode:
            secs_left = self.super_timer // 60 + 1
            suptext = f"SUPER {secs_left}s"
            pyxel.text(SCREEN_W // 2 - len(suptext) * 2, 4, suptext, 8)

    def _draw_game_over(self) -> None:
        for i in range(SCREEN_H):
            pyxel.line(0, i, SCREEN_W, i, 5)

        self._draw_particles()
        self._draw_floating_texts()

        go = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go) * 2, 30, go, 8)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 60, score_text, 7)

        combo_text = f"MAX COMBO: x{self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 80, combo_text, 10)

        gem_text = f"GEMS: {self.gems_collected}"
        pyxel.text(SCREEN_W // 2 - len(gem_text) * 2, 100, gem_text, 7)

        if self.heat >= HEAT_MAX:
            reason = "OVERHEATED!"
        elif self.game_timer <= 0:
            reason = "TIME UP!"
        else:
            reason = "FELL OFF!"
        pyxel.text(SCREEN_W // 2 - len(reason) * 2, 125, reason, 8)

        retry = "PRESS ENTER TO RETRY"
        if (self.frame // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - len(retry) * 2, 160, retry, 7)


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="POGO CHAIN", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game
        if g.phase == "TITLE":
            g.update()
            if pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == "GAME_OVER":
            g.update()
            if pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == "PLAYING":
            g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
