import math
import random
import pygame
from game.button import ChoiceButton

PLAYING = "PLAYING"
GAME_OVER = "GAME_OVER"
DEFAULT_TARGET_SCORE = 5

MIN_HISTORY_ROUNDS = 3
ADAPT_STRENGTH = 3
BEATS = {"ROCK": "SCISSORS", "PAPER": "ROCK", "SCISSORS": "PAPER"}  # key beats value

SHAKE_DURATION = 900   # ms of shaking before the picks are revealed
SHAKE_PUMPS = 3        # up-down bounces during the shake
SHAKE_HEIGHT = 16      # px


def draw_rock(surf, cx, cy):
    pts = [(-34, 8), (-26, -16), (-8, -30), (16, -28), (32, -10), (34, 14), (18, 30), (-14, 30)]
    pts = [(cx + x, cy + y) for x, y in pts]
    pygame.draw.polygon(surf, (125, 130, 142), pts)
    pygame.draw.polygon(surf, (205, 210, 220), pts, 3)
    pygame.draw.lines(surf, (85, 90, 102), False,
                      [(cx - 8, cy - 18), (cx - 2, cy - 4), (cx - 12, cy + 8)], 2)


def draw_paper(surf, cx, cy):
    l, r, t, b = cx - 27, cx + 27, cy - 34, cy + 34
    sheet = [(l, t), (r - 14, t), (r, t + 14), (r, b), (l, b)]
    pygame.draw.polygon(surf, (238, 240, 247), sheet)
    pygame.draw.polygon(surf, (90, 140, 210), sheet, 3)
    fold = [(r - 14, t), (r - 14, t + 14), (r, t + 14)]
    pygame.draw.polygon(surf, (185, 195, 215), fold)
    pygame.draw.polygon(surf, (90, 140, 210), fold, 2)
    for y in (cy - 4, cy + 10, cy + 24):
        pygame.draw.line(surf, (150, 160, 180), (l + 10, y), (r - 10, y), 2)


def draw_scissors(surf, cx, cy):
    cy -= 3
    for sx in (1, -1):  # two blades crossing in an X
        start = (cx + sx * 14, cy + 24)
        tip = (cx - sx * 24, cy - 34)
        pygame.draw.line(surf, (205, 210, 222), start, tip, 7)
        pygame.draw.line(surf, (110, 118, 135), start, tip, 2)
    for sx in (-1, 1):  # ring handles
        pygame.draw.circle(surf, (225, 185, 55), (cx + sx * 17, cy + 33), 9, 3)
    pygame.draw.circle(surf, (60, 66, 80), (cx, cy + 3), 4)  # pivot


ICONS = {"ROCK": draw_rock, "PAPER": draw_paper, "SCISSORS": draw_scissors}


class GameEngine:
    def __init__(self, width, height, target_score=DEFAULT_TARGET_SCORE):
        if target_score < 1:
            raise ValueError("target_score must be at least 1")
        self.width = width
        self.height = height
        self.target_score = target_score

        self.choices = ["ROCK", "PAPER", "SCISSORS"]
        btn_w, btn_h = 130, 50
        gap = 20
        total_w = 3 * btn_w + 2 * gap
        start_x = (width - total_w) // 2
        btn_y = height - 85

        self.buttons = [
            ChoiceButton("ROCK", pygame.Rect(start_x, btn_y, btn_w, btn_h), (160, 50, 50), (200, 70, 70)),
            ChoiceButton("PAPER", pygame.Rect(start_x + btn_w + gap, btn_y, btn_w, btn_h), (40, 100, 170), (60, 130, 210)),
            ChoiceButton("SCISSORS", pygame.Rect(start_x + 2 * (btn_w + gap), btn_y, btn_w, btn_h), (180, 140, 30), (220, 180, 50)),
        ]

        self.display_duration = 1800

        self.font_title = pygame.font.SysFont(None, 36)
        self.font_hud = pygame.font.SysFont(None, 26)
        self.font_arena = pygame.font.SysFont(None, 32)

        self.reset_match()

    def reset_match(self):
        """Put every piece of per-match state back to a fresh start."""
        self.state = PLAYING
        self.winner = None

        self.player_choice = None
        self.cpu_choice = None
        self.player_history = []
        self.last_outcome = None
        self.result_text = "Make your move!"
        self.result_color = (220, 225, 235)

        self.player_score = 0
        self.cpu_score = 0

        self.round_resolved_time = 0   # moment the picks are revealed
        self.showing_result = False

    def is_revealing(self):
        """True while the shake animation is still playing."""
        return self.showing_result and pygame.time.get_ticks() < self.round_resolved_time

    def determine_winner(self, player, cpu):
        if player == cpu:
            return "TIE"

        rules = {
            ("ROCK", "SCISSORS"): "PLAYER",
            ("SCISSORS", "PAPER"): "PLAYER",
            ("PAPER", "ROCK"): "PLAYER",
            ("SCISSORS", "ROCK"): "CPU",
            ("PAPER", "SCISSORS"): "CPU",
            ("ROCK", "PAPER"): "CPU",
        }
        return rules.get((player, cpu), "TIE")

    def choose_cpu_move(self):
        total = len(self.player_history)
        if total < MIN_HISTORY_ROUNDS:
            return random.choice(self.choices)

        weights = []
        for cpu_move in self.choices:
            beaten = BEATS[cpu_move]
            freq = self.player_history.count(beaten) / total
            weights.append(1 + ADAPT_STRENGTH * freq)
        return random.choices(self.choices, weights=weights, k=1)[0]

    def play_round(self, choice):
        if self.state != PLAYING:
            return

        self.player_choice = choice
        self.cpu_choice = self.choose_cpu_move()   # decide BEFORE recording this throw
        self.player_history.append(choice)

        outcome = self.determine_winner(self.player_choice, self.cpu_choice)
        self.last_outcome = outcome
        if outcome == "PLAYER":
            self.player_score += 1
            self.result_text = f"You Win! {self.player_choice} beats {self.cpu_choice}."
            self.result_color = (80, 230, 120)
        elif outcome == "CPU":
            self.cpu_score += 1
            self.result_text = f"You Lose! {self.cpu_choice} beats {self.player_choice}."
            self.result_color = (240, 80, 80)
        else:
            self.result_text = f"It's a Draw! Both picked {self.player_choice}."
            self.result_color = (240, 210, 80)

        self.showing_result = True
        # The 1.8 s result window now starts at the reveal, after the shake.
        self.round_resolved_time = pygame.time.get_ticks() + SHAKE_DURATION

        if self.player_score >= self.target_score:
            self.state = GAME_OVER
            self.winner = "PLAYER"
        elif self.cpu_score >= self.target_score:
            self.state = GAME_OVER
            self.winner = "CPU"

    def handle_event(self, event):
        if self.is_revealing():
            return   # input is locked until the picks are revealed

        if self.state == GAME_OVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset_match()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn.contains(event.pos):
                    self.play_round(btn.choice_name)
                    break

    def update(self):
        now = pygame.time.get_ticks()
        if (self.state == PLAYING and self.showing_result
                and now - self.round_resolved_time >= self.display_duration):
            self.player_choice = None
            self.cpu_choice = None
            self.result_text = "Make your move!"
            self.result_color = (190, 195, 205)
            self.showing_result = False

    def render_arena(self, screen, revealing):
        bob = 0
        if revealing:
            phase = 1 - (self.round_resolved_time - pygame.time.get_ticks()) / SHAKE_DURATION
            bob = -int(SHAKE_HEIGHT * abs(math.sin(phase * SHAKE_PUMPS * math.pi)))

        slots = (
            (self.width // 4, "YOU", (100, 180, 255), self.player_choice),
            (3 * self.width // 4, "CPU", (255, 120, 120), self.cpu_choice),
        )
        for cx, label, color, move in slots:
            lab = self.font_hud.render(label, True, color)
            screen.blit(lab, (cx - lab.get_width() // 2, 88))

            panel = pygame.Rect(0, 0, 100, 90)
            panel.center = (cx, 152)
            pygame.draw.rect(screen, (32, 38, 50), panel, border_radius=10)
            pygame.draw.rect(screen, (55, 64, 82), panel, width=2, border_radius=10)

            if move is None:
                q = self.font_title.render("?", True, (70, 78, 95))
                screen.blit(q, (cx - q.get_width() // 2, 152 - q.get_height() // 2))
            else:
                shown = "ROCK" if revealing else move   # fists while shaking
                ICONS[shown](screen, cx, 152 + bob)

        vs = self.font_hud.render("VS", True, (120, 128, 145))
        screen.blit(vs, (self.width // 2 - vs.get_width() // 2, 152 - vs.get_height() // 2))

    def render_game_over(self, screen):
        if self.winner == "PLAYER":
            banner, color = "PLAYER is the Champion!", (80, 230, 120)
        else:
            banner, color = "CPU is the Champion!", (240, 80, 80)

        banner_surf = self.font_title.render(banner, True, color)
        screen.blit(banner_surf, (self.width // 2 - banner_surf.get_width() // 2, 245))

        hint_surf = self.font_hud.render("Press R to restart", True, (225, 225, 230))
        screen.blit(hint_surf, (self.width // 2 - hint_surf.get_width() // 2, self.height - 60))

    def render(self, screen):
        screen.fill((24, 28, 36))
        revealing = self.is_revealing()

        title_surf = self.font_title.render("Rock Paper Scissors", True, (245, 245, 245))
        screen.blit(title_surf, (self.width // 2 - title_surf.get_width() // 2, 14))

        # Hold back the pending point until the reveal so the HUD doesn't spoil it.
        p_score, c_score = self.player_score, self.cpu_score
        if revealing:
            if self.last_outcome == "PLAYER":
                p_score -= 1
            elif self.last_outcome == "CPU":
                c_score -= 1

        p_surf = self.font_hud.render(f"Player Score: {p_score}", True, (100, 180, 255))
        c_surf = self.font_hud.render(f"CPU Score: {c_score}", True, (255, 120, 120))
        screen.blit(p_surf, (35, 52))
        screen.blit(c_surf, (self.width - c_surf.get_width() - 35, 52))

        pygame.draw.line(screen, (45, 52, 66), (25, 82), (self.width - 25, 82), 2)

        self.render_arena(screen, revealing)

        if revealing:
            text, color = "Rock... Paper... Scissors!", (190, 195, 205)
        else:
            text, color = self.result_text, self.result_color
        res_surf = self.font_arena.render(text, True, color)
        screen.blit(res_surf, (self.width // 2 - res_surf.get_width() // 2, 205))

        if self.state == GAME_OVER:
            if not revealing:
                self.render_game_over(screen)
        else:
            for btn in self.buttons:
                btn.render(screen)