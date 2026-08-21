import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# 16-color palette
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

# Screen
WIDTH = 320
HEIGHT = 240

# Player
PLAYER_RADIUS = 6
PLAYER_SPEED = 2.0
PLAYER_HP = 5
PLAYER_COOLDOWN = 12
PLAYER_SHOT_RADIUS = 3
PLAYER_SHOT_SPEED = 5.0

# Boss
BOSS_RADIUS = 16
BOSS_HP = 100
BOSS_START_X = 160.0
BOSS_START_Y = 110.0
BOSS_SHOT_RADIUS = 4
BOSS_SHOT_BASE_SPEED = 1.8

# Rage / replay
RAGE_GAIN = 8
RAGE_DECAY = 0.25
MAX_REPLAY = 40
ENRAGE_TELEGRAPH = 60
SPREAD = 0.09

# Game
GAME_DURATION = 3600  # 60s at 60fps

# Projectile life (frames)
PLAYER_SHOT_LIFE = 240
BOSS_SHOT_LIFE = 600


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    radius: int
    kind: str  # "player" or "boss"
    life: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class Floater:
    x: float
    y: float
    text: str
    color: int
    life: int


def boss_fire_interval(rage: float, enrage_count: int) -> int:
    return max(16, 50 - int(rage * 0.3) - enrage_count * 4)


def boss_projectile_speed(enrage_count: int) -> float:
    return BOSS_SHOT_BASE_SPEED + enrage_count * 0.4


def rage_gain_per_hit() -> int:
    return RAGE_GAIN


def rage_decay_per_frame() -> float:
    return RAGE_DECAY


def player_damage_per_hit() -> int:
    return 4


class Game:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.best_score = getattr(self, "best_score", 0)
        if getattr(self, "rng", None) is None:
            self.rng = random.Random()
        self.phase = Phase.TITLE
        self.frame = 0
        self.player_x = 160.0
        self.player_y = 200.0
        self.player_hp = PLAYER_HP
        self.player_cooldown = 0
        self.boss_x = BOSS_START_X
        self.boss_y = BOSS_START_Y
        self.boss_hp = BOSS_HP
        self.rage = 0.0
        self.enrage_count = 0
        self.invincible_timer = 0
        self.boss_fire_timer = boss_fire_interval(0.0, 0)
        self.replay_log: list[tuple[float, float]] = []
        self.projectiles: list[Projectile] = []
        self.particles: list[Particle] = []
        self.floaters: list[Floater] = []
        self.score = 0
        self.shake_frames = 0
        self.victory = False
        self.defeat_reason = ""

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self.rng.uniform(-1.5, 1.5),
                    vy=self.rng.uniform(-1.5, 1.5),
                    life=self.rng.randint(12, 28),
                    color=color,
                )
            )

    def _fire_player(self) -> None:
        if self.player_cooldown > 0:
            return
        self.player_cooldown = PLAYER_COOLDOWN
        dx = self.boss_x - self.player_x
        dy = self.boss_y - self.player_y
        dist = math.hypot(dx, dy)
        if dist < 0.0001:
            dist = 1.0
        vx = dx / dist * PLAYER_SHOT_SPEED
        vy = dy / dist * PLAYER_SHOT_SPEED
        self.projectiles.append(
            Projectile(
                x=self.player_x,
                y=self.player_y,
                vx=vx,
                vy=vy,
                radius=PLAYER_SHOT_RADIUS,
                kind="player",
                life=PLAYER_SHOT_LIFE,
            )
        )

    def _update_player(self, dx: float, dy: float) -> None:
        if dx != 0.0 or dy != 0.0:
            mag = math.hypot(dx, dy)
            dx /= mag
            dy /= mag
        self.player_x += dx * PLAYER_SPEED
        self.player_y += dy * PLAYER_SPEED
        self.player_x = max(PLAYER_RADIUS, min(WIDTH - PLAYER_RADIUS, self.player_x))
        self.player_y = max(PLAYER_RADIUS, min(HEIGHT - PLAYER_RADIUS, self.player_y))

    def _update_projectiles(self) -> None:
        survivors: list[Projectile] = []
        for p in self.projectiles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                continue
            if p.x < -8 or p.x > WIDTH + 8 or p.y < -8 or p.y > HEIGHT + 8:
                continue
            survivors.append(p)
        self.projectiles = survivors

    def _check_player_hit(self) -> bool:
        hit = False
        survivors: list[Projectile] = []
        for p in self.projectiles:
            if p.kind == "boss":
                dx = p.x - self.player_x
                dy = p.y - self.player_y
                rr = PLAYER_RADIUS + p.radius
                if dx * dx + dy * dy <= rr * rr:
                    self.player_hp -= 1
                    self.shake_frames += 8
                    self._spawn_particles(self.player_x, self.player_y, 8, RED)
                    hit = True
                    continue
            survivors.append(p)
        self.projectiles = survivors
        return hit

    def _check_boss_hit(self) -> bool:
        hit = False
        survivors: list[Projectile] = []
        for p in self.projectiles:
            if p.kind == "player":
                dx = p.x - self.boss_x
                dy = p.y - self.boss_y
                rr = BOSS_RADIUS + p.radius
                if dx * dx + dy * dy <= rr * rr:
                    if self.invincible_timer <= 0:
                        self.boss_hp -= player_damage_per_hit()
                        self.rage += rage_gain_per_hit()
                        self.score += 10
                        self.replay_log.append((p.x, p.y))
                        self._spawn_particles(p.x, p.y, 6, YELLOW)
                        hit = True
                    continue
            survivors.append(p)
        self.projectiles = survivors
        return hit

    def _update_rage(self) -> None:
        if self.rage >= 100.0:
            self._trigger_enrage()
            return
        self.rage = max(0.0, self.rage - rage_decay_per_frame())

    def _trigger_enrage(self) -> None:
        self.invincible_timer = ENRAGE_TELEGRAPH
        self.enrage_count += 1
        self.rage = 0.0
        self.floaters.append(
            Floater(self.boss_x, self.boss_y - 24, "ENRAGE!", RED, 40)
        )
        self._spawn_particles(self.boss_x, self.boss_y, 20, PINK)
        self.shake_frames += 6

    def _update_enrage_timers(self) -> None:
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self._fire_replay_volley()

    def _fire_replay_volley(self) -> None:
        n = min(len(self.replay_log), MAX_REPLAY)
        if n == 0:
            n = 1
        px = self.player_x
        py = self.player_y
        base = math.atan2(py - self.boss_y, px - self.boss_x)
        speed = boss_projectile_speed(self.enrage_count)
        for i in range(n):
            angle = base + (i - (n - 1) / 2) * SPREAD
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            self.projectiles.append(
                Projectile(
                    x=self.boss_x,
                    y=self.boss_y,
                    vx=vx,
                    vy=vy,
                    radius=BOSS_SHOT_RADIUS,
                    kind="boss",
                    life=BOSS_SHOT_LIFE,
                )
            )
        self.replay_log.clear()
        self._spawn_particles(self.boss_x, self.boss_y, 12, CYAN)

    def _update_boss(self) -> None:
        self.boss_x += math.sin(self.frame * 0.02) * 0.4
        self.boss_y += math.cos(self.frame * 0.013) * 0.3
        self.boss_x = max(BOSS_RADIUS, min(WIDTH - BOSS_RADIUS, self.boss_x))
        self.boss_y = max(BOSS_RADIUS + 16, min(HEIGHT - BOSS_RADIUS - 10, self.boss_y))
        self.boss_fire_timer -= 1
        if self.boss_fire_timer <= 0:
            angle = math.atan2(self.player_y - self.boss_y, self.player_x - self.boss_x)
            speed = boss_projectile_speed(self.enrage_count)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            self.projectiles.append(
                Projectile(
                    x=self.boss_x,
                    y=self.boss_y,
                    vx=vx,
                    vy=vy,
                    radius=BOSS_SHOT_RADIUS,
                    kind="boss",
                    life=BOSS_SHOT_LIFE,
                )
            )
            self.boss_fire_timer = boss_fire_interval(self.rage, self.enrage_count)

    def _check_game_over(self) -> None:
        if self.boss_hp <= 0:
            self.victory = True
            self.score += 1000 + (GAME_DURATION - self.frame) + (500 if self.enrage_count == 0 else 0)
            self.defeat_reason = "VICTORY"
            self._spawn_particles(self.boss_x, self.boss_y, 40, LIME)
            self._finish()
            return
        if self.player_hp <= 0:
            self.defeat_reason = "DEFEATED"
            self._finish()
            return
        if self.frame >= GAME_DURATION:
            self.defeat_reason = "TIME UP"
            self._finish()
            return

    def _finish(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    def _update_particles(self) -> None:
        survivors: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survivors.append(p)
        self.particles = survivors
        survivor_f: list[Floater] = []
        for f in self.floaters:
            f.y -= 0.5
            f.life -= 1
            if f.life > 0:
                survivor_f.append(f)
        self.floaters = survivor_f

    def _advance(self) -> None:
        self.frame += 1
        self._update_boss()
        self._update_enrage_timers()
        self._update_rage()
        self._update_projectiles()
        self._check_player_hit()
        self._check_boss_hit()
        self._update_particles()
        self._check_game_over()

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase is Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
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
        self._update_player(dx, dy)
        if self.player_cooldown > 0:
            self.player_cooldown -= 1
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._fire_player()
        self._advance()

    def _apply_shake(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1
            try:
                pyxel.camera(self.rng.randint(-2, 2), self.rng.randint(-2, 2))
            except BaseException:
                pass
        else:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

    def _draw_title(self) -> None:
        pyxel.text(138, 80, "RAGE REPLAY", YELLOW)
        pyxel.text(76, 110, "The boss throws your", WHITE)
        pyxel.text(88, 122, "attacks back at you", WHITE)
        pyxel.text(90, 150, "ARROWS/WASD MOVE", LIGHT_BLUE)
        pyxel.text(108, 162, "SPACE FIRE", LIGHT_BLUE)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(92, 190, "PRESS SPACE TO START", LIME)

    def _draw_playing(self) -> None:
        pyxel.rectb(0, 0, WIDTH, HEIGHT, NAVY)

        # Rage meter (top)
        pyxel.rect(8, 6, 100, 8, GRAY)
        fill = int(max(0.0, min(100.0, self.rage)))
        mcolor = PINK if self.rage >= 80 else YELLOW
        if fill > 0:
            pyxel.rect(8, 6, fill, 8, mcolor)
        pyxel.rectb(8, 6, 100, 8, WHITE)
        pyxel.text(10, 18, "RAGE", WHITE)

        # Boss HP bar (top-left)
        pyxel.rect(120, 8, 120, 6, GRAY)
        bh = max(0, min(120, int(120 * self.boss_hp / BOSS_HP)))
        if bh > 0:
            pyxel.rect(120, 8, bh, 6, RED)
        pyxel.rectb(120, 8, 120, 6, WHITE)
        pyxel.text(120, 18, "BOSS", WHITE)

        # Hearts (top-right)
        for i in range(PLAYER_HP):
            color = LIME if self.player_hp > i else GRAY
            pyxel.rect(250 + i * 14, 6, 10, 10, color)

        # Score (top-center)
        score_text = "SCORE " + str(self.score)
        pyxel.text(160 - len(score_text) * 2, 0, score_text, YELLOW)

        # Timer bar (bottom)
        frac = max(0.0, (GAME_DURATION - self.frame) / GAME_DURATION)
        bar_w = int(frac * WIDTH)
        tcolor = LIME if frac > 0.5 else (YELLOW if frac > 0.25 else RED)
        if bar_w > 0:
            pyxel.rect(0, HEIGHT - 6, bar_w, 6, tcolor)

        # Replay-log track (small GRAY dots above the boss)
        n = min(len(self.replay_log), MAX_REPLAY)
        for i in range(n):
            px = self.boss_x - 24 + (i % 8) * 6
            py = self.boss_y - 30 - (i // 8) * 5
            pyxel.rect(int(px), int(py), 2, 2, GRAY)

        # Boss
        if self.invincible_timer > 0:
            body = ORANGE if (self.frame // 4) % 2 == 0 else PINK
            pyxel.circ(int(self.boss_x), int(self.boss_y), BOSS_RADIUS, body)
            pyxel.circb(int(self.boss_x), int(self.boss_y), BOSS_RADIUS, PINK)
        else:
            pyxel.circ(int(self.boss_x), int(self.boss_y), BOSS_RADIUS, RED)
            pyxel.circb(int(self.boss_x), int(self.boss_y), BOSS_RADIUS, NAVY)

        # Player
        pyxel.circ(int(self.player_x), int(self.player_y), PLAYER_RADIUS, DARK_BLUE)
        pyxel.circb(int(self.player_x), int(self.player_y), PLAYER_RADIUS, LIGHT_BLUE)
        dx = self.boss_x - self.player_x
        dy = self.boss_y - self.player_y
        d = math.hypot(dx, dy)
        if d > 0.0001:
            tx = self.player_x + dx / d * (PLAYER_RADIUS + 3)
            ty = self.player_y + dy / d * (PLAYER_RADIUS + 3)
            pyxel.rect(int(tx) - 1, int(ty) - 1, 3, 3, WHITE)

        # Projectiles
        for p in self.projectiles:
            color = WHITE if p.kind == "player" else CYAN
            pyxel.circ(int(p.x), int(p.y), p.radius, color)

        # Particles
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)

        # Floaters
        for f in self.floaters:
            pyxel.text(int(f.x) - len(f.text) * 2, int(f.y), f.text, f.color)

        self._apply_shake()

    def _draw_game_over(self) -> None:
        if self.victory:
            pyxel.text(146, 60, "VICTORY", LIME)
            pyxel.text(100, 76, "FLAWLESS! NO ENRAGE", PINK if self.enrage_count == 0 else BLACK)
        else:
            pyxel.text(120, 60, self.defeat_reason, RED)
        pyxel.text(104, 100, "SCORE " + str(self.score), WHITE)
        pyxel.text(104, 114, "BEST " + str(self.best_score), YELLOW)
        pyxel.text(84, 140, "ENRAGES " + str(self.enrage_count), GRAY)
        pyxel.text(104, 170, "SPACE = RETRY", LIME)

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase is Phase.TITLE:
            self._draw_title()
        elif self.phase is Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_playing()


def main() -> None:
    game = Game()

    def update() -> None:
        game.update()

    def draw() -> None:
        game.draw()

    pyxel.init(WIDTH, HEIGHT, title="RAGE REPLAY", display_scale=2, fps=60)
    pyxel.run(update, draw)


if __name__ == "__main__":
    main()
