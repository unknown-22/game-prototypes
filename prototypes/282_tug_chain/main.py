"""TUG CHAIN — Color-Match Tug of War Prototype.

Core fun moment: timing a perfect pull when your color matches the rope
segment — then chaining multiple same-color pulls for a SUPER PULL that
yanks the opponent across the line in one dramatic tug.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GAME_DURATION = 60 * FPS  # 60 seconds at 30fps

PLAYER_COLORS: tuple[int, int, int, int] = (
    pyxel.COLOR_RED,
    pyxel.COLOR_LIME,
    pyxel.COLOR_DARK_BLUE,
    pyxel.COLOR_YELLOW,
)
NUM_COLORS = 4

SEGMENT_WIDTH = 24
SEGMENT_HEIGHT = 12
SEGMENT_COUNT = 12
PLAYER_X = 40
AI_X = 280
ROPE_Y = 120
CENTER_X = 160
CENTER_Y = 110
GROUND_Y = 140
ACTIVE_MARGIN = 12

SUPER_COMBO_THRESHOLD = 4  # combo >= 4 activates SUPER MODE
SUPER_DURATION = 300  # frames (10 seconds)

HEAT_WRONG = 15
HEAT_PASSIVE = 0.02
HEAT_AI_SUCCESS = 1
HEAT_COOL_PLAYER = -5
HEAT_COOL_SUPER = -0.05
HEAT_MAX = 100
HEAT_WARN = 70
HEAT_DANGER = 90

PULL_FORCE_BASE = 2.0
PULL_FORCE_COMBO = 0.5
AI_PULL_FORCE_BASE = 1.5
AI_PULL_VARIATION = 1.0
AI_PULL_INTERVAL_MIN = 30
AI_PULL_INTERVAL_MAX = 60

WIN_THRESHOLD = -80
LOSE_THRESHOLD = 80


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SUPER_ANIM = auto()
    VICTORY = auto()
    DEFEAT = auto()
    GAME_OVER = auto()


@dataclass(slots=True)
class Segment:
    x: float
    color: int
    width: int = SEGMENT_WIDTH
    height: int = SEGMENT_HEIGHT


@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass(slots=True)
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float = -1.0


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="TUG CHAIN", fps=FPS, display_scale=2)
        self._rng = random.Random()
        self.best_score = 0
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.player_color = 0
        self.rope_position = 0.0
        self.segments: list[Segment] = []
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.score = 0
        self.timer = GAME_DURATION
        self.ai_pull_timer = random.randint(AI_PULL_INTERVAL_MIN, AI_PULL_INTERVAL_MAX)
        self.ai_pull_target = 0
        self.super_mode = False
        self.super_timer = 0
        self.shake_frames = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.rope_speed = 0.8
        self.spawn_timer = 0
        self.last_color = -1
        self.ai_last_color = -1
        self.just_pulled = False
        self.ai_just_pulled = False
        self.super_anim_timer = 0

        self._init_segments()

    def _init_segments(self) -> None:
        self.segments.clear()
        start_x = CENTER_X - SEGMENT_WIDTH * SEGMENT_COUNT // 2
        for i in range(SEGMENT_COUNT):
            self.segments.append(
                Segment(x=start_x + i * SEGMENT_WIDTH, color=self._rng.randint(0, NUM_COLORS - 1))
            )

    def reset(self) -> None:
        self._init_state()

    # ── Segment Logic ────────────────────────────────────────────────────

    def _update_segments(self) -> None:
        for seg in self.segments:
            seg.x -= self.rope_speed

        while self.segments and self.segments[0].x < SEGMENT_WIDTH:
            del self.segments[0]

        right_edge = self.segments[-1].x + SEGMENT_WIDTH if self.segments else 0
        while right_edge <= SCREEN_W + SEGMENT_WIDTH:
            new_color = self._rng.randint(0, NUM_COLORS - 1)
            self.segments.append(Segment(x=right_edge, color=new_color))
            right_edge += SEGMENT_WIDTH

    def _find_active_segment(self) -> Segment | None:
        best_seg: Segment | None = None
        best_dist = float("inf")
        for seg in self.segments:
            seg_center = seg.x + SEGMENT_WIDTH // 2 + self.rope_position
            dist = abs(seg_center - CENTER_X)
            if dist < ACTIVE_MARGIN and dist < best_dist:
                best_dist = dist
                best_seg = seg
        return best_seg

    # ── Player Pull ──────────────────────────────────────────────────────

    def _player_pull(self) -> str:
        """Returns 'success', 'miss', or 'none'."""
        active = self._find_active_segment()
        if active is None:
            return "none"

        if self.super_mode or active.color == self.player_color:
            self._on_pull_success(active)
            return "success"
        else:
            self._on_pull_fail(active)
            return "miss"

    def _on_pull_success(self, seg: Segment) -> None:
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        pull_force = PULL_FORCE_BASE + self.combo * PULL_FORCE_COMBO
        if self.super_mode:
            pull_force *= 2
        self.rope_position -= pull_force
        score_gain = 10 * max(1, self.combo) * (3 if self.super_mode else 1)
        self.score += score_gain
        if not self.super_mode:
            self.player_color = (self.player_color + 1) % NUM_COLORS
        self.heat = max(0, self.heat + HEAT_COOL_PLAYER)
        self.last_color = seg.color

        pull_x = seg.x + self.rope_position + SEGMENT_WIDTH // 2
        self._spawn_particles(pull_x, ROPE_Y, seg.color, 8)
        self._spawn_floating_text(pull_x, ROPE_Y - 8, f"+{score_gain}", pyxel.COLOR_WHITE)

        if self.combo >= SUPER_COMBO_THRESHOLD and not self.super_mode:
            self._activate_super_mode()

    def _on_pull_fail(self, seg: Segment) -> None:
        self.combo = 0
        self.heat = min(HEAT_MAX, self.heat + HEAT_WRONG)
        self.shake_frames = 5
        self.last_color = -1

        pull_x = seg.x + self.rope_position + SEGMENT_WIDTH // 2
        self._spawn_particles(pull_x, ROPE_Y, pyxel.COLOR_GRAY, 4)
        self._spawn_floating_text(pull_x, ROPE_Y - 8, "WRONG!", pyxel.COLOR_RED)

    # ── SUPER MODE ───────────────────────────────────────────────────────

    def _activate_super_mode(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.phase = Phase.SUPER_ANIM
        self.super_anim_timer = 15
        self.shake_frames = 10
        self._spawn_particles(CENTER_X, ROPE_Y, pyxel.COLOR_YELLOW, 20, life=30)
        self._spawn_floating_text(CENTER_X, ROPE_Y - 20, "SUPER PULL!", pyxel.COLOR_YELLOW, life=60)

    def _update_super_mode(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        self.heat = max(0, self.heat + HEAT_COOL_SUPER)
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0
            self.combo = 0
            self.player_color = self._rng.randint(0, NUM_COLORS - 1)
            self._spawn_floating_text(CENTER_X, ROPE_Y - 20, "SUPER END", pyxel.COLOR_ORANGE)

    # ── AI Pull ──────────────────────────────────────────────────────────

    def _ai_pull(self) -> None:
        active = self._find_active_segment()
        if active is None or self.ai_just_pulled:
            return
        self.ai_just_pulled = True

        if active.color == self.ai_pull_target:
            force = AI_PULL_FORCE_BASE + self._rng.random() * AI_PULL_VARIATION
            self.rope_position += force
            self.heat = min(HEAT_MAX, self.heat + HEAT_AI_SUCCESS)
            self.ai_last_color = active.color
            # Change target after success
            self.ai_pull_target = self._rng.randint(0, NUM_COLORS - 1)
        else:
            # AI learns: next pull comes faster after a miss
            self.ai_last_color = -1
            self.ai_pull_timer = min(self.ai_pull_timer, AI_PULL_INTERVAL_MIN + 10)

        diff = max(0, self.ai_pull_timer - AI_PULL_INTERVAL_MIN)
        max_diff = AI_PULL_INTERVAL_MAX - AI_PULL_INTERVAL_MIN
        if max_diff == 0:
            max_diff = 1
        heat_ratio = 1.0 - diff / max_diff
        self.ai_pull_target = (active.color + 1) % NUM_COLORS if self._rng.random() < heat_ratio else self.ai_pull_target

    # ── Heat ─────────────────────────────────────────────────────────────

    def _update_heat(self) -> None:
        self.heat = min(HEAT_MAX, self.heat + HEAT_PASSIVE)

    # ── Timer ────────────────────────────────────────────────────────────

    def _update_timer(self) -> bool:
        self.timer -= 1
        return self.timer < 0

    # ── Difficulty ───────────────────────────────────────────────────────

    def _update_difficulty(self) -> None:
        elapsed = GAME_DURATION - self.timer
        progress = elapsed / GAME_DURATION
        self.rope_speed = 0.8 + progress * 0.7
        self.ai_pull_interval_min = int(AI_PULL_INTERVAL_MIN - progress * 20)
        self.ai_pull_interval_max = int(AI_PULL_INTERVAL_MAX - progress * 15)

    # ── Win/Lose Check ───────────────────────────────────────────────────

    def _check_win_lose(self) -> bool:
        if self.rope_position <= WIN_THRESHOLD:
            self.phase = Phase.VICTORY
            return True
        if self.rope_position >= LOSE_THRESHOLD or self.heat >= HEAT_MAX:
            self.phase = Phase.DEFEAT
            return True
        return False

    # ── Particle System ──────────────────────────────────────────────────

    def _spawn_particles(self, x: float, y: float, color: int, count: int, life: int = 20) -> None:
        for _ in range(count):
            angle = self._rng.random() * 2 * math.pi
            speed = self._rng.random() * 3 + 1
            self.particles.append(
                Particle(
                    x=x + self._rng.random() * 6 - 3,
                    y=y + self._rng.random() * 6 - 3,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=color,
                    life=life,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Floating Text ────────────────────────────────────────────────────

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int = 40) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self._init_state()
            return

        match self.phase:
            case Phase.TITLE:
                if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                    self._init_state()
                    self.phase = Phase.PLAYING

            case Phase.PLAYING:
                self._update_playing()

            case Phase.SUPER_ANIM:
                self.super_anim_timer -= 1
                if self.super_anim_timer <= 0:
                    self.phase = Phase.PLAYING

            case Phase.GAME_OVER:
                if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                    self._init_state()
                    self.phase = Phase.PLAYING

            case _:
                pass

    def _update_playing(self) -> None:
        if self.phase not in (Phase.PLAYING, Phase.SUPER_ANIM):
            return

        self._update_segments()
        self._update_super_mode()
        self._update_heat()
        timed_out = self._update_timer()

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._player_pull()

        self.ai_pull_timer -= 1
        if self.ai_pull_timer <= 0:
            self._ai_pull()
            self.ai_pull_timer = random.randint(
                max(15, self.ai_pull_interval_min),
                max(20, self.ai_pull_interval_max),
            )
        else:
            self.ai_just_pulled = False

        self._update_difficulty()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if timed_out and self.rope_position <= 0:
            self.phase = Phase.VICTORY
        elif timed_out:
            self.phase = Phase.DEFEAT

        if self.rope_position <= WIN_THRESHOLD:
            self.phase = Phase.VICTORY
            self._spawn_particles(CENTER_X, ROPE_Y, pyxel.COLOR_YELLOW, 40, life=60)
            self._spawn_floating_text(CENTER_X, ROPE_Y - 20, "VICTORY!", pyxel.COLOR_YELLOW, life=60)
        elif self.rope_position >= LOSE_THRESHOLD or self.heat >= HEAT_MAX:
            self.phase = Phase.DEFEAT
            self._spawn_floating_text(CENTER_X, ROPE_Y - 20, "DEFEATED", pyxel.COLOR_RED, life=60)

        if self.phase in (Phase.VICTORY, Phase.DEFEAT):
            self.best_score = max(self.best_score, self.score)
            self.phase = Phase.GAME_OVER

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-3, 3)
            shake_y = self._rng.randint(-3, 3)
        if self.heat >= HEAT_DANGER:
            shake_x += self._rng.randint(-2, 2)
            shake_y += self._rng.randint(-2, 2)
        elif self.heat >= HEAT_WARN:
            shake_x += self._rng.randint(-1, 1)
            shake_y += self._rng.randint(-1, 1)

        pyxel.camera(shake_x, shake_y)

        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING | Phase.SUPER_ANIM:
                self._draw_playing()
            case Phase.GAME_OVER:
                self._draw_playing()
                self._draw_game_over()

        pyxel.camera(0, 0)

    def _draw_title(self) -> None:
        pyxel.text(CENTER_X - 35, 60, "TUG CHAIN", pyxel.COLOR_LIME)
        pyxel.text(CENTER_X - 80, 90, "Color-Match Tug of War", pyxel.COLOR_WHITE)
        pyxel.text(CENTER_X - 90, 130, "Press SPACE to Start", pyxel.COLOR_YELLOW)
        pyxel.text(CENTER_X - 95, 150, "Match rope color -> PULL!", pyxel.COLOR_GRAY)
        pyxel.text(CENTER_X - 95, 162, "COMBO x4 = SUPER PULL!", pyxel.COLOR_GRAY)
        pyxel.text(CENTER_X - 72, 174, "R = Restart anytime", pyxel.COLOR_GRAY)

        c = PLAYER_COLORS[0]
        pyxel.circ(60, 200, 10, c)
        pyxel.text(76, 196, "Player Color", pyxel.COLOR_WHITE)
        pyxel.text(76, 206, "(changes each pull)", pyxel.COLOR_GRAY)

    def _draw_playing(self) -> None:
        self._draw_background()
        self._draw_rope()
        self._draw_player()
        self._draw_ai()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()
        self._draw_super_effects()

    def _draw_background(self) -> None:
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, pyxel.COLOR_BROWN)
        for i in range(0, SCREEN_H - GROUND_Y, 12):
            pyxel.rect(0, GROUND_Y + i, SCREEN_W, 6, pyxel.COLOR_BROWN if i % 24 == 0 else pyxel.COLOR_DARK_BLUE)

        for y in range(CENTER_Y, GROUND_Y, 6):
            if (y - CENTER_Y) % 12 == 0:
                pyxel.line(CENTER_X, y, CENTER_X, y + 4, pyxel.COLOR_WHITE)

    def _draw_rope(self) -> None:
        max_y_offset = 4
        mid_count = len(self.segments) // 2

        for i, seg in enumerate(self.segments):
            sx = seg.x + self.rope_position
            dist_from_center = abs(i - mid_count)
            wave = math.sin((pyxel.frame_count + i * 3) * 0.1) * max(0, max_y_offset - dist_from_center * 0.5)
            sy = ROPE_Y + wave
            seg_color = PLAYER_COLORS[seg.color]
            pyxel.rect(int(sx), int(sy) - SEGMENT_HEIGHT // 2, SEGMENT_WIDTH, SEGMENT_HEIGHT, seg_color)

            active = self._find_active_segment()
            if active is seg:
                pyxel.rectb(int(sx) - 1, int(sy) - SEGMENT_HEIGHT // 2 - 1, SEGMENT_WIDTH + 2, SEGMENT_HEIGHT + 2, pyxel.COLOR_WHITE)

        for i in range(len(self.segments) - 1):
            s1 = self.segments[i]
            s2 = self.segments[i + 1]
            x1 = s1.x + self.rope_position + SEGMENT_WIDTH
            x2 = s2.x + self.rope_position
            y1 = ROPE_Y + math.sin((pyxel.frame_count + i * 3) * 0.1) * max(0, max_y_offset - abs(i - mid_count) * 0.5)
            y2 = ROPE_Y + math.sin((pyxel.frame_count + (i + 1) * 3) * 0.1) * max(0, max_y_offset - abs(i + 1 - mid_count) * 0.5)
            pyxel.line(int(x1), int(y1), int(x2), int(y2), pyxel.COLOR_GRAY)

    def _draw_player(self) -> None:
        pyxel.rect(PLAYER_X - 6, GROUND_Y - 32, 12, 24, pyxel.COLOR_WHITE)
        pyxel.circ(PLAYER_X, GROUND_Y - 36, 8, pyxel.COLOR_WHITE)
        pyxel.rect(PLAYER_X - 12, GROUND_Y - 30, 8, 4, pyxel.COLOR_WHITE)
        pyxel.rect(PLAYER_X + 4, GROUND_Y - 30, 8, 4, pyxel.COLOR_WHITE)

        if self.super_mode:
            rainbow_idx = (pyxel.frame_count // 5) % NUM_COLORS
            indicator_color = PLAYER_COLORS[rainbow_idx]
        else:
            indicator_color = PLAYER_COLORS[self.player_color]
        pyxel.circ(PLAYER_X + 20, GROUND_Y - 70, 10, indicator_color)
        if self.super_mode:
            pyxel.circb(PLAYER_X + 20, GROUND_Y - 70, 13, pyxel.COLOR_YELLOW)

        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            combo_color = pyxel.COLOR_YELLOW if self.combo >= SUPER_COMBO_THRESHOLD else pyxel.COLOR_LIME
            pyxel.text(PLAYER_X - 25, GROUND_Y - 80, combo_text, combo_color)

    def _draw_ai(self) -> None:
        pyxel.rect(AI_X - 6, GROUND_Y - 32, 12, 24, pyxel.COLOR_RED)
        pyxel.circ(AI_X, GROUND_Y - 36, 8, pyxel.COLOR_RED)
        pyxel.rect(AI_X - 12, GROUND_Y - 30, 8, 4, pyxel.COLOR_RED)
        pyxel.rect(AI_X + 4, GROUND_Y - 30, 8, 4, pyxel.COLOR_RED)

        ai_color = PLAYER_COLORS[self.ai_pull_target]
        pyxel.circ(AI_X - 20, GROUND_Y - 70, 8, ai_color)
        pyxel.circb(AI_X - 20, GROUND_Y - 70, 8, pyxel.COLOR_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30
            color = p.color
            if alpha < 0.3 and p.color != pyxel.COLOR_WHITE:
                color = pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 60
            color = ft.color
            if alpha < 0.4:
                color = pyxel.COLOR_GRAY
            pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, color)

    def _draw_hud(self) -> None:
        heat_bar_x = 8
        heat_bar_top = 40
        heat_bar_bottom = 200
        heat_bar_height = heat_bar_bottom - heat_bar_top
        pyxel.rectb(heat_bar_x - 1, heat_bar_top - 1, 10, heat_bar_height + 2, pyxel.COLOR_WHITE)
        pyxel.rect(heat_bar_x, heat_bar_bottom, 8, 0, pyxel.COLOR_GREEN)

        heat_pixels = int(self.heat / HEAT_MAX * heat_bar_height)
        if self.heat >= HEAT_DANGER:
            heat_color = pyxel.COLOR_RED
        elif self.heat >= HEAT_WARN:
            heat_color = pyxel.COLOR_ORANGE
        elif self.heat >= HEAT_WARN // 2:
            heat_color = pyxel.COLOR_YELLOW
        else:
            heat_color = pyxel.COLOR_GREEN
        pyxel.rect(heat_bar_x, heat_bar_bottom - heat_pixels, 8, heat_pixels, heat_color)
        pyxel.text(heat_bar_x - 2, heat_bar_top - 12, "HEAT", pyxel.COLOR_WHITE)

        seconds = max(0, self.timer // FPS)
        time_text = f"TIME: {seconds}s"
        time_color = pyxel.COLOR_RED if seconds <= 10 else pyxel.COLOR_WHITE
        pyxel.text(CENTER_X - len(time_text) * 2, 4, time_text, time_color)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W - len(score_text) * 4 - 4, 4, score_text, pyxel.COLOR_YELLOW)

        rope_indicator_x = CENTER_X + int(self.rope_position)
        rope_indicator_x = max(40, min(280, rope_indicator_x))
        pyxel.tri(rope_indicator_x, GROUND_Y + 4, rope_indicator_x - 6, GROUND_Y + 14, rope_indicator_x + 6, GROUND_Y + 14, pyxel.COLOR_WHITE)

    def _draw_super_effects(self) -> None:
        if self.super_mode:
            rainbow_idx = (pyxel.frame_count // 5) % NUM_COLORS
            border_color = PLAYER_COLORS[rainbow_idx]
            for offset in range(0, 6):
                pyxel.rectb(offset, offset, SCREEN_W - offset * 2, SCREEN_H - offset * 2, border_color)
            for _ in range(3):
                px = PLAYER_X + self._rng.randint(-30, 30)
                py = ROPE_Y + self._rng.randint(-20, 20)
                pyxel.pset(int(px), int(py), pyxel.COLOR_YELLOW)

        if self.phase == Phase.SUPER_ANIM:
            flash_alpha = self.super_anim_timer / 15
            if flash_alpha > 0:
                flash_color = pyxel.COLOR_YELLOW if int(self.super_anim_timer * 2) % 2 == 0 else pyxel.COLOR_WHITE
                pyxel.rect(0, 0, SCREEN_W, SCREEN_H, flash_color if flash_alpha > 0.5 else pyxel.COLOR_BLACK)

    def _draw_game_over(self) -> None:
        pyxel.rect(CENTER_X - 70, 50, 140, 130, pyxel.COLOR_BLACK)
        pyxel.rectb(CENTER_X - 70, 50, 140, 130, pyxel.COLOR_WHITE)

        if self.phase == Phase.GAME_OVER and hasattr(self, 'rope_position') and self.rope_position <= WIN_THRESHOLD:
            title = "YOU WIN!"
            title_color = pyxel.COLOR_LIME
        else:
            title = "DEFEATED"
            title_color = pyxel.COLOR_RED

        pyxel.text(CENTER_X - len(title) * 2, 60, title, title_color)
        pyxel.text(CENTER_X - 40, 85, f"Score: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(CENTER_X - 40, 97, f"Max Combo: {self.max_combo}", pyxel.COLOR_YELLOW)
        pyxel.text(CENTER_X - 40, 109, f"Best: {self.best_score}", pyxel.COLOR_GRAY)
        pyxel.text(CENTER_X - 50, 145, "SPACE to Retry", pyxel.COLOR_LIME)
        pyxel.text(CENTER_X - 40, 157, "R to Restart", pyxel.COLOR_GRAY)


if __name__ == "__main__":
    Game()
