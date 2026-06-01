"""
Chroma Ice — Top-down ice hockey arcade game.
Same-color consecutive goals build COMBO multiplier chain (x2->x4->x8...).
HEAT builds as a risk system — overheat makes the goalie invincible temporarily.
60-second timed round, maximize score = sum(goals * combo_multiplier).

最前面白い瞬間: 同じ色のパックを連続でゴールに叩き込み、
コンボ倍率が爆発的に増える瞬間。
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
import pyxel

W, H = 320, 240
GOAL_X_MIN = 305
GOAL_X_MAX = 315
GOAL_Y_MIN = 90
GOAL_Y_MAX = 150
GOALIE_X = 298
GOALIE_W = 12
GOALIE_H = 30
GOALIE_Y_MIN = 75
GOALIE_Y_MAX = 165
PLAYER_RADIUS = 8
PUCK_RADIUS = 6
PLAYER_START_X = 60.0
PLAYER_START_Y = 120.0
PLAYER_ACCEL = 0.8
PLAYER_MAX_SPEED = 3.0
PLAYER_FRICTION = 0.92
SHOT_MAX_DRAG = 150.0
SHOT_MAX_SPEED = 8.0
PUCK_FRICTION = 0.98
PUCK_MIN_SPEED = 0.3
HEAT_DECAY_RATE = 0.5
HEAT_OVERHEAT_DECAY = 2.0
HEAT_OVERHEAT_THRESHOLD = 80.0
HEAT_MAX = 100.0
OVERHEAT_DURATION = 180
GAME_DURATION = 3600
MAX_COMBO = 7
PUCK_MIN_COUNT = 4
PUCK_MAX_COUNT = 6
RINK_BORDER = 4

PUCK_COLORS = [pyxel.COLOR_RED, pyxel.COLOR_CYAN, pyxel.COLOR_YELLOW, pyxel.COLOR_PURPLE]


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Puck:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    color: int = 0
    active: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class Goalie:
    y: float
    target_y: float
    speed: float = 1.2
    width: int = GOALIE_W
    height: int = GOALIE_H


class Game:
    def __init__(self) -> None:
        pyxel.init(W, H, title="Chroma Ice", display_scale=2)
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.player_x = PLAYER_START_X
        self.player_y = PLAYER_START_Y
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.pucks: list[Puck] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[tuple[str, float, float, int]] = []
        self.goalie = Goalie(y=120.0, target_y=120.0)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.overheat_timer = 0
        self.game_timer = GAME_DURATION
        self.last_goal_color: int = -1
        self.held_puck: Puck | None = None
        self.aim_active = False
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.rng = random.Random()
        self.shake_frames = 0
        self.heat_decay_timer = 0

    def reset(self) -> None:
        self.player_x = PLAYER_START_X
        self.player_y = PLAYER_START_Y
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.pucks.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.goalie = Goalie(y=120.0, target_y=120.0)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.overheat_timer = 0
        self.game_timer = GAME_DURATION
        self.last_goal_color = -1
        self.held_puck = None
        self.aim_active = False
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.shake_frames = 0
        self.heat_decay_timer = 0
        self._spawn_pucks(PUCK_MIN_COUNT)

    def _spawn_pucks(self, count: int) -> None:
        for _ in range(min(count, PUCK_MAX_COUNT - len(self.pucks))):
            angle = self.rng.uniform(0, math.pi * 2)
            dist = self.rng.uniform(40, 140)
            x = 100 + math.cos(angle) * dist
            y = 120 + math.sin(angle) * dist
            x = max(RINK_BORDER + PUCK_RADIUS, min(280, x))
            y = max(RINK_BORDER + PUCK_RADIUS, min(H - RINK_BORDER - PUCK_RADIUS, y))
            color = self.rng.choice([pyxel.COLOR_RED, pyxel.COLOR_CYAN, pyxel.COLOR_YELLOW, pyxel.COLOR_PURPLE])
            self.pucks.append(Puck(x=x, y=y, color=color))

    def _shoot_puck(self, angle: float, power: float) -> None:
        if self.held_puck is None:
            return
        puck = self.held_puck
        self.held_puck = None
        puck.vx = math.cos(angle) * power
        puck.vy = math.sin(angle) * power
        puck.active = True
        self.heat = min(HEAT_MAX, self.heat + 5.0)

    def _update_player(self, dx: float, dy: float) -> None:
        self.player_vx += dx * PLAYER_ACCEL
        self.player_vy += dy * PLAYER_ACCEL
        self.player_vx *= PLAYER_FRICTION
        self.player_vy *= PLAYER_FRICTION
        speed = math.hypot(self.player_vx, self.player_vy)
        if speed > PLAYER_MAX_SPEED:
            scale = PLAYER_MAX_SPEED / speed
            self.player_vx *= scale
            self.player_vy *= scale
        if abs(self.player_vx) < 0.01:
            self.player_vx = 0.0
        if abs(self.player_vy) < 0.01:
            self.player_vy = 0.0
        self.player_x += self.player_vx
        self.player_y += self.player_vy
        self.player_x = max(RINK_BORDER + PLAYER_RADIUS, min(W - RINK_BORDER - PLAYER_RADIUS, self.player_x))
        self.player_y = max(RINK_BORDER + PLAYER_RADIUS, min(H - RINK_BORDER - PLAYER_RADIUS, self.player_y))

    def _update_pucks(self) -> None:
        for puck in self.pucks:
            if not puck.active:
                continue
            puck.x += puck.vx
            puck.y += puck.vy
            puck.vx *= PUCK_FRICTION
            puck.vy *= PUCK_FRICTION
            if math.hypot(puck.vx, puck.vy) < PUCK_MIN_SPEED:
                puck.vx = 0.0
                puck.vy = 0.0
        self.pucks = [p for p in self.pucks if not (p.active and (p.x < -20 or p.x > W + 20 or p.y < -20 or p.y > H + 20))]

    def _update_goalie(self) -> None:
        goalie = self.goalie
        if goalie.y < goalie.target_y:
            goalie.y = min(goalie.target_y, goalie.y + goalie.speed)
        elif goalie.y > goalie.target_y:
            goalie.y = max(goalie.target_y, goalie.y - goalie.speed)
        goalie.y = max(GOALIE_Y_MIN, min(GOALIE_Y_MAX, goalie.y))

    def _check_player_puck_collision(self) -> Puck | None:
        for puck in self.pucks:
            if puck.active:
                continue
            dx = self.player_x - puck.x
            dy = self.player_y - puck.y
            if math.hypot(dx, dy) < PLAYER_RADIUS + PUCK_RADIUS:
                return puck
        return None

    def _check_goal(self, puck: Puck) -> bool:
        return puck.active and puck.x > GOAL_X_MIN and GOAL_Y_MIN < puck.y < GOAL_Y_MAX

    def _check_save(self, puck: Puck) -> bool:
        if not puck.active:
            return False
        goalie = self.goalie
        half_w = goalie.width / 2
        half_h = goalie.height / 2
        return (
            abs(puck.x - GOALIE_X) < (PUCK_RADIUS + half_w)
            and abs(puck.y - goalie.y) < (PUCK_RADIUS + half_h)
        )

    def _handle_shot_result(self, scored: bool, saved: bool, puck_color: int) -> None:
        if scored:
            if puck_color == self.last_goal_color:
                if self.combo < MAX_COMBO:
                    self.combo += 1
            else:
                self.combo = 0
                self.heat = max(0.0, self.heat - 15.0)
            self.last_goal_color = puck_color
            multiplier = self._compute_combo_multiplier()
            self.score += multiplier
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._spawn_particles(GOAL_X_MIN, (GOAL_Y_MIN + GOAL_Y_MAX) / 2, 12, puck_color)
            if self.combo >= 2:
                self.floating_texts.append((f"COMBO x{multiplier}!", GOAL_X_MIN - 10, GOAL_Y_MIN - 8, 30))
            self.shake_frames = 4
            self.heat = min(HEAT_MAX, self.heat + 8.0)
        elif saved:
            self.heat = min(HEAT_MAX, self.heat + 10.0)
            self.combo = 0
            self._spawn_particles(GOALIE_X, self.goalie.y, 6, pyxel.COLOR_GRAY)
        else:
            self.heat = min(HEAT_MAX, self.heat + 3.0)

    def _update_heat(self, dt: float = 1.0) -> None:
        if self.overheat_timer > 0:
            self.heat = max(0.0, self.heat - HEAT_OVERHEAT_DECAY * dt)
            self.overheat_timer -= int(dt)
            if self.overheat_timer <= 0:
                self.overheat_timer = 0
                self._spawn_particles(self.player_x, self.player_y, 4, pyxel.COLOR_WHITE)
        else:
            self.heat_decay_timer += 1
            if self.heat_decay_timer >= 2:
                self.heat_decay_timer = 0
                self.heat = max(0.0, self.heat - HEAT_DECAY_RATE * dt)
            if self.heat >= HEAT_OVERHEAT_THRESHOLD:
                self.overheat_timer = OVERHEAT_DURATION
                self._spawn_particles(self.player_x, self.player_y, 8, pyxel.COLOR_RED)

    def _compute_combo_multiplier(self) -> int:
        return 1 << self.combo

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            vx = self.rng.uniform(-3, 3)
            vy = self.rng.uniform(-3, 3)
            life = self.rng.randint(10, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        new_texts: list[tuple[str, float, float, int]] = []
        for text, x, y, life in self.floating_texts:
            if life > 0:
                new_texts.append((text, x, y - 0.5, life - 1))
        self.floating_texts = new_texts

    def _update_goalie_target(self) -> None:
        active_pucks = [p for p in self.pucks if p.active]
        if active_pucks:
            target_puck = min(active_pucks, key=lambda p: abs(p.x - GOALIE_X))
            predict_y = target_puck.y
            if target_puck.vx != 0:
                time_to_goal = (GOALIE_X - target_puck.x) / target_puck.vx if target_puck.vx > 0 else float("inf")
                if time_to_goal > 0:
                    predict_y = target_puck.y + target_puck.vy * time_to_goal
            self.goalie.target_y = max(GOALIE_Y_MIN, min(GOALIE_Y_MAX, predict_y))
        else:
            self.goalie.target_y = 120.0

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_R):
                self.phase = Phase.TITLE
            return

        if self.phase == Phase.PLAYING:
            self.game_timer -= 1
            if self.game_timer <= 0:
                self.game_timer = 0
                self.phase = Phase.GAME_OVER
                return

            if pyxel.btnp(pyxel.KEY_R):
                self.phase = Phase.TITLE
                return

            dx = 0.0
            dy = 0.0
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                dx -= 1.0
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                dx += 1.0
            if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
                dy -= 1.0
            if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
                dy += 1.0
            if dx != 0.0 or dy != 0.0:
                mag = math.hypot(dx, dy)
                dx /= mag
                dy /= mag
            self._update_player(dx, dy)

            puck = self._check_player_puck_collision()
            if puck is not None and self.held_puck is None:
                self.held_puck = puck
                puck.x = self.player_x
                puck.y = self.player_y

            if self.held_puck is not None:
                self.held_puck.x = self.player_x
                self.held_puck.y = self.player_y

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.aim_active = True
                self.aim_start_x = float(pyxel.mouse_x)
                self.aim_start_y = float(pyxel.mouse_y)

            if self.aim_active and pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                self.aim_active = False
                if self.held_puck is not None:
                    release_x = float(pyxel.mouse_x)
                    release_y = float(pyxel.mouse_y)
                    dx_drag = release_x - self.aim_start_x
                    dy_drag = release_y - self.aim_start_y
                    drag_dist = math.hypot(dx_drag, dy_drag)
                    drag_dist = min(drag_dist, SHOT_MAX_DRAG)
                    power = (drag_dist / SHOT_MAX_DRAG) * SHOT_MAX_SPEED
                    if drag_dist > 0.1:
                        angle = math.atan2(dy_drag, dx_drag)
                    else:
                        angle = math.atan2(self.player_y - GOALIE_X, self.player_x - 120)
                    self._shoot_puck(angle, power)
                    self.heat_decay_timer = 0

            if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
                self.aim_active = False

            self._update_pucks()
            self._update_goalie_target()
            self._update_goalie()

            for puck in self.pucks:
                if not puck.active:
                    continue
                if puck == self.held_puck:
                    continue
                scored = self._check_goal(puck)
                saved = not scored and self.overheat_timer > 0 and self._check_save(puck)
                if not saved and not scored and self.overheat_timer <= 0:
                    saved = self._check_save(puck)
                if scored or saved:
                    puck.active = False
                    puck.vx = 0.0
                    puck.vy = 0.0
                    self._handle_shot_result(scored, saved, puck.color)

            inactive_count = sum(1 for p in self.pucks if not p.active)
            if inactive_count < PUCK_MIN_COUNT:
                self._spawn_pucks(PUCK_MIN_COUNT - inactive_count)

            self._update_heat()
            self._update_particles()
            self._update_floating_texts()

            if self.shake_frames > 0:
                self.shake_frames -= 1


    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.shake_frames > 0:
            sx = self.rng.randint(-3, 3)
            sy = self.rng.randint(-3, 3)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()
        pyxel.camera(0, 0)

    def _draw_title(self) -> None:
        pyxel.rect(0, 0, W, H, pyxel.COLOR_NAVY)
        pyxel.text(W // 2 - 32, 40, "CHROMA ICE", pyxel.COLOR_WHITE)
        pyxel.text(W // 2 - 60, 54, "[ Ice Hockey Arcade ]", pyxel.COLOR_CYAN)
        pyxel.text(W // 2 - 70, 80, "Same-color goals build COMBO!", pyxel.COLOR_YELLOW)
        pyxel.text(W // 2 - 85, 94, "x2 -> x4 -> x8 -> x16 -> x32...", pyxel.COLOR_ORANGE)
        pyxel.text(W // 2 - 70, 114, "HEAT builds risk!", pyxel.COLOR_RED)
        pyxel.text(W // 2 - 80, 128, "Overheat = Goalie Invincible", pyxel.COLOR_PURPLE)
        pyxel.text(W // 2 - 56, 158, "ARROWS/WASD  : Move", pyxel.COLOR_WHITE)
        pyxel.text(W // 2 - 56, 170, "CLICK + DRAG : Shoot", pyxel.COLOR_WHITE)
        pyxel.text(W // 2 - 56, 182, "R            : Restart", pyxel.COLOR_WHITE)
        pyxel.text(W // 2 - 50, 210, "Press ENTER to play", pyxel.COLOR_GREEN)

    def _draw_game(self) -> None:
        for row in range(0, H, 10):
            color = pyxel.COLOR_LIGHT_BLUE if (row // 10) % 2 == 0 else pyxel.COLOR_DARK_BLUE
            pyxel.rect(0, row, W, 10, color)

        pyxel.rect(0, 0, W, H, pyxel.COLOR_BLACK)
        pyxel.rect(RINK_BORDER, RINK_BORDER, W - RINK_BORDER * 2, H - RINK_BORDER * 2, pyxel.COLOR_DARK_BLUE)
        for row in range(RINK_BORDER, H - RINK_BORDER, 10):
            color = pyxel.COLOR_LIGHT_BLUE if ((row - RINK_BORDER) // 10) % 2 == 0 else pyxel.COLOR_DARK_BLUE
            pyxel.rect(RINK_BORDER, row, W - RINK_BORDER * 2, 10, color)

        pyxel.rect(GOAL_X_MIN - 2, GOAL_Y_MIN - 2, 4, GOAL_Y_MAX - GOAL_Y_MIN + 4, pyxel.COLOR_BLACK)
        pyxel.rect(GOAL_X_MIN, GOAL_Y_MIN, GOAL_X_MAX - GOAL_X_MIN, GOAL_Y_MAX - GOAL_Y_MIN, pyxel.COLOR_WHITE)

        pyxel.rect(GOAL_X_MIN - 2, GOAL_Y_MIN - 2, 4, GOAL_Y_MAX - GOAL_Y_MIN + 4, pyxel.COLOR_WHITE)
        pyxel.rect(GOAL_X_MIN + GOAL_X_MAX - GOAL_X_MIN - 2, GOAL_Y_MIN - 2, 4, GOAL_Y_MAX - GOAL_Y_MIN + 4, pyxel.COLOR_WHITE)

        for puck in self.pucks:
            if puck is self.held_puck:
                continue
            if puck.active:
                pyxel.circ(int(puck.x), int(puck.y), PUCK_RADIUS - 1, pyxel.COLOR_BLACK)
                pyxel.circ(int(puck.x), int(puck.y), PUCK_RADIUS, puck.color)
            else:
                pyxel.circ(int(puck.x), int(puck.y), PUCK_RADIUS - 1, pyxel.COLOR_BLACK)
                pyxel.circ(int(puck.x), int(puck.y), PUCK_RADIUS - 1, puck.color)

        if self.held_puck is not None:
            px = int(self.held_puck.x)
            py = int(self.held_puck.y)
            pyxel.circ(px, py, PUCK_RADIUS + 2, pyxel.COLOR_WHITE)
            pyxel.circ(px, py, PUCK_RADIUS - 1, pyxel.COLOR_BLACK)
            pyxel.circ(px, py, PUCK_RADIUS - 1, self.held_puck.color)

        g = self.goalie
        goalie_color = pyxel.COLOR_RED if self.overheat_timer > 0 else pyxel.COLOR_GRAY
        pyxel.rect(
            int(GOALIE_X - g.width / 2),
            int(g.y - g.height / 2),
            g.width,
            g.height,
            goalie_color,
        )

        px = int(self.player_x)
        py = int(self.player_y)
        pyxel.circ(px, py, PLAYER_RADIUS + 1, pyxel.COLOR_BLACK)
        pyxel.circ(px, py, PLAYER_RADIUS, pyxel.COLOR_WHITE)
        stick_end_x = px + math.cos(0.3) * 12
        stick_end_y = py + math.sin(0.3) * 12
        pyxel.line(px, py, int(stick_end_x), int(stick_end_y), pyxel.COLOR_BROWN)

        if self.aim_active and self.held_puck is not None:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dist = math.hypot(mx - self.aim_start_x, my - self.aim_start_y)
            clamped = min(dist, SHOT_MAX_DRAG)
            if dist > 0:
                end_x = self.player_x + (mx - self.aim_start_x) / dist * clamped
                end_y = self.player_y + (my - self.aim_start_y) / dist * clamped
            else:
                end_x = self.player_x + 100
                end_y = self.player_y
            steps = 12
            for i in range(steps):
                t = i / (steps - 1)
                lx = int(self.player_x + (end_x - self.player_x) * t)
                ly = int(self.player_y + (end_y - self.player_y) * t)
                if i % 2 == 0:
                    pyxel.pset(lx, ly, pyxel.COLOR_WHITE)

        for p in self.particles:
            if p.life > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        for text, x, y, life in self.floating_texts:
            if life > 0:
                alpha_cyc = life % 20
                if alpha_cyc >= 10:
                    pyxel.text(int(x), int(y), text, pyxel.COLOR_YELLOW)

        pyxel.text(6, 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)

        combo_mult = self._compute_combo_multiplier()
        if self.combo > 0:
            combo_str = f"COMBO x{combo_mult}"
            pyxel.text(W // 2 - len(combo_str) * 2, 4, combo_str, pyxel.COLOR_YELLOW)
        else:
            pyxel.text(W // 2 - 32, 4, "NO COMBO", pyxel.COLOR_GRAY)

        heat_bar_x = W - 44
        heat_bar_y = 4
        heat_bar_w = 40
        heat_bar_h = 6
        pyxel.rect(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, pyxel.COLOR_GRAY)
        heat_fill = int(self.heat / HEAT_MAX * heat_bar_w)
        if self.heat >= 80:
            heat_color = pyxel.COLOR_RED
        elif self.heat >= 50:
            heat_color = pyxel.COLOR_YELLOW
        else:
            heat_color = pyxel.COLOR_GREEN
        pyxel.rect(heat_bar_x, heat_bar_y, heat_fill, heat_bar_h, heat_color)
        pyxel.text(heat_bar_x - 16, heat_bar_y, "HEAT", pyxel.COLOR_WHITE)

        if self.overheat_timer > 0:
            pyxel.text(W // 2 - 36, 16, "OVERHEAT!", pyxel.COLOR_RED)

        secs = max(0, self.game_timer // 60)
        timer_str = f"TIME: {secs}"
        pyxel.text(W // 2 - len(timer_str) * 2, H - 10, timer_str, pyxel.COLOR_WHITE)

    def _draw_game_over(self) -> None:
        pyxel.rect(W // 2 - 60, H // 2 - 40, 120, 80, pyxel.COLOR_BLACK)
        pyxel.rectb(W // 2 - 60, H // 2 - 40, 120, 80, pyxel.COLOR_WHITE)
        pyxel.text(W // 2 - 28, H // 2 - 32, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(W // 2 - 52, H // 2 - 18, f"Score: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(W // 2 - 52, H // 2 - 6, f"Max Combo: x{self._compute_combo_multiplier() if self.max_combo > 0 else 1}", pyxel.COLOR_YELLOW)
        pyxel.text(W // 2 - 40, H // 2 + 16, "ENTER to retry", pyxel.COLOR_GREEN)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
