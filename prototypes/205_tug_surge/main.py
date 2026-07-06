from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


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
    vy: float = -1.0


@dataclass
class EchoGhost:
    rope_pos: float
    life: int
    color: int


COLORS = (8, 3, 5, 10)
COLOR_NAMES = ("RED", "GREEN", "BLUE", "YELLOW")


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    ROPE_Y = 140
    ROPE_START_X = 160
    ROPE_THICKNESS = 6
    LEFT_LOSE_X = 60
    RIGHT_WIN_X = 260
    CENTER_FLAG_SIZE = 8
    GAME_TIME = 60 * 60
    COLOR_CYCLE_FRAMES = 120
    SUPER_TUG_DURATION = 300
    SUPER_TUG_COMBO = 4
    PULL_COOLDOWN = 15
    PULL_STRENGTH_BASE = 0.5
    PULL_STRENGTH_COMBO = 0.3
    PULL_STRENGTH_SUPER = 3.0
    AI_PULL_MIN = 0.3
    AI_PULL_MAX = 0.8
    IDLE_THRESHOLD = 120
    HEAT_MAX = 100.0
    HEAT_WRONG = 15.0
    HEAT_PULL = 2.0
    HEAT_DECAY_IDLE = 0.05
    HEAT_DECAY_SUPER = 0.1
    SCORE_BASE = 10
    SCORE_SUPER_MULTIPLIER = 3
    VICTORY_BONUS = 1000
    MAX_PARTICLES = 200
    MAX_ECHOS = 20
    MAX_FLOATING_TEXTS = 30
    GHOST_LIFE = 120
    GHOST_PULL_BONUS = 0.1

    def __init__(self) -> None:
        font_path = Path(__file__).with_name("k8x12.bdf")
        if font_path.exists():
            pyxel.load(str(font_path))
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="TUG SURGE", display_scale=2)
        self._rng = random.Random(42)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat: float = 0.0
        self.timer = self.GAME_TIME
        self.super_tug_active = False
        self.super_tug_timer = 0
        self.rope_center: float = float(self.ROPE_START_X)
        self.current_flag_color_idx = 0
        self.flag_color_timer = 0
        self.resonance_color_idx: int | None = None
        self.pull_cooldown = 0
        self.ai_pull_force = 0.5
        self.ai_force_timer = 0
        self.idle_frames = 0
        self.won = False
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.echo_ghosts: list[EchoGhost] = []
        self._rng = random.Random(42)
        self._elapsed_time = 0.0

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.GAME_TIME
        self.super_tug_active = False
        self.super_tug_timer = 0
        self.rope_center = float(self.ROPE_START_X)
        self.current_flag_color_idx = 0
        self.flag_color_timer = 0
        self.resonance_color_idx = None
        self.pull_cooldown = 0
        self.ai_pull_force = 0.5
        self.ai_force_timer = 0
        self.idle_frames = 0
        self.won = False
        self.particles.clear()
        self.floating_texts.clear()
        self.echo_ghosts.clear()
        self._rng = random.Random(42)
        self._elapsed_time = 0.0

    def _pull(self) -> tuple[bool, int]:
        """Returns (combo_increased: bool, score_gained: int)"""
        if self.pull_cooldown > 0:
            return False, 0

        self.pull_cooldown = self.PULL_COOLDOWN
        self.idle_frames = 0

        flag_color = self.current_flag_color_idx

        if self.super_tug_active:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            points = int(self.SCORE_BASE * self.SCORE_SUPER_MULTIPLIER * (1 + self.combo * 0.3))
            self.score += points
            self._spawn_super_tug_particles()
            self._add_floating_text(
                self.rope_center, self.ROPE_Y - 20,
                f"+{points}", COLORS[flag_color],
            )
            return True, points

        self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_PULL)

        if self.resonance_color_idx is None:
            self.resonance_color_idx = flag_color
            self._spawn_pull_particles()
            return False, 0

        if flag_color == self.resonance_color_idx:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            points = int(self.SCORE_BASE * (1 + self.combo * 0.5))
            self.score += points
            self._spawn_pull_particles()
            if self.combo >= 2:
                self._add_floating_text(
                    self.rope_center, self.ROPE_Y - 32,
                    f"COMBO x{self.combo}", 10 if self.combo >= self.SUPER_TUG_COMBO else 7,
                )
            self._add_floating_text(
                self.rope_center, self.ROPE_Y - 16,
                f"+{points}", COLORS[flag_color],
            )
            self.echo_ghosts.append(
                EchoGhost(
                    rope_pos=self.rope_center,
                    life=self.GHOST_LIFE,
                    color=COLORS[flag_color],
                )
            )
            self.resonance_color_idx = flag_color
            if self.combo >= self.SUPER_TUG_COMBO:
                self._activate_super_tug()
            return True, points
        else:
            prev_combo = self.combo
            self.combo = 0
            self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_WRONG)
            self._spawn_pull_particles()
            if prev_combo > 0:
                self._add_floating_text(
                    self.rope_center, self.ROPE_Y - 16,
                    "WRONG!", 8,
                )
            self.resonance_color_idx = flag_color
            return False, 0

    def _update_rope(self, dt: float) -> None:
        pull_strength = self.PULL_STRENGTH_BASE + self.combo * self.PULL_STRENGTH_COMBO
        if self.super_tug_active:
            pull_strength = self.PULL_STRENGTH_SUPER

        ghost_bonus = min(len(self.echo_ghosts), self.MAX_ECHOS) * self.GHOST_PULL_BONUS
        pull_strength += ghost_bonus

        net_force = pull_strength - self.ai_pull_force
        self.rope_center += net_force * dt

        if self.rope_center < self.LEFT_LOSE_X:
            self.rope_center = float(self.LEFT_LOSE_X)
        elif self.rope_center > self.RIGHT_WIN_X:
            self.rope_center = float(self.RIGHT_WIN_X)

    def _update_ai(self) -> None:
        self.ai_force_timer -= 1
        if self.ai_force_timer <= 0:
            base = self.AI_PULL_MIN + self._elapsed_time * 0.02 / 10.0
            if self._elapsed_time > 30:
                base += 0.1
            max_force = min(self.AI_PULL_MAX + self._elapsed_time * 0.005, 1.2)
            self.ai_pull_force = self._rng.uniform(base, max_force)
            self.ai_force_timer = self._rng.randint(60, 180)

    def _update_flag_color(self) -> None:
        self.flag_color_timer -= 1
        if self.flag_color_timer <= 0:
            cycle_speed = max(80, self.COLOR_CYCLE_FRAMES - int(self._elapsed_time * 0.66))
            self.current_flag_color_idx = (self.current_flag_color_idx + 1) % len(COLORS)
            self.flag_color_timer = cycle_speed

    def _update_heat(self) -> None:
        if self.super_tug_active:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY_SUPER)
        elif self.idle_frames > self.IDLE_THRESHOLD:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY_IDLE)

    def _update_super_tug(self) -> None:
        if self.super_tug_active:
            self.super_tug_timer -= 1
            if self.super_tug_timer <= 0:
                self.super_tug_active = False
                self.super_tug_timer = 0

    def _activate_super_tug(self) -> None:
        self.super_tug_active = True
        self.super_tug_timer = self.SUPER_TUG_DURATION
        self._add_floating_text(
            self.rope_center, self.ROPE_Y - 40,
            "SUPER TUG!", 10,
        )
        self._spawn_super_tug_activate_particles()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]
        while len(self.particles) > self.MAX_PARTICLES:
            self.particles.pop(0)

    def _update_echos(self) -> None:
        for g in self.echo_ghosts:
            g.life -= 1
        self.echo_ghosts = [g for g in self.echo_ghosts if g.life > 0]
        while len(self.echo_ghosts) > self.MAX_ECHOS:
            self.echo_ghosts.pop(0)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]
        while len(self.floating_texts) > self.MAX_FLOATING_TEXTS:
            self.floating_texts.pop(0)

    def _check_win_lose(self) -> bool:
        """Returns True if game should end."""
        if self.rope_center >= self.RIGHT_WIN_X:
            self.phase = Phase.GAME_OVER
            self.won = True
            self.score += int(self.rope_center * 2)
            self.score += self.VICTORY_BONUS
            return True
        if self.rope_center <= self.LEFT_LOSE_X:
            self.phase = Phase.GAME_OVER
            self.won = False
            self.score += int(self.rope_center * 2)
            return True
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.won = False
            self.score += int(self.rope_center * 2)
            return True
        return False

    def _spawn_pull_particles(self) -> None:
        cx = self.rope_center
        cy = float(self.ROPE_Y)
        color = COLORS[self.current_flag_color_idx]
        for _ in range(8):
            angle = self._rng.uniform(-0.8, 0.8)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=cx,
                    y=cy,
                    vx=pyxel.cos(angle) * speed + 2.0,
                    vy=pyxel.sin(angle) * speed,
                    life=self._rng.randint(12, 25),
                    color=color,
                    size=2,
                )
            )

    def _spawn_combo_particles(self) -> None:
        cx = self.rope_center
        cy = float(self.ROPE_Y)
        for _ in range(15):
            angle = self._rng.uniform(0, 6.283185307179586)
            speed = self._rng.uniform(2.0, 4.0)
            color = COLORS[self._rng.randrange(len(COLORS))]
            self.particles.append(
                Particle(
                    x=cx,
                    y=cy,
                    vx=pyxel.cos(angle) * speed,
                    vy=pyxel.sin(angle) * speed,
                    life=self._rng.randint(15, 35),
                    color=color,
                    size=2,
                )
            )

    def _spawn_super_tug_particles(self) -> None:
        cx = self.rope_center
        cy = float(self.ROPE_Y)
        for _ in range(20):
            angle = self._rng.uniform(-0.6, 0.6)
            speed = self._rng.uniform(2.0, 5.0)
            color = COLORS[self._rng.randrange(len(COLORS))]
            self.particles.append(
                Particle(
                    x=cx,
                    y=cy,
                    vx=pyxel.cos(angle) * speed + 3.0,
                    vy=pyxel.sin(angle) * speed,
                    life=self._rng.randint(20, 40),
                    color=color,
                    size=2,
                )
            )

    def _spawn_super_tug_activate_particles(self) -> None:
        cx = self.rope_center
        cy = float(self.ROPE_Y)
        for _ in range(40):
            angle = self._rng.uniform(0, 6.283185307179586)
            speed = self._rng.uniform(3.0, 6.0)
            color = COLORS[self._rng.randrange(len(COLORS))]
            self.particles.append(
                Particle(
                    x=cx,
                    y=cy,
                    vx=pyxel.cos(angle) * speed,
                    vy=pyxel.sin(angle) * speed,
                    life=self._rng.randint(25, 50),
                    color=color,
                    size=2,
                )
            )

    def _add_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=45, color=color, vy=-1.0)
        )

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_end_screen()

        self._update_particles()
        self._update_floating_texts()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._start_game()

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_D) or pyxel.btnp(pyxel.KEY_RIGHT):
            self._pull()
        elif pyxel.btnp(pyxel.KEY_A) or pyxel.btnp(pyxel.KEY_LEFT):
            pass

        dt = 1.0
        if not self.super_tug_active:
            self._update_rope(dt)
        else:
            pull_strength = self.PULL_STRENGTH_SUPER
            ghost_bonus = min(len(self.echo_ghosts), self.MAX_ECHOS) * self.GHOST_PULL_BONUS
            net_force = pull_strength + ghost_bonus - self.ai_pull_force
            self.rope_center += net_force * dt

        if self.rope_center < self.LEFT_LOSE_X:
            self.rope_center = float(self.LEFT_LOSE_X)
        elif self.rope_center > self.RIGHT_WIN_X:
            self.rope_center = float(self.RIGHT_WIN_X)

        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            self.won = False
            self.score += int(self.rope_center * 2)
            return

        if self.pull_cooldown > 0:
            self.pull_cooldown -= 1

        self.idle_frames += 1
        self._elapsed_time += 1.0 / 60.0

        self._update_ai()
        self._update_flag_color()
        self._update_heat()
        self._update_super_tug()
        self._update_echos()

        if self._check_win_lose():
            return

    def _update_end_screen(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self._start_game()
        if pyxel.btnp(pyxel.KEY_T):
            self.reset()
            self.phase = Phase.TITLE

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        self._draw_particles()
        self._draw_floating_texts()

    def _draw_title(self) -> None:
        pyxel.cls(1)
        cx = self.SCREEN_W // 2
        pyxel.text(cx - 30, 30, "TUG SURGE", 7)

        instructions = [
            ("Pull the rope!", 7),
            ("Match colors for COMBO!", 7),
            ("SPACE / D / RIGHT to pull", 7),
            ("Same color = COMBO UP", 10),
            ("Wrong color = HEAT UP!", 8),
            ("COMBO x4 = SUPER TUG!", 10),
        ]
        for i, (text, col) in enumerate(instructions):
            pyxel.text(cx - len(text) * 2, 70 + i * 14, text, col)

        anim_offset = pyxel.sin(pyxel.frame_count * 0.08) * 20
        rope_x = int(self.ROPE_START_X + anim_offset)
        pyxel.rect(
            rope_x - 40, self.ROPE_Y + 40 - 3,
            80, 6, 7,
        )
        for i, c in enumerate(COLORS):
            pyxel.rect(rope_x - 40 + i * 20, self.ROPE_Y + 40 - 3, 20, 6, c)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(cx - 48, 200, "Press SPACE to start", 10)

    def _draw_playing(self) -> None:
        pyxel.cls(0)

        self._draw_arena()
        self._draw_rope()
        self._draw_echo_ghosts()
        self._draw_center_flag()
        self._draw_pull_indicators()
        self._draw_hud()

        if self.super_tug_active:
            hue = (pyxel.frame_count // 4) % 16
            pyxel.rectb(0, 0, self.SCREEN_W, self.SCREEN_H, hue)
            sec = self.super_tug_timer // 60
            pyxel.text(self.SCREEN_W // 2 - 30, 24, f"SUPER TUG {sec}s", 10)

    def _draw_arena(self) -> None:
        pyxel.rect(0, self.ROPE_Y - 30, self.SCREEN_W, 90, 1)
        pyxel.rect(0, self.ROPE_Y - 30, self.SCREEN_W, 2, 6)
        pyxel.rect(0, self.ROPE_Y + 58, self.SCREEN_W, 2, 6)

        pyxel.text(4, self.ROPE_Y - 20, "YOU", 7)
        pyxel.text(self.SCREEN_W - 24, self.ROPE_Y - 20, "CPU", 7)

    def _draw_rope(self) -> None:
        rope_y = self.ROPE_Y
        segment_count = 16
        segment_width = self.SCREEN_W // segment_count

        for i in range(segment_count):
            seg_x = i * segment_width
            color_idx = (i + self.current_flag_color_idx) % len(COLORS)
            pyxel.rect(
                seg_x, rope_y - self.ROPE_THICKNESS // 2,
                segment_width, self.ROPE_THICKNESS, COLORS[color_idx],
            )

    def _draw_center_flag(self) -> None:
        cx = int(self.rope_center)
        cy = self.ROPE_Y
        flag_color = COLORS[self.current_flag_color_idx]

        if self.super_tug_active:
            flag_color = (pyxel.frame_count // 4) % 16

        pyxel.pal(6, flag_color + 8 if flag_color < 8 else flag_color)
        pyxel.tri(
            cx, cy - self.CENTER_FLAG_SIZE - 2,
            cx - 6, cy - self.CENTER_FLAG_SIZE + 6,
            cx + 6, cy - self.CENTER_FLAG_SIZE + 6,
            7,
        )
        pyxel.pal()

    def _draw_echo_ghosts(self) -> None:
        for ghost in self.echo_ghosts:
            alpha = ghost.life / self.GHOST_LIFE
            if alpha < 0.15:
                continue
            gx = int(ghost.rope_pos)
            gy = self.ROPE_Y

            col = ghost.color
            if alpha < 0.4:
                col = 5

            pyxel.rectb(
                gx - 8, gy - 10,
                16, 20, col,
            )

    def _draw_pull_indicators(self) -> None:
        center = int(self.rope_center)
        left_fill = center
        right_fill = self.SCREEN_W - center

        if left_fill > 0:
            pyxel.rect(0, self.ROPE_Y - 1, left_fill, 2, 6)
        if right_fill > 0:
            pyxel.rect(center, self.ROPE_Y + 3, right_fill, 2, 6)

        pyxel.line(self.LEFT_LOSE_X, self.ROPE_Y - 20, self.LEFT_LOSE_X, self.ROPE_Y + 20, 8)
        pyxel.line(self.RIGHT_WIN_X, self.ROPE_Y - 20, self.RIGHT_WIN_X, self.ROPE_Y + 20, 3)

    def _draw_hud(self) -> None:
        seconds = self.timer // 60
        minutes = seconds // 60
        sec_remainder = seconds % 60
        pyxel.text(4, 4, f"TIME {minutes}:{sec_remainder:02d}", 7)

        pyxel.text(self.SCREEN_W // 2 - 24, 4, f"SCORE {self.score}", 7)

        combo_color = 10 if self.combo >= self.SUPER_TUG_COMBO else 7
        pyxel.text(self.SCREEN_W - 72, 4, f"COMBO {self.combo}", combo_color)

        bar_x = 4
        bar_y = 16
        bar_w = 80
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        fill = min(int(self.heat / self.HEAT_MAX * (bar_w - 2)), bar_w - 2)
        if self.heat > 60:
            bar_color = 8
        elif self.heat > 30:
            bar_color = 10
        else:
            bar_color = 3
        pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, bar_color)
        pyxel.text(bar_x, bar_y + 8, f"HEAT {int(self.heat)}", 7)

    def _draw_game_over(self) -> None:
        pyxel.cls(0)
        cx = self.SCREEN_W // 2

        if self.won:
            pyxel.cls(3)
            pyxel.text(cx - 40, 30, "YOU WIN!", 7)
        else:
            pyxel.cls(1)
            pyxel.text(cx - 36, 30, "GAME OVER", 7)

        pyxel.text(cx - 40, 70, f"SCORE: {self.score}", 7)
        pyxel.text(
            cx - 40, 90,
            f"Pull Distance: {int(self.rope_center)}", 7,
        )
        pyxel.text(
            cx - 40, 110,
            f"Max Combo: {self.max_combo}", 7,
        )

        if not self.won:
            if self.heat >= self.HEAT_MAX:
                pyxel.text(cx - 32, 130, "EXHAUSTED!", 8)
            elif self.timer <= 0:
                pyxel.text(cx - 24, 130, "TIME UP!", 10)
            elif self.rope_center <= self.LEFT_LOSE_X:
                pyxel.text(cx - 32, 130, "PULLED OVER!", 8)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(cx - 50, 200, "R: Retry  T: Title", 10)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 40
            if alpha > 0.5:
                pyxel.rect(
                    int(p.x) - 1, int(p.y) - 1,
                    p.size + 1, p.size + 1, p.color,
                )
            elif alpha > 0.2:
                pyxel.rect(
                    int(p.x), int(p.y),
                    p.size, p.size, p.color,
                )
            else:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 45
            if alpha <= 0:
                continue
            col = ft.color
            if alpha < 0.25:
                col = 5
            pyxel.text(
                int(ft.x) - len(ft.text) * 2,
                int(ft.y),
                ft.text,
                col,
            )


if __name__ == "__main__":
    Game()
