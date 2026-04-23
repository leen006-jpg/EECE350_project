"""Connect screen — enter server IP and port."""
import pygame

# ── Colours (feel free to edit these) ────────────────────────────────────────
TITLE_COLOR  = (80,  220, 100)   # banner title
LABEL_COLOR  = (150, 150, 180)   # input labels
ERROR_COLOR  = (255,  80,  80)
WHITE        = (255, 255, 255)
import time

def draw(client, events):
    cx = client.screen.get_width() // 2

    # ── Title ─────────────────────────────────────────────────────────────────
    client._title_banner("Connect to Server")

    # ── Input boxes ───────────────────────────────────────────────────────────
    r_host = pygame.Rect(cx - 160, 130, 320, 34)
    r_port = pygame.Rect(cx - 160, 205, 320, 34)
    r_btn  = pygame.Rect(cx -  90, 260, 180, 42)

    # Focus switching
    for ev in events:
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if r_host.collidepoint(ev.pos): client.active_inp = "host"
            elif r_port.collidepoint(ev.pos): client.active_inp = "port"
            elif r_btn.collidepoint(ev.pos):  _do_connect(client)
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
            if client.active_inp == "host": client.active_inp = "port"
            else: _do_connect(client)

    client.inp_host = client._handle_text_input(events, client.active_inp == "host", client.inp_host)
    client.inp_port = client._handle_text_input(events, client.active_inp == "port", client.inp_port, 6)

    client._input_box(r_host, client.inp_host, client.active_inp == "host", "Server IP")
    client._input_box(r_port, client.inp_port, client.active_inp == "port", "Port")

    # ── Connect button ────────────────────────────────────────────────────────
    mouse = pygame.mouse.get_pos()
    client._button("Connect", r_btn, r_btn.collidepoint(mouse))
    client._error_label(320)


def _do_connect(client):
    try:
        client.net.connect(client.inp_host.strip(), int(client.inp_port.strip()))
        client.state   = "login"
        client.err_msg = ""
    except Exception as e:
        client._set_err(f"Connection failed: {e}")
