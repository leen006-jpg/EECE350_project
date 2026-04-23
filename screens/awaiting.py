"""Awaiting screen — challenger waits here after sending challenge.
game_start from the server will automatically move state to 'game'."""
import pygame

DIM    = (70,  70,  90)
GRAY   = (120, 120, 140)
ORANGE = (255, 165,   0)


def draw(client, events):
    cx = client.screen.get_width() // 2
    client._title_banner("Challenge Sent!")

    msg = f"Waiting for  {client.challenge_target}  to accept…"
    client._text(client.f_md, msg, ORANGE, cx=cx, y=150)
    client._text(client.f_sm, "The game will start automatically once they're ready.", GRAY, cx=cx, y=190)

    r_back = pygame.Rect(cx - 70, 250, 140, 38)
    mouse  = pygame.mouse.get_pos()
    client._button("← Cancel", r_back, r_back.collidepoint(mouse),
                   (100, 30, 30), (140, 40, 40))

    for ev in events:
        if ev.type == pygame.MOUSEBUTTONDOWN and r_back.collidepoint(ev.pos):
            client.state = "lobby"
            client.challenge_target = ""
