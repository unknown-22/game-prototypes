from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
COLOR_VALS: tuple[int, int, int, int] = (8, 3, 12, 10)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "BLUE", "YELLOW")
NUM_COLORS = 4
PLAYER_X = 80
AI_X = 240
FIGHTER_Y = 120
ARM_REACH = 140
RING_FLOOR_Y = 180
RING_TOP_Y = 50
BASE_DAMAGE = 10
PUNCH_COOLDOWN = 15
SUPER_COMBO_THRESHOLD = 4
SUPER_DAMAGE_MULT = 2
AI_BASE_INTERVAL = 60
AI_MIN_INTERVAL = 30
AI_PUNCH_DAMAGE = 8
GAME_DURATION = 60 * 30
SHAKE_FRAMES = 10
HIT_STUN_PLAYER_HIT = 10
HIT_STUN_AI_HIT = 10
MAX_HP = 100


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Fighter:
    x: int
    y: int
    hp: int = MAX_HP
    max_hp: int = MAX_HP
    combo: int = 0
    max_combo: int = 0
    color: int = 0
    punching: bool = False
    punch_timer: int = 0
    hit_stun: int = 0


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


class ChromaJab:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player: Fighter = Fighter(x=PLAYER_X, y=FIGHTER_Y)
        self.ai: Fighter = Fighter(x=AI_X, y=FIGHTER_Y)
        self.selected_color: int = 0
        self.game_timer: int = GAME_DURATION
        self.total_damage: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self._rng: random.Random = random.Random()
        self._player_punch_cooldown: int = 0
        self._ai_punch_timer: int = 45
        self._ai_punch_interval: int = AI_BASE_INTERVAL
        self._ai_punch_count: int = 0
        self._last_player_color: int = -1
        self.result_text: str = ""
        self._ai_color_counter: int = 0
        self._last_super_combo: bool = False
        self._last_super_frame: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.player = Fighter(x=PLAYER_X, y=FIGHTER_Y)
        self.ai = Fighter(x=AI_X, y=FIGHTER_Y)
        self.selected_color = 0
        self.game_timer = GAME_DURATION
        self.total_damage = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self._player_punch_cooldown = 0
        self._ai_punch_timer = 45
        self._ai_punch_interval = AI_BASE_INTERVAL
        self._ai_punch_count = 0
        self._last_player_color = -1
        self.result_text = ""
        self._ai_color_counter = 0
        self._last_super_combo = False
        self._last_super_frame = 0

    def _player_body_rect(self) -> tuple[int, int, int, int]:
        return (self.player.x - 15, self.player.y - 25, 30, 50)

    def _ai_body_rect(self) -> tuple[int, int, int, int]:
        return (self.ai.x - 15, self.ai.y - 25, 30, 50)

    def _player_punch_rect(self) -> tuple[int, int, int, int]:
        return (self.player.x + 8, self.player.y - 20, ARM_REACH, 16)

    def _ai_punch_rect(self) -> tuple[int, int, int, int]:
        return (self.ai.x - 8 - ARM_REACH, self.ai.y - 20, ARM_REACH, 16)

    @staticmethod
    def _aabb_overlap(
        r1: tuple[int, int, int, int], r2: tuple[int, int, int, int]
    ) -> bool:
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2

    def _try_punch(self, color: int) -> tuple[bool, int, bool]:
        """Returns (hit, damage, is_super)."""
        if self._player_punch_cooldown > 0:
            return (False, 0, False)
        if self.player.hp <= 0 or self.ai.hp <= 0:
            return (False, 0, False)

        self._player_punch_cooldown = PUNCH_COOLDOWN
        self.player.punching = True
        self.player.punch_timer = 8
        self.player.color = color

        self._ai_color_counter += 1

        if not self._aabb_overlap(self._player_punch_rect(), self._ai_body_rect()):
            return (False, 0, False)

        if self._last_player_color < 0 or color == self._last_player_color:
            self.player.combo += 1
        else:
            self.player.combo = 0

        self.player.max_combo = max(self.player.max_combo, self.player.combo)
        self._last_player_color = color

        is_super = self.player.combo >= SUPER_COMBO_THRESHOLD
        ai_stun_frames = HIT_STUN_AI_HIT

        if is_super:
            self.player.combo = 0
            ai_stun_frames = HIT_STUN_AI_HIT + 5
            self.shake_frames = SHAKE_FRAMES
            self._last_super_combo = True
            self._last_super_frame = pyxel.frame_count
            self._spawn_particles(self.ai.x, self.ai.y, -1, 12)
            self.floating_texts.append(
                FloatingText(self.ai.x - 15, self.ai.y - 40, "SUPER!", 30, 10)
            )

        combo_bonus = 1 + self.player.combo * 0.25
        damage = BASE_DAMAGE * combo_bonus
        if is_super:
            damage *= SUPER_DAMAGE_MULT

        dmg_int = int(damage)
        self.ai.hp = max(0, self.ai.hp - dmg_int)
        self.total_damage += dmg_int
        self.ai.hit_stun = ai_stun_frames

        hit_color = COLOR_VALS[color]
        impact_x = self.ai.x - 15 + self._rng.randint(0, 20)
        impact_y = self.ai.y - 20 + self._rng.randint(0, 20)
        if is_super:
            self._spawn_particles(impact_x, impact_y, hit_color, 8)
        else:
            self._spawn_particles(impact_x, impact_y, hit_color, 4)

        self.floating_texts.append(
            FloatingText(
                float(self.ai.x + self._rng.randint(-10, 10)),
                float(self.ai.y - 25),
                f"-{dmg_int}",
                20,
                hit_color,
            )
        )

        return (True, dmg_int, is_super)

    def _ai_act(self) -> None:
        if self.ai.hp <= 0 or self.player.hp <= 0:
            return
        if self.ai.hit_stun > 0:
            return

        self._ai_punch_timer -= 1
        if self._ai_punch_timer <= 0:
            self._ai_punch_count += 1

            if self._ai_punch_count % 3 == 0:
                if self._last_player_color >= 0 and self._rng.random() < 0.5:
                    self.ai.color = self._last_player_color
                else:
                    self.ai.color = self._rng.randint(0, NUM_COLORS - 1)

            self.ai.punching = True
            self.ai.punch_timer = 8

            if self._aabb_overlap(self._ai_punch_rect(), self._player_body_rect()):
                self.player.hp = max(0, self.player.hp - AI_PUNCH_DAMAGE)
                self.player.hit_stun = HIT_STUN_PLAYER_HIT

                ai_color = COLOR_VALS[self.ai.color]
                self._spawn_particles(
                    float(self.player.x + self._rng.randint(-10, 10)),
                    float(self.player.y - 10 + self._rng.randint(0, 10)),
                    ai_color,
                    4,
                )
                self.floating_texts.append(
                    FloatingText(
                        float(self.player.x + self._rng.randint(-10, 10)),
                        float(self.player.y - 25),
                        f"-{AI_PUNCH_DAMAGE}",
                        20,
                        ai_color,
                    )
                )

            elapsed = GAME_DURATION - self.game_timer
            aggression = min(1.0, elapsed / GAME_DURATION)
            self._ai_punch_interval = int(
                AI_BASE_INTERVAL - aggression * (AI_BASE_INTERVAL - AI_MIN_INTERVAL)
            )
            self._ai_punch_timer = self._ai_punch_interval

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            if color == -1:
                pcolor = COLOR_VALS[self._rng.randint(0, NUM_COLORS - 1)]
            else:
                pcolor = color
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-3, 3),
                    vy=self._rng.uniform(-3, 3),
                    life=self._rng.randint(15, 30),
                    color=pcolor,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _compute_score(self) -> int:
        return int(self.total_damage * (1 + self.player.max_combo * 0.1))

    def _is_game_over(self) -> bool:
        return self.player.hp <= 0 or self.ai.hp <= 0 or self.game_timer <= 0

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.phase = Phase.TITLE
            return

        if self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_Q):
                self.selected_color = 0
            if pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_W):
                self.selected_color = 1
            if pyxel.btnp(pyxel.KEY_3) or pyxel.btnp(pyxel.KEY_E):
                self.selected_color = 2
            if pyxel.btnp(pyxel.KEY_4):
                self.selected_color = 3

            if pyxel.btnp(pyxel.KEY_SPACE):
                self._try_punch(self.selected_color)

            self._ai_act()

            if self._player_punch_cooldown > 0:
                self._player_punch_cooldown -= 1

            if self.player.hit_stun > 0:
                self.player.hit_stun -= 1
            if self.player.punch_timer > 0:
                self.player.punch_timer -= 1
                if self.player.punch_timer == 0:
                    self.player.punching = False

            if self.ai.hit_stun > 0:
                self.ai.hit_stun -= 1
            if self.ai.punch_timer > 0:
                self.ai.punch_timer -= 1
                if self.ai.punch_timer == 0:
                    self.ai.punching = False

            self.game_timer -= 1

            self._update_particles()
            self._update_floating_texts()

            if self.shake_frames > 0:
                self.shake_frames -= 1

            if self._is_game_over():
                self.phase = Phase.GAME_OVER
                if self.player.hp <= 0:
                    self.result_text = "YOU LOSE"
                elif self.ai.hp <= 0:
                    self.result_text = "YOU WIN!"
                else:
                    self.result_text = "TIME UP"

    def draw(self) -> None:
        if self.shake_frames > 0:
            sx = self._rng.randint(-4, 4)
            sy = self._rng.randint(-4, 4)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera()

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(0)
        pyxel.text(88, 16, "CHROMA JAB", 8)
        pyxel.rect(90, 26, 142, 2, 8)

        pyxel.text(96, 44, "COLOR-MATCH BOXING", 7)

        pyxel.text(64, 68, "PUNCH COLORS:", 7)
        for i, (name, col) in enumerate(zip(COLOR_NAMES, COLOR_VALS)):
            px = 40 + i * 64
            pyxel.rect(px, 82, 50, 20, col)
            pyxel.text(px + 5, 88, name[0], 0)
            pyxel.text(px + 2, 106, name, col)

        pyxel.text(72, 138, "1-4 / Q-W-E: SELECT COLOR", 7)
        pyxel.text(96, 152, "SPACE: PUNCH", 7)

        pyxel.text(64, 174, "MATCH COLORS = BUILD COMBO", 3)
        pyxel.text(52, 190, "COMBO x4+ = SUPER COMBO!", 10)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(100, 220, "SPACE TO START", 10)
        else:
            pyxel.text(100, 220, "SPACE TO START", 7)

    def _draw_playing(self) -> None:
        pyxel.cls(0)

        pyxel.rect(0, RING_TOP_Y, SCREEN_W, RING_FLOOR_Y - RING_TOP_Y, 5)
        pyxel.rect(0, RING_FLOOR_Y, SCREEN_W, SCREEN_H - RING_FLOOR_Y, 4)

        for rope_y in (RING_TOP_Y, RING_TOP_Y + 42, RING_TOP_Y + 84):
            pyxel.rect(8, rope_y, SCREEN_W - 16, 2, 13)

        self._draw_fighter(self.player, facing_right=True)
        self._draw_fighter(self.ai, facing_right=False)

        self._draw_hud()

        for p in self.particles:
            if p.life > 0:
                alpha = p.life / 30.0
                if alpha > 0.15:
                    pyxel.pset(int(p.x), int(p.y), p.color)

        for ft in self.floating_texts:
            if ft.life > 0:
                alpha = ft.life / 30.0
                if alpha > 0.15:
                    pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

        self._draw_color_ui()

    def _draw_fighter(self, fighter: Fighter, facing_right: bool) -> None:
        x = fighter.x
        y = fighter.y
        col = COLOR_VALS[fighter.color]
        body_color = 7
        if fighter.hit_stun > 0 and fighter.hit_stun % 4 < 2:
            body_color = 8

        pyxel.rect(x - 6, y - 40, 12, 12, body_color)
        pyxel.rect(x - 8, y - 28, 16, 24, body_color)
        pyxel.rect(x - 6, y - 4, 4, 12, body_color)
        pyxel.rect(x + 2, y - 4, 4, 12, body_color)

        if fighter.punching:
            if facing_right:
                pyxel.rect(x + 8, y - 22, ARM_REACH, 6, col)
                pyxel.rect(x + 8 + ARM_REACH - 4, y - 26, 12, 14, col)
            else:
                pyxel.rect(x - 8 - ARM_REACH, y - 22, ARM_REACH, 6, col)
                pyxel.rect(x - 8 - ARM_REACH - 4, y - 26, 12, 14, col)
        else:
            if facing_right:
                pyxel.rect(x + 2, y - 24, 14, 6, col)
            else:
                pyxel.rect(x - 16, y - 24, 14, 6, col)

    def _draw_hud(self) -> None:
        bar_w = 80
        bar_h = 8
        bar_y = 8

        pyxel.rect(4, bar_y, bar_w, bar_h, 13)
        player_fill = int(bar_w * (self.player.hp / self.player.max_hp))
        if player_fill > 0:
            hp_col = 3
            if self.player.hp < 40:
                hp_col = 8
            elif self.player.hp < 70:
                hp_col = 9
            pyxel.rect(4, bar_y, player_fill, bar_h, hp_col)
        pyxel.text(88, bar_y, "YOU", 7)

        pyxel.rect(SCREEN_W - 4 - bar_w, bar_y, bar_w, bar_h, 13)
        ai_fill = int(bar_w * (self.ai.hp / self.ai.max_hp))
        if ai_fill > 0:
            ai_hp_col = 3
            if self.ai.hp < 40:
                ai_hp_col = 8
            elif self.ai.hp < 70:
                ai_hp_col = 9
            pyxel.rect(SCREEN_W - 4 - ai_fill, bar_y, ai_fill, bar_h, ai_hp_col)
        pyxel.text(SCREEN_W - 88 - 30, bar_y, "AI", 7)

        seconds = self.game_timer // 30
        timer_col = 7
        if seconds <= 10:
            timer_col = 8
        elif seconds <= 20:
            timer_col = 9
        pyxel.text(SCREEN_W // 2 - 12, bar_y, f"{seconds:2d}s", timer_col)

        combo_col = 7
        if self.player.combo >= SUPER_COMBO_THRESHOLD:
            combo_col = 10
        elif self.player.combo >= 2:
            combo_col = 9
        pyxel.text(SCREEN_W // 2 - 30, bar_y + 12, f"COMBO x{self.player.combo}", combo_col)

    def _draw_color_ui(self) -> None:
        ui_y = 205
        box_size = 36
        spacing = 8
        total_w = NUM_COLORS * box_size + (NUM_COLORS - 1) * spacing
        start_x = SCREEN_W // 2 - total_w // 2

        for i, col in enumerate(COLOR_VALS):
            px = start_x + i * (box_size + spacing)
            pyxel.rect(px, ui_y, box_size, box_size, col)
            if i == self.selected_color:
                pyxel.rectb(px - 1, ui_y - 1, box_size + 2, box_size + 2, 7)
                if (pyxel.frame_count // 8) % 2 == 0:
                    pyxel.rectb(px - 2, ui_y - 2, box_size + 4, box_size + 4, 10)
            else:
                pyxel.rectb(px, ui_y, box_size, box_size, 13)

        key_labels = ("1/Q", "2/W", "3/E", "4")
        for i, label in enumerate(key_labels):
            px = start_x + i * (box_size + spacing) + 2
            pyxel.text(px, ui_y + box_size + 4, label, 7)

    def _draw_game_over(self) -> None:
        pyxel.cls(0)
        result_col = 3
        if "LOSE" in self.result_text:
            result_col = 8
        elif "WIN" in self.result_text:
            result_col = 3
        pyxel.text(SCREEN_W // 2 - 25, 16, self.result_text, result_col)

        pyxel.text(110, 40, "GAME OVER", 8)
        pyxel.rect(112, 50, 96, 1, 8)

        score = self._compute_score()
        pyxel.text(100, 64, f"SCORE: {score}", 7)
        pyxel.text(100, 82, f"MAX COMBO: {self.player.max_combo}", 9)
        pyxel.text(100, 100, f"DAMAGE: {self.total_damage}", 3)
        pyxel.text(100, 120, f"YOU HP: {self.player.hp}", 8)
        pyxel.text(100, 138, f"AI HP: {self.ai.hp}", 12)

        timer_text = f"TIME LEFT: {(GAME_DURATION - self.game_timer) // 30}s"
        pyxel.text(100, 160, timer_text, 7)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(100, 220, "R: RETRY", 10)
        else:
            pyxel.text(100, 220, "R: RETRY", 7)


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Chroma Jab", display_scale=2)
        self.game = ChromaJab()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
