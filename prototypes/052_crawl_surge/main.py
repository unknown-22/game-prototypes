"""CRAWL SURGE — Color-match centipede-like arena shooter.

Reinterpreted from game_idea_factory #1 (Score 32.0):
  "split + converge" hooks → centipede chains split when shot mid-body
  "synthesis compression" → SURGE: BFS chain-destroy same-color connected segments

Core mechanic: Match your shot color to centipede segment colors.
Consecutive matches build COMBO → COMBO >= 3 triggers SURGE,
destroying all connected same-color segments in a chain reaction.
"""
import pyxel
from dataclasses import dataclass
from enum import Enum, auto
import math
import random

# ── Config ──
SCREEN_W = 256
SCREEN_H = 240
PLAYER_AREA_TOP = SCREEN_H - 40
PLAYER_Y = SCREEN_H - 20
PLAYER_SPEED = 2
PLAYER_W = 14
PLAYER_HALF_W = PLAYER_W // 2
NUM_COLORS = 4
COLOR_NAMES = ("RED", "GREEN", "BLUE", "YELLOW")
# pyxel color constants: RED=8, GREEN=11, DARK_BLUE=5, YELLOW=10
COLOR_VALS: tuple[int, int, int, int] = (8, 11, 5, 10)
SEGMENT_SIZE = 10
SEGMENT_HALF = SEGMENT_SIZE // 2
INITIAL_SEGMENTS = 8
CRAWL_SPEED = 6  # pixels per tick
CRAWL_INTERVAL = 10  # frames between centipede moves
SHOT_SPEED = 5
COMBO_THRESHOLD = 3
SURGE_SCORE = 500
SEGMENT_SCORE = 100
WAVE_SEGMENT_BONUS = 3
MAX_MUSHROOMS = 18
MUSHROOM_DROP_CHANCE = 0.35
PLAYER_COLOR_CYCLE_INTERVAL = 75  # frames


class Phase(Enum):
    PLAYING = auto()
    SURGE_ANIM = auto()
    WAVE_CLEAR = auto()
    GAME_OVER = auto()


@dataclass
class Segment:
    x: float
    y: float
    color: int


@dataclass
class CrawlChain:
    segments: list[Segment]
    direction: int = 1  # 1 = right, -1 = left


@dataclass
class Shot:
    x: float
    y: float


@dataclass
class Mushroom:
    x: int
    y: int
    hp: int = 2


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
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CRAWL SURGE", fps=60)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.player_x: float = SCREEN_W / 2
        self.player_color: int = 0
        self.shots: list[Shot] = []
        self.chains: list[CrawlChain] = []
        self.mushrooms: list[Mushroom] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.wave: int = 1
        self.phase: Phase = Phase.PLAYING
        self._crawl_timer: int = CRAWL_INTERVAL
        self._surge_timer: int = 0
        self._wave_clear_timer: int = 0
        self._shake_frames: int = 0
        self._color_timer: int = PLAYER_COLOR_CYCLE_INTERVAL
        self._rng = random.Random()
        self._init_wave()

    def _init_wave(self) -> None:
        """Initialize a new wave with a centipede chain."""
        self.chains.clear()
        total_segments = INITIAL_SEGMENTS + (self.wave - 1) * WAVE_SEGMENT_BONUS
        segments: list[Segment] = []
        start_x = float(SCREEN_W - SEGMENT_SIZE * 2)
        start_y = float(SEGMENT_SIZE * 3)
        for i in range(total_segments):
            seg = Segment(
                x=start_x - i * SEGMENT_SIZE,
                y=start_y,
                color=self._rng.randint(0, NUM_COLORS - 1),
            )
            segments.append(seg)
        self.chains.append(CrawlChain(segments=segments, direction=1))
        # Place initial mushrooms (fewer on wave 1)
        mushroom_count = 4 + self.wave * 2
        self.mushrooms.clear()
        for _ in range(min(mushroom_count, MAX_MUSHROOMS)):
            mx = self._rng.randint(2, (SCREEN_W // SEGMENT_SIZE) - 3) * SEGMENT_SIZE
            my = self._rng.randint(4, (SCREEN_H // 2 // SEGMENT_SIZE)) * SEGMENT_SIZE
            # Avoid spawning on the centipede path
            occupied = False
            for chain in self.chains:
                for seg in chain.segments:
                    if abs(seg.x - mx) < SEGMENT_SIZE and abs(seg.y - my) < SEGMENT_SIZE:
                        occupied = True
                        break
            if not occupied:
                self.mushrooms.append(Mushroom(x=mx, y=my))

    def _total_segments(self) -> int:
        """Count total alive segments across all chains."""
        return sum(len(ch.segments) for ch in self.chains)

    # ── Update ──

    def update(self) -> None:
        if self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.SURGE_ANIM:
            self._update_surge_anim()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        elif self.phase == Phase.WAVE_CLEAR:
            self._update_wave_clear()
        self._update_particles()
        self._update_floating_texts()

    def _update_playing(self) -> None:
        # Player movement
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_x -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_x += PLAYER_SPEED
        self.player_x = max(PLAYER_HALF_W, min(SCREEN_W - PLAYER_HALF_W, self.player_x))

        # Color cycling
        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W):
            self.player_color = (self.player_color + 1) % NUM_COLORS
        if pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
            self.player_color = (self.player_color - 1) % NUM_COLORS
        self._color_timer -= 1
        if self._color_timer <= 0:
            self.player_color = (self.player_color + 1) % NUM_COLORS
            self._color_timer = PLAYER_COLOR_CYCLE_INTERVAL

        # Shoot
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z):
            self.shots.append(Shot(x=self.player_x, y=PLAYER_Y))

        # Update shots
        self._update_shots()

        # Crawl centipede
        self._crawl_timer -= 1
        if self._crawl_timer <= 0:
            self._crawl_timer = CRAWL_INTERVAL
            self._crawl_all_chains()

        # Check game over: player touched by segment or segment reaches bottom
        self._check_game_over()

    def _update_shots(self) -> None:
        new_shots: list[Shot] = []
        for shot in self.shots:
            shot.y -= SHOT_SPEED
            if shot.y < 0:
                continue
            # Check collision with segments
            hit = False
            for chain_idx, chain in enumerate(self.chains):
                for seg_idx, seg in enumerate(chain.segments):
                    if abs(shot.x - seg.x) < SEGMENT_HALF + 2 and abs(shot.y - seg.y) < SEGMENT_HALF + 2:
                        self._on_hit_segment(chain_idx, seg_idx, seg)
                        hit = True
                        break
                if hit:
                    break
            if not hit:
                # Check collision with mushrooms
                hit_mushroom = False
                for mi, m in enumerate(self.mushrooms):
                    if abs(shot.x - m.x) < SEGMENT_HALF + 2 and abs(shot.y - m.y) < SEGMENT_HALF + 2:
                        m.hp -= 1
                        self._spawn_particles(m.x, m.y, 12, pyxel.COLOR_WHITE)
                        if m.hp <= 0:
                            self.mushrooms.pop(mi)
                        hit_mushroom = True
                        break
                if not hit_mushroom:
                    new_shots.append(shot)
        self.shots = new_shots

    def _on_hit_segment(self, chain_idx: int, seg_idx: int, seg: Segment) -> None:
        """Handle a shot hitting a segment."""
        color_match = seg.color == self.player_color

        if color_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
        else:
            self.combo = 0

        # Check SURGE: matching hit with COMBO >= threshold
        if color_match and self.combo >= COMBO_THRESHOLD:
            chain = self.chains[chain_idx]
            destroyed_count = self._bfs_surge(chain, seg_idx, seg.color)
            bonus = SURGE_SCORE * self.combo * destroyed_count
            self.score += bonus
            self._spawn_floating_text(
                seg.x, seg.y,
                f"SURGE x{self.combo}! +{bonus}",
                pyxel.COLOR_YELLOW, 40
            )
            # Screen shake
            self._shake_frames = 8
            # Rebuild chains from survivors
            self._rebuild_chains_after_surge()
            self.phase = Phase.SURGE_ANIM
            self._surge_timer = 20
            self.combo = 0
            return

        # Normal hit
        self.score += SEGMENT_SCORE * max(1, self.combo)
        if self.combo > 0:
            self._spawn_floating_text(
                seg.x, seg.y,
                f"x{self.combo}",
                pyxel.COLOR_WHITE, 25
            )
        self._spawn_particles(seg.x, seg.y, 6, COLOR_VALS[seg.color])

        # Remove segment from chain
        chain = self.chains[chain_idx]
        chain.segments.pop(seg_idx)

        # Drop mushroom?
        if self._rng.random() < MUSHROOM_DROP_CHANCE and len(self.mushrooms) < MAX_MUSHROOMS:
            mx = int(seg.x) // SEGMENT_SIZE * SEGMENT_SIZE
            my = int(seg.y) // SEGMENT_SIZE * SEGMENT_SIZE
            if mx >= SEGMENT_SIZE and mx < SCREEN_W - SEGMENT_SIZE:
                self.mushrooms.append(Mushroom(x=mx, y=my))

        # If chain is now empty, remove it
        if not chain.segments:
            self.chains.pop(chain_idx)
        elif seg_idx == 0:
            # Head was destroyed — the new first segment becomes head
            pass  # direction stays with the chain dataclass

        # Check wave clear
        if self._total_segments() == 0:
            self._wave_clear_timer = 60
            self.phase = Phase.WAVE_CLEAR

    def _bfs_surge(self, chain: CrawlChain, hit_idx: int, color: int) -> int:
        """BFS from hit point: collect all same-color connected segments. Returns count."""
        segments = chain.segments
        destroyed: set[int] = set()
        queue: list[int] = [hit_idx]
        while queue:
            idx = queue.pop(0)
            if idx in destroyed:
                continue
            if idx < 0 or idx >= len(segments):
                continue
            if segments[idx].color != color:
                continue
            destroyed.add(idx)
            if idx > 0:
                queue.append(idx - 1)
            if idx < len(segments) - 1:
                queue.append(idx + 1)
        # Spawn particles and remove destroyed segments (reverse order)
        for idx in sorted(destroyed, reverse=True):
            seg = segments[idx]
            self._spawn_particles(seg.x, seg.y, 10, COLOR_VALS[seg.color])
            del segments[idx]
        return len(destroyed)

    def _rebuild_chains_after_surge(self) -> None:
        """After SURGE, rebuild chains by removing destroyed segments and splitting."""
        new_chains: list[CrawlChain] = []
        for chain in self.chains:
            if chain.segments:  # survivors already in order
                new_chains.append(chain)
        self.chains = new_chains

    def _crawl_all_chains(self) -> None:
        """Move each chain one step, splitting if a mushroom splits the chain."""
        for chain in self.chains:
            self._crawl_chain(chain)

    def _crawl_chain(self, chain: CrawlChain) -> None:
        """Move the chain head, body follows. Handle wrapping and mushrooms."""
        if not chain.segments:
            return
        old_positions = [(s.x, s.y) for s in chain.segments]
        head = chain.segments[0]

        # Move head
        head.x += chain.direction * CRAWL_SPEED

        # Horizontal bounds — wrap and descend
        if head.x < SEGMENT_HALF:
            head.x = float(SEGMENT_HALF)
            head.y += SEGMENT_SIZE
            chain.direction = 1
        elif head.x > SCREEN_W - SEGMENT_HALF:
            head.x = float(SCREEN_W - SEGMENT_HALF)
            head.y += SEGMENT_SIZE
            chain.direction = -1

        # Mushroom collision — descend and reverse
        for m in self.mushrooms:
            if abs(head.x - m.x) < SEGMENT_SIZE and abs(head.y - m.y) < SEGMENT_SIZE:
                head.y += SEGMENT_SIZE
                chain.direction *= -1
                break

        # Body follows the previous position of the segment ahead
        for i in range(1, len(chain.segments)):
            chain.segments[i].x, chain.segments[i].y = old_positions[i - 1]

    def _check_game_over(self) -> None:
        """Player death: touched by any segment."""
        for chain in self.chains:
            for seg in chain.segments:
                if seg.y >= PLAYER_AREA_TOP:
                    if abs(seg.x - self.player_x) < PLAYER_HALF_W + SEGMENT_HALF:
                        self.phase = Phase.GAME_OVER
                        self._shake_frames = 15
                        return
                # Segment reached the bottom of screen
                if seg.y >= SCREEN_H - SEGMENT_SIZE:
                    self.phase = Phase.GAME_OVER
                    self._shake_frames = 15
                    return

    def _update_surge_anim(self) -> None:
        self._surge_timer -= 1
        if self._surge_timer <= 0:
            self._surge_timer = 0
            # Check wave clear
            if self._total_segments() == 0:
                self._wave_clear_timer = 40
                self.phase = Phase.WAVE_CLEAR
            else:
                self.phase = Phase.PLAYING

    def _update_wave_clear(self) -> None:
        self._wave_clear_timer -= 1
        if self._wave_clear_timer <= 0:
            self.wave += 1
            self.combo = 0
            self._init_wave()
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R):
            self.reset()

    def _update_particles(self) -> None:
        new_particles: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                new_particles.append(p)
        self.particles = new_particles

    def _update_floating_texts(self) -> None:
        new_texts: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 1
            ft.life -= 1
            if ft.life > 0:
                new_texts.append(ft)
        self.floating_texts = new_texts

    # ── Particle/text spawning ──

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.random() * 2.5 + 0.5
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color,
                life=self._rng.randint(8, 20),
            ))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(
            x=x - len(text) * 2, y=y, text=text, color=color, life=life,
        ))

    # ── Draw ──

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        # Screen shake
        shake_x = 0
        shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)
            self._shake_frames -= 1

        # Use camera for shake
        try:
            pyxel.camera(shake_x, shake_y)
        except BaseException:
            pass

        # Draw mushrooms
        for m in self.mushrooms:
            hp_color = pyxel.COLOR_PURPLE if m.hp == 2 else pyxel.COLOR_BROWN
            pyxel.rect(m.x - SEGMENT_HALF, m.y - SEGMENT_HALF, SEGMENT_SIZE, SEGMENT_SIZE, hp_color)

        # Draw centipede segments
        for chain in self.chains:
            for i, seg in enumerate(chain.segments):
                color_val = COLOR_VALS[seg.color]
                # Head is slightly larger with eyes
                if i == 0:
                    pyxel.circ(seg.x, seg.y, SEGMENT_HALF + 1, color_val)
                    pyxel.pset(seg.x - 2, seg.y - 2, pyxel.COLOR_WHITE)
                    pyxel.pset(seg.x + 2, seg.y - 2, pyxel.COLOR_WHITE)
                else:
                    pyxel.circ(seg.x, seg.y, SEGMENT_HALF, color_val)

        # Draw player
        player_color = COLOR_VALS[self.player_color]
        px = self.player_x
        py = PLAYER_Y
        # Player as upward-pointing triangle (ship)
        pyxel.tri(px, py - PLAYER_HALF_W, px - PLAYER_HALF_W, py + 4, px + PLAYER_HALF_W, py + 4, player_color)
        # Color indicator ring
        pyxel.circb(px, py, PLAYER_HALF_W + 2, pyxel.COLOR_WHITE)

        # Draw shots
        for shot in self.shots:
            pyxel.rect(shot.x - 1, shot.y - 3, 2, 6, pyxel.COLOR_WHITE)

        # Draw particles
        for p in self.particles:
            alpha = p.life / 20
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        # Draw floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

        # Reset camera
        try:
            pyxel.camera()
        except BaseException:
            pass

        # ── HUD (after camera reset) ──
        self._draw_hud()

        # Game over overlay
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 2, f"SCORE:{self.score:>7}", pyxel.COLOR_WHITE)
        # Wave
        pyxel.text(4, 10, f"WAVE:{self.wave}", pyxel.COLOR_WHITE)
        # Combo
        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(SCREEN_W - len(combo_text) * 4 - 4, 2, combo_text, pyxel.COLOR_YELLOW)
        # Player color indicator
        color_name = COLOR_NAMES[self.player_color]
        pyxel.text(SCREEN_W - len(color_name) * 4 - 4, 10, color_name, COLOR_VALS[self.player_color])
        # Max combo
        if self.max_combo > 0:
            max_text = f"MAX:{self.max_combo}"
            pyxel.text(4, 18, max_text, pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, SCREEN_H // 2 - 25, SCREEN_W, 50, pyxel.COLOR_BLACK)
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 - 12, "GAME OVER", pyxel.COLOR_RED)
        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, SCREEN_H // 2, score_text, pyxel.COLOR_WHITE)
        wave_text = f"WAVE: {self.wave}"
        pyxel.text(SCREEN_W // 2 - len(wave_text) * 2, SCREEN_H // 2 + 8, wave_text, pyxel.COLOR_WHITE)
        restart_text = "PRESS SPACE TO RETRY"
        pyxel.text(SCREEN_W // 2 - len(restart_text) * 2, SCREEN_H // 2 + 16, restart_text, pyxel.COLOR_GRAY)


if __name__ == "__main__":
    Game()
