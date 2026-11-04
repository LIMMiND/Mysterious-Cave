"""
ТАИНСТВЕННАЯ ПЕЩЕРА — расширенная версия (pygame)
Бесконечное подземелье: процедурные этажи, разные монстры, квесты, лавка, эффекты.
Графика и звуки-эффекты создаются кодом. Музыка берётся из папки "music" рядом с game.py:
    music/mainmenusong.mp3  - главное меню
    music/bosssong.mp3      - бой с Королём гоблинов

Управление:
    WASD / стрелки   - ходить (в врага = удар, в NPC / бочку / фонтан = действие)
    Пробел           - пропустить ход
    Q                - переключить оружие (меч / секира)
    H                - выпить зелье лечения
    1-8              - использовать предмет из панели
    M                - звук вкл/выкл
    F11              - полный экран
    Esc              - пауза
"""
import json
import math
import os
import random
import sys
from array import array
from collections import deque

import pygame

# ============================================================ настройки
PX = 16                       # размер "настоящего" пикселя-арта
SCALE = 3
TILE = PX * SCALE             # 48 px на экране
VIEW_COLS, VIEW_ROWS = 20, 12  # сколько клеток видно на экране
MAP_W, MAP_H = VIEW_COLS * TILE, VIEW_ROWS * TILE
COLS, ROWS = 64, 40           # размер этажа в клетках
HUD_H = 144
WIN_W, WIN_H = MAP_W, MAP_H + HUD_H
FPS = 60
WINDOW_W, WINDOW_H = 1440, 900   # размер окна на экране (игра масштабируется под него)
BASE_LIGHT = 6                # радиус света факела (в клетках)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "music")
SAVE_FILE = os.path.join(BASE_DIR, "cave_records.json")
AXE_DROP = 0.10               # шанс выпадения секиры с огра

TEXT = (225, 220, 235)
GRAY = (150, 145, 165)
RED = (235, 90, 90)
GOLD = (240, 200, 70)
GREEN = (110, 220, 120)
BLUE = (110, 170, 255)
ORANGE = (255, 150, 50)
PURPLE = (190, 120, 255)
CYAN = (90, 230, 230)
PANEL_BG = (20, 17, 28)
PANEL_BORDER = (110, 85, 140)


# ============================================================ данные
ITEMS = {
    "heal":   dict(name="Зелье лечения",  kind="potion", col=(205, 40, 65),   light=(255, 150, 165), price=25, desc="Восстанавливает 40 HP"),
    "elixir": dict(name="Эликсир жизни",  kind="potion", col=(240, 120, 200), light=(255, 210, 240), price=70, desc="Полностью восстанавливает здоровье"),
    "rage":   dict(name="Зелье ярости",   kind="potion", col=(230, 90, 30),   light=(255, 190, 120), price=40, desc="+50% урона на 10 ходов"),
    "iron":   dict(name="Зелье стали",    kind="potion", col=(140, 150, 175), light=(220, 225, 240), price=40, desc="Получаемый урон -50% на 10 ходов"),
    "haste":  dict(name="Зелье скорости", kind="potion", col=(60, 220, 220),  light=(200, 255, 255), price=45, desc="Враги ходят вдвое реже, 8 ходов"),
    "vamp":   dict(name="Зелье вампира",  kind="potion", col=(140, 40, 150),  light=(220, 150, 230), price=50, desc="Лечит от твоих ударов, 12 ходов"),
    "fire":   dict(name="Свиток огня",    kind="scroll", col=(255, 110, 30),  light=None,            price=55, desc="Взрыв вокруг: большой урон врагам рядом"),
    "map":    dict(name="Свиток карты",   kind="scroll", col=(80, 200, 120),  light=None,            price=35, desc="Открывает карту всего этажа"),
}
ORDER = ["heal", "elixir", "rage", "iron", "haste", "vamp", "fire", "map"]
DROP_W = {"heal": 40, "elixir": 5, "rage": 10, "iron": 10, "haste": 8, "vamp": 8, "fire": 10, "map": 9}
BUFF_TURNS = {"rage": 10, "iron": 10, "haste": 8, "vamp": 12}
STATUS_NAME = {"rage": "Ярость", "iron": "Сталь", "haste": "Скорость", "vamp": "Вампир",
               "poison": "Яд", "burn": "Горение"}
STATUS_COL = {"rage": ORANGE, "iron": (170, 180, 205), "haste": CYAN, "vamp": PURPLE,
              "poison": GREEN, "burn": ORANGE}

# (ключ, название, описание, базовая цена, рост цены, максимум уровней)
UPGRADES = [
    ("weapon", "Заточка клинка",    "+2 к мин. и +3 к макс. урону",  50, 1.7, 10),
    ("armor",  "Кольчуга",          "Получаемый урон -2 и новая деталь доспеха", 60, 1.8, 10),
    ("vit",    "Эликсир стойкости", "+20 к максимуму здоровья",      45, 1.5, 10),
    ("lamp",   "Масло для фонаря",  "+1 к радиусу света",            40, 1.9, 4),
    ("crit",   "Точильный камень",  "+5% к шансу критического удара", 55, 1.7, 5),
]
# появляется в лавке только после получения секиры
AXE_UPGRADE = ("axe", "Заточка секиры", "+4 к мин. и +6 к макс. урону секиры", 80, 1.7, 8)

ARMOR_STAGES = ["", "наплечники и наколенники", "нагрудник", "шлем", "перчатки и сапоги",
                "плюмаж на шлеме", "плащ", "золотая отделка", "металлический щит",
                "шипы на наплечниках", "полный золотой доспех"]

MOBS = {
    "goblin": dict(name="Гоблин", plural="гоблинов", hp=26, dmg=(5, 12), xp=10, gold=(8, 18), sight=8,
                   col=(90, 170, 70), desc="Обычный воин. Бьёт в ближнем бою."),
    "bat":    dict(name="Летучая мышь", plural="летучих мышей", hp=12, dmg=(3, 7), xp=7, gold=(3, 9), sight=9,
                   col=(120, 85, 150), desc="Двигается дважды за ход. Кусает и лечится."),
    "slime":  dict(name="Слизень", plural="слизней", hp=34, dmg=(4, 9), xp=12, gold=(6, 14), sight=6,
                   col=(90, 205, 120), desc="Медленный. Его укус отравляет."),
    "archer": dict(name="Скелет-лучник", plural="скелетов-лучников", hp=20, dmg=(4, 9), xp=16, gold=(10, 22), sight=9,
                   col=(225, 220, 200), desc="Стреляет издалека и держит дистанцию."),
    "mage":   dict(name="Колдун", plural="колдунов", hp=22, dmg=(5, 10), xp=20, gold=(14, 28), sight=8,
                   col=(160, 80, 210), desc="Метает огненные шары и поджигает."),
    "ogre":   dict(name="Огр", plural="огров", hp=75, dmg=(16, 26), xp=40, gold=(25, 50), sight=7,
                   col=(150, 110, 80), desc="Медленный. Замахивается дубиной — успей отойти! С него может выпасть секира."),
    "king":   dict(name="Король гоблинов", plural="королей", hp=220, dmg=(12, 20), xp=150, gold=(120, 200), sight=12,
                   col=(240, 200, 70), desc="БОСС (каждые 5 этажей). Призывает гоблинов."),
}

ELDER_NAMES = ["Старец Альдрик", "Отшельница Мира", "Рудокоп Брон", "Хранитель Эдвин", "Знахарка Лира"]
MERCH_NAMES = ["Гном Бэрри", "Торговка Сильва", "Бродячий гном Торин", "Лавочник Гром"]
ELDER_HELLO = [
    "Путник! Не думал встретить живую душу в этих проклятых залах.",
    "Подойди ближе, не бойся. Я не кусаюсь... в отличие от местных обитателей.",
    "Ох, наконец-то герой! Я так долго ждал кого-нибудь вроде тебя.",
]
ELDER_WAIT = [
    "Ты ещё здесь? Поспеши, дело не ждёт!",
    "Удачи тебе, смельчак. Да хранят тебя боги.",
    "Я верю, что у тебя всё получится.",
]
MERCH_HELLO = [
    "Эй, герой! Лучшие товары под землёй — только у меня!",
    "Золото любит счёт, а я люблю золото. Выбирай!",
    "Зелья, свитки, заточка... Что тебе по карману?",
]
STORIES = {
    "kill": ["Твари совсем распоясались и не дают спать. {t}.",
             "Эти монстры разрушили мой лагерь. {t}, прошу тебя."],
    "killkind": ["Эти твари мне особенно ненавистны. {t}!",
                 "Они украли мои запасы и разбежались. {t}, и я буду в долгу."],
    "gold": ["Мне нужны деньги на лекарство для внука. {t}.",
             "Хочу выкупить свою лавку наверху. {t}."],
    "chests": ["Говорят, в сундуках лежат древние реликвии. {t}.",
               "В одном из сундуков моя фамильная вещь. {t}."],
    "barrels": ["В бочках спрятаны мои припасы! {t}.",
                "Эти бочки мешают пройти, да и внутри что-то есть. {t}."],
    "descend": ["Внизу остался мой брат. {t}.",
                "Я слышал зов из глубин пещеры. {t}."],
}


def mob_pool(depth):
    pool = [("goblin", 10), ("bat", 6)]
    if depth >= 2:
        pool.append(("slime", 6))
    if depth >= 3:
        pool.append(("archer", 5))
    if depth >= 4:
        pool.append(("mage", 4))
    if depth >= 5:
        pool.append(("ogre", 3))
    return pool


# ============================================================ мелкие помощники
def sign(v):
    return (v > 0) - (v < 0)


def clamp01(v):
    return max(0.0, min(1.0, v))


def ease(v):
    """Плавное замедление к концу (ease-out cubic)."""
    v = clamp01(v)
    return 1 - (1 - v) ** 3


def ease_back(v):
    """Лёгкий «перелёт» и возврат — для всплывающих окон."""
    v = clamp01(v)
    c = 1.70158
    return 1 + (c + 1) * (v - 1) ** 3 + c * (v - 1) ** 2


def tc(x, y):
    """Центр клетки в пикселях мира."""
    return x * TILE + TILE // 2, y * TILE + TILE // 2


def line_pts(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


def wrap(text, font, width):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if font.size(test)[0] <= width:
            cur = test
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def get_font(size, bold=False):
    return pygame.font.SysFont(
        "segoeui,arial,dejavusans,liberationsans,notosans,helvetica", size, bold=bold)


def draw_text(surf, font, s, color, x, y, align="l", shadow=True, alpha=255):
    img = font.render(s, True, color)
    if align == "c":
        x -= img.get_width() // 2
    elif align == "r":
        x -= img.get_width()
    if alpha < 255:
        img.set_alpha(alpha)
    if shadow:
        sh = font.render(s, True, (0, 0, 0))
        if alpha < 255:
            sh.set_alpha(alpha)
        surf.blit(sh, (x + 2, y + 2))
    surf.blit(img, (x, y))
    return img.get_width()


def panel(surf, rect, border=PANEL_BORDER, alpha=240):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    s.fill((PANEL_BG[0], PANEL_BG[1], PANEL_BG[2], alpha))
    surf.blit(s, rect.topleft)
    pygame.draw.rect(surf, border, rect, 3)


def load_records():
    rec = {"depth": 0, "gold": 0, "kills": 0, "runs": 0}
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            rec.update(json.load(f))
    except Exception:
        pass
    return rec


def save_records(rec):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(rec, f)
    except Exception:
        pass


# ============================================================ звук (синтез кодом)
class Sfx:
    def __init__(self):
        self.ok = False
        self.on = True
        self.snd = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 1024)
            info = pygame.mixer.get_init()
            if not info or info[1] != -16:
                return
            rate, ch = info[0], info[2]
            recipes = {
                "hit":    [(220, 80, .09, "n"), (160, 60, .06, "s")],
                "crit":   [(420, 100, .12, "n"), (600, 200, .10, "s")],
                "hurt":   [(180, 60, .15, "s"), (120, 50, .10, "n")],
                "coin":   [(880, 880, .05, "s"), (1320, 1320, .09, "s")],
                "potion": [(400, 900, .16, "t")],
                "level":  [(523, 523, .08, "s"), (659, 659, .08, "s"), (784, 784, .08, "s"), (1047, 1047, .18, "s")],
                "shoot":  [(900, 300, .10, "s")],
                "boom":   [(150, 40, .30, "n")],
                "ui":     [(700, 700, .04, "s")],
                "quest":  [(660, 660, .08, "t"), (880, 880, .16, "t")],
                "stairs": [(300, 150, .25, "t")],
                "die":    [(300, 60, .50, "s")],
                "bump":   [(120, 90, .05, "n")],
                "whoosh": [(500, 160, .16, "n")],
                "axe":    [(260, 70, .18, "n"), (110, 40, .20, "s")],
                "equip":  [(520, 780, .07, "s"), (780, 1040, .07, "s")],
            }
            for name, segs in recipes.items():
                self.snd[name] = self._synth(segs, rate, ch)
            self.ok = True
        except Exception:
            self.ok = False

    @staticmethod
    def _synth(segs, rate, ch, vol=0.30):
        buf = array("h")
        for f0, f1, dur, wave in segs:
            n = int(rate * dur)
            ph = 0.0
            for i in range(n):
                k = i / n
                ph += (f0 + (f1 - f0) * k) / rate
                if wave == "s":
                    v = 1.0 if (ph % 1.0) < 0.5 else -1.0
                elif wave == "n":
                    v = random.uniform(-1, 1)
                else:
                    v = math.sin(ph * math.tau)
                s = int(v * ((1 - k) ** 1.5) * vol * 32767)
                for _ in range(ch):
                    buf.append(s)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.ok and self.on and name in self.snd:
            self.snd[name].play()


# ============================================================ музыка (файлы из папки music)
class Music:
    """Плавные переходы между треками: затухание -> смена -> нарастание."""
    OUT_MS, IN_MS, MASTER = 1100.0, 1800.0, 0.55

    def __init__(self, sfx):
        self.sfx = sfx
        self.paths = {k: self._find(n) for k, n in (("menu", "mainmenusong"), ("boss", "bosssong"))}
        self.cur = None       # что сейчас играет
        self.want = None      # что должно играть
        self.vol = 0.0        # текущая "плавная" громкость 0..1
        self.ok = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 1024)
            self.ok = True
        except Exception:
            pass

    @staticmethod
    def _find(name):
        for folder in (MUSIC_DIR, BASE_DIR):
            for ext in (".mp3", ".ogg", ".wav", ".flac"):
                p = os.path.join(folder, name + ext)
                if os.path.isfile(p):
                    return p
        return None

    def play(self, key):
        """key: 'menu', 'boss' или None (тишина). Переход плавный."""
        self.want = key

    def update(self, dt):
        if not self.ok:
            return
        try:
            if self.cur != self.want:
                self.vol -= dt / self.OUT_MS
                if self.vol <= 0 or self.cur is None:
                    self.vol = 0.0
                    pygame.mixer.music.stop()
                    self.cur = self.want
                    path = self.paths.get(self.want) if self.want else None
                    if path:
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.set_volume(0.0)
                        pygame.mixer.music.play(-1)
            elif self.cur:
                self.vol = min(1.0, self.vol + dt / self.IN_MS)
            pygame.mixer.music.set_volume(self.vol * self.MASTER if self.sfx.on else 0.0)
        except Exception:
            self.cur = self.want      # нет файла / ошибка кодека — играем без музыки


# ============================================================ пиксель-арт
def new_sprite():
    return pygame.Surface((PX, PX), pygame.SRCALPHA)


def scaled(surf, k=SCALE):
    return pygame.transform.scale(surf, (PX * k, PX * k))


def rect(s, color, x, y, w, h):
    pygame.draw.rect(s, color, (x, y, w, h))


def shadow(s, x=3, w=10):
    rect(s, (0, 0, 0, 70), x, 14, w, 2)


def whiten(surf):
    m = pygame.mask.from_surface(surf)
    return m.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))


def ip(x, y):
    return int(round(x)), int(round(y))


def floor_tile(seed, deco=0):
    rng = random.Random(seed)
    s = pygame.Surface((PX, PX))
    s.fill((38, 34, 44))
    for _ in range(14):
        s.set_at((rng.randrange(PX), rng.randrange(PX)),
                 rng.choice([(46, 41, 54), (32, 28, 38), (52, 46, 60)]))
    pygame.draw.rect(s, (30, 26, 36), (0, 0, PX, PX), 1)
    if deco == 1:      # мох
        for _ in range(10):
            s.set_at((rng.randrange(1, 15), rng.randrange(1, 15)),
                     rng.choice([(48, 78, 50), (40, 66, 44), (58, 92, 58)]))
    elif deco == 2:    # кости
        rect(s, (205, 200, 185), 4, 10, 7, 1)
        s.set_at((3, 9), (205, 200, 185)); s.set_at((3, 11), (205, 200, 185))
        s.set_at((11, 9), (205, 200, 185)); s.set_at((11, 11), (205, 200, 185))
        rect(s, (215, 210, 195), 9, 4, 3, 3)
        s.set_at((9, 5), (30, 25, 30)); s.set_at((11, 5), (30, 25, 30))
    return scaled(s)


def wall_tile():
    s = pygame.Surface((PX, PX))
    s.fill((78, 64, 92))
    mortar = (36, 28, 46)
    for i, y in enumerate((0, 5, 10)):
        pygame.draw.line(s, (98, 82, 112), (0, y + 1), (PX, y + 1))
        pygame.draw.line(s, mortar, (0, y), (PX, y))
        offset = 0 if i % 2 == 0 else 4
        for x in range(offset, PX, 8):
            pygame.draw.line(s, mortar, (x, y), (x, y + 4))
    pygame.draw.line(s, mortar, (0, 15), (PX, 15))
    return scaled(s)


def torch_sprite(f):
    s = new_sprite()
    rect(s, (60, 45, 35), 6, 7, 4, 2)
    rect(s, (100, 78, 55), 7, 8, 2, 6)
    if f == 0:
        pygame.draw.polygon(s, (255, 150, 40), [(8, 1), (5, 7), (11, 7)])
        pygame.draw.polygon(s, (255, 230, 120), [(8, 3), (7, 7), (9, 7)])
    else:
        pygame.draw.polygon(s, (255, 130, 35), [(9, 2), (5, 7), (11, 7)])
        pygame.draw.polygon(s, (255, 220, 110), [(8, 4), (7, 7), (9, 7)])
    return scaled(s)


# ---------------------------------------------------------------- герой: кадры анимации
def armor_palette(lvl):
    """(тёмный, средний, светлый) цвет металла по уровню кольчуги."""
    if lvl >= 10:
        return (170, 120, 30), (225, 175, 60), (255, 235, 140)
    if lvl >= 4:
        return (125, 135, 160), (180, 190, 212), (232, 238, 252)
    return (95, 100, 115), (140, 145, 160), (195, 200, 215)


def draw_sword(s, hand, ang):
    hx, hy = hand
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    pygame.draw.line(s, (120, 70, 40), ip(hx, hy), ip(hx - ca * 2, hy - sa * 2))            # рукоять
    pygame.draw.line(s, (205, 210, 225), ip(hx + ca, hy + sa), ip(hx + ca * 8, hy + sa * 8))  # клинок
    pygame.draw.line(s, (255, 230, 120), ip(hx - sa * 1.6, hy + ca * 1.6),
                     ip(hx + sa * 1.6, hy - ca * 1.6))                                      # гарда


def draw_axe(s, hand, ang):
    hx, hy = hand
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    d, p = (ca, sa), (-sa, ca)
    pygame.draw.line(s, (120, 80, 45), ip(hx - ca * 2, hy - sa * 2), ip(hx + ca * 8, hy + sa * 8))  # древко
    cx, cy = hx + ca * 6, hy + sa * 6
    pts = [ip(cx - d[0] * 2, cy - d[1] * 2),
           ip(cx - d[0] * 2 + p[0] * 3.2, cy - d[1] * 2 + p[1] * 3.2),
           ip(cx + d[0] * 2 + p[0] * 3.8, cy + d[1] * 2 + p[1] * 3.8),
           ip(cx + d[0] * 2.5, cy + d[1] * 2.5)]
    pygame.draw.polygon(s, (170, 176, 195), pts)
    pygame.draw.polygon(s, (70, 72, 90), pts, 1)
    pygame.draw.line(s, (240, 245, 255), pts[1], pts[2])                                   # лезвие


def build_player(anim, f, armor, weapon):
    """16x16 герой, смотрит ВПРАВО. anim: idle(2) / walk(4) / attack(3)."""
    s = new_sprite()
    dark, mid, light = armor_palette(armor)
    trim = (255, 215, 80) if armor >= 7 else light
    b = 0
    lf = rf = 14
    if anim == "idle":
        b = f % 2                                   # дыхание
    elif anim == "walk":
        b = 1 if f in (1, 3) else 0                 # шаг: корпус пружинит
        lf = 13 if f == 1 else 14
        rf = 13 if f == 3 else 14
    if anim == "attack":
        hand, ang = [((11, 7), -125), ((11, 8), -15), ((12, 9), 55)][f]
        b = 0
    else:
        hand, ang = (12, 11 + b), -90

    shadow(s, 4, 8)
    if armor >= 6:                                  # плащ (за спиной)
        rect(s, (150, 30, 45), 3, 6 + b, 3, 9 - b)
        rect(s, (105, 18, 32), 3, 13, 3, 2)
    sh_col = (120, 90, 60) if armor < 8 else mid     # щит
    rect(s, sh_col, 1, 8 + b, 3, 4)
    rect(s, (235, 200, 90) if armor < 8 else trim, 2, 9 + b, 1, 2)
    arm = (170, 70, 35)
    rect(s, arm, 4, 8 + b, 1, 4)                    # левая рука (со щитом)
    pygame.draw.line(s, arm, (11, 8 + b), ip(*hand))  # правая рука к оружию
    rect(s, (205, 95, 45), 5, 7 + b, 6, 7 - b)      # ряса
    if armor >= 2:                                  # нагрудник
        rect(s, mid, 6, 8 + b, 4, 2)
        rect(s, light, 6, 8 + b, 1, 2)
        if armor >= 7:
            rect(s, trim, 6, 8 + b, 4, 1)
    rect(s, (245, 205, 90), 5, 10 + b, 6, 1)        # пояс
    if armor >= 3:                                  # шлем
        rect(s, mid, 5, 2 + b, 6, 3)
        rect(s, light, 6, 2 + b, 3, 1)
        if armor >= 7:
            rect(s, trim, 5, 4 + b, 6, 1)
    else:                                           # капюшон
        rect(s, (150, 60, 30), 5, 2 + b, 6, 3)
    rect(s, (235, 195, 155), 6, 4 + b, 4, 3)        # лицо
    if armor >= 3:
        rect(s, mid, 5, 4 + b, 1, 3)
        rect(s, mid, 10, 4 + b, 1, 3)
    eye = (255, 230, 120) if armor >= 10 else (25, 20, 20)
    s.set_at((8, 5 + b), eye)
    s.set_at((9, 5 + b), eye)
    if armor >= 5:                                  # плюмаж
        rect(s, (220, 40, 50), 7, 0 + b, 2, 2)
        s.set_at((6, 1 + b), (220, 40, 50))
    if armor >= 1:                                  # наплечники
        rect(s, mid, 3, 7 + b, 3, 2)
        rect(s, mid, 10, 7 + b, 3, 2)
        s.set_at((3, 7 + b), light)
        s.set_at((10, 7 + b), light)
        if armor >= 7:
            rect(s, trim, 4, 7 + b, 1, 1)
            rect(s, trim, 11, 7 + b, 1, 1)
        if armor >= 9:
            s.set_at((4, 6 + b), light)
            s.set_at((11, 6 + b), light)
    if armor >= 4:                                  # перчатки
        rect(s, mid, 4, 10 + b, 1, 2)
        rect(s, mid, hand[0], hand[1], 1, 1)
    boot = mid if armor >= 4 else (70, 45, 35)      # ноги / сапоги
    rect(s, boot, 5, lf, 2, 1)
    rect(s, boot, 9, rf, 2, 1)
    if armor >= 1:                                  # наколенники
        rect(s, mid, 5, 12, 2, 1)
        rect(s, mid, 9, 12, 2, 1)
    (draw_axe if weapon == "axe" else draw_sword)(s, hand, ang)
    return scaled(s)


def weapon_icon(kind):
    s = new_sprite()
    if kind == "axe":
        pygame.draw.line(s, (120, 80, 45), (3, 14), (11, 4))
        pygame.draw.line(s, (120, 80, 45), (4, 14), (12, 4))
        pts = [(8, 3), (14, 2), (14, 8), (11, 7)]
        pygame.draw.polygon(s, (170, 176, 195), pts)
        pygame.draw.polygon(s, (70, 72, 90), pts, 1)
        pygame.draw.line(s, (240, 245, 255), (14, 2), (14, 8))
    else:
        pygame.draw.line(s, (205, 210, 225), (5, 11), (13, 3))
        pygame.draw.line(s, (235, 240, 250), (6, 11), (14, 3))
        pygame.draw.line(s, (255, 230, 120), (3, 9), (7, 13))
        pygame.draw.line(s, (120, 70, 40), (2, 14), (4, 12))
    return scaled(s, 2)


def goblin_sprite():
    s = new_sprite()
    rect(s, (0, 0, 0, 70), 3, 14, 10, 2)
    rect(s, (115, 72, 40), 5, 9, 6, 5)
    rect(s, (85, 165, 65), 4, 3, 8, 6)
    rect(s, (85, 165, 65), 2, 4, 2, 2)
    rect(s, (85, 165, 65), 12, 4, 2, 2)
    rect(s, (255, 60, 50), 5, 5, 2, 2)
    rect(s, (255, 60, 50), 9, 5, 2, 2)
    rect(s, (30, 50, 30), 6, 8, 4, 1)
    s.set_at((6, 8), (235, 235, 220))
    s.set_at((9, 8), (235, 235, 220))
    rect(s, (70, 45, 30), 5, 14, 2, 1)
    rect(s, (70, 45, 30), 9, 14, 2, 1)
    return scaled(s)


def bat_sprite(up):
    s = new_sprite()
    shadow(s, 5, 6)
    wing, dark = (95, 60, 125), (60, 38, 85)
    if up:
        rect(s, wing, 0, 2, 6, 4); rect(s, wing, 10, 2, 6, 4)
        rect(s, dark, 0, 5, 3, 2); rect(s, dark, 13, 5, 3, 2)
    else:
        rect(s, wing, 0, 7, 6, 4); rect(s, wing, 10, 7, 6, 4)
        rect(s, dark, 0, 10, 3, 2); rect(s, dark, 13, 10, 3, 2)
    rect(s, (80, 55, 105), 5, 5, 6, 7)
    rect(s, (105, 75, 135), 5, 3, 6, 4)
    s.set_at((5, 2), (80, 55, 105)); s.set_at((10, 2), (80, 55, 105))
    rect(s, (255, 70, 70), 6, 4, 1, 1); rect(s, (255, 70, 70), 9, 4, 1, 1)
    s.set_at((7, 7), (240, 240, 230)); s.set_at((8, 7), (240, 240, 230))
    return scaled(s)


def slime_sprite():
    s = new_sprite()
    shadow(s, 2, 12)
    pygame.draw.ellipse(s, (50, 140, 80), (2, 6, 12, 9))
    pygame.draw.ellipse(s, (90, 205, 120), (2, 5, 12, 9))
    rect(s, (190, 255, 205), 4, 7, 3, 1)
    s.set_at((4, 8), (190, 255, 205))
    rect(s, (20, 40, 25), 5, 9, 2, 2); rect(s, (20, 40, 25), 9, 9, 2, 2)
    s.set_at((5, 9), (255, 255, 255)); s.set_at((9, 9), (255, 255, 255))
    rect(s, (20, 40, 25), 7, 12, 2, 1)
    return scaled(s)


def archer_sprite():
    s = new_sprite()
    shadow(s, 4, 8)
    bone, bone2 = (225, 220, 200), (190, 185, 165)
    rect(s, bone, 6, 2, 4, 4)
    rect(s, (20, 20, 25), 6, 3, 1, 2); rect(s, (20, 20, 25), 9, 3, 1, 2)
    rect(s, bone2, 7, 6, 2, 1)
    rect(s, bone, 7, 7, 2, 5)
    rect(s, bone2, 5, 8, 6, 1); rect(s, bone2, 5, 10, 6, 1)
    rect(s, bone, 6, 12, 1, 3); rect(s, bone, 9, 12, 1, 3)
    rect(s, (140, 90, 45), 12, 4, 1, 8)
    rect(s, (140, 90, 45), 11, 3, 1, 1); rect(s, (140, 90, 45), 11, 12, 1, 1)
    rect(s, (235, 235, 235), 11, 4, 1, 8)
    return scaled(s)


def mage_sprite():
    s = new_sprite()
    shadow(s, 4, 8)
    rect(s, (70, 35, 110), 5, 7, 6, 7)
    rect(s, (240, 200, 80), 5, 13, 6, 1)
    pygame.draw.polygon(s, (90, 45, 140), [(8, 0), (5, 5), (11, 5)])
    rect(s, (60, 30, 95), 4, 5, 8, 1)
    rect(s, (30, 20, 40), 6, 6, 4, 2)
    s.set_at((7, 6), (255, 230, 80)); s.set_at((9, 6), (255, 230, 80))
    rect(s, (110, 75, 40), 12, 4, 1, 10)
    rect(s, (255, 140, 40), 11, 2, 3, 3)
    s.set_at((12, 3), (255, 230, 150))
    return scaled(s)


def ogre_sprite():
    s = new_sprite()
    rect(s, (0, 0, 0, 80), 1, 14, 14, 2)
    rect(s, (140, 100, 70), 3, 6, 10, 8)
    rect(s, (160, 120, 85), 5, 2, 6, 5)
    rect(s, (60, 40, 30), 5, 3, 6, 1)
    rect(s, (255, 220, 60), 6, 4, 1, 1); rect(s, (255, 220, 60), 9, 4, 1, 1)
    s.set_at((6, 6), (240, 240, 225)); s.set_at((9, 6), (240, 240, 225))
    rect(s, (160, 120, 85), 1, 7, 2, 5); rect(s, (160, 120, 85), 13, 7, 2, 5)
    rect(s, (80, 50, 30), 3, 11, 10, 1)
    rect(s, (110, 75, 40), 14, 3, 2, 9)
    rect(s, (90, 60, 30), 13, 2, 3, 4)
    rect(s, (100, 70, 50), 4, 14, 3, 1); rect(s, (100, 70, 50), 9, 14, 3, 1)
    return scaled(s)


def king_sprite():
    s = new_sprite()
    shadow(s, 2, 12)
    rect(s, (160, 28, 45), 2, 7, 12, 8)
    rect(s, (95, 62, 36), 5, 9, 6, 5)
    rect(s, (240, 200, 70), 5, 11, 6, 1)
    rect(s, (80, 165, 62), 4, 3, 8, 6)
    rect(s, (80, 165, 62), 2, 4, 2, 2); rect(s, (80, 165, 62), 12, 4, 2, 2)
    rect(s, (255, 60, 50), 5, 5, 2, 2); rect(s, (255, 60, 50), 9, 5, 2, 2)
    rect(s, (30, 50, 30), 6, 8, 4, 1)
    s.set_at((6, 8), (235, 235, 220)); s.set_at((9, 8), (235, 235, 220))
    rect(s, (245, 205, 70), 4, 1, 8, 2)
    for x in (4, 7, 11):
        s.set_at((x, 0), (245, 205, 70))
    s.set_at((7, 2), (220, 40, 60))
    rect(s, (70, 45, 30), 5, 14, 2, 1); rect(s, (70, 45, 30), 9, 14, 2, 1)
    return scaled(s)


def elder_sprite():
    s = new_sprite()
    shadow(s, 4, 8)
    rect(s, (60, 90, 170), 4, 7, 8, 7)
    rect(s, (60, 90, 170), 5, 2, 6, 3)
    rect(s, (235, 195, 155), 6, 4, 4, 3)
    rect(s, (235, 235, 245), 5, 7, 6, 4)
    s.set_at((7, 5), (25, 20, 20)); s.set_at((9, 5), (25, 20, 20))
    rect(s, (130, 90, 50), 12, 3, 1, 11)
    rect(s, (120, 220, 255), 11, 1, 3, 3)
    return scaled(s)


def merchant_sprite():
    s = new_sprite()
    shadow(s, 3, 10)
    rect(s, (170, 50, 50), 5, 1, 6, 3)
    rect(s, (190, 65, 60), 7, 0, 2, 2)
    rect(s, (235, 190, 150), 5, 4, 6, 3)
    s.set_at((6, 5), (25, 20, 20)); s.set_at((9, 5), (25, 20, 20))
    s.set_at((8, 6), (220, 130, 120))
    rect(s, (205, 205, 215), 5, 7, 6, 3)
    rect(s, (70, 110, 70), 4, 10, 8, 4)
    rect(s, (120, 80, 45), 1, 6, 3, 7)
    rect(s, (235, 195, 65), 12, 10, 3, 3)
    rect(s, (60, 40, 30), 5, 14, 2, 1); rect(s, (60, 40, 30), 9, 14, 2, 1)
    return scaled(s)


def chest_sprite():
    s = new_sprite()
    rect(s, (0, 0, 0, 70), 2, 14, 12, 2)
    rect(s, (120, 70, 30), 3, 8, 10, 6)
    rect(s, (155, 95, 42), 3, 5, 10, 4)
    pygame.draw.rect(s, (60, 35, 15), (3, 5, 10, 9), 1)
    rect(s, (235, 195, 65), 7, 5, 2, 9)
    rect(s, (255, 230, 120), 7, 8, 2, 2)
    return scaled(s)


def spikes_sprite():
    s = new_sprite()
    rect(s, (70, 65, 80), 1, 13, 14, 2)
    for x in (2, 6, 10):
        pygame.draw.polygon(s, (190, 190, 205), [(x, 13), (x + 2, 6), (x + 4, 13)])
    return scaled(s)


def barrel_sprite():
    s = new_sprite()
    rect(s, (0, 0, 0, 70), 3, 14, 10, 2)
    rect(s, (130, 85, 45), 3, 3, 10, 11)
    rect(s, (155, 105, 58), 4, 3, 2, 11)
    rect(s, (70, 70, 80), 3, 5, 10, 1); rect(s, (70, 70, 80), 3, 11, 10, 1)
    pygame.draw.rect(s, (70, 45, 20), (3, 3, 10, 11), 1)
    return scaled(s)


def fountain_sprite(dry=False):
    s = new_sprite()
    rect(s, (0, 0, 0, 70), 2, 14, 12, 2)
    rect(s, (110, 105, 125), 2, 8, 12, 6)
    rect(s, (80, 80, 90) if dry else (80, 150, 230), 3, 8, 10, 3)
    if not dry:
        rect(s, (150, 200, 255), 5, 9, 3, 1)
        rect(s, (150, 200, 255), 6, 1, 4, 2)
    rect(s, (130, 125, 145), 7, 2 if dry else 3, 2, 6)
    return scaled(s)


def exit_sprite():
    s = new_sprite()
    rect(s, (95, 70, 45), 2, 1, 12, 14)
    rect(s, (255, 225, 130), 4, 3, 8, 12)
    rect(s, (255, 245, 200), 6, 5, 4, 10)
    rect(s, (60, 40, 25), 1, 15, 14, 1)
    return scaled(s)


def potion_sprite(col, light):
    s = new_sprite()
    shadow(s, 4, 8)
    rect(s, (150, 105, 60), 6, 3, 4, 2)
    rect(s, (200, 205, 225), 7, 5, 2, 2)
    rect(s, col, 5, 6, 6, 1)
    rect(s, col, 4, 7, 8, 7)
    rect(s, light, 5, 8, 1, 3)
    return scaled(s, 2)


def scroll_sprite(col):
    s = new_sprite()
    shadow(s, 3, 10)
    rect(s, (225, 205, 160), 3, 4, 10, 9)
    rect(s, (170, 140, 90), 2, 3, 12, 2)
    rect(s, (170, 140, 90), 2, 12, 12, 2)
    rect(s, (150, 125, 85), 5, 7, 6, 1)
    rect(s, col, 7, 9, 3, 3)
    return scaled(s, 2)


def make_light(size):
    """Круглая маска света: в центре прозрачно, к краям темнота."""
    small = max(2, size // 8)
    s = pygame.Surface((small, small), pygame.SRCALPHA)
    c = (small - 1) / 2
    for y in range(small):
        for x in range(small):
            d = math.hypot(x - c, y - c) / c
            k = min(1.0, max(0.0, (d - 0.25) / 0.75)) ** 1.2
            s.set_at((x, y), (0, 0, 0, int(250 * k)))
    return pygame.transform.smoothscale(s, (size, size))


def make_glow(size):
    s = pygame.Surface((size, size))
    s.fill((0, 0, 0))
    r0 = size // 2
    for r in range(r0, 0, -3):
        k = (1 - r / r0) ** 1.6
        pygame.draw.circle(s, (int(90 * k), int(45 * k), int(10 * k)), (r0, r0), r)
    return s


def make_vignette(k):
    s = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    for i in range(42):
        c = (190, 0, 0, int(150 * (1 - i / 42) ** 2 * k))
        s.fill(c, (i, i, MAP_W - 2 * i, 1))
        s.fill(c, (i, MAP_H - 1 - i, MAP_W - 2 * i, 1))
        s.fill(c, (i, i, 1, MAP_H - 2 * i))
        s.fill(c, (MAP_W - 1 - i, i, 1, MAP_H - 2 * i))
    return s


class Assets:
    def __init__(self):
        self.floor = [floor_tile(i) for i in range(4)]
        self.moss = floor_tile(11, 1)
        self.bones = floor_tile(12, 2)
        self.wall = wall_tile()
        self.torch = [torch_sprite(0), torch_sprite(1)]
        self._pb, self._pf = {}, {}          # кеши кадров героя
        self.player = self.pframe("idle", 0, 0, "sword")
        self.chest = chest_sprite()
        self.spikes = spikes_sprite()
        self.barrel = barrel_sprite()
        self.fountain = fountain_sprite()
        self.fountain_dry = fountain_sprite(True)
        self.exit = exit_sprite()
        self.elder = elder_sprite()
        self.merchant = merchant_sprite()
        self.wicon = {"sword": weapon_icon("sword"), "axe": weapon_icon("axe")}
        self.mob = {
            "goblin": [goblin_sprite()],
            "bat": [bat_sprite(True), bat_sprite(False)],
            "slime": [slime_sprite()],
            "archer": [archer_sprite()],
            "mage": [mage_sprite()],
            "ogre": [ogre_sprite()],
            "king": [king_sprite()],
        }
        self.mob_w = {k: [whiten(f) for f in v] for k, v in self.mob.items()}
        self.icons, self.icons_dim = {}, {}
        for k, d in ITEMS.items():
            ic = potion_sprite(d["col"], d["light"]) if d["kind"] == "potion" else scroll_sprite(d["col"])
            self.icons[k] = ic
            dim = ic.copy()
            dim.set_alpha(80)
            self.icons_dim[k] = dim
        self.portrait = {
            "elder": pygame.transform.scale(self.elder, (96, 96)),
            "merchant": pygame.transform.scale(self.merchant, (96, 96)),
        }
        self.big = {
            "player": pygame.transform.scale(self.player, (96, 96)),
            "walk": [pygame.transform.scale(self.pframe("walk", i, 0, "sword"), (96, 96)) for i in range(4)],
            "goblin": pygame.transform.scale(self.mob["goblin"][0], (96, 96)),
            "bat": pygame.transform.scale(self.mob["bat"][0], (96, 96)),
            "torch": [pygame.transform.scale(t, (TILE * 2, TILE * 2)) for t in self.torch],
        }
        self.dim = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        self.dim.fill((6, 4, 12, 170))
        self.tele = pygame.Surface((TILE, TILE), pygame.SRCALPHA)     # подсветка дуги секиры
        self.tele.fill((255, 120, 40, 95))
        pygame.draw.rect(self.tele, (255, 190, 90, 230), (0, 0, TILE, TILE), 3)
        self.glow = make_glow(110)
        self.glow_big = make_glow(320)
        self.view = pygame.Surface((MAP_W, MAP_H))
        self.overlay = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        self.flashsurf = pygame.Surface((MAP_W, MAP_H))
        self.blacksurf = pygame.Surface((WIN_W, WIN_H))
        self.blacksurf.fill((0, 0, 0))
        self.ui_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)  # окна диалогов/лавки
        self.page = pygame.Surface((WIN_W, WIN_H))                      # экраны меню для анимации
        self.vigs = [make_vignette(0.3 + 0.7 * k / 5) for k in range(6)]   # 6 степеней пульсации
        self._lights = {}

    def pframe(self, anim, f, armor, weapon, white=False, left=False):
        """Кадр героя из кеша. Кадры рисуются один раз, потом переиспользуются."""
        key = (anim, f, armor, weapon, white, left)
        img = self._pf.get(key)
        if img is None:
            bk = (anim, f, armor, weapon)
            base = self._pb.get(bk)
            if base is None:
                base = self._pb[bk] = build_player(anim, f, armor, weapon)
            img = whiten(base) if white else base
            if left:
                img = pygame.transform.flip(img, True, False)
            self._pf[key] = img
        return img

    def light(self, radius):
        if radius not in self._lights:
            self._lights[radius] = [make_light(int((radius + 1.5) * 2 * TILE) + d) for d in (-16, 0, 16)]
        return self._lights[radius]

    def mob_img(self, kind, t, white=False):
        frames = (self.mob_w if white else self.mob)[kind]
        return frames[(t // 140) % len(frames)]


# ============================================================ генерация этажа
def carve_h(grid, y, xa, xb):
    for x in range(min(xa, xb), max(xa, xb) + 1):
        grid[y][x] = 0


def carve_v(grid, x, ya, yb):
    for y in range(min(ya, yb), max(ya, yb) + 1):
        grid[y][x] = 0


def generate_level():
    """Комнаты разной формы + коридоры (минимальное остовное дерево + петли).
    1 = стена, 0 = пол."""
    while True:
        grid = [[1] * COLS for _ in range(ROWS)]
        rooms = []
        target = random.randint(11, 16)
        for _ in range(400):
            w, h = random.randint(4, 10), random.randint(4, 8)
            x, y = random.randint(1, COLS - w - 2), random.randint(1, ROWS - h - 2)
            r = pygame.Rect(x, y, w, h)
            if any(r.inflate(3, 3).colliderect(o) for o in rooms):
                continue
            rooms.append(r)
            if len(rooms) >= target:
                break
        if len(rooms) >= 8:
            break

    for r in rooms:
        shape = random.choice(("rect", "rect", "oval", "pillars"))
        cx, cy = r.x + (r.w - 1) / 2, r.y + (r.h - 1) / 2
        for yy in range(r.top, r.bottom):
            for xx in range(r.left, r.right):
                if shape == "oval" and ((xx - cx) / (r.w / 2)) ** 2 + ((yy - cy) / (r.h / 2)) ** 2 > 1.0:
                    continue
                grid[yy][xx] = 0
        if shape == "pillars" and r.w >= 7 and r.h >= 6:
            for qx, qy in ((r.x + 2, r.y + 2), (r.right - 3, r.y + 2),
                           (r.x + 2, r.bottom - 3), (r.right - 3, r.bottom - 3)):
                grid[qy][qx] = 1

    n = len(rooms)
    cs = [r.center for r in rooms]

    def dist(i, j):
        return abs(cs[i][0] - cs[j][0]) + abs(cs[i][1] - cs[j][1])

    linked, rest, edges = [0], set(range(1, n)), []
    while rest:
        i, j = min(((a, b) for a in linked for b in rest), key=lambda e: dist(*e))
        edges.append((i, j))
        linked.append(j)
        rest.discard(j)
    for _ in range(3):
        a, b = random.sample(range(n), 2)
        edges.append((a, b))
    for a, b in edges:
        (x1, y1), (x2, y2) = cs[a], cs[b]
        if random.random() < 0.5:
            carve_h(grid, y1, x1, x2); carve_v(grid, x2, y1, y2)
        else:
            carve_v(grid, x1, y1, y2); carve_h(grid, y2, x1, x2)

    deco = [[0] * COLS for _ in range(ROWS)]
    torches = set()
    for y in range(1, ROWS - 1):
        for x in range(1, COLS - 1):
            if grid[y][x] == 0:
                v = random.random()
                deco[y][x] = 1 if v < 0.06 else 2 if v < 0.09 else 0
            elif grid[y + 1][x] == 0 and random.random() < 0.06:
                torches.add((x, y))
    return grid, rooms, deco, torches


# ============================================================ сущности
class Mob:
    def __init__(self, kind, x, y, depth):
        d = MOBS[kind]
        self.kind = kind
        self.x, self.y = x, y
        self.rx, self.ry = float(x), float(y)
        hs, ds = 1 + 0.18 * (depth - 1), 1 + 0.10 * (depth - 1)
        self.max = self.hp = int(d["hp"] * hs)
        self.dmg = (max(1, int(d["dmg"][0] * ds)), max(2, int(d["dmg"][1] * ds)))
        self.awake = False
        self.cd = 0
        self.charge = False
        self.summon_cd = 3
        self.flash = 0
        self.lunge = None
        self.seed = random.random() * 10


class NPC:
    def __init__(self, kind, x, y, name):
        self.kind, self.x, self.y, self.name = kind, x, y, name
        self.state = "new"     # new / accepted / done
        self.quest = None


class Dialog:
    def __init__(self, g, name, who, pages, choices=None):
        self.g, self.name, self.who, self.pages = g, name, who, pages
        self.choices = choices or []
        self.i = 0
        self.t = 0
        self.typed = 0          # отдельный счётчик для печати текста
        self.sel = 0

    def done(self):
        return self.typed * 0.8 >= len(self.pages[self.i])

    def key(self, ev):
        k = ev.key
        if k == pygame.K_ESCAPE:
            self.g.ui = None
            return
        last = self.i == len(self.pages) - 1
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_e):
            self.g.sfx.play("ui")
            if not self.done():
                self.typed = 9999
            elif not last:
                self.i += 1
                self.typed = 0
            elif self.choices:
                cb = self.choices[self.sel][1]
                self.g.ui = None
                cb()
            else:
                self.g.ui = None
        elif last and self.choices and self.done():
            if k in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.choices)
            elif k in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.choices)

    def draw(self, screen, A, F):
        r = pygame.Rect(24, MAP_H - 222, MAP_W - 48, 210)
        panel(screen, r)
        screen.blit(A.portrait[self.who], (r.x + 16, r.y + r.h // 2 - 48 + int(math.sin(self.t / 14) * 2)))
        draw_text(screen, F["normal_b"], self.name, GOLD, r.x + 130, r.y + 10)
        n = int(self.typed * 0.8)
        y = r.y + 44
        for ln in wrap(self.pages[self.i], F["normal"], r.w - 160):
            part = ln[:max(0, n)]
            n -= len(ln) + 1
            if part:
                draw_text(screen, F["normal"], part, TEXT, r.x + 130, y)
            y += 26
        last = self.i == len(self.pages) - 1
        if self.done() and last and self.choices:
            for i, (label, _) in enumerate(self.choices):
                b = pygame.Rect(r.x + 130 + i * 200, r.bottom - 54, 180, 38)
                on = i == self.sel
                if on:
                    b = b.inflate(int(math.sin(self.t / 8) * 3) + 4, 2)
                pygame.draw.rect(screen, (60, 45, 85) if on else (35, 30, 48), b)
                pygame.draw.rect(screen, GOLD if on else PANEL_BORDER, b, 2)
                draw_text(screen, F["normal"], label, TEXT, b.centerx, b.y + 7, "c")
        elif self.done():
            a = int(160 + 95 * math.sin(self.t / 10))
            draw_text(screen, F["small"], "Enter — дальше", GRAY, r.right - 20, r.bottom - 28, "r", alpha=a)


class Shop:
    def __init__(self, g, npc):
        self.g, self.npc = g, npc
        self.sel = 0
        self.t = 0
        self.msg = random.choice(MERCH_HELLO)

    def entries(self):
        g = self.g
        infl = 1 + 0.05 * (g.depth - 1)
        res = []
        for k in ORDER:
            d = ITEMS[k]
            res.append(("item", k, d["name"], d["desc"], int(d["price"] * infl)))
        ups = list(UPGRADES)
        if g.has_axe:
            ups.append(AXE_UPGRADE)
        for key, name, desc, base, growth, cap in ups:
            lvl = g.up[key]
            price = None if lvl >= cap else int(base * growth ** lvl)
            if key == "armor" and lvl < cap:
                desc = f"{desc}: {ARMOR_STAGES[lvl + 1]}"
            res.append(("up", key, f"{name} (ур. {lvl})", desc, price))
        return res

    def key(self, ev):
        k = ev.key
        ents = self.entries()
        if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_e):
            self.g.ui = None
        elif k in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(ents)
            self.g.sfx.play("ui")
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(ents)
            self.g.sfx.play("ui")
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.buy(ents[self.sel])

    def buy(self, e):
        g = self.g
        kind, key, name, desc, price = e
        if price is None:
            self.msg = "Это улучшение уже на максимуме!"
            return
        if g.gold < price:
            self.msg = "Не хватает золота, дружище!"
            g.sfx.play("bump")
            return
        g.gold -= price
        if kind == "item":
            g.inv[key] += 1
            g.slot_t[key] = 14
            self.msg = f"Держи: {ITEMS[key]['name']}!"
        else:
            g.up[key] += 1
            if key == "vit":
                g.hp = min(g.max_hp, g.hp + 20)
            if key == "lamp":
                g.compute_fov()
            if key == "armor":
                g.toast(f"Доспех: {ARMOR_STAGES[g.up['armor']]}", (190, 200, 225))
            self.msg = "Отличный выбор! Теперь ты сильнее."
        g.sfx.play("coin")
        px, py = tc(g.px, g.py)
        g.burst(px, py, GOLD, 14, 3)

    def draw(self, screen, A, F):
        g = self.g
        r = pygame.Rect(110, 14, MAP_W - 220, MAP_H - 28)
        panel(screen, r)
        draw_text(screen, F["big"], f"Лавка — {self.npc.name}", GOLD, r.centerx, r.y + 8, "c")
        pygame.draw.circle(screen, GOLD, (r.x + 28, r.y + 60), 8)
        draw_text(screen, F["normal"], f"{g.gold}", GOLD, r.x + 44, r.y + 48)
        ents = self.entries()
        rowh = 27 if len(ents) > 13 else 30
        y = r.y + 80
        for i, (kind, key, name, desc, price) in enumerate(ents):
            row = pygame.Rect(r.x + 12, y, r.w - 24, rowh - 2)
            if i == self.sel:
                pygame.draw.rect(screen, (60, 45, 85), row)
                pygame.draw.rect(screen, GOLD, row, 1)
            if kind == "item":
                ic = pygame.transform.scale(A.icons[key], (24, 24))
                screen.blit(ic, (row.x + 4, row.y + 1))
                extra = f"  (есть: {g.inv[key]})"
            else:
                pygame.draw.polygon(screen, GREEN, [(row.x + 17, row.y + 4), (row.x + 8, row.y + 21), (row.x + 26, row.y + 21)])
                extra = ""
            draw_text(screen, F["normal"], name + extra, TEXT, row.x + 40, row.y + 1)
            if price is None:
                draw_text(screen, F["normal"], "МАКС", GRAY, row.right - 8, row.y + 1, "r")
            else:
                col = TEXT if g.gold >= price else RED
                draw_text(screen, F["normal"], str(price), col, row.right - 30, row.y + 1, "r")
                pygame.draw.circle(screen, GOLD, (row.right - 16, row.y + 13), 7)
            y += rowh
        e = ents[self.sel]
        draw_text(screen, F["small"], e[3], BLUE, r.x + 20, r.bottom - 62)
        draw_text(screen, F["small"], f"«{self.msg}»", GRAY, r.x + 20, r.bottom - 38)
        draw_text(screen, F["small"], "W/S выбрать • Enter купить • Esc выйти",
                  GRAY, r.right - 16, r.bottom - 38, "r")


# ============================================================ игра
class Game:
    def __init__(self, name, sfx, rec):
        self.name, self.sfx, self.rec = name, sfx, rec
        self.lvl, self.xp = 1, 0
        self.up = {k: 0 for k in ("weapon", "armor", "vit", "lamp", "crit", "axe")}
        self.hp = self.max_hp
        self.gold = self.total_gold = self.kills = self.turn = self.done_quests = 0
        self.depth = 1
        self.inv = {k: 0 for k in ORDER}
        self.inv["heal"] = 2
        self.weapon = "sword"           # sword / axe
        self.has_axe = False
        self.axe_pending = None         # [dx, dy, x, y, задержка] — замах секиры
        self.st = {}
        self.haste_flip = False
        self.quests = []
        self.over = None
        self.cause = ""
        self.new_record = False
        self.ui = None
        self.paused = False
        self.log = deque(maxlen=4)
        self.toasts = []
        self.parts, self.floaters, self.rings, self.slashes, self.projs, self.swings = [], [], [], [], [], []
        self.shake = self.flash_t = self.freeze = self.cd = self.pflash = 0
        self.flash = (0, 0, 0)
        self.plunge = None
        self.facing = 1          # 1 = вправо, -1 = влево
        self.lvl_banner = 0
        self.fade = 255
        self.banner = 170
        self.end_t = 0
        self.pause_t = 0
        self.hp_lag = float(self.hp)    # «хвост» полоски здоровья
        self.xp_disp = 0.0
        self.gold_disp = 0.0
        self.slot_t = {k: 0 for k in ORDER}
        self.new_floor()
        self.snap_camera()
        self.say(f"Приветствуем, {name}! Спускайся глубже, копи золото и становись сильнее.", TEXT)
        self.say("Загляни к торговцу и старцу — на первом этаже они рядом.", GRAY)

    # ---- характеристики
    @property
    def max_hp(self):
        return 100 + 10 * (self.lvl - 1) + 20 * self.up["vit"]

    def atk_range(self, weapon=None):
        weapon = weapon or self.weapon
        if weapon == "axe":
            a = self.up["axe"]
            return 14 + 4 * a + (self.lvl - 1), 28 + 6 * a + 2 * (self.lvl - 1)
        w = self.up["weapon"]
        return 8 + 2 * w + (self.lvl - 1), 18 + 3 * w + 2 * (self.lvl - 1)

    def armor_val(self):
        return 2 * self.up["armor"]

    def crit_chance(self):
        return 0.12 + 0.05 * self.up["crit"]

    def light_radius(self):
        return BASE_LIGHT + self.up["lamp"]

    def xp_need(self):
        return 30 + 25 * (self.lvl - 1)

    # ---- вспомогательное
    def say(self, text, color=TEXT):
        self.log.append((text, color, pygame.time.get_ticks()))

    def toast(self, text, color=GOLD):
        self.toasts.append([text, color, 0, 170])
        self.toasts = self.toasts[-4:]

    def mob_at(self, x, y):
        for m in self.mobs:
            if m.x == x and m.y == y:
                return m
        return None

    def blocked(self, x, y):
        return (self.grid[y][x] == 1 or (x, y) == (self.px, self.py) or self.mob_at(x, y)
                or (x, y) in self.npcs or (x, y) in self.fountains or (x, y) in self.barrels)

    def bfs(self, sx, sy, limit):
        dm = {(sx, sy): 0}
        q = deque([(sx, sy)])
        while q:
            x, y = q.popleft()
            d = dm[(x, y)]
            if d >= limit:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) not in dm and self.grid[ny][nx] == 0:
                    dm[(nx, ny)] = d + 1
                    q.append((nx, ny))
        return dm

    def los(self, x0, y0, x1, y1):
        for x, y in line_pts(x0, y0, x1, y1)[1:-1]:
            if self.grid[y][x] == 1:
                return False
        return True

    def room_tiles(self, r):
        return [(x, y) for y in range(r.top, r.bottom) for x in range(r.left, r.right) if self.grid[y][x] == 0]

    def interior(self, x, y):
        return all(self.grid[y + dy][x + dx] == 0 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))

    def take_tile(self, room, taken, inner=False):
        tiles = [t for t in self.room_tiles(room) if t not in taken]
        if inner:
            tiles = [t for t in tiles if self.interior(*t)] or tiles
        if not tiles:
            return None
        t = random.choice(tiles)
        taken.add(t)
        return t

    def reach_count(self, blocked):
        seen = {(self.px, self.py)}
        q = deque(seen)
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in seen and n not in blocked and self.grid[n[1]][n[0]] == 0:
                    seen.add(n)
                    q.append(n)
        return len(seen)

    def take_safe_tile(self, room, taken):
        """Клетка для NPC/фонтана: так, чтобы НИКАКОЙ проход не оказался перекрыт."""
        tiles = [t for t in self.room_tiles(room) if t not in taken]
        roomy = [t for t in tiles if all(self.grid[t[1] + dy][t[0] + dx] == 0
                                         for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
        random.shuffle(roomy)
        random.shuffle(tiles)
        blockers = set(self.npcs) | set(self.fountains)
        total = sum(row.count(0) for row in self.grid)
        for t in roomy + tiles:
            b = blockers | {t}
            if self.reach_count(b) == total - len(b):
                taken.add(t)
                return t
        return None

    # ---- новый этаж
    def new_floor(self):
        d = self.depth
        self.grid, rooms, self.deco, self.torches = generate_level()
        self.explored = [[False] * COLS for _ in range(ROWS)]
        self.visible = [[False] * COLS for _ in range(ROWS)]
        self.mobs, self.npcs, self.chests, self.barrels = [], {}, set(), set()
        self.fountains, self.traps = {}, {}
        self.axe_pending = None
        for lst in (self.parts, self.floaters, self.rings, self.slashes, self.projs, self.swings):
            lst.clear()
        self.mini = pygame.Surface((COLS * 2, ROWS * 2), pygame.SRCALPHA)
        self.mini_dirty = True

        start = random.choice(rooms)
        self.px, self.py = start.center
        self.prx, self.pry = float(self.px), float(self.py)
        dm = self.bfs(self.px, self.py, 999)
        others = [r for r in rooms if r is not start]
        exit_room = max(others, key=lambda r: dm.get(r.center, 0))
        taken = {(self.px, self.py)}
        tiles = self.room_tiles(exit_room)
        self.exit_pos = random.choice([t for t in tiles if self.interior(*t)] or tiles)
        taken.add(self.exit_pos)
        self.boss_alive = (d % 5 == 0)

        special = [r for r in others if r is not exit_room] or others
        if d == 1:
            special.sort(key=lambda r: dm.get(r.center, 999))
            want = ["elder", "merchant"]
        else:
            random.shuffle(special)
            want = []
            if random.random() < 0.75:
                want.append("merchant")
            if random.random() < 0.45:
                want.append("elder")
        if random.random() < 0.4:
            want.append("fountain")
        for i, kind in enumerate(want):
            pos = self.take_safe_tile(special[i % len(special)], taken)
            if not pos:
                continue
            if kind == "elder":
                self.npcs[pos] = NPC("elder", pos[0], pos[1], random.choice(ELDER_NAMES))
            elif kind == "merchant":
                self.npcs[pos] = NPC("merchant", pos[0], pos[1], random.choice(MERCH_NAMES))
            else:
                self.fountains[pos] = False

        pool = mob_pool(d)
        kinds, weights = [k for k, _ in pool], [w for _, w in pool]
        for r in rooms:
            if random.random() < 0.55:
                t = self.take_tile(r, taken)
                if t:
                    self.chests.add(t)
            if random.random() < 0.15:
                t = self.take_tile(r, taken)
                if t:
                    self.chests.add(t)
            for _ in range(random.choice([0, 0, 1, 2, 3])):
                t = self.take_tile(r, taken)
                if t:
                    self.barrels.add(t)
            if r is start:
                continue
            for _ in range(random.choice([1, 2])):
                if random.random() < 0.5:
                    t = self.take_tile(r, taken)
                    if t:
                        self.traps[t] = "hidden"
                    break
            if self.boss_alive and r is exit_room:
                continue
            n = int(random.random() < 0.85) + int(random.random() < min(0.7, 0.12 * d)) \
                + int(random.random() < min(0.4, 0.05 * d))
            for _ in range(n):
                t = self.take_tile(r, taken)
                if t and abs(t[0] - self.px) + abs(t[1] - self.py) >= 7:
                    self.mobs.append(Mob(random.choices(kinds, weights)[0], t[0], t[1], d))
        if self.boss_alive:
            t = self.take_tile(exit_room, taken)
            if t:
                self.mobs.append(Mob("king", t[0], t[1], d))
            else:
                self.boss_alive = False
        self.compute_fov()
        if self.boss_alive:
            self.say("Дверь вниз запечатана магией. Победи Короля гоблинов!", RED)

    def descend(self):
        self.depth += 1
        self.quest_event("descend")
        self.heal(self.max_hp // 10, quiet=True)
        self.sfx.play("stairs")
        self.new_floor()
        self.snap_camera()
        self.fade, self.banner = 255, 170
        self.say(f"Ты спустился на этаж {self.depth}. Враги становятся сильнее...", ORANGE)

    # ---- обзор
    def compute_fov(self):
        R = self.light_radius()
        vis = [[False] * COLS for _ in range(ROWS)]
        changed = False
        for yy in range(max(0, self.py - R), min(ROWS, self.py + R + 1)):
            for xx in range(max(0, self.px - R), min(COLS, self.px + R + 1)):
                if (xx - self.px) ** 2 + (yy - self.py) ** 2 > R * R + R:
                    continue
                if self.los(self.px, self.py, xx, yy):
                    vis[yy][xx] = True
                    if not self.explored[yy][xx]:
                        self.explored[yy][xx] = True
                        changed = True
        self.visible = vis
        if changed:
            self.mini_dirty = True

    def rebuild_mini(self):
        self.mini.fill((0, 0, 0, 0))
        for y in range(ROWS):
            for x in range(COLS):
                if self.explored[y][x]:
                    c = (34, 28, 46) if self.grid[y][x] == 1 else (110, 96, 135)
                    self.mini.fill(c, (x * 2, y * 2, 2, 2))
        self.mini_dirty = False

    # ---- эффекты
    def burst(self, x, y, col, n=12, spd=3.0, life=26, grav=0.12, size=3):
        for _ in range(n):
            a = random.random() * math.tau
            s = random.random() * spd
            self.parts.append([x, y, math.cos(a) * s, math.sin(a) * s - 0.5,
                               life * (0.6 + random.random() * 0.6), life, col, size, grav])

    def float_text(self, text, tx, ty, color, big=False):
        x, y = tc(tx, ty)
        self.floaters.append([text, x, y - 14, color, 55, big])

    def ring(self, x, y, col, maxr=90, life=18):
        self.rings.append([x, y, 6, maxr, col, life, life])

    def slash(self, x, y, dx, dy, col=(255, 255, 255), crit=False):
        self.slashes.append([x, y, dx, dy, 9, col, crit])

    def add_proj(self, x0, y0, x1, y1, kind):
        a, b = tc(x0, y0), tc(x1, y1)
        self.projs.append([a[0], a[1], b[0], b[1], 0, 10, kind])
        self.sfx.play("shoot")

    def snap_camera(self):
        self.prx, self.pry = float(self.px), float(self.py)
        self.camx = max(0, min(COLS * TILE - MAP_W, self.prx * TILE + TILE / 2 - MAP_W / 2))
        self.camy = max(0, min(ROWS * TILE - MAP_H, self.pry * TILE + TILE / 2 - MAP_H / 2))

    def update(self):
        k = 0.35
        self.prx += (self.px - self.prx) * k
        self.pry += (self.py - self.pry) * k
        for m in self.mobs:
            m.rx += (m.x - m.rx) * k
            m.ry += (m.y - m.ry) * k
            if m.flash > 0:
                m.flash -= 1
            if m.lunge:
                m.lunge[2] -= 1
                if m.lunge[2] <= 0:
                    m.lunge = None
        if self.plunge:
            self.plunge[2] -= 1
            if self.plunge[2] <= 0:
                self.plunge = None
        if self.pflash > 0:
            self.pflash -= 1
        tx = max(0, min(COLS * TILE - MAP_W, self.prx * TILE + TILE / 2 - MAP_W / 2))
        ty = max(0, min(ROWS * TILE - MAP_H, self.pry * TILE + TILE / 2 - MAP_H / 2))
        self.camx += (tx - self.camx) * 0.18
        self.camy += (ty - self.camy) * 0.18
        if self.shake > 0:
            self.shake -= 1
        if self.flash_t > 0:
            self.flash_t -= 1
        if self.fade > 0:
            self.fade = max(0, self.fade - 6)
        if self.banner > 0:
            self.banner -= 1
        if self.lvl_banner > 0:
            self.lvl_banner -= 1
        if self.cd > 0:
            self.cd -= 1
        if self.over:
            self.end_t += 1
        if self.ui:
            self.ui.t += 1
            if isinstance(self.ui, Dialog):
                self.ui.typed += 1
        if self.mini_dirty:
            self.rebuild_mini()
        # плавные значения интерфейса
        self.hp_lag += (self.hp - self.hp_lag) * (0.06 if self.hp_lag > self.hp else 0.3)
        self.xp_disp += (self.xp - self.xp_disp) * 0.2
        self.gold_disp += (self.gold - self.gold_disp) * 0.2
        if abs(self.gold - self.gold_disp) < 0.5:
            self.gold_disp = float(self.gold)
        for key in self.slot_t:
            if self.slot_t[key] > 0:
                self.slot_t[key] -= 1
        for t in self.toasts:
            t[2] += 1
        self.toasts = [t for t in self.toasts if t[2] < t[3]]
        for p in self.parts:
            p[0] += p[2]; p[1] += p[3]; p[3] += p[8]; p[4] -= 1
        self.parts = [p for p in self.parts if p[4] > 0]
        for f in self.floaters:
            f[2] -= 0.8; f[4] -= 1
        self.floaters = [f for f in self.floaters if f[4] > 0]
        for r in self.rings:
            r[2] += (r[3] - r[2]) * 0.25; r[5] -= 1
        self.rings = [r for r in self.rings if r[5] > 0]
        for s in self.slashes:
            s[4] -= 1
        self.slashes = [s for s in self.slashes if s[4] > 0]
        for s in self.swings:
            s[3] -= 1
        self.swings = [s for s in self.swings if s[3] > 0]
        for p in self.projs:
            p[4] += 1
            if p[6] == "fire":
                t = p[4] / p[5]
                self.burst(p[0] + (p[2] - p[0]) * t, p[1] + (p[3] - p[1]) * t, (255, 150, 40), 1, 0.6, 12, 0, 3)
            if p[4] >= p[5]:
                self.burst(p[2], p[3], (255, 170, 60) if p[6] == "fire" else (230, 230, 210), 8, 2.5, 16)
        self.projs = [p for p in self.projs if p[4] < p[5]]

    # ---- урон, лечение, опыт
    def hurt_player(self, dmg, src, pierce=False):
        if self.over:
            return 0
        if not pierce:
            dmg = max(1, dmg - self.armor_val())
            if "iron" in self.st:
                dmg = max(1, dmg // 2)
        self.hp -= dmg
        self.pflash = 6
        self.shake = max(self.shake, 3 if pierce else (8 if dmg < 15 else 14))
        self.flash, self.flash_t = (200, 0, 0), 12
        self.float_text(f"-{dmg}", self.px, self.py, RED, dmg >= 15)
        x, y = tc(self.px, self.py)
        self.burst(x, y, (200, 30, 40), 10, 3)
        self.sfx.play("hurt")
        if self.hp <= 0:
            self.die(src)
        return dmg

    def die(self, src):
        self.hp = 0
        self.over = "dead"
        self.cause = src
        self.axe_pending = None
        x, y = tc(self.px, self.py)
        self.burst(x, y, (200, 30, 40), 40, 5, 40)
        self.ring(x, y, RED, 160, 30)
        self.shake = 22
        self.sfx.play("die")
        r = self.rec
        self.new_record = self.depth > r["depth"] or self.total_gold > r["gold"]
        r["depth"] = max(r["depth"], self.depth)
        r["gold"] = max(r["gold"], self.total_gold)
        r["kills"] = max(r["kills"], self.kills)
        r["runs"] += 1
        save_records(r)

    def heal(self, n, quiet=False):
        amt = min(n, self.max_hp - self.hp)
        if amt <= 0:
            return
        self.hp += amt
        self.float_text(f"+{amt}", self.px, self.py, GREEN)
        x, y = tc(self.px, self.py)
        self.burst(x, y, GREEN, 14, 2.5, 30, -0.05)
        if not quiet:
            self.flash, self.flash_t = (0, 160, 60), 12

    def add_gold(self, n, event=True):
        self.gold += n
        self.total_gold += n
        if event:
            self.quest_event("gold", n)

    def gain_xp(self, n):
        self.xp += n
        while self.xp >= self.xp_need():
            self.xp -= self.xp_need()
            self.lvl += 1
            self.hp = min(self.max_hp, self.hp + 30)
            x, y = tc(self.px, self.py)
            self.burst(x, y, GOLD, 22, 4, 34, -0.02, 2)
            self.ring(x, y, GOLD, 100, 22)
            self.lvl_banner = 130
            self.say(f"Новый уровень: {self.lvl}! Здоровье и урон выросли.", GOLD)
            self.toast(f"Уровень {self.lvl}!", GOLD)
            self.sfx.play("level")

    def give_item(self, key, n=1):
        self.inv[key] += n
        self.slot_t[key] = 14
        self.float_text(f"+{ITEMS[key]['name']}", self.px, self.py - 1, GREEN)
        self.say(f"Получено: {ITEMS[key]['name']}!", GREEN)
        self.toast(ITEMS[key]["name"], GREEN)

    def drop_item(self):
        return random.choices(list(DROP_W), list(DROP_W.values()))[0]

    # ---- оружие
    def get_axe(self):
        self.has_axe = True
        x, y = tc(self.px, self.py)
        self.burst(x, y, (255, 200, 90), 30, 5, 36)
        self.ring(x, y, ORANGE, 130, 26)
        self.say("Из огра выпала СЕКИРА! Нажми Q, чтобы взять её в руки. В лавке — заточка секиры.", ORANGE)
        self.toast("Редкая находка: Секира! (Q)", ORANGE)
        self.sfx.play("level")

    def switch_weapon(self):
        if self.over or self.ui:
            return
        if not self.has_axe:
            self.say("Другого оружия у тебя пока нет. Секиру можно выбить из огра.", GRAY)
            return
        self.weapon = "axe" if self.weapon == "sword" else "sword"
        name = "Секира" if self.weapon == "axe" else "Меч"
        x, y = tc(self.px, self.py)
        self.burst(x, y, (220, 225, 245), 10, 2.5, 18, -0.03, 2)
        self.say(f"Оружие: {name}.", ORANGE if self.weapon == "axe" else TEXT)
        self.sfx.play("equip")

    def axe_cells(self, ox, oy, dx, dy):
        """Дуга секиры: клетка перед героем + клетки сверху и снизу от неё."""
        fx, fy = ox + dx, oy + dy
        px_, py_ = -dy, dx
        return [(fx + px_, fy + py_), (fx, fy), (fx - px_, fy - py_)]

    # ---- квесты
    def make_quest(self, npc):
        d = self.depth
        kind = random.choice(["kill", "kill", "killkind", "gold", "chests", "barrels", "descend"])
        q = {"kind": kind, "sub": None, "p": 0, "npc": npc}
        if kind == "kill":
            n = random.randint(4, 7) + d // 2
            q["text"] = f"Убей {n} монстров"
            per = 14
        elif kind == "killkind":
            sub = random.choice([k for k, _ in mob_pool(d)])
            n = random.randint(2, 4) + d // 4
            q["sub"] = sub
            q["text"] = f"Убей {n} {MOBS[sub]['plural']}"
            per = 24
        elif kind == "gold":
            n = (random.randint(60, 110) + 25 * d) // 10 * 10
            q["text"] = f"Собери {n} золота"
            per = 0.6
        elif kind == "chests":
            n = random.randint(2, 4)
            q["text"] = f"Открой {n} сундуков"
            per = 30
        elif kind == "barrels":
            n = random.randint(3, 6)
            q["text"] = f"Разбей {n} бочек"
            per = 14
        else:
            n = random.randint(2, 3)
            q["text"] = f"Спустись на {n} этажа вниз"
            per = 45
        q["n"] = n
        q["gold"] = max(10, int(n * per * (1 + 0.1 * (d - 1))))
        q["xp"] = q["gold"] // 2
        q["item"] = self.drop_item() if random.random() < 0.5 else None
        q["story"] = random.choice(STORIES[kind]).format(t=q["text"])
        return q

    def quest_event(self, kind, amt=1, sub=None):
        for q in list(self.quests):
            k = q["kind"]
            if k == kind or (k == "killkind" and kind == "kill" and q["sub"] == sub):
                q["p"] += amt
                if q["p"] >= q["n"]:
                    self.complete_quest(q)

    def complete_quest(self, q):
        if q in self.quests:
            self.quests.remove(q)
        self.done_quests += 1
        self.add_gold(q["gold"], event=False)
        self.gain_xp(q["xp"])
        if q["item"]:
            self.give_item(q["item"])
        if q.get("npc"):
            q["npc"].state = "done"
        x, y = tc(self.px, self.py)
        self.burst(x, y, GOLD, 30, 4, 36)
        self.ring(x, y, GOLD, 110, 24)
        self.float_text("КВЕСТ!", self.px, self.py - 1, GOLD, True)
        self.say(f"Квест выполнен: {q['text']}! +{q['gold']} золота, +{q['xp']} опыта.", GOLD)
        self.toast(f"Квест выполнен! +{q['gold']} золота", GOLD)
        self.sfx.play("quest")

    def open_npc(self, n):
        self.sfx.play("ui")
        if n.kind == "merchant":
            self.ui = Shop(self, n)
            return
        if n.state == "accepted":
            self.ui = Dialog(self, n.name, "elder", [random.choice(ELDER_WAIT)])
            return
        if len(self.quests) >= 3:
            self.ui = Dialog(self, n.name, "elder",
                             ["Ты уже взял кучу поручений, храбрец. Выполни их — и возвращайся!"])
            return
        intro = random.choice(ELDER_HELLO)
        if n.state == "done" or n.quest is None:
            if n.state == "done":
                intro = "Ты вернулся! Спасибо тебе. У меня есть ещё одно дело."
            n.quest = self.make_quest(n)
        n.state = "new"
        q = n.quest
        item = f", {ITEMS[q['item']]['name']}" if q["item"] else ""
        pages = [intro, q["story"], f"Награда: {q['gold']} золота, {q['xp']} опыта{item}. Берёшься?"]
        self.ui = Dialog(self, n.name, "elder", pages,
                         [("Принять", lambda: self.accept(n)), ("Отказаться", lambda: None)])

    def accept(self, n):
        self.quests.append(n.quest)
        n.state = "accepted"
        self.say(f"Квест принят: {n.quest['text']}.", GOLD)
        self.sfx.play("quest")

    # ---- действия игрока
    def try_move(self, dx, dy):
        if self.over or self.ui:
            return
        if dx:
            self.facing = dx
        nx, ny = self.px + dx, self.py + dy
        if self.grid[ny][nx] == 1:
            return
        m = self.mob_at(nx, ny)
        if m:
            self.player_attack(m, dx, dy)
        elif (nx, ny) in self.npcs:
            self.open_npc(self.npcs[(nx, ny)])
            return
        elif (nx, ny) in self.barrels:
            self.smash_barrel(nx, ny)
        elif (nx, ny) in self.fountains:
            if not self.use_fountain(nx, ny):
                return
        else:
            ox, oy = tc(self.px, self.py)
            self.px, self.py = nx, ny
            self.burst(ox, oy + 16, (95, 85, 110), 2, 1.2, 12, 0.0, 2)      # пыль из-под ног
            if self.step_on():
                return
        self.end_turn()

    def wait(self):
        if not self.over and not self.ui:
            self.end_turn()

    def player_attack(self, m, dx, dy):
        if self.weapon == "axe":
            if self.axe_pending:
                self.say("Секира ещё замахивается...", GRAY)
                return
            # замах: удар придёт только на следующем ходу
            self.axe_pending = [dx, dy, self.px, self.py, 1]
            self.say("Ты заносишь секиру для мощного удара! Враги могут успеть отойти...", ORANGE)
            self.sfx.play("whoosh")
            x, y = tc(self.px, self.py)
            self.ring(x, y, ORANGE, 60, 14)
            return
        lo, hi = self.atk_range("sword")
        dmg = random.randint(lo, hi)
        if "rage" in self.st:
            dmg = int(dmg * 1.5)
        crit = random.random() < self.crit_chance()
        if crit:
            dmg *= 2
        self.plunge = [dx, dy, 10, 10, "sword"]
        x, y = tc(m.x, m.y)
        self.slash(x - dx * 8, y - dy * 8, dx, dy, (255, 240, 180) if crit else (255, 255, 255), crit)
        self.say(("КРИТ! " if crit else "") + f"Ты нанёс {MOBS[m.kind]['name']} {dmg} урона.",
                 GOLD if crit else TEXT)
        self.sfx.play("crit" if crit else "hit")
        self.shake = max(self.shake, 9 if crit else 3)
        self.freeze = 5 if crit else 2
        if "vamp" in self.st:
            self.heal(max(1, int(dmg * 0.3)), quiet=True)
        self.damage_mob(m, dmg, crit)

    def resolve_axe(self):
        """Удар секиры по дуге из 3 клеток (после задержки в один ход)."""
        dx, dy, ox, oy, _ = self.axe_pending
        self.axe_pending = None
        cells = self.axe_cells(ox, oy, dx, dy)
        lo, hi = self.atk_range("axe")
        hit = 0
        cx, cy = tc(ox, oy)
        self.plunge = [dx, dy, 14, 14, "axe"]
        self.swings.append([cx, cy, math.atan2(dy, dx), 14])
        for c in cells:
            if c in self.barrels:
                self.smash_barrel(*c)
            m = self.mob_at(*c)
            if not m:
                continue
            dmg = random.randint(lo, hi)
            if "rage" in self.st:
                dmg = int(dmg * 1.5)
            crit = random.random() < self.crit_chance()
            if crit:
                dmg *= 2
            x, y = tc(*c)
            self.slash(x - dx * 8, y - dy * 8, dx, dy, (255, 200, 120), True)
            if "vamp" in self.st:
                self.heal(max(1, int(dmg * 0.3)), quiet=True)
            self.damage_mob(m, dmg, crit)
            hit += 1
        if hit:
            self.say(f"СЕКИРА! Удар по дуге задел врагов: {hit}.", ORANGE)
            self.sfx.play("axe")
            self.shake = max(self.shake, 14)
            self.freeze = 7
        else:
            self.say("Секира рассекла пустоту — враги успели уйти.", GRAY)
            self.sfx.play("whoosh")
            self.shake = max(self.shake, 4)

    def damage_mob(self, m, dmg, crit=False):
        m.hp -= dmg
        m.flash = 6
        m.awake = True
        x, y = tc(m.x, m.y)
        self.float_text(("КРИТ " if crit else "") + str(dmg), m.x, m.y, (255, 220, 120), crit)
        self.burst(x, y, MOBS[m.kind]["col"], 18 if crit else 9, 4 if crit else 3)
        if m.hp <= 0:
            self.kill_mob(m)

    def kill_mob(self, m):
        if m in self.mobs:
            self.mobs.remove(m)
        info = MOBS[m.kind]
        d = self.depth
        x, y = tc(m.x, m.y)
        self.burst(x, y, info["col"], 30, 5, 34)
        self.ring(x, y, info["col"], 70, 16)
        gold = int(random.randint(*info["gold"]) * (1 + 0.1 * (d - 1)))
        self.add_gold(gold)
        self.float_text(f"+{gold}", m.x, m.y - 1, GOLD)
        for _ in range(6):
            self.burst(x, y, GOLD, 1, 4, 30, 0.2, 3)
        self.say(f"{info['name']} повержен! +{gold} золота.", GOLD)
        self.sfx.play("coin")
        self.kills += 1
        self.gain_xp(int(info["xp"] * (1 + 0.08 * (d - 1))))
        if random.random() < 0.25:
            self.give_item(self.drop_item())
        if m.kind == "ogre" and not self.has_axe and random.random() < AXE_DROP:
            self.get_axe()
        if m.kind == "king":
            self.boss_alive = False
            self.ring(x, y, GOLD, 220, 40)
            self.shake = 20
            self.give_item("elixir")
            self.give_item(self.drop_item())
            self.say("Король пал! Дверь вниз открыта!", GOLD)
            self.toast("Король гоблинов повержен!", GOLD)
            self.sfx.play("boom")
        self.quest_event("kill", 1, m.kind)

    def smash_barrel(self, x, y):
        self.barrels.discard((x, y))
        px, py = tc(x, y)
        self.burst(px, py, (140, 95, 50), 16, 3.5)
        self.sfx.play("bump")
        self.quest_event("barrels")
        r = random.random()
        if r < 0.10:
            self.give_item("heal")
        elif r < 0.42:
            g = int(random.randint(3, 12) * (1 + 0.1 * (self.depth - 1)))
            self.add_gold(g)
            self.float_text(f"+{g}", x, y, GOLD)
            self.say(f"В бочке нашлось {g} золота.", GOLD)
        elif r < 0.47:
            self.burst(px, py, ORANGE, 30, 5, 28)
            self.ring(px, py, ORANGE, 110, 20)
            self.sfx.play("boom")
            self.say("Бочка с порохом! БАХ!", ORANGE)
            if abs(x - self.px) + abs(y - self.py) <= 2:
                self.hurt_player(8 + self.depth, "взрыв бочки")
            for m in list(self.mobs):
                if abs(m.x - x) + abs(m.y - y) <= 2:
                    self.damage_mob(m, 15 + 2 * self.depth)

    def use_fountain(self, x, y):
        if self.fountains[(x, y)]:
            self.say("Фонтан высох.", GRAY)
            return False
        if self.hp >= self.max_hp:
            self.say("Ты полностью здоров — вода пока не нужна.", GRAY)
            return False
        self.fountains[(x, y)] = True
        self.heal(self.max_hp // 2)
        px, py = tc(x, y)
        self.burst(px, py, (120, 190, 255), 24, 3, 32, -0.05)
        self.sfx.play("potion")
        self.say("Ты пьёшь из фонтана и чувствуешь, как возвращаются силы.", BLUE)
        return True

    def step_on(self):
        """Возвращает True, если этаж сменился."""
        pos = (self.px, self.py)
        if pos in self.chests:
            self.chests.remove(pos)
            found = int(random.randint(15, 35) * (1 + 0.12 * (self.depth - 1)))
            self.add_gold(found)
            x, y = tc(*pos)
            self.burst(x, y, GOLD, 20, 4, 30)
            self.float_text(f"+{found}", self.px, self.py, GOLD)
            self.say(f"Ты открыл сундук: {found} золота!", GOLD)
            self.sfx.play("coin")
            self.quest_event("chests")
            if random.random() < 0.3:
                self.give_item(self.drop_item())
        elif self.traps.get(pos) == "hidden":
            self.traps[pos] = "sprung"
            dmg = random.randint(10, 18) + self.depth
            self.say(f"Ловушка! Шипы вонзаются в ноги: -{dmg} HP.", RED)
            self.hurt_player(dmg, "ловушка", pierce=True)
        elif pos == self.exit_pos:
            if self.boss_alive:
                self.say("Дверь заперта магией Короля гоблинов!", RED)
                self.sfx.play("bump")
            else:
                self.descend()
                return True
        return False

    def use_item(self, key):
        if self.over or self.ui:
            return
        if self.inv[key] <= 0:
            self.say("Такого предмета нет!", GRAY)
            return
        x, y = tc(self.px, self.py)
        if key in ("heal", "elixir"):
            if self.hp >= self.max_hp:
                self.say("У тебя полное здоровье!", GRAY)
                return
            self.heal(40 if key == "heal" else self.max_hp)
            self.say(f"Ты выпил «{ITEMS[key]['name']}». Здоровье: {self.hp}.", GREEN)
        elif key in BUFF_TURNS:
            self.st[key] = BUFF_TURNS[key]
            c = STATUS_COL[key]
            self.burst(x, y, c, 24, 3.5, 30, -0.06)
            self.ring(x, y, c, 80, 18)
            self.float_text(STATUS_NAME[key] + "!", self.px, self.py, c, True)
            self.say(f"Эффект «{STATUS_NAME[key]}» на {BUFF_TURNS[key]} ходов!", c)
        elif key == "fire":
            self.burst(x, y, ORANGE, 50, 6, 30)
            self.ring(x, y, ORANGE, 170, 26)
            self.ring(x, y, (255, 230, 120), 110, 20)
            self.shake = 14
            self.sfx.play("boom")
            hit = 0
            for m in list(self.mobs):
                if max(abs(m.x - self.px), abs(m.y - self.py)) <= 3 and self.los(self.px, self.py, m.x, m.y):
                    self.damage_mob(m, random.randint(25, 40) + 3 * self.depth)
                    hit += 1
            self.say(f"Огненный взрыв! Задето врагов: {hit}.", ORANGE)
        elif key == "map":
            for yy in range(ROWS):
                for xx in range(COLS):
                    if self.grid[yy][xx] == 0:
                        for ddy in (-1, 0, 1):
                            for ddx in (-1, 0, 1):
                                self.explored[yy + ddy][xx + ddx] = True
            self.mini_dirty = True
            self.say("Карта этажа открыта!", GREEN)
        self.inv[key] -= 1
        self.slot_t[key] = 14
        if key not in ("fire",):
            self.sfx.play("potion")
        self.end_turn()

    # ---- ход врагов
    def end_turn(self):
        if self.over:
            return
        self.turn += 1
        self.cd = 6
        self.compute_fov()
        for k in list(self.st):
            if k in ("poison", "burn"):
                dmg = (2 + self.depth // 3) if k == "poison" else (2 + self.depth // 4)
                self.hurt_player(dmg, "яд" if k == "poison" else "огонь", pierce=True)
                if self.over:
                    return
            self.st[k] -= 1
            if self.st[k] <= 0:
                del self.st[k]
                self.say(f"Эффект «{STATUS_NAME[k]}» закончился.", GRAY)
        if self.axe_pending:                # задержка секиры: 1 -> 0, а на следующем ходу — удар
            if self.axe_pending[4] > 0:
                self.axe_pending[4] -= 1
            else:
                self.resolve_axe()
        skip = False
        if "haste" in self.st:
            self.haste_flip = not self.haste_flip
            skip = self.haste_flip
        if not skip:
            self.mobs_turn()

    def mobs_turn(self):
        dm = self.bfs(self.px, self.py, 24)
        for m in list(self.mobs):
            if self.over:
                return
            if m in self.mobs:
                self.mob_act(m, dm)

    def add_status(self, name, turns):
        self.st[name] = max(self.st.get(name, 0), turns)
        self.float_text(STATUS_NAME[name] + "!", self.px, self.py - 1, STATUS_COL[name])

    def mob_attack(self, m, mult=1.0, effect=None):
        info = MOBS[m.kind]
        dmg = int(random.randint(*m.dmg) * mult)
        m.lunge = [sign(self.px - m.x), sign(self.py - m.y), 10]
        real = self.hurt_player(max(1, dmg), info["name"])
        self.say(f"{info['name']} бьёт тебя: -{real} HP!", RED)
        if effect and not self.over:
            self.add_status(effect, 4)
        return real

    def step_toward(self, m, dm):
        cur = dm.get((m.x, m.y), 999)
        best = None
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = m.x + dx, m.y + dy
            d = dm.get((nx, ny))
            if d is None or d >= cur or self.blocked(nx, ny):
                continue
            if best is None or d < best[0]:
                best = (d, nx, ny)
        if best:
            m.x, m.y = best[1], best[2]
            return True
        return False

    def step_away(self, m):
        cur = abs(m.x - self.px) + abs(m.y - self.py)
        best = None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = m.x + dx, m.y + dy
            if self.blocked(nx, ny):
                continue
            d = abs(nx - self.px) + abs(ny - self.py)
            if d > cur and (best is None or d > best[0]):
                best = (d, nx, ny)
        if best:
            m.x, m.y = best[1], best[2]

    def random_step(self, m):
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            if not self.blocked(m.x + dx, m.y + dy):
                m.x += dx
                m.y += dy
                return

    def summon(self, m):
        spots = [(m.x + dx, m.y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
        random.shuffle(spots)
        n = 0
        for x, y in spots:
            if n >= 2:
                break
            if not self.blocked(x, y):
                g = Mob("goblin", x, y, self.depth)
                g.awake = True
                self.mobs.append(g)
                px, py = tc(x, y)
                self.burst(px, py, (90, 170, 70), 14, 3)
                n += 1
        self.ring(*tc(m.x, m.y), RED, 100, 20)
        self.say("Король гоблинов призывает подданных!", RED)
        self.sfx.play("boom")

    def mob_act(self, m, dm):
        info = MOBS[m.kind]
        dist = abs(m.x - self.px) + abs(m.y - self.py)
        sees = dist <= info["sight"] and self.los(m.x, m.y, self.px, self.py)
        if not m.awake:
            if sees:
                m.awake = True
                self.float_text("!", m.x, m.y, RED, True)
            return
        k = m.kind
        if k == "king":
            m.summon_cd -= 1
            if m.summon_cd <= 0 and sees and len(self.mobs) < 9:
                m.summon_cd = 7
                self.summon(m)
                return
        if k in ("goblin", "king"):
            if dist == 1:
                self.mob_attack(m)
            else:
                self.step_toward(m, dm)
        elif k == "bat":
            for _ in range(2):
                d = abs(m.x - self.px) + abs(m.y - self.py)
                if d == 1:
                    real = self.mob_attack(m)
                    m.hp = min(m.max, m.hp + max(1, real // 2))
                    break
                if random.random() < 0.3:
                    self.random_step(m)
                else:
                    self.step_toward(m, dm)
        elif k == "slime":
            if m.cd > 0:
                m.cd -= 1
                return
            if dist == 1:
                self.mob_attack(m, effect="poison")
                m.cd = 1
            elif self.step_toward(m, dm):
                m.cd = 1
        elif k in ("archer", "mage"):
            if m.cd > 0:
                m.cd -= 1
                if dist <= 3:
                    self.step_away(m)
                return
            if sees and 2 <= dist <= 7:
                self.add_proj(m.x, m.y, self.px, self.py, "arrow" if k == "archer" else "fire")
                dmg = random.randint(*m.dmg)
                real = self.hurt_player(dmg, info["name"])
                self.say(f"{info['name']} стреляет: -{real} HP!", RED)
                if k == "mage" and not self.over:
                    self.add_status("burn", 3)
                m.cd = 1 if k == "archer" else 2
            elif dist == 1:
                self.mob_attack(m, 0.5)
            else:
                self.step_toward(m, dm)
        elif k == "ogre":
            if dist == 1:
                if not m.charge:
                    m.charge = True
                    self.float_text("!", m.x, m.y, RED, True)
                    self.say("Огр заносит дубину! Отойди!", ORANGE)
                else:
                    m.charge = False
                    self.mob_attack(m, 1.0)
                    x, y = tc(self.px, self.py)
                    self.ring(x, y, (200, 170, 120), 110, 20)
                    self.shake = 16
                    self.sfx.play("boom")
            else:
                m.charge = False
                if m.cd > 0:
                    m.cd -= 1
                elif self.step_toward(m, dm):
                    m.cd = 1


# ============================================================ отрисовка мира
def player_anim(g, t):
    """Выбор анимации героя: (anim, кадр, оружие в руке)."""
    if g.plunge:
        kind = g.plunge[4]
        prog = 1 - g.plunge[2] / g.plunge[3]
        f = 1 + min(1, int(prog * 2)) if kind == "axe" else min(2, int(prog * 3))
        return "attack", f, kind
    if g.axe_pending:
        return "attack", 0, "axe"              # замах секиры «висит» до удара
    if abs(g.px - g.prx) + abs(g.py - g.pry) > 0.06:
        return "walk", (t // 95) % 4, g.weapon
    return "idle", (t // 500) % 2, g.weapon


def draw_world(screen, g, A, F):
    t = pygame.time.get_ticks()
    cx, cy = int(g.camx), int(g.camy)
    w = A.view
    w.fill((8, 6, 12))
    tx0, ty0 = cx // TILE, cy // TILE
    glows = []
    for ty in range(ty0, min(ROWS, ty0 + VIEW_ROWS + 2)):
        row, exr, vis = g.grid[ty], g.explored[ty], g.visible[ty]
        for tx in range(tx0, min(COLS, tx0 + VIEW_COLS + 2)):
            if not exr[tx]:
                continue
            sx, sy = tx * TILE - cx, ty * TILE - cy
            if row[tx] == 1:
                w.blit(A.wall, (sx, sy))
                if (tx, ty) in g.torches:
                    w.blit(A.torch[(t // 110 + tx) % 2], (sx, sy))
                    if vis[tx]:
                        glows.append((sx, sy))
            else:
                dc = g.deco[ty][tx]
                w.blit(A.moss if dc == 1 else A.bones if dc == 2 else A.floor[(tx * 7 + ty * 13) % 4], (sx, sy))
            if not vis[tx]:
                w.blit(A.dim, (sx, sy))

    def seen(x, y):
        return g.visible[y][x]

    def S(rx, ry):
        return int(rx * TILE) - cx, int(ry * TILE) - cy

    # подсветка дуги замаха секиры (телеграф удара)
    if g.axe_pending:
        dx, dy, ox, oy, _ = g.axe_pending
        A.tele.set_alpha(int(150 + 105 * math.sin(t / 90)))
        for (x, y) in g.axe_cells(ox, oy, dx, dy):
            if 0 <= x < COLS and 0 <= y < ROWS and g.grid[y][x] == 0:
                w.blit(A.tele, S(x, y))

    ex, ey = g.exit_pos
    if seen(ex, ey) or g.explored[ey][ex]:
        sx, sy = S(ex, ey)
        w.blit(A.exit, (sx, sy))
        if g.boss_alive:
            pygame.draw.rect(w, (200, 50, 50), (sx, sy, TILE, TILE), 3)
    for (x, y), state in g.traps.items():
        if state == "sprung" and g.explored[y][x]:
            w.blit(A.spikes, S(x, y))
    for (x, y) in g.chests:
        if seen(x, y):
            w.blit(A.chest, S(x, y))
    for (x, y) in g.barrels:
        if seen(x, y):
            w.blit(A.barrel, S(x, y))
    for (x, y), used in g.fountains.items():
        if g.explored[y][x]:
            w.blit(A.fountain_dry if used else A.fountain, S(x, y))
    for (x, y), n in g.npcs.items():
        if seen(x, y):
            sx, sy = S(x, y)
            bob = int(math.sin(t / 260 + x) * 2)
            w.blit(A.elder if n.kind == "elder" else A.merchant, (sx, sy + bob))
            if n.kind == "merchant":
                draw_text(w, F["normal_b"], "$", GOLD, sx + TILE // 2, sy - 22 + bob, "c")
            elif n.state == "new":
                draw_text(w, F["normal_b"], "!", GOLD, sx + TILE // 2, sy - 22 + bob, "c")

    for m in g.mobs:
        if not seen(m.x, m.y):
            continue
        sx, sy = S(m.rx, m.ry)
        bob = int(math.sin(t / 180 + m.seed) * 2)
        if m.lunge:
            a = math.sin(math.pi * (1 - m.lunge[2] / 10)) * 14
            sx += int(m.lunge[0] * a)
            sy += int(m.lunge[1] * a)
        img = A.mob_img(m.kind, t, m.flash > 0)
        if m.kind == "slime":
            sq = int((math.sin(t / 160 + m.seed) + 1) * 2.5)
            img = pygame.transform.scale(img, (TILE + sq, TILE - sq))
            w.blit(img, (sx - sq // 2, sy + sq))
        else:
            w.blit(img, (sx, sy + bob))
        if m.charge:
            pygame.draw.ellipse(w, (220, 60, 40), (sx + 2, sy + TILE - 12, TILE - 4, 12), 3)
            draw_text(w, F["big"], "!", RED, sx + TILE // 2, sy - 32, "c")
        elif not m.awake:
            draw_text(w, F["small"], "z", GRAY, sx + TILE - 8, sy - 6 + bob)
        if m.hp < m.max:
            bw = TILE - 12
            pygame.draw.rect(w, (60, 20, 20), (sx + 6, sy - 4, bw, 5))
            pygame.draw.rect(w, (220, 60, 60), (sx + 6, sy - 4, max(1, int(bw * m.hp / m.max)), 5))

    if g.over != "dead":
        sx, sy = S(g.prx, g.pry)
        if g.plunge:
            amp = 9 if g.plunge[4] == "axe" else 14
            a = math.sin(math.pi * (1 - g.plunge[2] / g.plunge[3])) * amp
            sx += int(g.plunge[0] * a)
            sy += int(g.plunge[1] * a)
        for key, col in (("rage", (230, 90, 30)), ("iron", (170, 180, 205)),
                         ("haste", CYAN), ("vamp", PURPLE)):
            if key in g.st:
                pulse = int(2 + math.sin(t / 120) * 2)
                pygame.draw.ellipse(w, col, (sx + 4 - pulse, sy + TILE - 14, TILE - 8 + pulse * 2, 12), 2)
        anim, f, wp = player_anim(g, t)
        img = A.pframe(anim, f, g.up["armor"], wp, g.pflash > 0, g.facing < 0)
        w.blit(img, (sx, sy))

    for p in g.projs:
        tt = p[4] / p[5]
        x = p[0] + (p[2] - p[0]) * tt - cx
        y = p[1] + (p[3] - p[1]) * tt - cy
        if p[6] == "arrow":
            ang = math.atan2(p[3] - p[1], p[2] - p[0])
            pygame.draw.line(w, (235, 225, 190), (x - math.cos(ang) * 14, y - math.sin(ang) * 14), (x, y), 3)
            pygame.draw.circle(w, (255, 255, 255), (int(x), int(y)), 3)
        else:
            pygame.draw.circle(w, (255, 120, 30), (int(x), int(y)), 9)
            pygame.draw.circle(w, (255, 230, 120), (int(x), int(y)), 5)

    for s in g.slashes:
        x, y, dx, dy, life, col, crit = s
        base = math.atan2(dy, dx)
        r = 26
        for off in ((0,) if not crit else (-0.5, 0.5)):
            pts = [(x - cx + math.cos(base + off + a) * r, y - cy + math.sin(base + off + a) * r)
                   for a in (-1.0, -0.5, 0, 0.5, 1.0)]
            pygame.draw.lines(w, col, False, pts, max(1, int(7 * life / 9)))

    # широкая дуга удара секиры
    for scx, scy, base, life in g.swings:
        prog = 1 - life / 14
        head = base + 1.15 - 2.3 * ease(prog)
        n = 10
        pts = [(scx - cx + math.cos(a) * TILE * 1.15, scy - cy + math.sin(a) * TILE * 1.15)
               for a in [base + 1.15 + (head - base - 1.15) * i / n for i in range(n + 1)]]
        if len(pts) > 1:
            wd = max(2, int(14 * life / 14))
            pygame.draw.lines(w, (255, 170, 70), False, pts, wd)
            pygame.draw.lines(w, (255, 245, 210), False, pts, max(1, wd // 3))

    for p in g.parts:
        sz = max(1, int(p[7] * p[4] / p[5] * 1.6))
        pygame.draw.rect(w, p[6], (int(p[0]) - cx - sz // 2, int(p[1]) - cy - sz // 2, sz, sz))
    for r in g.rings:
        fr = r[5] / r[6]
        col = tuple(int(c * fr) for c in r[4])
        pygame.draw.circle(w, col, (int(r[0]) - cx, int(r[1]) - cy), int(r[2]), max(1, int(5 * fr)))

    # тьма + круг света факела
    ov = A.overlay
    ov.fill((0, 0, 0, 228))
    light = A.light(g.light_radius())[(t // 120) % 3]
    pcx, pcy = int(g.prx * TILE) - cx + TILE // 2, int(g.pry * TILE) - cy + TILE // 2
    ov.blit(light, (pcx - light.get_width() // 2, pcy - light.get_height() // 2),
            special_flags=pygame.BLEND_RGBA_MIN)
    w.blit(ov, (0, 0))
    for sx, sy in glows:
        w.blit(A.glow, (sx + TILE // 2 - 55, sy + TILE // 2 - 55), special_flags=pygame.BLEND_RGB_ADD)

    if g.hp < g.max_hp * 0.3 and not g.over:
        w.blit(A.vigs[int((math.sin(t / 150) + 1) / 2 * 5.99)], (0, 0))
    if g.flash_t > 0:
        A.flashsurf.fill(g.flash)
        A.flashsurf.set_alpha(g.flash_t * 8)
        w.blit(A.flashsurf, (0, 0))

    for f in g.floaters:
        font = F["big"] if f[5] else F["normal_b"]
        img = font.render(f[0], True, f[3])
        pos = (int(f[1]) - cx - img.get_width() // 2, int(f[2]) - cy)
        w.blit(font.render(f[0], True, (0, 0, 0)), (pos[0] + 2, pos[1] + 2))
        w.blit(img, pos)

    ox = oy = 0
    if g.shake > 0:
        s = min(8, g.shake // 2 + 1)
        ox, oy = random.randint(-s, s), random.randint(-s, s)
    screen.fill((10, 8, 14))
    screen.blit(w, (ox, oy))

    # миникарта
    screen.blit(g.mini, (10, 10))
    pygame.draw.rect(screen, PANEL_BORDER, (8, 8, COLS * 2 + 4, ROWS * 2 + 4), 2)
    if g.explored[ey][ex]:
        pygame.draw.rect(screen, GOLD, (10 + ex * 2 - 1, 10 + ey * 2 - 1, 4, 4))
    for (x, y), n in g.npcs.items():
        if g.explored[y][x]:
            pygame.draw.rect(screen, CYAN if n.kind == "merchant" else (255, 255, 120),
                             (10 + x * 2 - 1, 10 + y * 2 - 1, 4, 4))
    if (t // 300) % 2 == 0:
        pygame.draw.rect(screen, (255, 255, 255), (10 + g.px * 2 - 1, 10 + g.py * 2 - 1, 4, 4))

    # статусы
    chips = [(f"{STATUS_NAME[k]} {v}", STATUS_COL[k]) for k, v in g.st.items()]
    if chips:
        total = sum(F["small"].size(c[0])[0] + 18 for c in chips)
        x = MAP_W // 2 - total // 2
        for label, col in chips:
            wd = F["small"].size(label)[0] + 12
            pygame.draw.rect(screen, (20, 17, 28), (x, 8, wd, 24))
            pygame.draw.rect(screen, col, (x, 8, wd, 24), 2)
            draw_text(screen, F["small"], label, col, x + 6, 10, shadow=False)
            x += wd + 6

    # квесты
    if g.quests:
        qw = 330
        qh = 28 + 22 * len(g.quests)
        pan = pygame.Surface((qw, qh), pygame.SRCALPHA)
        pan.fill((20, 17, 28, 200))
        screen.blit(pan, (MAP_W - qw - 8, 8))
        pygame.draw.rect(screen, PANEL_BORDER, (MAP_W - qw - 8, 8, qw, qh), 2)
        draw_text(screen, F["small"], "Задания", GOLD, MAP_W - qw, 12)
        for i, q in enumerate(g.quests):
            draw_text(screen, F["small"], f"{q['text']} ({min(q['p'], q['n'])}/{q['n']})",
                      TEXT, MAP_W - qw, 34 + 22 * i, shadow=False)

    # уведомления: вылетают слева, потом уезжают обратно
    ty = 104
    for text, col, age, life in g.toasts:
        k_in = ease_back(age / 16)
        k_out = ease((age - (life - 22)) / 22) if age > life - 22 else 0.0
        off = -(1 - k_in) * 280 - k_out * 280
        wd = F["small"].size(text)[0] + 32
        ts = pygame.Surface((wd, 28), pygame.SRCALPHA)
        ts.fill((20, 17, 28, 225))
        pygame.draw.rect(ts, col, (0, 0, wd, 28), 2)
        pygame.draw.rect(ts, col, (0, 0, 6, 28))
        ts.blit(F["small"].render(text, True, TEXT), (16, 4))
        ts.set_alpha(int(255 * (1 - k_out)))
        screen.blit(ts, (8 + off, ty))
        ty += 34

    if g.fade > 0:
        A.blacksurf.set_alpha(g.fade)
        screen.blit(A.blacksurf, (0, 0), (0, 0, MAP_W, MAP_H))
    if g.banner > 0:
        a = max(0, min(255, g.banner * 5, (170 - g.banner) * 10))
        title = F["title"].render(f"ЭТАЖ {g.depth}", True, GOLD)
        title.set_alpha(a)
        screen.blit(title, (MAP_W // 2 - title.get_width() // 2, MAP_H // 2 - 70))
        if g.boss_alive:
            sub = F["big"].render("БОСС: Король гоблинов", True, RED)
            sub.set_alpha(a)
            screen.blit(sub, (MAP_W // 2 - sub.get_width() // 2, MAP_H // 2 + 6))

    if g.lvl_banner > 0:
        a = max(0, min(255, g.lvl_banner * 8, (130 - g.lvl_banner) * 16))
        for txt, font, col, yy in ((f"УРОВЕНЬ {g.lvl}!", F["big"], GOLD, 96),
                                   ("Здоровье и урон выросли", F["normal"], TEXT, 134)):
            sh = font.render(txt, True, (0, 0, 0))
            im = font.render(txt, True, col)
            sh.set_alpha(a)
            im.set_alpha(a)
            x = MAP_W // 2 - im.get_width() // 2
            screen.blit(sh, (x + 2, yy + 2))
            screen.blit(im, (x, yy))

    if g.ui:
        # окна диалога/лавки плавно «выезжают» снизу и проявляются
        us = A.ui_surf
        us.fill((0, 0, 0, 0))
        g.ui.draw(us, A, F)
        k = ease(g.ui.t / 12)
        us.set_alpha(int(255 * k))
        screen.blit(us, (0, int((1 - k) * 50)))


def fit_text(font, text, maxw):
    if font.size(text)[0] <= maxw:
        return text
    while text and font.size(text + "…")[0] > maxw:
        text = text[:-1]
    return text.rstrip() + "…"


def draw_hud(screen, g, A, F):
    t = pygame.time.get_ticks()
    y0 = MAP_H
    pygame.draw.rect(screen, PANEL_BG, (0, y0, WIN_W, HUD_H))
    pygame.draw.line(screen, PANEL_BORDER, (0, y0), (WIN_W, y0), 3)
    draw_text(screen, F["big"], g.name, TEXT, 16, y0 + 5)

    bar = pygame.Rect(16, y0 + 40, 250, 22)
    pygame.draw.rect(screen, (50, 20, 28), bar)
    hp = max(0, g.hp)
    if g.hp_lag > hp + 0.5:                         # бледный «хвост» потерянного здоровья
        pygame.draw.rect(screen, (235, 215, 170), (bar.x, bar.y, int(bar.w * min(1, g.hp_lag / g.max_hp)), bar.h))
    col = GREEN if hp > g.max_hp * 0.6 else GOLD if hp > g.max_hp * 0.3 else RED
    pygame.draw.rect(screen, col, (bar.x, bar.y, int(bar.w * hp / g.max_hp), bar.h))
    pygame.draw.rect(screen, (200, 190, 220), bar, 2)
    label = F["small"].render(f"HP {hp}/{g.max_hp}", True, (15, 15, 20))
    screen.blit(label, (bar.centerx - label.get_width() // 2, bar.centery - label.get_height() // 2))
    xb = pygame.Rect(16, y0 + 66, 250, 8)
    pygame.draw.rect(screen, (30, 40, 60), xb)
    pygame.draw.rect(screen, BLUE, (xb.x, xb.y, int(xb.w * clamp01(g.xp_disp / g.xp_need())), xb.h))
    pygame.draw.rect(screen, (150, 170, 220), xb, 1)

    pygame.draw.circle(screen, GOLD, (28, y0 + 94), 9)
    pygame.draw.circle(screen, (170, 130, 30), (28, y0 + 94), 9, 2)
    draw_text(screen, F["normal"], f"{int(round(g.gold_disp))}", GOLD, 46, y0 + 82)
    draw_text(screen, F["normal"], f"Этаж {g.depth}  •  Ур. {g.lvl}", TEXT, 16, y0 + 110)

    for i, key in enumerate(ORDER):
        x = 290 + i * 54
        n = g.inv[key]
        pop = int(math.sin(g.slot_t[key] / 14 * math.pi) * 5)      # «подпрыгивание» при изменении
        slot = pygame.Rect(x, y0 + 6, 50, 56).inflate(pop * 2, pop * 2)
        pygame.draw.rect(screen, (32, 27, 44), slot)
        pygame.draw.rect(screen, ITEMS[key]["col"] if n else (70, 62, 90), slot, 2)
        screen.blit((A.icons if n else A.icons_dim)[key], (x + 9, y0 + 12 - pop))
        draw_text(screen, F["small"], str(i + 1), GRAY, slot.x + 4, slot.y - 2, shadow=False)
        draw_text(screen, F["small"], f"x{n}", TEXT if n else GRAY, slot.centerx, y0 + 42, "c", shadow=False)

    now = pygame.time.get_ticks()
    for i, (text, c, born) in enumerate(g.log):
        newest = i == len(g.log) - 1
        cc = c if newest else tuple(int(v * 0.65) for v in c)
        k = ease((now - born) / 260) if newest else 1.0       # новая строка выезжает слева
        draw_text(screen, F["small"], fit_text(F["small"], text, 440), cc,
                  290 - int((1 - k) * 70), y0 + 68 + i * 18,
                  shadow=False, alpha=int(255 * k))

    # оружие
    wx = 745
    wname = "Секира" if g.weapon == "axe" else "Меч"
    screen.blit(A.wicon[g.weapon], (wx, y0 + 6))
    draw_text(screen, F["normal_b"], wname, ORANGE if g.weapon == "axe" else TEXT, wx + 38, y0 + 6)
    if g.has_axe:
        draw_text(screen, F["small"], "Q — сменить", GRAY, wx + 38, y0 + 28, shadow=False)
    if g.axe_pending and (t // 200) % 2 == 0:
        draw_text(screen, F["small"], "ЗАМАХ!", ORANGE, wx + 130, y0 + 12, shadow=False)
    lo, hi = g.atk_range()
    stats = [f"Атака {lo}–{hi}", f"Броня {g.armor_val()}", f"Крит {int(g.crit_chance() * 100)}%",
             f"Свет {g.light_radius()}", f"Убито {g.kills}"]
    for i, s in enumerate(stats):
        draw_text(screen, F["small"], s, GRAY, wx, y0 + 48 + i * 19, shadow=False)


def draw_end(screen, g, F):
    k0 = ease(g.end_t / 50)
    dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    dim.fill((0, 0, 0, int(200 * k0)))
    screen.blit(dim, (0, 0))
    cx = WIN_W // 2

    def line(i, text, font, col, y):
        k = ease((g.end_t - 24 - i * 9) / 28)
        if k > 0:
            draw_text(screen, font, text, col, cx, y + int((1 - k) * 36), "c", alpha=int(255 * k))

    line(0, "ИГРА ОКОНЧЕНА", F["title"], RED, 90)
    line(1, f"{g.name} погиб: {g.cause}", F["big"], TEXT, 180)
    lines = [f"Достигнут этаж: {g.depth}", f"Золота собрано: {g.total_gold}",
             f"Врагов убито: {g.kills}", f"Уровень героя: {g.lvl}", f"Квестов выполнено: {g.done_quests}"]
    for i, s in enumerate(lines):
        line(2 + i, s, F["normal"], GOLD if i == 1 else TEXT, 250 + i * 34)
    if g.new_record:
        line(8, "НОВЫЙ РЕКОРД!", F["big"], GREEN, 440)
    line(9, "R — начать заново   •   Enter — в главное меню", F["normal"], GRAY, 520)


# ============================================================ меню и экраны
GLYPHS = {}


def glyph(font, ch, col):
    key = (id(font), ch, col)
    if key not in GLYPHS:
        GLYPHS[key] = font.render(ch, True, col)
    return GLYPHS[key]


def wavy_title(screen, font, text, y, t, c1, c2, phase=0.0, dx=0):
    widths = [font.size(ch)[0] for ch in text]
    x = WIN_W // 2 - sum(widths) // 2 + dx
    n = max(1, len(text) - 1)
    for i, ch in enumerate(text):
        k = i / n
        col = tuple(int(c1[j] + (c2[j] - c1[j]) * k) for j in range(3))
        off = int(math.sin(t / 300 + i * 0.55 + phase) * 6)
        screen.blit(glyph(font, ch, (30, 10, 0)), (x + 4, y + off + 4))
        for ddx, ddy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            screen.blit(glyph(font, ch, (120, 50, 10)), (x + ddx, y + off + ddy))
        screen.blit(glyph(font, ch, col), (x, y + off))
        x += widths[i]


def build_menu_bg(A):
    bg = pygame.Surface((WIN_W, WIN_H))
    for y in range(WIN_H // TILE + 1):
        for x in range(WIN_W // TILE + 1):
            bg.blit(A.wall if (x * 3 + y * 5) % 7 else A.floor[(x + y) % 4], (x * TILE, y * TILE))
    shade = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 165))
    bg.blit(shade, (0, 0))
    vig = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    for i in range(50):
        pygame.draw.rect(vig, (0, 0, 0, int(170 * (1 - i / 50) ** 2)), (i * 3, i * 3, WIN_W - 6 * i, WIN_H - 6 * i), 3)
    bg.blit(vig, (0, 0))
    return bg


class MenuFx:
    def __init__(self):
        self.embers = [self.new_ember(True) for _ in range(70)]

    @staticmethod
    def new_ember(anywhere=False):
        return [random.uniform(0, WIN_W), random.uniform(0, WIN_H) if anywhere else WIN_H + 5,
                random.uniform(0.4, 1.4), random.uniform(0, 6.28), random.uniform(1, 3)]

    def draw(self, screen):
        for e in self.embers:
            e[1] -= e[2]
            e[0] += math.sin(e[3] + e[1] / 40) * 0.5
            if e[1] < -5:
                e[:] = self.new_ember()
            b = max(0, min(1, e[1] / WIN_H))
            c = (min(255, int(255 * b + 60)), min(255, int(140 * b + 30)), 30)
            pygame.draw.rect(screen, c, (int(e[0]), int(e[1]), int(e[4]), int(e[4])))


def draw_torches(screen, A, t):
    for side, x in ((0, 40), (1, WIN_W - 40 - TILE * 2)):
        screen.blit(A.glow_big, (x + TILE - 160, 330 - 160 + int(math.sin(t / 90 + side) * 6)),
                    special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(A.big["torch"][(t // 120 + side) % 2], (x, 290))


def menu_items(sfx):
    return ["Новая игра", "Как играть", "Рекорды", "Создатели",
            "Звук: " + ("вкл" if sfx.on else "выкл"), "Выход"]


def draw_menu(screen, A, F, bg, fx, sel, sfx, rec, age, hov):
    t = pygame.time.get_ticks()
    screen.blit(bg, (0, 0))
    draw_torches(screen, A, t)
    fx.draw(screen)
    tk = ease(age / 800)
    wavy_title(screen, F["title"], "ТАИНСТВЕННАЯ", 40 - int((1 - tk) * 150), t, (255, 230, 110), (255, 150, 40))
    wavy_title(screen, F["huge"], "ПЕЩЕРА", 110 - int((1 - tk) * 220), t, (255, 150, 40), (230, 70, 40), 1.2)
    draw_text(screen, F["normal"], "бесконечное подземелье • золото • слава", GRAY, WIN_W // 2, 212, "c",
              alpha=int(255 * ease((age - 300) / 500)))
    rects = []
    for i, label in enumerate(menu_items(sfx)):
        base = pygame.Rect(WIN_W // 2 - 170, 262 + i * 54, 340, 44)
        rects.append(base)
        on = i == sel
        hov[i] += ((1.0 if on else 0.0) - hov[i]) * 0.25          # плавное наведение
        k = ease((age - 350 - i * 90) / 450)                       # кнопки влетают по очереди
        xoff = (-1 if i % 2 == 0 else 1) * int((1 - k) * 560)
        r = base.move(xoff, 0).inflate(int(hov[i] * 18), int(hov[i] * 4))
        mix = hov[i]
        fill = tuple(int(a + (b - a) * mix) for a, b in ((28, 70), (23, 48), (40, 95)))
        border = tuple(int(a + (b - a) * mix) for a, b in (((110, 240)), ((85, 200)), ((140, 70))))
        pygame.draw.rect(screen, fill, r)
        pygame.draw.rect(screen, border, r, 3 if on else 2)
        txt = tuple(int(a + (b - a) * mix) for a, b in ((225, 240), (220, 200), (235, 70)))
        draw_text(screen, F["big"], label, txt, r.centerx, r.y + 4, "c")
        if on and k >= 1:
            o = int(math.sin(t / 150) * 4)
            pygame.draw.polygon(screen, GOLD, [(r.x - 26 + o, r.centery - 10), (r.x - 26 + o, r.centery + 10), (r.x - 8 + o, r.centery)])
            pygame.draw.polygon(screen, GOLD, [(r.right + 26 - o, r.centery - 10), (r.right + 26 - o, r.centery + 10), (r.right + 8 - o, r.centery)])
    # погоня на дне экрана (герой теперь бежит по-настоящему)
    L = WIN_W + 400
    hx = int((t * 0.13) % L) - 200
    bob = int(abs(math.sin(t / 110)) * 6)
    screen.blit(A.big["goblin"], (hx - 140, WIN_H - 110 - int(abs(math.sin(t / 100 + 1)) * 8)))
    screen.blit(A.big["walk"][(t // 110) % 4], (hx, WIN_H - 110 - bob))
    bx = WIN_W - int((t * 0.09) % (WIN_W + 200))
    screen.blit(A.big["bat"], (bx, WIN_H - 220 + int(math.sin(t / 250) * 30)))
    if rec["depth"]:
        draw_text(screen, F["small"], f"Лучший забег: этаж {rec['depth']} • золото {rec['gold']}",
                  GRAY, WIN_W // 2, WIN_H - 26, "c")
    return rects


def draw_name_screen(screen, A, F, bg, fx, text, age):
    t = pygame.time.get_ticks()
    screen.blit(bg, (0, 0))
    fx.draw(screen)
    tk = ease(age / 600)
    wavy_title(screen, F["title"], "ТАИНСТВЕННАЯ ПЕЩЕРА", 120 - int((1 - tk) * 120), t,
               (255, 230, 110), (255, 120, 40))
    draw_text(screen, F["big"], "Как тебя зовут, искатель приключений?", TEXT, WIN_W // 2, 280, "c",
              alpha=int(255 * ease((age - 150) / 400)))
    bk = ease((age - 250) / 450)
    box = pygame.Rect(0, 340, int(440 * bk), 54)
    box.centerx = WIN_W // 2
    pygame.draw.rect(screen, PANEL_BG, box)
    pygame.draw.rect(screen, PANEL_BORDER, box, 3)
    if bk > 0.95:
        cursor = "|" if (t // 500) % 2 == 0 else ""
        screen.blit(F["big"].render(text + cursor, True, TEXT), (box.x + 14, box.y + 8))
        draw_text(screen, F["small"], "Enter — начать   •   пустое имя = «Безымянный Герой»   •   Esc — назад",
                  GRAY, WIN_W // 2, 415, "c")
    screen.blit(A.big["player"],
                (WIN_W // 2 - 48, 460 + int(math.sin(t / 220) * 4)))


def draw_help(screen, A, F, bg):
    screen.blit(bg, (0, 0))
    draw_text(screen, F["title"], "Как играть", GOLD, WIN_W // 2, 14, "c")
    lines = [
        ("Управление", GOLD),
        ("WASD / стрелки — ходьба", TEXT),
        ("Идти в врага — удар", TEXT),
        ("Идти в NPC, бочку, фонтан — действие", TEXT),
        ("Пробел — пропустить ход", TEXT),
        ("Q — сменить оружие (меч / секира)", TEXT),
        ("H — зелье лечения,  1–8 — предметы", TEXT),
        ("M — звук,  Esc — пауза,  F11 — экран", TEXT),
        ("", TEXT),
        ("Секира", GOLD),
        ("Редко выпадает из огра. Бьёт дугой по 3", TEXT),
        ("клеткам, но с задержкой в один ход.", TEXT),
        ("После находки в лавке есть её заточка.", TEXT),
        ("", TEXT),
        ("Советы", GOLD),
        ("Дверь на этаже ведёт вниз. На каждом", TEXT),
        ("5-м этаже дверь заперта, пока жив босс.", TEXT),
        ("Торговец ($) продаёт зелья и улучшения,", TEXT),
        ("кольчуга меняет внешний вид героя.", TEXT),
        ("Старцы (!) дают квесты с наградами.", TEXT),
    ]
    y = 84
    for s, c in lines:
        draw_text(screen, F["normal_b"] if c == GOLD else F["normal"], s, c, 40, y)
        y += 28
    draw_text(screen, F["big"], "Бестиарий", GOLD, 600, 84)
    y = 124
    for k, d in MOBS.items():
        screen.blit(pygame.transform.scale(A.mob[k][0], (44, 44)), (520, y))
        draw_text(screen, F["normal_b"], d["name"], d["col"], 574, y - 2)
        for j, ln in enumerate(wrap(d["desc"], F["small"], 360)):
            draw_text(screen, F["small"], ln, GRAY, 574, y + 22 + j * 16, shadow=False)
        y += 66
    draw_text(screen, F["small"], "Esc / Enter — назад", GRAY, WIN_W // 2, WIN_H - 28, "c")


def draw_records(screen, F, bg, rec):
    screen.blit(bg, (0, 0))
    draw_text(screen, F["title"], "Рекорды", GOLD, WIN_W // 2, 60, "c")
    rows = [("Самый глубокий этаж", rec["depth"]), ("Больше всего золота за забег", rec["gold"]),
            ("Больше всего убийств за забег", rec["kills"]), ("Всего забегов", rec["runs"])]
    for i, (a, b) in enumerate(rows):
        draw_text(screen, F["big"], a, TEXT, WIN_W // 2 - 20, 200 + i * 70, "r")
        draw_text(screen, F["big"], str(b), GOLD, WIN_W // 2 + 20, 200 + i * 70)
    draw_text(screen, F["small"], "Esc / Enter — назад", GRAY, WIN_W // 2, WIN_H - 28, "c")


CREATORS = ["LIMMiND", "Rusik"]


def draw_credits(screen, A, F, bg, fx, age):
    t = pygame.time.get_ticks()
    screen.blit(bg, (0, 0))
    draw_torches(screen, A, t)
    fx.draw(screen)
    tk = ease(age / 600)
    draw_text(screen, F["title"], "Создатели", GOLD, WIN_W // 2, 60 - int((1 - tk) * 100), "c")
    for i, name in enumerate(CREATORS):
        k = ease((age - 300 - i * 250) / 700)
        dx = (-1 if i % 2 == 0 else 1) * int((1 - k) * 700)
        wavy_title(screen, F["huge"], name, 200 + i * 130, t,
                   (255, 230, 110) if i == 0 else (255, 150, 40),
                   (255, 150, 40) if i == 0 else (230, 70, 40), i * 1.7, dx)
    draw_text(screen, F["normal"], "Спасибо, что играешь в «Таинственную пещеру»!", TEXT, WIN_W // 2, 500, "c",
              alpha=int(255 * ease((age - 1000) / 600)))
    draw_text(screen, F["small"], "Esc / Enter — назад", GRAY, WIN_W // 2, WIN_H - 28, "c")


# ============================================================ главный цикл
def view_info():
    win = pygame.display.get_surface()
    ww, wh = win.get_size()
    k = max(0.1, min(ww / WIN_W, wh / WIN_H))
    sw, sh = max(1, int(WIN_W * k)), max(1, int(WIN_H * k))
    return win, k, (ww - sw) // 2, (wh - sh) // 2, sw, sh


def ks(name):
    return getattr(pygame, "KSCAN_" + name, -1)


def main():
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    try:
        pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE, vsync=1)
    except Exception:
        pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)
    screen = pygame.Surface((WIN_W, WIN_H))      # игра рисует сюда, потом масштабируем в окно
    pygame.display.set_caption("Таинственная пещера")
    clock = pygame.time.Clock()
    pygame.key.set_repeat()          # повтор клавиш нужен только при вводе имени
    sfx = Sfx()
    music = Music(sfx)
    A = Assets()
    F = {"small": get_font(16), "normal": get_font(20), "normal_b": get_font(22, True),
         "big": get_font(28, True), "title": get_font(60, True), "huge": get_font(88, True)}
    bg = build_menu_bg(A)
    fx = MenuFx()
    rec = load_records()

    scan_moves = {ks("W"): (0, -1), ks("S"): (0, 1), ks("A"): (-1, 0), ks("D"): (1, 0)}
    key_moves = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}
    SC_Q, SC_R, SC_M, SC_H = ks("Q"), ks("R"), ks("M"), ks("H")
    ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER)
    N_MENU = 6

    state, sel, typed, game = "menu", 0, "", None
    state_t0 = pygame.time.get_ticks()
    rects = []
    hov = [0.0] * N_MENU
    held = {}                # зажатые клавиши движения: scancode -> (dx, dy)
    buffered = [None, 0]     # «запомненное» нажатие, чтобы короткие тапы не терялись
    fade, fade_dir, pending = 0.0, 0, None
    dt = 16

    # ---- плавные переходы между экранами: затемнение -> смена -> проявление
    def go(new_state, setup=None):
        nonlocal fade_dir, pending
        if fade_dir:
            return

        def do():
            nonlocal state, state_t0
            if setup:
                setup()
            if new_state:
                state = new_state
            state_t0 = pygame.time.get_ticks()
        pending = do
        fade_dir = 1

    def setup_name():
        nonlocal typed
        typed = ""
        pygame.key.set_repeat(400, 40)

    def setup_back():
        pygame.key.set_repeat()
        held.clear()

    def setup_game():
        nonlocal game
        pygame.key.set_repeat()
        held.clear()
        buffered[0] = None
        game = Game(typed.strip().capitalize() or "Безымянный Герой", sfx, rec)

    def setup_restart():
        nonlocal game
        held.clear()
        buffered[0] = None
        game = Game(game.name, sfx, rec)

    def activate(i):
        sfx.play("ui")
        if i == 0:
            go("name", setup_name)
        elif i == 1:
            go("help")
        elif i == 2:
            go("records")
        elif i == 3:
            go("credits")
        elif i == 4:
            sfx.on = not sfx.on
        else:
            pygame.quit()
            sys.exit()

    while True:
        _, vk, vox, voy, _, _ = view_info()
        now = pygame.time.get_ticks()
        age = now - state_t0

        def mpos(p):
            return int((p[0] - vox) / vk), int((p[1] - voy) / vk)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
                continue
            if ev.type == pygame.KEYUP:
                held.pop(ev.scancode, None)
                continue
            if ev.type == pygame.WINDOWFOCUSLOST:
                held.clear()
                buffered[0] = None
                continue
            if fade_dir:                  # во время перехода ввод не принимаем
                continue
            if state == "menu":
                if ev.type == pygame.MOUSEMOTION:
                    for i, r in enumerate(rects):
                        if r.collidepoint(mpos(ev.pos)):
                            if sel != i:
                                sfx.play("ui")
                            sel = i
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for i, r in enumerate(rects):
                        if r.collidepoint(mpos(ev.pos)):
                            sel = i
                            activate(i)
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_UP, pygame.K_w) or ev.scancode == ks("W"):
                        sel = (sel - 1) % N_MENU
                        sfx.play("ui")
                    elif ev.key in (pygame.K_DOWN, pygame.K_s) or ev.scancode == ks("S"):
                        sel = (sel + 1) % N_MENU
                        sfx.play("ui")
                    elif ev.key in ENTER or ev.key == pygame.K_SPACE:
                        activate(sel)
                    elif ev.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                continue
            if ev.type != pygame.KEYDOWN:
                continue
            if state in ("help", "records", "credits"):
                if ev.key in ENTER or ev.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                    go("menu")
                continue
            if state == "name":
                if ev.key == pygame.K_ESCAPE:
                    go("menu", setup_back)
                elif ev.key in ENTER:
                    go("play", setup_game)
                elif ev.key == pygame.K_BACKSPACE:
                    typed = typed[:-1]
                elif ev.unicode and ev.unicode.isprintable() and len(typed) < 16:
                    typed += ev.unicode
                continue

            # ----- state == "play"
            if ev.key == pygame.K_m or ev.scancode == SC_M:
                sfx.on = not sfx.on
                continue
            if game.paused:
                if ev.key == pygame.K_ESCAPE:
                    game.paused = False
                elif ev.key in ENTER:
                    go("menu")
                continue
            if game.ui:
                game.ui.key(ev)
                continue
            if game.over:
                if ev.key == pygame.K_r or ev.scancode == SC_R:
                    go(None, setup_restart)
                elif ev.key in ENTER or ev.key == pygame.K_ESCAPE:
                    go("menu")
                continue
            if ev.key == pygame.K_ESCAPE:
                game.paused = True
                game.pause_t = 0
                continue
            move = key_moves.get(ev.key) or scan_moves.get(ev.scancode)
            if move:
                held[ev.scancode] = move
                buffered[0], buffered[1] = move, 10
                continue
            if ev.key == pygame.K_q or ev.scancode == SC_Q:
                game.switch_weapon()                 # смена оружия не тратит ход
                continue
            if game.cd > 0 or game.freeze > 0:
                continue
            if ev.key == pygame.K_SPACE:
                game.wait()
            elif ev.key == pygame.K_h or ev.scancode == SC_H:
                game.use_item("heal")
            elif pygame.K_1 <= ev.key <= pygame.K_8:
                game.use_item(ORDER[ev.key - pygame.K_1])

        if state == "play":
            if game.ui or game.over or game.paused:
                held.clear()
                buffered[0] = None
            elif game.cd <= 0 and game.freeze <= 0 and not fade_dir:
                d = buffered[0] or (list(held.values())[-1] if held else None)
                buffered[0] = None
                if d:
                    game.try_move(*d)
            elif buffered[0]:
                buffered[1] -= 1
                if buffered[1] <= 0:
                    buffered[0] = None

        # ---- какая музыка должна играть
        if state in ("menu", "name", "help", "records", "credits"):
            music.play("menu")
        elif game is None or game.over:
            music.play(None)
        elif any(m.kind == "king" and m.awake for m in game.mobs):
            music.play("boss")                       # бой с Королём гоблинов
        else:
            music.play(None)
        music.update(dt)

        # ---- отрисовка
        if state == "menu":
            rects = draw_menu(screen, A, F, bg, fx, sel, sfx, rec, age, hov)
        elif state == "name":
            draw_name_screen(screen, A, F, bg, fx, typed, age)
        elif state in ("help", "records", "credits"):
            if state == "help":
                draw_help(A.page, A, F, bg)
            elif state == "records":
                draw_records(A.page, F, bg, rec)
            else:
                draw_credits(A.page, A, F, bg, fx, age)
            k = ease(age / 380)
            A.page.set_alpha(int(255 * k))
            screen.fill((0, 0, 0))
            screen.blit(A.page, (0, int((1 - k) * 30)))
        else:
            if not game.paused:
                if game.freeze > 0:
                    game.freeze -= 1
                else:
                    game.update()
            else:
                game.pause_t += 1
            draw_world(screen, game, A, F)
            draw_hud(screen, game, A, F)
            if game.over:
                draw_end(screen, game, F)
            if game.paused:
                k = ease(game.pause_t / 14)
                dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
                dim.fill((0, 0, 0, int(190 * k)))
                screen.blit(dim, (0, 0))
                draw_text(screen, F["title"], "ПАУЗА", GOLD, WIN_W // 2, 220 + int((1 - k) * 40), "c",
                          alpha=int(255 * k))
                draw_text(screen, F["normal"], "Esc — продолжить   •   Enter — в главное меню",
                          GRAY, WIN_W // 2, 320 + int((1 - k) * 40), "c", alpha=int(255 * k))

        # ---- затемнение при переходе между экранами
        if fade_dir == 1:
            fade += dt / 220
            if fade >= 1:
                fade, fade_dir = 1.0, -1
                if pending:
                    pending()
                    pending = None
        elif fade_dir == -1:
            fade -= dt / 280
            if fade <= 0:
                fade, fade_dir = 0.0, 0
        if fade > 0:
            A.blacksurf.set_alpha(int(255 * fade))
            screen.blit(A.blacksurf, (0, 0))

        win, _, ox, oy, sw, sh = view_info()
        win.fill((0, 0, 0))
        win.blit(pygame.transform.smoothscale(screen, (sw, sh)), (ox, oy))
        pygame.display.flip()
        dt = clock.tick(FPS)


if __name__ == "__main__":
    main()