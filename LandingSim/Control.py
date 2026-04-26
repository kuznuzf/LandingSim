import pygame
import socket
import select
import sys

class ButtonControl:
    def __init__(self, x, y, width, heigth, color, flag, cmd, text):
        self.x = x
        self.y = y
        self.width = width
        self.heigth = heigth
        self.color = color
        self.flag = flag
        self.cmd = cmd
        self.text = text

def telemetry(data):
    parts = data.split()
    vel = "*****"
    hgt = "*****"
    pr_fuel = "****"
    for part in parts:
        if part.startswith('v'):
            vel = part[1:]
        elif part.startswith('h'):
            hgt = part[1:]
        elif part.startswith('f'):
            pr_fuel = part[1:]
    return vel, hgt, pr_fuel

def main():
    pygame.init()
    pygame.font.init()
    main_font = pygame.font.SysFont(None, 28)
    display = (400, 400)
    screen = pygame.display.set_mode(display)
    pygame.display.set_caption("Control Mission")

    Buttons = [ButtonControl(250, 50, 100, 40, (45, 255, 45), False, "s_l", main_font.render("standart", True, (255, 255, 255))),
               ButtonControl(250, 100, 100, 40, (255, 45, 45), False, "d_l", main_font.render("delete", True, (255, 255, 255))),
               ButtonControl(10, 150, 40, 40, (255, 45, 45), False, "m_o", main_font.render("", True, (255, 255, 255)))]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock.setblocking(False)
    try:
        sock.connect(('localhost', 5000))
        print("Подключено к симулятору")
        status_text = "Connected"
        status_color = (40, 255, 40)
    except ConnectionRefusedError:
        print("Сервер не запущен")
        status_text = "Not Connected"
        status_color = (255, 40, 40)
        sock = None
    
    clock = pygame.time.Clock()

    while True:
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                elif event.key == pygame.K_c:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        sock.connect(('localhost', 5000))
                        print("Подключено к симулятору")
                        status_text = "Connected"
                        status_color = (40, 255, 40)
                    except ConnectionRefusedError:
                        print("Сервер не запущен")
                        status_text = "Not Connected"
                        status_color = (255, 40, 40)
                        sock = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse = pygame.mouse.get_pos()
                if Buttons[0].flag == False:
                    if Buttons[0].x <= mouse[0] <= Buttons[0].x + Buttons[0].width and Buttons[0].y <= mouse[1] <= Buttons[0].y + Buttons[0].heigth:
                        Buttons[0].flag = True
                if Buttons[1].flag == False:
                    if Buttons[1].x <= mouse[0] <= Buttons[1].x + Buttons[1].width and Buttons[1].y <= mouse[1] <= Buttons[1].y + Buttons[1].heigth:
                        Buttons[1].flag = True
                if Buttons[2].flag == False:
                    if Buttons[2].x <= mouse[0] <= Buttons[2].x + Buttons[2].width and Buttons[2].y <= mouse[1] <= Buttons[2].y + Buttons[2].heigth:
                        Buttons[2].flag = True
            elif event.type == pygame.MOUSEBUTTONUP:
                Buttons[0].flag = False
                Buttons[1].flag = False
                Buttons[2].flag = False
        for i in range(len(Buttons)):
            if Buttons[i].flag: 
                pygame.draw.rect(screen, Buttons[i].color, [Buttons[i].x, Buttons[i].y, Buttons[i].width, Buttons[i].heigth], 0)
                if sock != None:
                    try:
                        sock.sendall(bytes(Buttons[i].cmd, "utf-8"))
                        Buttons[i].flag = False
                    except:
                        pass
            else: pygame.draw.rect(screen, (45, 45, 45), [Buttons[i].x, Buttons[i].y, Buttons[i].width, Buttons[i].heigth], 0)
        
        if sock:
            try:
                data = sock.recv(1024).decode().strip()
                if data:
                    vel, hgt, pr_fuel = telemetry(data)
                    velocity_text = f"Скорость: {vel} м/с"
                    height_text = f"Высота: {hgt} м"
                    fuel_text = f"Осталось топлива: {pr_fuel}%"
            except BlockingIOError:
                pass
            except ConnectionResetError:
                print("Сервер отключился")
                sock = None
                status_text = "Not Connected"
                status_color = (255, 40, 40)
            text_velocity = main_font.render(velocity_text, True, (255, 255, 255))
            screen.blit(text_velocity, (10, 60))
            text_height = main_font.render(height_text, True, (255, 255, 255))
            screen.blit(text_height, (10, 80))
            text_fuel = main_font.render(fuel_text, True, (255, 255, 255))
            screen.blit(text_fuel, (10, 100))
        
        text_connect = main_font.render(status_text, True, status_color)
        screen.blit(text_connect, (10, 20))
        text_manual = main_font.render("Режим управления", True, (255,255,255))
        screen.blit(text_manual, (55, 160))
        for i in range(len(Buttons)):
            screen.blit(Buttons[i].text, (Buttons[i].x + 10, Buttons[i].y + Buttons[i].heigth/3))
        
        pygame.display.flip()


if __name__ == "__main__":
    main()