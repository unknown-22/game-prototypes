"""YO SURGE — Top-down yo-yo skill toy game."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
import pyxel

# ============================================================
# Constants
# ============================================================
SCREEN_W = 320
SCREEN_H = 240
HAND_X = 160
HAND_Y = 24
COLLECT_RADIUS = 12
SUPER_COLLECT_RADIUS = 24
GEM_RADIUS = 4
YO_RADIUS = 6
HAND_RADIUS = 5
MAX_HEAT: float = 15.0
HEAT_DECAY: float = 0.5  # per second (normal)
SUPER_HEAT_DECAY: float = 1.0  # per second (SUPER)
SUPER_DURATION: int = 300  # frames (5 seconds)
GAME_DURATION: int = 3600  # frames (60 seconds)
INITIAL_SPAWN_INTERVAL: int = 45
MIN_SPAWN_INTERVAL: int = 15
SPAWN_INTERVAL_DECREASE: int = 5
DIFFICULTY_INTERVAL: int = 600  # frames (10 seconds)
MARGIN: int = 20
LERP_FACTOR: float = 0.15
SHAKE_FRAMES: int = 5

GEM_COLORS: tuple[int, ...] = (8, 3, 6, 10)  # RED, GREEN, LIGHT_BLUE, YELLOW

# ============================================================
# Enums
# ============================================================
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ============================================================
# Data Classes
# ============================================================
@dataclass
class Gem:
    x: float
    y: float
    color: int
    speed: float


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


# ============================================================
# Game
# ============================================================
class Game:
    """Top-down yo-yo skill toy game. Catch falling gems to build combos."""

    # Pre-initialized state (required for Game.__new__ bypass in tests)
    phase: Phase = Phase.TITLE
    score: int = 0
    high_score: int = 0
    combo: int = 0
    max_combo: int = 0
    yo_x: float = 160.0
    yo_y: float = 60.0
    yo_color: int = 8  # RED
    heat: float = 0.0
    super_timer: int = 0
    game_timer: int = GAME_DURATION
    spawn_timer: int = 0
    spawn_interval: int = INITIAL_SPAWN_INTERVAL
    gems: list[Gem] = []
    particles: list[Particle] = []
    floating_texts: list[FloatingText] = []
    shake_frames: int = 0
    elapsed_frames: int = 0
    _hand_x: int = HAND_X
    _hand_y: int = HAND_Y
    _title_swing: float = 0.0
    _title_spawn_timer: int = 0
    _title_gems: list[Gem] = []

    def __init__(self) -> None:
        self.gems = []
        self.particles = []
        self.floating_texts = []
        self._title_gems = []
        pyxel.init(SCREEN_W, SCREEN_H, title="YO SURGE", display_scale=2, fps=60)
        pyxel.run(self.update, self.draw)

    # ============================================================
    # Main Loop
    # ============================================================
    def update(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1
            pyxel.camera(random.randint(-2, 2), random.randint(-2, 2))
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(0)  # BLACK background
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ============================================================
    # Phase Updates
    # ============================================================
    def _update_title(self) -> None:
        self._title_swing += 0.05
        self._title_spawn_timer -= 1
        if self._title_spawn_timer <= 0:
            self._title_spawn_timer = 45
            x = random.uniform(MARGIN, SCREEN_W - MARGIN)
            color = random.choice(GEM_COLORS)
            speed = random.uniform(60, 120) / 60.0
            self._title_gems.append(Gem(x=x, y=-4.0, color=color, speed=speed))

        for gem in self._title_gems:
            gem.y += gem.speed
        self._title_gems = [g for g in self._title_gems if g.y <= SCREEN_H + 4]

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.elapsed_frames += 1
        self._update_yo(pyxel.mouse_x, pyxel.mouse_y)

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_gems()
            self.spawn_timer = self.spawn_interval

        self._update_gems()
        self._check_collection()
        self._update_super()
        self._update_heat_decay()
        self._update_particles()
        self._update_floating_texts()
        self._update_game_timer()
        self._update_difficulty()

        if self.phase == Phase.PLAYING and self.heat >= MAX_HEAT:
            self._trigger_game_over()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    # ============================================================
    # Phase Draws
    # ============================================================
    def _draw_title(self) -> None:
        # Background falling gems
        for gem in self._title_gems:
            px, py = int(gem.x), int(gem.y)
            pyxel.circ(px, py, GEM_RADIUS, gem.color)
            pyxel.circb(px, py, GEM_RADIUS, 7)
            pyxel.pset(px - 1, py - 1, 7)

        # Dangling yo-yo
        swing_x = HAND_X + math.sin(self._title_swing) * 30.0
        swing_y = 60.0 + math.cos(self._title_swing * 2.0) * 10.0

        pyxel.line(HAND_X, HAND_Y, int(swing_x), int(swing_y), 7)
        pyxel.circ(HAND_X, HAND_Y, HAND_RADIUS, 7)
        pyxel.circ(int(swing_x), int(swing_y), YO_RADIUS, 8)
        pyxel.circb(int(swing_x), int(swing_y), YO_RADIUS + 1, 7)

        # Title
        title = "YO SURGE"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 90, title, 7)

        # Instructions
        inst = "CLICK OR SPACE TO START"
        pyxel.text(SCREEN_W // 2 - len(inst) * 2, 130, inst, 7)

        # High score
        if self.high_score > 0:
            hs = f"HIGH SCORE: {self.high_score}"
            pyxel.text(SCREEN_W // 2 - len(hs) * 2, 150, hs, 10)

    def _draw_playing(self) -> None:
        is_super = self._is_super()
        rainbow_idx = pyxel.frame_count % len(GEM_COLORS)

        # ===== Gems =====
        for gem in self.gems:
            px, py = int(gem.x), int(gem.y)
            pyxel.circ(px, py, GEM_RADIUS, gem.color)
            pyxel.circb(px, py, GEM_RADIUS, 7)
            pyxel.pset(px - 1, py - 1, 7)

        # ===== Particles =====
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # ===== String =====
        string_color = GEM_COLORS[rainbow_idx] if is_super else 7
        pyxel.line(self._hand_x, self._hand_y, int(self.yo_x), int(self.yo_y), string_color)

        # ===== Hand =====
        pyxel.circ(self._hand_x, self._hand_y, HAND_RADIUS, 7)

        # ===== Yo-yo =====
        yo_color = GEM_COLORS[rainbow_idx] if is_super else self.yo_color
        pyxel.circ(int(self.yo_x), int(self.yo_y), YO_RADIUS, yo_color)
        pyxel.circb(int(self.yo_x), int(self.yo_y), YO_RADIUS + 1, 7)

        # ===== Floating Texts =====
        for ft in self.floating_texts:
            tx = int(ft.x) - len(ft.text) * 2
            pyxel.text(tx, int(ft.y), ft.text, ft.color)

        # ===== HUD =====
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)

        combo_text = f"COMBO: {self.combo}"
        pyxel.text(SCREEN_W - len(combo_text) * 4 - 4, 4, combo_text, 7)

        timer_text = f"TIME: {max(0, self.game_timer // 60)}"
        pyxel.text(SCREEN_W // 2 - len(timer_text) * 2, 4, timer_text, 7)

        if is_super:
            super_color = GEM_COLORS[rainbow_idx]
            pyxel.text(SCREEN_W - 44, 14, "SUPER!", super_color)

        # ===== HEAT Bar =====
        bar_w = 100
        bar_h = 6
        bar_x = (SCREEN_W - bar_w) // 2
        bar_y = SCREEN_H - 12
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 13)  # GRAY background

        heat_ratio = min(1.0, self.heat / MAX_HEAT)
        fill_w = int(bar_w * heat_ratio)
        if fill_w > 0:
            if heat_ratio < 0.5:
                heat_color = 3  # GREEN
            elif heat_ratio < 0.75:
                heat_color = 10  # YELLOW
            else:
                heat_color = 8  # RED
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_color)

        label = "HEAT"
        pyxel.text(bar_x - 22, bar_y - 1, label, 7)

    def _draw_game_over(self) -> None:
        go_text = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go_text) * 2, 70, go_text, 8)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 95, score_text, 7)

        if self.score >= self.high_score > 0:
            nhs = "NEW HIGH SCORE!"
            pyxel.text(SCREEN_W // 2 - len(nhs) * 2, 115, nhs, 10)
        elif self.high_score > 0:
            hs = f"HIGH SCORE: {self.high_score}"
            pyxel.text(SCREEN_W // 2 - len(hs) * 2, 115, hs, 7)

        max_combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(max_combo_text) * 2, 130, max_combo_text, 7)

        inst = "CLICK OR SPACE TO RETRY"
        pyxel.text(SCREEN_W // 2 - len(inst) * 2, 160, inst, 7)

    # ============================================================
    # Game Logic (Testable — no pyxel input calls)
    # ============================================================
    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.yo_x = 160.0
        self.yo_y = 60.0
        self.yo_color = 8  # RED
        self.heat = 0.0
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.spawn_timer = INITIAL_SPAWN_INTERVAL
        self.spawn_interval = INITIAL_SPAWN_INTERVAL
        self.gems.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self.elapsed_frames = 0
        self._title_swing = 0.0
        self._title_spawn_timer = 0
        self._title_gems.clear()

    def _trigger_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        self.shake_frames = SHAKE_FRAMES
        if self.score > self.high_score:
            self.high_score = self.score

    def _update_yo(self, mouse_x: int, mouse_y: int) -> None:
        target_x = max(10.0, min(310.0, float(mouse_x)))
        target_y = max(30.0, min(230.0, float(mouse_y)))
        self.yo_x += (target_x - self.yo_x) * LERP_FACTOR
        self.yo_y += (target_y - self.yo_y) * LERP_FACTOR

    def _spawn_gems(self) -> None:
        x = random.uniform(MARGIN, SCREEN_W - MARGIN)
        color = random.choice(GEM_COLORS)
        speed = random.uniform(60, 120) / 60.0
        self.gems.append(Gem(x=x, y=-4.0, color=color, speed=speed))

    def _update_gems(self) -> None:
        for gem in self.gems:
            gem.y += gem.speed

        missed: list[Gem] = [g for g in self.gems if g.y > SCREEN_H + 4]
        for gem in missed:
            self.gems.remove(gem)
            if not self._is_super():
                self.heat += 1.0
                for _ in range(random.randint(4, 6)):
                    self.particles.append(
                        Particle(
                            x=gem.x,
                            y=float(SCREEN_H),
                            vx=random.uniform(-1, 1),
                            vy=random.uniform(-2, 0),
                            life=random.randint(10, 20),
                            color=13,
                        )
                    )

    def _check_collection(self) -> None:
        collect_radius = SUPER_COLLECT_RADIUS if self._is_super() else COLLECT_RADIUS
        collected: list[Gem] = []
        for gem in self.gems:
            if math.hypot(gem.x - self.yo_x, gem.y - self.yo_y) <= collect_radius:
                collected.append(gem)

        for gem in collected:
            self.gems.remove(gem)
            is_super = self._is_super()

            if is_super or gem.color == self.yo_color:
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                score_val = self._score_for_gem(gem.color)
                self.score += score_val

                ft_text = f"x3 +{score_val}" if is_super else f"+{score_val}"
                ft_color = GEM_COLORS[random.randint(0, 3)] if is_super else 7
                self.floating_texts.append(
                    FloatingText(x=gem.x, y=gem.y, text=ft_text, life=30, color=ft_color)
                )

                particle_count = random.randint(12, 16) if is_super else random.randint(8, 12)
                self._spawn_collect_particles(gem.x, gem.y, gem.color, particle_count)

                if self.combo >= 4:
                    self._activate_super()
            else:
                self.combo = 0
                self.yo_color = gem.color
                if not is_super:
                    self.heat += 0.5
                for _ in range(random.randint(4, 6)):
                    self.particles.append(
                        Particle(
                            x=gem.x,
                            y=gem.y,
                            vx=random.uniform(-1.5, 1.5),
                            vy=random.uniform(-1.5, 1.5),
                            life=random.randint(8, 15),
                            color=gem.color,
                        )
                    )

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.shake_frames = SHAKE_FRAMES
        self.combo = 0
        burst_count = random.randint(30, 40)
        for _ in range(burst_count):
            color = random.choice(GEM_COLORS)
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.randint(20, 40)
            self.particles.append(
                Particle(x=self.yo_x, y=self.yo_y, vx=vx, vy=vy, life=life, color=color)
            )

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_heat_decay(self) -> None:
        rate = SUPER_HEAT_DECAY if self._is_super() else HEAT_DECAY
        self.heat -= rate / 60.0
        if self.heat < 0.0:
            self.heat = 0.0

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _score_for_gem(self, color: int) -> int:
        multiplier = 300 if self._is_super() else 100
        return multiplier * self.combo

    def _spawn_collect_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 3)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.randint(15, 25)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color)
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_game_timer(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self._trigger_game_over()

    def _update_difficulty(self) -> None:
        if self.elapsed_frames > 0 and self.elapsed_frames % DIFFICULTY_INTERVAL == 0:
            self.spawn_interval = max(MIN_SPAWN_INTERVAL, self.spawn_interval - SPAWN_INTERVAL_DECREASE)


# ============================================================
# Entry Point
# ============================================================
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
