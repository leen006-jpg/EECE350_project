"""Login screen — enter username."""
import pygame


def draw(client, events):
    cx = client.screen.get_width() // 2
    client._title_banner("Enter Your Username")

    r_user = pygame.Rect(cx - 160, 150, 320, 34)
    r_btn  = pygame.Rect(cx -  80, 210, 160, 42)

    for ev in events:
        if ev.type == pygame.MOUSEBUTTONDOWN and r_btn.collidepoint(ev.pos):
            _do_login(client)
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
            _do_login(client)

    client.inp_user = client._handle_text_input(events, True, client.inp_user, 20)
    client._input_box(r_user, client.inp_user, True, "Username  (max 20 chars)")

    mouse = pygame.mouse.get_pos()
    client._button("Join", r_btn, r_btn.collidepoint(mouse))
    client._error_label(275)


def _do_login(client):
    name = client.inp_user.strip()
    if name:
        client.net.send({"type": "join", "username": name})
        client.err_msg = ""
