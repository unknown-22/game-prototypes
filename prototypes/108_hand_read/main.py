from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Color constants ---
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

HAND_COLORS: dict[int, int] = {0: RED, 1: LIME, 2: CYAN}
HAND_CHARS: dict[int, str] = {0: "R", 1: "P", 2: "S"}
HAND_NAMES: dict[int, str] = {0: "ROCK", 1: "PAPER", 2: "SCISSORS"}

# rock(0) beats scissors(2), scissors(2) beats paper(1), paper(1) beats rock(0)
BEAT_MAP: dict[int, int] = {0: 2, 1: 0, 2: 1}
LOSE_MAP: dict[int, int] = {0: 1, 1: 2, 2: 0}


class Phase(Enum):
    TITLE = auto()
    QUEUE = auto()
    BATTLE = auto()
    RESULT = auto()
    GAME_OVER = auto()


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 1


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    AI_MAX_HP = 10
    PLAYER_MAX_HP = 5
    MAX_ENERGY = 3
    COMBO_SUPER_THRESHOLD = 4
    SUPER_DURATION = 5
    QUEUE_SIZE = 3
    BATTLE_DURATION = 30
    RESULT_DURATION = 60
    AUTO_ADVANCE_TIME = 8 * 30

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="Hand Read")
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.queue: list[int] = []
        self.ai_hp: int = self.AI_MAX_HP
        self.player_hp: int = self.PLAYER_MAX_HP
        self.energy: int = self.MAX_ENERGY
        self.combo: int = 0
        self.same_hand_streak: int = 0
        self.last_hand: int = -1
        self.max_combo: int = 0
        self.score: int = 0
        self.ai_prediction: int = 0
        self.player_history: list[int] = []
        self.ai_history: list[int] = []
        self.phase_timer: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.turn_count: int = 0
        self.result_text: str = ""
        self.result_color: int = WHITE
        self.current_player_hand: int = -1
        self.current_ai_hand: int = -1
        self.battle_frame: int = 0
        self.particles: list[Particle] = []
        self._shake_frames: int = 0
        self._prev_mouse_pressed: bool = False
        self.high_score: int = 0
        self._fill_queue()
        self._update_ai_prediction()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.queue.clear()
        self.ai_hp = self.AI_MAX_HP
        self.player_hp = self.PLAYER_MAX_HP
        self.energy = self.MAX_ENERGY
        self.combo = 0
        self.same_hand_streak = 0
        self.last_hand = -1
        self.max_combo = 0
        self.score = 0
        self.ai_prediction = 0
        self.player_history.clear()
        self.ai_history.clear()
        self.phase_timer = 0
        self.super_mode = False
        self.super_timer = 0
        self.turn_count = 0
        self.result_text = ""
        self.result_color = WHITE
        self.current_player_hand = -1
        self.current_ai_hand = -1
        self.battle_frame = 0
        self.particles.clear()
        self._shake_frames = 0
        self._fill_queue()
        self._update_ai_prediction()

    def _fill_queue(self) -> None:
        while len(self.queue) < self.QUEUE_SIZE:
            self.queue.append(self._rng.randint(0, 2))

    def _resolve_battle(self, player_hand: int, ai_hand: int) -> tuple[int, int, bool, bool]:
        if player_hand == ai_hand:
            return 0, 0, False, True
        if BEAT_MAP[player_hand] == ai_hand:
            return 0, 1, True, False
        return 1, 0, False, False

    def _update_ai_prediction(self) -> None:
        history_window = self._shrink_history_window(self.ai_hp)
        recent = self.player_history[-history_window:] if self.player_history else []
        if not recent:
            self.ai_prediction = self._rng.randint(0, 2)
            return
        counts = [0, 0, 0]
        for h in recent:
            counts[h] += 1
        max_count = max(counts)
        candidates = [i for i, c in enumerate(counts) if c == max_count]
        self.ai_prediction = self._rng.choice(candidates)

    def _shrink_history_window(self, ai_hp: int) -> int:
        if ai_hp > 6:
            return 8
        if ai_hp >= 4:
            return 6
        return 4

    def _update_combo(self, is_win: bool, player_hand: int) -> None:
        if not is_win:
            self.combo = 0
            self.same_hand_streak = 0
            self.last_hand = -1
            return
        if player_hand == self.last_hand:
            self.combo += 1
            self.same_hand_streak = self.combo
        else:
            self.combo = 1
            self.same_hand_streak = 1
            self.last_hand = player_hand
        self.max_combo = max(self.max_combo, self.combo)

    def _get_damage_multiplier(self) -> float:
        if self.super_mode:
            return 3.0
        if self.combo >= 6:
            return 2.0
        if self.combo >= 2:
            return 1.5
        return 1.0

    def _spawn_particles(self, x: float, y: float, color: int, count: int, radius: float = 2.0) -> None:
        import math
        for _ in range(count):
            angle = self._rng.uniform(0, 6.283185)
            speed = self._rng.uniform(0.5, radius) * 2
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed * 0.7
            life = self._rng.randint(15, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_win_particles(self, x: float, y: float, hand_color: int) -> None:
        import math
        for _ in range(14):
            angle = self._rng.uniform(0, 6.283185)
            speed = self._rng.uniform(2.0, 5.0)
            vx = math.cos(angle) * speed * 0.7
            vy = math.sin(angle) * speed * 0.7
            life = self._rng.randint(12, 25)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=hand_color))

    def _spawn_lose_particles(self, x: float, y: float) -> None:
        for _ in range(8):
            vx = self._rng.uniform(-1.0, 1.0)
            vy = self._rng.uniform(0.5, 3.0)
            life = self._rng.randint(10, 20)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=RED))

    def _spawn_rainbow_particles(self) -> None:
        colors = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]
        for _ in range(3):
            color = self._rng.choice(colors)
            self.particles.append(
                Particle(
                    x=self.SCREEN_W // 2 + self._rng.uniform(-20, 20),
                    y=150 + self._rng.uniform(-10, 10),
                    vx=self._rng.uniform(-0.5, 0.5),
                    vy=self._rng.uniform(-2.0, -0.5),
                    life=self._rng.randint(20, 35),
                    color=color,
                    size=2,
                )
            )

    def _replace_hand_at(self, index: int) -> bool:
        if self.phase != Phase.QUEUE:
            return False
        if self.energy <= 0:
            return False
        if index < 0 or index >= self.QUEUE_SIZE:
            return False
        old = self.queue[index]
        new_hand: int
        while True:
            new_hand = self._rng.randint(0, 2)
            if new_hand != old or self.queue.count(old) <= 1:
                break
        self.queue[index] = new_hand
        self.energy -= 1
        return True

    def _advance_to_battle(self) -> None:
        if self.phase != Phase.QUEUE:
            return
        self.phase = Phase.BATTLE
        self.battle_frame = 0
        self.current_player_hand = self.queue.pop(0)
        self.current_ai_hand = self._rng.randint(0, 2)
        self._fill_queue()
        self._update_ai_prediction()
        self.turn_count += 1

    def _do_super_tick(self) -> None:
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.combo = 0
            self.last_hand = -1
            self.same_hand_streak = 0

    def update(self) -> None:
        mouse_pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        mouse_clicked = mouse_pressed and not self._prev_mouse_pressed
        self._prev_mouse_pressed = mouse_pressed

        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()
            return

        if self.phase == Phase.TITLE:
            if mouse_clicked or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.QUEUE
                self.phase_timer = 0
                self.combo = 0
                self.same_hand_streak = 0
                self.last_hand = -1
                self.max_combo = 0
                self.score = 0
                self.ai_hp = self.AI_MAX_HP
                self.player_hp = self.PLAYER_MAX_HP
                self.energy = self.MAX_ENERGY
                self.turn_count = 0
                self.super_mode = False
                self.super_timer = 0
                self.current_player_hand = -1
                self.current_ai_hand = -1
                self.result_text = ""
                self.particles.clear()
                self.player_history.clear()
                self.ai_history.clear()
                self.queue.clear()
                self._fill_queue()
                self._update_ai_prediction()
            return

        if self.phase == Phase.GAME_OVER:
            if mouse_clicked or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.QUEUE:
            self.phase_timer += 1
            mx = pyxel.mouse_x
            my = pyxel.mouse_y

            if mouse_clicked:
                for i in range(self.QUEUE_SIZE):
                    qx, qy, qw, qh = self._queue_card_rect(i)
                    if qx <= mx < qx + qw and qy <= my < qy + qh:
                        self._replace_hand_at(i)
                        break
                if self._end_turn_button_hover():
                    self._advance_to_battle()

            if self.phase_timer >= self.AUTO_ADVANCE_TIME:
                self._advance_to_battle()

            if self.super_mode:
                self._do_super_tick()
                if self.super_mode:
                    self._spawn_rainbow_particles()
            return

        if self.phase == Phase.BATTLE:
            self.battle_frame += 1
            if self.battle_frame >= self.BATTLE_DURATION:
                self._process_result()
            return

        if self.phase == Phase.RESULT:
            self.battle_frame += 1
            if self.battle_frame >= self.RESULT_DURATION:
                if self.player_hp <= 0 or self.ai_hp <= 0:
                    self.phase = Phase.GAME_OVER
                    if self.score > self.high_score:
                        self.high_score = self.score
                else:
                    self.phase = Phase.QUEUE
                    self.phase_timer = 0
                    self.result_text = ""
            return

        self._update_particles()

    def _process_result(self) -> None:
        player_hand = self.current_player_hand
        ai_hand = self.current_ai_hand
        self.player_history.append(player_hand)
        self.ai_history.append(ai_hand)

        ai_predicted = self.ai_prediction == player_hand

        if self.super_mode:
            player_dmg, ai_dmg, is_win, is_tie = 0, 1, True, False
            multiplier = 3.0
        else:
            player_dmg, ai_dmg, is_win, is_tie = self._resolve_battle(player_hand, ai_hand)
            multiplier = self._get_damage_multiplier()

        effective_ai_dmg = int(ai_dmg * multiplier)

        if is_win:
            self._update_combo(True, player_hand)
            self.ai_hp = max(0, self.ai_hp - effective_ai_dmg)
            self.score += effective_ai_dmg
            self.result_text = f"HIT! x{multiplier}"
            self.result_color = YELLOW
            if self.super_mode:
                self.result_text = "SUPER! x3"
                self.result_color = RED
            self._spawn_win_particles(self.SCREEN_W // 2 - 20, 150, HAND_COLORS[player_hand])
            if self.combo >= self.COMBO_SUPER_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_timer = self.SUPER_DURATION
                self.result_text = "SUPER MODE!"
                self.result_color = RED
                self._spawn_rainbow_particles()
        elif is_tie:
            self.result_text = "TIE"
            self.result_color = GRAY
            self._spawn_particles(self.SCREEN_W // 2 + 20, 150, WHITE, 6, 1.5)
        else:
            self._update_combo(False, player_hand)
            self.player_hp = max(0, self.player_hp - player_dmg)
            self.combo = 0
            self.last_hand = -1
            self.same_hand_streak = 0
            self.result_text = "MISS"
            self.result_color = RED
            self._spawn_lose_particles(self.SCREEN_W // 2 - 20, 150)

        if ai_predicted and not self.super_mode:
            self.result_text += " (READ!)"
            self.result_color = RED

        self.energy = min(self.MAX_ENERGY, self.energy + 1)
        self.phase = Phase.RESULT
        self.battle_frame = 0

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.08
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _queue_card_rect(self, index: int) -> tuple[int, int, int, int]:
        start_x = self.SCREEN_W // 2 - 140
        card_w = 80
        card_h = 30
        card_gap = 12
        x = start_x + index * (card_w + card_gap)
        y = 192
        return x, y, card_w, card_h

    def _end_turn_button_rect(self) -> tuple[int, int, int, int]:
        return self.SCREEN_W - 85, 192, 75, 30

    def _end_turn_button_hover(self) -> bool:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        bx, by, bw, bh = self._end_turn_button_rect()
        return bx <= mx < bx + bw and by <= my < by + bh

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self._shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            pyxel.camera(ox, oy)
            self._shake_frames -= 1
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        else:
            self._draw_hud()
            if self.phase == Phase.QUEUE:
                self._draw_queue()
                self._draw_ai_prediction()
                self._draw_ai_history()
                self._draw_end_turn_button()
            elif self.phase == Phase.BATTLE:
                self._draw_battle()
            elif self.phase == Phase.RESULT:
                self._draw_battle()
                self._draw_result_text()
            elif self.phase == Phase.GAME_OVER:
                self._draw_game_over()
            self._draw_particles()

    def _draw_center_text(self, y: int, text: str, color: int) -> None:
        pyxel.text(self.SCREEN_W // 2 - len(text) * 2, y, text, color)

    def _draw_title(self) -> None:
        self._draw_center_text(20, "HAND READ", WHITE)
        self._draw_center_text(32, "========", CYAN)

        pyxel.text(self.SCREEN_W // 2 - 80, 60, "RPS prediction battle!", LIME)
        pyxel.text(self.SCREEN_W // 2 - 80, 72, "AI learns your patterns to predict", LIME)
        pyxel.text(self.SCREEN_W // 2 - 80, 82, "your next move.", LIME)

        pyxel.text(self.SCREEN_W // 2 - 80, 100, "Pre-commit your next 3 hands.", GREEN)
        pyxel.text(self.SCREEN_W // 2 - 80, 110, "Swap before play (costs 1 Energy).", GREEN)
        pyxel.text(self.SCREEN_W // 2 - 80, 120, "Break AI's prediction -> COMBO chain!", YELLOW)

        pyxel.text(self.SCREEN_W // 2 - 80, 140, "COMBO x4 -> SUPER MODE (beats all)", RED)
        pyxel.text(self.SCREEN_W // 2 - 80, 150, "Win: AI HP 0. Lose: Your HP 0.", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 80, 160, "Click cards to swap / End Turn.", CYAN)

        if self.high_score > 0:
            self._draw_center_text(190, f"HIGH SCORE: {self.high_score}", YELLOW)

        self._draw_center_text(215, "Click or SPACE to start", WHITE)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, "HAND READ", WHITE)
        pyxel.text(4, 10, f"TURN {self.turn_count}", CYAN)

        ai_bar_x = self.SCREEN_W - 85
        pyxel.text(ai_bar_x - 10, 2, "AI", GRAY)
        self._draw_hp_bar(ai_bar_x, 10, self.ai_hp, self.AI_MAX_HP)

        pyxel.text(4, 30, "YOU", GRAY)
        self._draw_hp_bar(20, 36, self.player_hp, self.PLAYER_MAX_HP)

        if self.combo >= 2:
            if self.combo >= 4:
                cc = RED
            else:
                cc = YELLOW
            pyxel.text(self.SCREEN_W // 2 - 20, 10, f"COMBO x{self.combo}", cc)

        if self.super_mode:
            pyxel.text(self.SCREEN_W // 2 - 32, 20, f"SUPER {self.super_timer}", RED)

    def _draw_hp_bar(self, x: int, y: int, hp: int, max_hp: int) -> None:
        w = 60
        h = 6
        ratio = hp / max_hp
        if ratio > 0.5:
            color = GREEN
        elif ratio > 0.25:
            color = YELLOW
        else:
            color = RED
        pyxel.rectb(x - 1, y - 1, w + 2, h + 2, WHITE)
        pyxel.rect(x, y, int(w * ratio), h, color)

    def _draw_ai_prediction(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 35, 52, "AI PREDICTS:", GRAY)
        px = self.SCREEN_W // 2 + 30
        py = 48
        self._draw_hand_icon(px, py, self.ai_prediction, scale=0.7)
        pyxel.text(px + 14, py + 4, HAND_CHARS[self.ai_prediction], WHITE)

    def _draw_ai_history(self) -> None:
        pyxel.text(4, 52, "AI HISTORY:", GRAY)
        recent = self.ai_history[-8:] if self.ai_history else []
        for i, h in enumerate(recent):
            self._draw_hand_icon(60 + i * 16, 48, h, scale=0.5)

    def _draw_hand_icon(self, x: int, y: int, hand: int, scale: float = 1.0) -> None:
        r = int(16 * scale)
        pyxel.circ(x + r, y + r, r, HAND_COLORS[hand])
        pyxel.circb(x + r, y + r, r, WHITE)

    def _draw_hand_big(self, x: int, y: int, hand: int, label: str) -> None:
        r = 28
        cx = x + r
        cy = y + r
        color = HAND_COLORS[hand]
        pyxel.circ(cx, cy, r, color)
        pyxel.circb(cx, cy, r, WHITE)
        ch = HAND_CHARS[hand]
        pyxel.text(cx - 2, cy - 3, ch, WHITE)
        pyxel.text(cx - len(label) * 2, cy + r + 4, label, WHITE)

    def _draw_queue(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 50, 180, "YOUR QUEUE:", GRAY)
        for i, hand in enumerate(self.queue):
            x, y, w, h = self._queue_card_rect(i)
            hover = self._is_mouse_over(x, y, w, h)
            border = YELLOW if hover else WHITE
            pyxel.rect(x, y, w, h, DARK_BLUE)
            pyxel.rectb(x, y, w, h, border)
            self._draw_hand_icon(x + 6, y + 6, hand, scale=0.55)
            nm = HAND_NAMES[hand]
            pyxel.text(x + 26, y + 12, nm[:4], WHITE)

        pyxel.text(4, 202, f"ENERGY: {self.energy}/{self.MAX_ENERGY}", YELLOW)

    def _is_mouse_over(self, x: int, y: int, w: int, h: int) -> bool:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        return x <= mx < x + w and y <= my < y + h

    def _draw_end_turn_button(self) -> None:
        bx, by, bw, bh = self._end_turn_button_rect()
        hover = self._end_turn_button_hover()
        color = LIME if hover else GREEN
        pyxel.rect(bx, by, bw, bh, color)
        pyxel.rectb(bx, by, bw, bh, WHITE)
        pyxel.text(bx + 12, by + 10, "END TURN", WHITE)

    def _draw_battle(self) -> None:
        t = self.battle_frame
        shake_x = max(0, (10 - t)) * self._rng.randint(-1, 1) if t < 10 else 0

        px = self.SCREEN_W // 2 - 100 + shake_x
        py = 90
        self._draw_hand_big(px, py, self.current_player_hand, "YOU")

        ax = self.SCREEN_W // 2 + 20
        ay = 90
        self._draw_hand_big(ax, ay, self.current_ai_hand, "AI")

        vs_x = self.SCREEN_W // 2 - 6
        vs_y = 120
        vs_color = YELLOW if t % 8 < 4 else WHITE
        pyxel.text(vs_x, vs_y, "VS", vs_color)

    def _draw_result_text(self) -> None:
        if self.result_text:
            alpha = self.battle_frame
            if alpha < 40:
                color = self.result_color
            else:
                color = GRAY
            self._draw_center_text(170, self.result_text, color)

    def _draw_game_over(self) -> None:
        if self.ai_hp <= 0:
            self._draw_center_text(30, "YOU WIN!", LIME)
            self._draw_center_text(42, "========", LIME)
        else:
            self._draw_center_text(30, "GAME OVER", RED)
            self._draw_center_text(42, "=========", RED)

        self._draw_center_text(70, f"SCORE: {self.score}", WHITE)
        self._draw_center_text(84, f"TURNS: {self.turn_count}", CYAN)
        self._draw_center_text(98, f"MAX COMBO: x{self.max_combo}", YELLOW)
        self._draw_center_text(112, f"AI HP LEFT: {self.ai_hp}", ORANGE)

        if self.score == self.high_score and self.score > 0:
            self._draw_center_text(140, "** NEW HIGH SCORE! **", YELLOW)

        self._draw_center_text(215, "Click or SPACE to retry", WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < self.SCREEN_W and 0 <= py < self.SCREEN_H:
                if p.size > 1:
                    pyxel.rect(px, py, p.size, p.size, p.color)
                else:
                    pyxel.pset(px, py, p.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
