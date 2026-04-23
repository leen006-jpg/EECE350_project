"""
Watch screen — spectator view
==============================
Spectators see the live game board (same renderer as game.py)
plus a banner showing they are watching, and a Leave button.
"""
import pygame
from screens import game as game_screen

ORANGE = (255, 165,  0)
WHITE  = (255, 255, 255)
DIM    = ( 70,  70, 90)


def draw(client, events):
    # Reuse the full game renderer (board + panel)
    game_screen.draw(client, events)

    # ── Spectator banner across the top ───────────────────────────────────────
    banner = pygame.Rect(0, 0, client.gw * 20, 32)
    pygame.draw.rect(client.screen, (40, 25, 0), banner)
    pygame.draw.rect(client.screen, ORANGE, banner, 2)

    p1 = client.usernames.get("1", "P1")
    p2 = client.usernames.get("2", "P2")
    msg = client.f_sm.render(f">> SPECTATING  —  {p1}  vs  {p2}", True, ORANGE)
    client.screen.blit(msg, msg.get_rect(centerx=banner.centerx, centery=banner.centery))

    # ── Leave button ──────────────────────────────────────────────────────────
    r_leave = pygame.Rect(banner.right - 110, 3, 105, 26)
    mouse   = pygame.mouse.get_pos()
    hover   = r_leave.collidepoint(mouse)
    pygame.draw.rect(client.screen, (120, 40, 40) if hover else (80, 25, 25),
                     r_leave, border_radius=5)
    pygame.draw.rect(client.screen, (200, 80, 80), r_leave, 1, border_radius=5)
    lbl = client.f_sm.render("<< Leave", True, WHITE)
    client.screen.blit(lbl, lbl.get_rect(center=r_leave.center))

    for ev in events:
        if ev.type == pygame.MOUSEBUTTONDOWN and r_leave.collidepoint(ev.pos):
            client.state    = "lobby"
            client.gs       = {}
            client.chat_log = []
