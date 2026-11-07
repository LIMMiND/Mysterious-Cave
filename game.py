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
SAVE_GAME = os.path.join(BASE_DIR, "cave_save.json")   # сохранение текущего забега
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
    "heal":   dict(name="Зелье лечения",    kind="potion", col=(205, 40, 65),   light=(255, 150, 165), price=25, glyph="plus",
                   desc="Восстанавливает 40 HP"),
    "elixir": dict(name="Эликсир жизни",    kind="potion", col=(240, 120, 200), light=(255, 210, 240), price=70, glyph="heart",
                   desc="Полностью восстанавливает здоровье"),
    "rage":   dict(name="Зелье силы",       kind="potion", col=(230, 90, 30),   light=(255, 190, 120), price=40, glyph="fist",
                   desc="+50% урона на 10 ходов"),
    "iron":   dict(name="Зелье стали",      kind="potion", col=(140, 150, 175), light=(220, 225, 240), price=40, glyph="shield",
                   gcol=(40, 46, 66), desc="Получаемый урон -50% на 10 ходов"),
    "invis":  dict(name="Зелье невидимости", kind="potion", col=(150, 200, 255), light=(230, 245, 255), price=45, glyph="ghost",
                   gcol=(235, 248, 255), alpha=125, desc="Враги теряют тебя из виду (заметят только вплотную), 8 ходов"),
    "vamp":   dict(name="Зелье вампира",    kind="potion", col=(140, 40, 150),  light=(220, 150, 230), price=50, glyph="drop",
                   desc="Лечит от твоих ударов, 12 ходов"),
    "fire":   dict(name="Свиток огня",      kind="scroll", col=(200, 50, 10),   light=None,            price=55, glyph="flame",
                   desc="Взрыв вокруг: большой урон врагам рядом"),
    "map":    dict(name="Свиток карты",     kind="scroll", col=(40, 120, 60),   light=None,            price=35, glyph="cross",
                   desc="Открывает карту всего этажа"),
}
ITEM_COL = {"fire": (255, 110, 30), "map": (80, 200, 120)}      # цвет рамки слота для свитков
ORDER = ["heal", "elixir", "rage", "iron", "invis", "vamp", "fire", "map"]
DROP_W = {"heal": 40, "elixir": 5, "rage": 10, "iron": 10, "invis": 8, "vamp": 8, "fire": 10, "map": 9}
BUFF_TURNS = {"rage": 10, "iron": 10, "invis": 8, "vamp": 12}
STATUS_NAME = {"rage": "Сила", "iron": "Сталь", "invis": "Невидимость", "vamp": "Вампир",
               "poison": "Яд", "burn": "Горение", "frost": "Холод"}
STATUS_COL = {"rage": ORANGE, "iron": (170, 180, 205), "invis": (190, 225, 255), "vamp": PURPLE,
              "poison": GREEN, "burn": ORANGE, "frost": (150, 210, 255)}

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


def mob_pool(depth, biome="cave"):
    pool = [("goblin", 10), ("bat", 6)]
    if depth >= 2:
        pool.append(("slime", 6))
    if depth >= 3:
        pool.append(("archer", 5))
    if depth >= 4:
        pool.append(("mage", 4))
    if depth >= 5:
        pool.append(("ogre", 3))
    mult = BIOME_WEIGHT.get(biome, {})
    return [(k, w * mult.get(k, 1.0)) for k, w in pool]


# ============================================================ локации (биомы)
# Каждые 10 этажей — новая локация. Порядок выбора случайный, но без повторов подряд:
# новая локация не совпадает ни с текущей, ни с предыдущей.
BIOMES = {
    "cave": dict(
        name="Заброшенная пещера", wall_style="brick",
        floor=(38, 34, 44), dots=[(46, 41, 54), (32, 28, 38), (52, 46, 60)],
        wall=((78, 64, 92), (98, 82, 112), (36, 28, 46)),
        alts=[(40, 70, 120), (110, 60, 60), (40, 100, 90)],
        torch=((255, 150, 40), (255, 230, 120)), tint=(0, 0, 0, 0), haz=None,
        skin=None, color=(200, 170, 255)),
    "quarry": dict(
        name="Камнеломня", wall_style="block",
        floor=(62, 58, 52), dots=[(74, 70, 62), (50, 47, 42), (86, 82, 74)],
        wall=((118, 108, 92), (146, 136, 116), (62, 54, 44)),
        alts=[(130, 100, 60), (90, 100, 120), (120, 80, 70)],
        torch=((255, 160, 50), (255, 235, 130)), tint=(40, 30, 10, 14), haz=None,
        skin=((60, 56, 52), (130, 124, 114), (205, 200, 188), (255, 170, 40)), color=(210, 190, 150)),
    "flooded": dict(
        name="Затопленная пещера", wall_style="wet",
        floor=(30, 48, 62), dots=[(38, 60, 76), (24, 40, 52), (48, 76, 92)],
        wall=((44, 78, 98), (74, 118, 140), (20, 38, 52)),
        alts=[(30, 90, 110), (40, 60, 120), (30, 100, 80)],
        torch=((60, 200, 220), (200, 255, 255)), tint=(0, 40, 90, 26), haz="water",
        skin=((20, 50, 70), (50, 130, 150), (175, 228, 238), (230, 255, 255)), color=(110, 200, 230)),
    "lava": dict(
        name="Лавовая пещера", wall_style="basalt",
        floor=(44, 26, 24), dots=[(58, 32, 26), (34, 20, 20), (80, 40, 24)],
        wall=((62, 44, 44), (88, 62, 58), (26, 16, 16)),
        alts=[(120, 40, 20), (90, 20, 40), (110, 70, 20)],
        torch=((255, 120, 30), (255, 220, 90)), tint=(120, 20, 0, 26), haz="lava",
        skin=((50, 16, 10), (190, 60, 20), (255, 190, 60), (255, 240, 120)), color=(255, 120, 40)),
    "crystal": dict(
        name="Пещера самоцветов", wall_style="crystal",
        floor=(40, 32, 62), dots=[(52, 42, 80), (30, 24, 50), (70, 56, 100)],
        wall=((84, 64, 128), (136, 106, 196), (40, 28, 70)),
        alts=[(30, 90, 140), (140, 50, 110), (40, 120, 110)],
        torch=((200, 120, 255), (255, 220, 255)), tint=(80, 20, 120, 20), haz=None,
        skin=((50, 24, 90), (150, 80, 210), (242, 192, 255), (255, 255, 255)), color=(210, 150, 255)),
    "crypt": dict(
        name="Склеп", wall_style="crypt",
        floor=(52, 50, 48), dots=[(62, 60, 56), (42, 40, 38), (72, 70, 66)],
        wall=((96, 92, 84), (126, 122, 108), (44, 42, 38)),
        alts=[(70, 90, 70), (100, 90, 60), (70, 70, 100)],
        torch=((110, 230, 130), (220, 255, 220)), tint=(0, 40, 10, 18), haz=None,
        skin=((40, 44, 40), (110, 126, 100), (208, 214, 192), (120, 255, 140)), color=(190, 210, 170)),
    "castle": dict(
        name="Подземный замок", wall_style="block",
        floor=(46, 44, 60), dots=[(56, 54, 74), (36, 34, 48), (66, 62, 86)],
        wall=((82, 84, 106), (112, 114, 140), (38, 38, 54)),
        alts=[(100, 40, 60), (40, 60, 110), (60, 50, 100)],
        torch=((255, 150, 60), (255, 235, 150)), tint=(30, 10, 50, 20), haz=None,
        skin=((30, 24, 52), (84, 72, 130), (192, 182, 232), (255, 60, 70)), color=(170, 150, 230)),
    "acid": dict(
        name="Кислотные пещеры", wall_style="acid",
        floor=(38, 52, 34), dots=[(48, 66, 40), (28, 40, 26), (66, 92, 46)],
        wall=((70, 96, 60), (102, 136, 82), (30, 44, 26)),
        alts=[(110, 130, 30), (30, 120, 80), (80, 110, 60)],
        torch=((140, 255, 60), (230, 255, 150)), tint=(40, 120, 10, 24), haz="acid",
        skin=((20, 60, 10), (90, 190, 40), (222, 255, 122), (255, 255, 60)), color=(150, 240, 70)),
    "ice": dict(
        name="Ледяная пещера", wall_style="ice",
        floor=(86, 112, 134), dots=[(104, 134, 158), (70, 94, 116), (130, 160, 182)],
        wall=((120, 156, 184), (180, 214, 236), (62, 90, 116)),
        alts=[(120, 130, 210), (100, 190, 200), (150, 150, 230)],
        torch=((90, 170, 255), (220, 245, 255)), tint=(30, 80, 160, 24), haz="ice",
        skin=((50, 90, 130), (140, 200, 235), (242, 252, 255), (60, 120, 255)), color=(180, 225, 255)),
    "diamond": dict(
        name="Алмазная пещера", wall_style="crystal",
        floor=(90, 100, 120), dots=[(110, 122, 146), (74, 84, 104), (160, 180, 205)],
        wall=((132, 152, 182), (204, 228, 252), (70, 84, 110)),
        alts=[(150, 200, 230), (200, 170, 230), (160, 230, 215)],
        torch=((200, 240, 255), (255, 255, 255)), tint=(60, 110, 160, 14), haz=None,
        skin=((90, 120, 160), (170, 225, 250), (255, 255, 255), (120, 200, 255)), color=(190, 235, 255)),
}
BIOME_ORDER = list(BIOMES)
HAZ_FRAC = {"lava": 0.05, "water": 0.11, "acid": 0.05, "ice": 0.11}
# множители шанса появления видов монстров в локации
BIOME_WEIGHT = {
    "quarry": {"ogre": 1.6}, "flooded": {"slime": 2.0, "archer": 0.6}, "lava": {"mage": 2.0},
    "crystal": {"mage": 1.5}, "crypt": {"archer": 2.0, "bat": 0.6}, "castle": {"archer": 1.5, "mage": 1.5},
    "acid": {"slime": 2.2}, "ice": {"ogre": 1.5, "bat": 0.7}, "diamond": {"mage": 1.4, "ogre": 1.3},
}
NV = 5                      # сколько «оттенков» градиента у плиток
PROJ_COL = {"fire": (255, 150, 40), "arrow": (235, 225, 190), "rock": (150, 135, 110),
            "shard": (214, 160, 255), "spit": (150, 235, 60), "curse": (150, 255, 160), "ice": (180, 232, 255)}

# имя и множественное число обычных монстров в каждой локации (только внешний вид + названия)
BIOME_NAMES = {
    "quarry": dict(goblin=("Каменотёс-гоблин", "каменотёсов-гоблинов"), bat=("Каменный нетопырь", "каменных нетопырей"),
                   slime=("Булыжный слизень", "булыжных слизней"), archer=("Шахтёр-арбалетчик", "шахтёров-арбалетчиков"),
                   mage=("Рудный шаман", "рудных шаманов"), ogre=("Каменный тролль", "каменных троллей")),
    "flooded": dict(goblin=("Утопленник", "утопленников"), bat=("Летучая рыба", "летучих рыб"),
                    slime=("Медуза", "медуз"), archer=("Скелет-гарпунщик", "скелетов-гарпунщиков"),
                    mage=("Морская ведьма", "морских ведьм"), ogre=("Глубинный тритон", "глубинных тритонов")),
    "lava": dict(goblin=("Огненный бес", "огненных бесов"), bat=("Пепельный нетопырь", "пепельных нетопырей"),
                 slime=("Магмовый слизень", "магмовых слизней"), archer=("Обугленный лучник", "обугленных лучников"),
                 mage=("Пиромант", "пиромантов"), ogre=("Лавовый голем", "лавовых големов")),
    "crystal": dict(goblin=("Кристальный гоблин", "кристальных гоблинов"), bat=("Светящийся мотылёк", "светящихся мотыльков"),
                    slime=("Минеральный гель", "минеральных гелей"), archer=("Кристальный стрелок", "кристальных стрелков"),
                    mage=("Маг самоцветов", "магов самоцветов"), ogre=("Самоцветный голем", "самоцветных големов")),
    "crypt": dict(goblin=("Зомби", "зомби"), bat=("Призрачный нетопырь", "призрачных нетопырей"),
                  slime=("Могильная жижа", "могильных жиж"), archer=("Костяной лучник", "костяных лучников"),
                  mage=("Некромант", "некромантов"), ogre=("Упырь", "упырей")),
    "castle": dict(goblin=("Рыцарь-страж", "рыцарей-стражей"), bat=("Вампир-летучка", "вампиров-летучек"),
                   slime=("Кровавый студень", "кровавых студней"), archer=("Королевский арбалетчик", "королевских арбалетчиков"),
                   mage=("Вампир-чародей", "вампиров-чародеев"), ogre=("Чёрный латник", "чёрных латников")),
    "acid": dict(goblin=("Токсичный гоблин", "токсичных гоблинов"), bat=("Кислотный нетопырь", "кислотных нетопырей"),
                 slime=("Кислотный слизень", "кислотных слизней"), archer=("Мутант-стрелок", "мутантов-стрелков"),
                 mage=("Алхимик-мутант", "алхимиков-мутантов"), ogre=("Ядовитый великан", "ядовитых великанов")),
    "ice": dict(goblin=("Ледяной гоблин", "ледяных гоблинов"), bat=("Морозный нетопырь", "морозных нетопырей"),
                slime=("Ледяной слизень", "ледяных слизней"), archer=("Замёрзший лучник", "замёрзших лучников"),
                mage=("Ледяной маг", "ледяных магов"), ogre=("Снежный йети", "снежных йети")),
    "diamond": dict(goblin=("Алмазный страж", "алмазных стражей"), bat=("Алмазный мотылёк", "алмазных мотыльков"),
                    slime=("Бриллиантовый гель", "бриллиантовых гелей"), archer=("Алмазный лучник", "алмазных лучников"),
                    mage=("Алмазный маг", "алмазных магов"), ogre=("Алмазный колосс", "алмазных колоссов")),
}

# ============================================================ боссы 10-го этажа каждой локации
# kit — способности (название, перезарядка в ходах). Остальные поля — особые свойства.
BOSSES = {
    "cave": dict(name="Громгар", title="Пещерный Тролль", hp=300, dmg=(14, 22), xp=220, gold=(180, 260), sight=12,
                 col=(150, 130, 105), kit=[("slam", 4), ("rock", 3)],
                 desc="Огромный тролль. Бьёт кулаком по площади и кидает камни."),
    "quarry": dict(name="Монолит", title="Каменный Голем", hp=340, dmg=(15, 24), xp=240, gold=(190, 270), sight=12,
                   col=(150, 155, 170), armor=6, kit=[("rockfall", 5), ("slam", 4)],
                   desc="Очень прочный голем (броня). Обрушивает камни на героя."),
    "flooded": dict(name="Глубоган", title="Повелитель Бездны", hp=320, dmg=(14, 22), xp=250, gold=(190, 280), sight=12,
                    col=(70, 160, 180), kit=[("flood", 6), ("slam", 4), ("summon", 9)],
                    desc="Кракен. Затапливает пол, замедляя всех, и призывает утопленников."),
    "lava": dict(name="Магмарис", title="Лавовый Титан", hp=360, dmg=(16, 26), xp=280, gold=(210, 300), sight=12,
                 col=(255, 120, 40), trail="lava", kit=[("breath", 5), ("slam", 5)],
                 desc="Оставляет за собой лаву, дышит огнём и бьёт по площади."),
    "crystal": dict(name="Аметрион", title="Хранитель Самоцветов", hp=320, dmg=(14, 22), xp=270, gold=(200, 290), sight=12,
                    col=(210, 150, 255), reflect=0.25, regen=0.01, kit=[("shard", 2), ("blink", 6)],
                    desc="Отражает часть урона, лечится и телепортируется. Стреляет осколками."),
    "crypt": dict(name="Некрос", title="Король-лич", hp=330, dmg=(13, 21), xp=290, gold=(220, 310), sight=12,
                  col=(150, 255, 160), drain=True, kit=[("summon", 7), ("curse", 3)],
                  desc="Призывает нежить, проклинает ядом и лечится, нанося удары."),
    "castle": dict(name="Сэр Мортемар", title="Призрачный Доспех", hp=380, dmg=(16, 26), xp=310, gold=(230, 330), sight=12,
                   col=(170, 190, 255), armor=10, kit=[("charge", 5)],
                   desc="Призрак в доспехах. Очень сильная броня, таранит в прыжке."),
    "acid": dict(name="Токсикус", title="Король Кислотной Слизи", hp=340, dmg=(13, 21), xp=300, gold=(220, 320), sight=12,
                 col=(150, 240, 70), trail="acid", split=True, kit=[("spit", 3)],
                 desc="Оставляет кислоту, плюётся ядом и делится на слизней."),
    "ice": dict(name="Йотун", title="Ледяной Великан", hp=400, dmg=(17, 27), xp=330, gold=(240, 340), sight=12,
                col=(190, 230, 255), trail="ice", kit=[("freeze", 4), ("slam", 4)],
                desc="Замораживает героя (холод замедляет) и оставляет лёд."),
    "diamond": dict(name="Адамас", title="Алмазный Колосс", hp=420, dmg=(18, 28), xp=360, gold=(260, 380), sight=12,
                    col=(190, 235, 255), armor=8, reflect=0.25, kit=[("shard", 3), ("blink", 7)],
                    desc="Броня, отражение урона и град алмазных осколков."),
}
for _k, _b in BOSSES.items():
    MOBS["boss_" + _k] = dict(_b, plural=_b["name"], boss=True)
MOBS["king"]["title"] = "Предводитель гоблинов"
MOBS["king"]["kit"] = []


def is_boss(m):
    return bool(MOBS[m.kind].get("boss")) or m.kind == "king"


def mob_plural(kind, biome):
    n = BIOME_NAMES.get(biome, {}).get(kind)
    return n[1] if n else MOBS[kind]["plural"]


SWORD_STAGES = ["Железный меч", "Стальной клинок", "Закалённая сталь", "Синяя сталь", "Мифриловый клинок",
                "Мифрил с рунами", "Золотой клинок", "Рунический клинок", "Клинок бури", "Пылающий меч",
                "Легендарный меч Зари"]


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


def save_game_to_disk(g):
    try:
        with open(SAVE_GAME, "w", encoding="utf-8") as f:
            json.dump(g.dump(), f)
    except Exception:
        pass


def load_save_file():
    try:
        with open(SAVE_GAME, "r", encoding="utf-8") as f:
            d = json.load(f)
        if d.get("version") == 2 and "floor" in d:
            return d
    except Exception:
        pass
    return None


def delete_save():
    try:
        if os.path.isfile(SAVE_GAME):
            os.remove(SAVE_GAME)
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


def torch_sprite(f, c1=(255, 150, 40), c2=(255, 230, 120)):
    s = new_sprite()
    rect(s, (60, 45, 35), 6, 7, 4, 2)
    rect(s, (100, 78, 55), 7, 8, 2, 6)
    if f == 0:
        pygame.draw.polygon(s, c1, [(8, 1), (5, 7), (11, 7)])
        pygame.draw.polygon(s, c2, [(8, 3), (7, 7), (9, 7)])
    else:
        pygame.draw.polygon(s, c1, [(9, 2), (5, 7), (11, 7)])
        pygame.draw.polygon(s, c2, [(8, 4), (7, 7), (9, 7)])
    return scaled(s)


# ---------------------------------------------------------------- герой: кадры анимации
def armor_palette(lvl):
    """(тёмный, средний, светлый) цвет металла по уровню кольчуги."""
    if lvl >= 10:
        return (170, 120, 30), (225, 175, 60), (255, 235, 140)
    if lvl >= 4:
        return (125, 135, 160), (180, 190, 212), (232, 238, 252)
    return (95, 100, 115), (140, 145, 160), (195, 200, 215)


def build_player(anim, f, armor, weapon, wl=0):
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
    (draw_axe if weapon == "axe" else draw_sword)(s, hand, ang, wl)
    return scaled(s)


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


# ============================================================ графика локаций
def lerpc(a, b, t):
    t = clamp01(t)
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def shade_c(c, k):
    return lerpc(c, (255, 255, 255), k) if k > 0 else lerpc(c, (0, 0, 0), -k)


def _floor_surf(biome, base, dots, seed, var=0):
    rng = random.Random(seed)
    s = pygame.Surface((PX, PX))
    s.fill(base)
    for _ in range(14):
        s.set_at((rng.randrange(PX), rng.randrange(PX)), rng.choice(dots))
    lt, dk = shade_c(base, 0.25), shade_c(base, -0.3)
    if biome == "quarry":
        for _ in range(5):
            x, y = rng.randrange(1, 14), rng.randrange(1, 15)
            pygame.draw.rect(s, lt, (x, y, 2, 1))
    elif biome == "flooded":
        wl = lerpc(base, (120, 190, 230), 0.4)
        for y in (4, 11):
            for x in range(PX):
                if (x + y) % 4 < 2:
                    s.set_at((x, y), wl)
    elif biome == "lava":
        x, y = rng.randrange(3, 12), 1
        for _ in range(7):
            s.set_at((x, y), (22, 10, 10))
            if rng.random() < 0.35:
                s.set_at((x, y), (225, 90, 30))
            y += 2
            x = max(1, min(14, x + rng.choice((-1, 0, 1))))
    elif biome == "crystal":
        for _ in range(2):
            s.set_at((rng.randrange(1, 15), rng.randrange(1, 15)), shade_c(base, 0.55))
    elif biome == "crypt":
        if var == 1:
            for _ in range(8):
                s.set_at((rng.randrange(PX), rng.randrange(PX)), (176, 156, 102))
        elif var == 2:
            for i in range(5):
                s.set_at((2 + i * 2, 13 - i * 2), lt)
        else:
            pygame.draw.line(s, dk, (0, 8), (PX, 8))
    elif biome == "castle":
        pygame.draw.line(s, dk, (0, 8), (PX, 8))
        pygame.draw.line(s, dk, (4, 0), (4, 7))
        pygame.draw.line(s, dk, (11, 8), (11, 15))
    elif biome == "acid":
        cx, cy = rng.randrange(3, 12), rng.randrange(3, 12)
        for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (1, 1)):
            s.set_at((cx + dx, cy + dy), (112, 172, 52))
    elif biome == "ice":
        for i in range(4):
            s.set_at((3 + i, 12 - i), lt)
        s.set_at((10, 5), lt)
        s.set_at((11, 4), lt)
    elif biome == "diamond":
        for _ in range(2):
            s.set_at((rng.randrange(1, 15), rng.randrange(1, 15)), (255, 255, 255))
    pygame.draw.rect(s, shade_c(base, -0.25), (0, 0, PX, PX), 1)
    return s


def _deco_draw(s, biome, which, rng):
    if biome == "cave":
        if which == 1:
            for _ in range(10):
                s.set_at((rng.randrange(1, 15), rng.randrange(1, 15)),
                         rng.choice([(48, 78, 50), (40, 66, 44), (58, 92, 58)]))
        else:
            rect(s, (205, 200, 185), 4, 10, 7, 1)
            s.set_at((3, 9), (205, 200, 185)); s.set_at((3, 11), (205, 200, 185))
            s.set_at((11, 9), (205, 200, 185)); s.set_at((11, 11), (205, 200, 185))
            rect(s, (215, 210, 195), 9, 4, 3, 3)
            s.set_at((9, 5), (30, 25, 30)); s.set_at((11, 5), (30, 25, 30))
    elif biome == "quarry":
        if which == 1:
            for _ in range(5):
                x, y = rng.randrange(2, 14), rng.randrange(2, 14)
                s.set_at((x, y), (240, 200, 60))
                s.set_at((x + 1, y), (190, 150, 40))
        else:
            for _ in range(3):
                x, y = rng.randrange(2, 11), rng.randrange(3, 12)
                rect(s, (122, 116, 106), x, y, 3, 2)
                rect(s, (86, 82, 74), x, y + 2, 3, 1)
    elif biome == "flooded":
        if which == 1:
            for x in (4, 8, 11):
                for y in range(13 - rng.randrange(3, 6), 13):
                    s.set_at((x + (y % 2), y), (40, 150, 84))
        else:
            rect(s, (240, 214, 196), 5, 9, 4, 2)
            rect(s, (212, 164, 152), 6, 11, 2, 1)
            rect(s, (240, 214, 196), 10, 5, 2, 2)
    elif biome == "lava":
        if which == 1:
            for _ in range(7):
                s.set_at((rng.randrange(1, 15), rng.randrange(1, 15)),
                         rng.choice([(255, 120, 30), (255, 200, 80), (120, 40, 20)]))
        else:
            rect(s, (74, 62, 60), 5, 6, 5, 4)
            s.set_at((6, 7), (20, 14, 14)); s.set_at((8, 7), (20, 14, 14))
            rect(s, (74, 62, 60), 4, 10, 7, 1)
    elif biome == "crystal":
        if which == 1:
            for x, y in ((4, 10), (10, 7)):
                pygame.draw.polygon(s, (214, 160, 255), [(x, y), (x + 1, y - 4), (x + 2, y)])
                s.set_at((x + 1, y - 3), (255, 245, 255))
        else:
            pygame.draw.circle(s, (92, 62, 142), (8, 9), 5)
            pygame.draw.circle(s, (232, 192, 255), (8, 9), 3)
            pygame.draw.circle(s, (255, 235, 255), (8, 8), 1)
    elif biome == "crypt":
        if which == 1:
            for i in range(7):
                s.set_at((1 + i, 1), (220, 220, 210))
                s.set_at((1, 1 + i), (220, 220, 210))
                s.set_at((1 + i // 2 + 1, 1 + i // 2 + 1), (200, 200, 190))
            pygame.draw.line(s, (200, 200, 190), (1, 1), (7, 7))
        else:
            rect(s, (205, 200, 185), 4, 10, 7, 1)
            s.set_at((3, 9), (205, 200, 185)); s.set_at((11, 11), (205, 200, 185))
            rect(s, (215, 210, 195), 8, 4, 3, 3)
            s.set_at((8, 5), (30, 25, 30)); s.set_at((10, 5), (30, 25, 30))
    elif biome == "castle":
        if which == 1:
            pygame.draw.lines(s, (20, 18, 30), False, [(3, 2), (6, 6), (5, 9), (9, 13)])
        else:
            rect(s, (150, 30, 44), 3, 6, 6, 4)
            rect(s, (190, 50, 64), 4, 7, 4, 1)
            s.set_at((11, 11), (240, 200, 70)); s.set_at((12, 11), (240, 200, 70))
    elif biome == "acid":
        if which == 1:
            pygame.draw.ellipse(s, (96, 190, 40), (3, 5, 10, 7))
            pygame.draw.ellipse(s, (170, 240, 90), (5, 6, 4, 3))
        else:
            rect(s, (200, 220, 160), 4, 10, 7, 1)
            rect(s, (210, 230, 170), 9, 4, 3, 3)
            s.set_at((9, 5), (30, 60, 20)); s.set_at((11, 5), (30, 60, 20))
    elif biome == "ice":
        if which == 1:
            for _ in range(10):
                s.set_at((rng.randrange(2, 14), rng.randrange(2, 14)), (232, 248, 255))
        else:
            for x in (5, 9):
                pygame.draw.polygon(s, (206, 238, 252), [(x, 12), (x + 1, 5), (x + 2, 12)])
    elif biome == "diamond":
        if which == 1:
            for x, y in ((4, 9), (9, 6), (11, 11)):
                pygame.draw.polygon(s, (230, 250, 255), [(x, y), (x + 1, y - 2), (x + 2, y)])
        else:
            for x, y in ((5, 5), (10, 10)):
                s.set_at((x, y), (255, 255, 255))
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    s.set_at((x + d[0], y + d[1]), (190, 235, 255))


def _wall_surf(biome, style, wall, seed, var=0):
    base, hi, mortar = wall
    rng = random.Random(seed)
    s = pygame.Surface((PX, PX))
    s.fill(base)
    if style in ("brick", "wet", "acid", "crypt"):
        mc = mortar
        if style == "crypt" and var == 1:        # песчаный склеп: кирпич светлее, швы тёплые
            s.fill(lerpc(base, (190, 160, 100), 0.5))
            hi, mc = (214, 188, 128), (110, 88, 50)
        elif style == "crypt" and var == 2:      # королевский склеп: тёмный мавзолей с нишами
            s.fill(lerpc(base, (40, 40, 60), 0.6))
            hi, mc = (96, 96, 128), (20, 20, 32)
        for i, y in enumerate((0, 5, 10)):
            pygame.draw.line(s, hi, (0, y + 1), (PX, y + 1))
            pygame.draw.line(s, mc, (0, y), (PX, y))
            off = 0 if i % 2 == 0 else 4
            for x in range(off, PX, 8):
                pygame.draw.line(s, mc, (x, y), (x, y + 4))
        pygame.draw.line(s, mc, (0, 15), (PX, 15))
        if style == "wet":
            for _ in range(3):
                x, y = rng.randrange(1, 15), rng.randrange(0, 6)
                for k in range(rng.randrange(3, 7)):
                    s.set_at((x, y + k), (130, 200, 230))
            pygame.draw.line(s, (26, 70, 104), (0, 14), (PX, 14))
        elif style == "acid":
            for _ in range(3):
                x, y = rng.randrange(1, 15), rng.randrange(0, 4)
                for k in range(rng.randrange(4, 9)):
                    s.set_at((x, y + k), (130, 220, 50))
                s.set_at((x, y + k + 1), (200, 255, 120))
        elif style == "crypt" and var == 0:      # костяной склеп: черепа в стене
            for x, y in ((2, 2), (9, 7)):
                rect(s, (214, 208, 190), x, y, 4, 3)
                s.set_at((x + 1, y + 1), (30, 26, 24)); s.set_at((x + 3, y + 1), (30, 26, 24))
        elif style == "crypt" and var == 1:      # иероглифы
            for x, y in ((3, 2), (10, 7)):
                pygame.draw.line(s, (90, 66, 36), (x, y), (x + 3, y))
                s.set_at((x + 1, y + 1), (90, 66, 36)); s.set_at((x + 2, y + 2), (90, 66, 36))
        elif style == "crypt" and var == 2:      # ниша-арка
            rect(s, (10, 10, 18), 5, 5, 6, 10)
            pygame.draw.ellipse(s, (10, 10, 18), (5, 2, 6, 6))
    elif style == "block":
        for i, y in enumerate((0, 8)):
            off = 0 if i == 0 else 5
            for x0 in range(-off, PX, 10):
                bc = lerpc(base, hi, rng.random() * 0.5)
                pygame.draw.rect(s, bc, (x0 + 1, y + 1, 9, 7))
        for y in (0, 8):
            pygame.draw.line(s, mortar, (0, y), (PX, y))
        for x in (0, 10):
            pygame.draw.line(s, mortar, (x + (0 if x == 0 else 0), 0), (x, 7))
        pygame.draw.line(s, mortar, (5, 8), (5, 15))
        pygame.draw.line(s, mortar, (15, 8), (15, 15))
        pygame.draw.line(s, hi, (1, 1), (8, 1))
    elif style == "basalt":
        for x in range(0, PX, 4):
            pygame.draw.line(s, mortar, (x, 0), (x + rng.choice((-1, 0, 1)), 15))
            pygame.draw.line(s, shade_c(base, 0.2), (x + 1, 0), (x + 1, 7))
        x, y = rng.randrange(3, 12), 0
        for _ in range(8):
            s.set_at((x, y), (255, 120, 30))
            if rng.random() < 0.4:
                s.set_at((x, y), (255, 210, 90))
            y += 2
            x = max(1, min(14, x + rng.choice((-1, 0, 1))))
    elif style == "crystal":
        s.fill(shade_c(base, -0.35))
        for _ in range(3):
            x, y = rng.randrange(2, 13), rng.randrange(7, 15)
            h = rng.randrange(4, 8)
            col = lerpc(base, hi, rng.random())
            pygame.draw.polygon(s, col, [(x, y), (x + 1, y - h), (x + 2, y)])
            s.set_at((x + 1, y - h + 1), (255, 255, 255))
        pygame.draw.line(s, mortar, (0, 15), (PX, 15))
        pygame.draw.line(s, shade_c(base, -0.1), (0, 0), (PX, 0))
    elif style == "ice":
        for i in range(3):
            pygame.draw.line(s, hi, (i * 6, 0), (i * 6 + 6, 6))
            pygame.draw.line(s, shade_c(base, 0.12), (i * 6 + 3, 8), (i * 6 + 8, 14))
        pygame.draw.lines(s, mortar, False, [(6, 3), (8, 7), (7, 10), (10, 14)])
        pygame.draw.line(s, hi, (0, 0), (PX, 0))
    return s


def make_tileset(biome, seed, alt_idx, var=0):
    """Плитки локации в NV оттенках (для градиента цвета по карте)."""
    B = BIOMES[biome]
    alt = B["alts"][alt_idx % len(B["alts"])]
    ts = {"floor": [], "deco": [], "wall": []}
    for v in range(NV):
        t = v / (NV - 1) * 0.55
        fb = lerpc(B["floor"], alt, t * 0.7)
        fd = [lerpc(c, alt, t * 0.6) for c in B["dots"]]
        wb, wh, wm = (lerpc(c, alt, t * 0.7) for c in B["wall"])
        ts["floor"].append([scaled(_floor_surf(biome, fb, fd, seed + i * 31 + v * 7, var)) for i in range(4)])
        decos = []
        for which in (1, 2):
            sf = _floor_surf(biome, fb, fd, seed + 500 + which, var)
            _deco_draw(sf, biome, which, random.Random(seed + which * 11 + v))
            decos.append(scaled(sf))
        ts["deco"].append(decos)
        ts["wall"].append([scaled(_wall_surf(biome, B["wall_style"], (wb, wh, wm), seed + 900 + j * 5 + v, var))
                           for j in range(2)])
    return ts


def hazard_sprite(kind, f):
    s = new_sprite()
    if kind == "lava":
        pygame.draw.ellipse(s, (60, 24, 16), (0, 1, 16, 14))
        pygame.draw.ellipse(s, (225, 85, 20), (1, 2, 14, 12))
        for x, y in (((3, 5), (9, 8), (6, 10), (11, 4)) if f == 0 else ((4, 6), (10, 7), (5, 9), (9, 4))):
            rect(s, (255, 205, 80), x, y, 2, 1)
        rect(s, (170, 50, 10), 3 + f, 8, 2, 1)
    elif kind == "water":
        pygame.draw.ellipse(s, (30, 80, 140, 215), (0, 1, 16, 14))
        pygame.draw.ellipse(s, (60, 130, 205, 215), (1, 2, 14, 12))
        for y in (5, 9):
            for x in range(3, 13):
                if (x + y + f * 2) % 4 < 2:
                    s.set_at((x, y), (170, 220, 250, 230))
    elif kind == "acid":
        pygame.draw.ellipse(s, (50, 110, 20), (0, 1, 16, 14))
        pygame.draw.ellipse(s, (110, 205, 40), (1, 2, 14, 12))
        for x, y in (((4, 5), (10, 8), (7, 10)) if f == 0 else ((5, 6), (9, 5), (6, 9))):
            pygame.draw.circle(s, (200, 255, 120), (x, y), 1)
        s.set_at((11 - f, 4), (240, 255, 190))
    else:   # ice
        pygame.draw.ellipse(s, (120, 175, 215, 230), (0, 1, 16, 14))
        pygame.draw.ellipse(s, (190, 232, 250, 230), (1, 2, 14, 12))
        pygame.draw.line(s, (255, 255, 255), (4, 10), (10, 4))
        pygame.draw.line(s, (235, 250, 255), (6, 11), (11, 6))
        s.set_at((11, 10), (255, 255, 255))
    return scaled(s)


# ---------------------------------------------------------------- скины монстров
def _recolor(src, skin):
    dark, mid, light, eye = skin
    out = src.copy()
    w, h = out.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = out.get_at((x, y))
            if a < 120:
                continue
            if (r > 200 and g < 110 and b < 110) or (r > 230 and g > 190 and b < 110):
                c = eye
            else:
                k = clamp01(((0.3 * r + 0.59 * g + 0.11 * b) / 255) * 1.15)
                c = lerpc(dark, mid, k * 2) if k < 0.5 else lerpc(mid, light, (k - 0.5) * 2)
            out.set_at((x, y), (c[0], c[1], c[2], a))
    return out


def _P(img, col, x, y, w=1, h=1):
    pygame.draw.rect(img, col, (x * SCALE, y * SCALE, w * SCALE, h * SCALE))


def _skin_overlay(img, biome, kind, f):
    humanoid = kind in ("goblin", "archer", "mage")
    rng = random.Random(hash((biome, kind)) & 0xFFFF)
    if biome == "quarry":
        if humanoid:
            _P(img, (250, 200, 40), 4, 2, 8, 1)
            _P(img, (250, 200, 40), 5, 1, 6, 1)
        for _ in range(4):
            _P(img, (160, 156, 146), rng.randrange(3, 13), rng.randrange(6, 13))
    elif biome == "flooded":
        if humanoid:
            _P(img, (40, 150, 80), 5, 2, 1, 2)
            _P(img, (40, 150, 80), 10, 1, 1, 3)
        if kind == "slime":
            for x in (4, 7, 10):
                _P(img, (180, 238, 248), x, 14 + (f if False else 0), 1, 2)
        _P(img, (160, 225, 255), 3, 10, 1, 2)
        _P(img, (160, 225, 255), 12, 12 - f, 1, 2)
    elif biome == "lava":
        top = 0 if f else 1
        _P(img, (255, 150, 30), 6, top, 4, 2)
        _P(img, (255, 225, 100), 7, top, 2, 1)
        for _ in range(5):
            _P(img, (255, 130, 30), rng.randrange(3, 13), rng.randrange(5, 14))
    elif biome == "crystal":
        for x in (3, 12):
            _P(img, (226, 170, 255), x, 5, 1, 3)
            _P(img, (255, 245, 255), x, 5)
        _P(img, (255, 255, 255), 5 + f * 5, 3)
    elif biome == "crypt":
        if kind != "bat":
            _P(img, (208, 202, 172), 5, 9, 6, 1)
            _P(img, (208, 202, 172), 5, 11, 6, 1)
    elif biome == "castle":
        _P(img, (150, 24, 40), 2, 7, 2, 7)
        _P(img, (150, 24, 40), 12, 7, 2, 7)
        if kind == "goblin":
            _P(img, (150, 156, 176), 4, 2, 8, 3)
            _P(img, (210, 40, 56), 7, 0, 2, 2)
        if kind == "bat":
            _P(img, (255, 255, 255), 6, 8)
            _P(img, (255, 255, 255), 9, 8)
    elif biome == "acid":
        _P(img, (205, 255, 135), 4, 8, 2, 2)
        _P(img, (205, 255, 135), 10, 6 + f, 1, 1)
        _P(img, (205, 255, 135), 8, 11, 1, 1)
        _P(img, (120, 230, 40), 3, 12, 1, 3)
    elif biome == "ice":
        _P(img, (232, 250, 255), 5, 2, 1, 2)
        _P(img, (232, 250, 255), 8, 1, 1, 3)
        _P(img, (232, 250, 255), 10, 2, 1, 2)
        for _ in range(4):
            _P(img, (255, 255, 255), rng.randrange(3, 13), rng.randrange(5, 14))
    elif biome == "diamond":
        for x, y in (((3, 3), (12, 10)) if f == 0 else ((12, 4), (4, 11))):
            _P(img, (255, 255, 255), x, y)
            _P(img, (200, 240, 255), x - 1, y)
            _P(img, (200, 240, 255), x + 1, y)
            _P(img, (200, 240, 255), x, y - 1)
            _P(img, (200, 240, 255), x, y + 1)
        _P(img, (255, 255, 255), 4, 6, 1, 1)
        _P(img, (255, 255, 255), 11, 8, 1, 1)


def skin_frames(base_frames, biome, kind):
    skin = BIOMES[biome]["skin"]
    out = []
    for f, fr in enumerate(base_frames):
        img = _recolor(fr, skin)
        _skin_overlay(img, biome, kind, f)
        out.append(img)
    return out


# ---------------------------------------------------------------- боссы (24x24, увеличены в 3 раза)
def _boss_canvas():
    s = pygame.Surface((24, 24), pygame.SRCALPHA)
    return s, (lambda c, x, y, w, h: pygame.draw.rect(s, c, (x, y, w, h)))


def _boss_cave(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 80), 3, 21, 18, 3)
    R((86, 72, 60), 7, 18, 4, 4); R((86, 72, 60), 13, 18, 4, 4)
    R((112, 96, 80), 5, 9 + b, 14, 10 - b)
    R((142, 124, 104), 7, 12 + b, 10, 6 - b)
    R((90, 130, 70), 6, 10 + b, 2, 2); R((90, 130, 70), 15, 15 + b, 3, 2)
    R((120, 70, 40), 6, 17, 12, 3)
    R((112, 96, 80), 2, 9 + b, 3, 9); R((112, 96, 80), 19, 9 + b, 3, 9)
    R((142, 124, 104), 2, 17 + b, 3, 2); R((142, 124, 104), 19, 17 + b, 3, 2)
    R((110, 70, 40), 21, 1, 2, 15); R((86, 52, 28), 20, 0, 4, 5)
    R((190, 190, 180), 19, 1, 1, 1); R((190, 190, 180), 24 - 1, 2, 1, 1)
    R((130, 114, 96), 7, 3 + b, 10, 7)
    R((130, 114, 96), 5, 5 + b, 2, 3); R((130, 114, 96), 17, 5 + b, 2, 3)
    R((255, 220, 60), 9, 6 + b, 2, 2); R((255, 220, 60), 13, 6 + b, 2, 2)
    R((30, 20, 20), 8, 5 + b, 4, 1); R((30, 20, 20), 12, 5 + b, 4, 1)
    R((236, 236, 214), 9, 9 + b, 1, 2); R((236, 236, 214), 14, 9 + b, 1, 2)
    R((60, 40, 40), 10, 9 + b, 4, 1)
    return s


def _boss_quarry(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 80), 2, 21, 20, 3)
    R((96, 100, 112), 6, 17, 5, 5); R((96, 100, 112), 13, 17, 5, 5)
    R((124, 128, 142), 5, 8 + b, 14, 10)
    R((150, 154, 168), 5, 8 + b, 14, 2)
    R((76, 80, 92), 11, 10 + b, 1, 6); R((76, 80, 92), 8, 13 + b, 4, 1); R((76, 80, 92), 14, 12 + b, 3, 1)
    R((240, 200, 60), 7, 11 + b, 1, 1); R((240, 200, 60), 16, 14 + b, 1, 1)
    R((110, 114, 128), 1, 8 + b, 5, 5); R((110, 114, 128), 18, 8 + b, 5, 5)
    R((124, 128, 142), 1, 13 + b, 4, 7); R((124, 128, 142), 19, 13 + b, 4, 7)
    R((96, 100, 112), 0, 20, 6, 2); R((96, 100, 112), 18, 20, 6, 2)
    R((104, 108, 122), 8, 2 + b, 8, 6)
    R((140, 144, 158), 8, 2 + b, 8, 1)
    R((255, 150, 30), 9, 4 + b, 2, 2); R((255, 150, 30), 13, 4 + b, 2, 2)
    R((60, 62, 74), 10, 7 + b, 4, 1)
    return s


def _boss_flooded(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 70), 2, 21, 20, 3)
    body, dark, light = (44, 128, 150), (28, 86, 108), (110, 200, 220)
    pygame.draw.ellipse(s, dark, (4, 1 + b, 16, 14))
    pygame.draw.ellipse(s, body, (5, 2 + b, 14, 12))
    R(light, 8, 3 + b, 4, 1); R(light, 7, 4 + b, 2, 1)
    R((255, 255, 255), 8, 8 + b, 3, 3); R((255, 255, 255), 14, 8 + b, 3, 3)
    R((20, 20, 40), 9, 9 + b, 2, 2); R((20, 20, 40), 15, 9 + b, 2, 2)
    R((255, 220, 90), 9, 9 + b, 1, 1); R((255, 220, 90), 15, 9 + b, 1, 1)
    for i, x in enumerate((3, 6, 9, 12, 15, 18)):
        sw = ((i + f) % 2) * 2 - 1
        for k in range(8):
            R(body if k % 2 == 0 else dark, x + (sw * (k // 3)), 14 + k, 3, 1)
        R(light, x + sw * 2, 20, 1, 1)
    R((230, 200, 140), 11, 12 + b, 3, 1)
    return s


def _boss_lava(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 80), 2, 21, 20, 3)
    rock, dark = (58, 46, 50), (34, 26, 30)
    R(dark, 6, 17, 5, 5); R(dark, 13, 17, 5, 5)
    R(rock, 5, 8 + b, 14, 10)
    R(dark, 5, 16, 14, 2)
    for x, y, w2, h2 in ((7, 10, 1, 5), (12, 9, 1, 6), (9, 14, 4, 1), (15, 12, 2, 1)):
        R((255, 120, 30), x, y + b, w2, h2)
        R((255, 220, 90), x, y + b, 1, 1)
    R(rock, 1, 8 + b, 5, 5); R(rock, 18, 8 + b, 5, 5)
    R(rock, 1, 13 + b, 4, 7); R(rock, 19, 13 + b, 4, 7)
    R((255, 120, 30), 1, 20, 4, 2); R((255, 120, 30), 19, 20, 4, 2)
    R(rock, 8, 2 + b, 8, 6)
    pygame.draw.polygon(s, dark, [(8, 3 + b), (5, 0), (9, 2 + b)])
    pygame.draw.polygon(s, dark, [(16, 3 + b), (19, 0), (15, 2 + b)])
    R((255, 230, 90), 9, 4 + b, 2, 2); R((255, 230, 90), 13, 4 + b, 2, 2)
    R((255, 120, 30), 10, 7 + b, 4, 1)
    top = 0 if f else 1
    pygame.draw.polygon(s, (255, 150, 30), [(9, 2 + b), (12, top - 1 if top else -0), (15, 2 + b)])
    return s


def _boss_crystal(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 80), 3, 21, 18, 3)
    c1, c2, c3 = (120, 70, 190), (176, 116, 240), (236, 196, 255)
    pygame.draw.polygon(s, c1, [(12, 7 + b), (5, 12), (7, 21), (17, 21), (19, 12)])
    pygame.draw.polygon(s, c2, [(12, 7 + b), (8, 12), (9, 20), (14, 20), (16, 12)])
    R(c3, 11, 9 + b, 1, 8)
    for x, y, h in ((2, 13, 7), (20, 12, 8), (4, 8, 5), (18, 7, 6)):
        pygame.draw.polygon(s, c2, [(x, y + h), (x + 1, y - (1 if f else 0)), (x + 3, y + h)])
        R(c3, x + 1, y + 1, 1, 2)
    R((70, 36, 120), 8, 3 + b, 8, 5)
    R(c2, 8, 3 + b, 8, 1)
    R((255, 255, 255), 9, 5 + b, 2, 2); R((255, 255, 255), 13, 5 + b, 2, 2)
    R((240, 100, 220), 10, 6 + b, 1, 1); R((240, 100, 220), 14, 6 + b, 1, 1)
    pygame.draw.polygon(s, c3, [(12, 0), (10, 3 + b), (14, 3 + b)])
    return s


def _boss_crypt(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 70), 3, 21, 18, 3)
    robe, trim = (54, 36, 78), (110, 80, 150)
    pygame.draw.polygon(s, robe, [(8, 9 + b), (3, 22), (21, 22), (16, 9 + b)])
    R(trim, 3, 21, 18, 1); R(trim, 11, 10 + b, 2, 11)
    R((190, 186, 168), 4, 11 + b, 3, 7); R((190, 186, 168), 17, 11 + b, 3, 7)
    R((130, 80, 40), 21, 2, 1, 19)
    pygame.draw.circle(s, (120, 255, 150), (21, 3 + b), 2)
    R((255, 255, 255), 21, 2 + b, 1, 1)
    R((218, 214, 196), 8, 2 + b, 8, 7)
    R((218, 214, 196), 9, 9 + b, 6, 2)
    R((20, 40, 24), 9, 4 + b, 2, 3); R((20, 40, 24), 13, 4 + b, 2, 3)
    R((120, 255, 150), 9, 5 + b, 1, 1); R((120, 255, 150), 14, 5 + b, 1, 1)
    R((20, 20, 20), 11, 7 + b, 2, 2)
    R((240, 200, 70), 8, 0 + b, 8, 2)
    for x in (8, 11, 14):
        R((240, 200, 70), x, -1 if False else 0, 2, 1)
    R((220, 50, 60), 11, 0 + b, 2, 1)
    R((140, 255, 160, 120), 2, 4 + (1 - f), 1, 1)
    return s


def _boss_castle(f):
    s, R = _boss_canvas()
    b = f
    steel, dark, light = (136, 148, 176), (84, 94, 122), (206, 218, 244)
    for i in range(5):                     # призрачный «хвост» вместо ног
        R((150, 170, 255, 190 - i * 38), 7 + i, 17 + i, 10 - 2 * i, 1)
    R((70, 36, 60), 3, 10 + b, 3, 8); R((70, 36, 60), 18, 10 + b, 3, 8)
    R(steel, 6, 9 + b, 12, 9)
    R(light, 6, 9 + b, 12, 1); R(dark, 6, 17, 12, 1)
    R(dark, 11, 10 + b, 2, 7)
    R(steel, 2, 8 + b, 5, 4); R(steel, 17, 8 + b, 5, 4)
    R(light, 2, 8 + b, 5, 1); R(light, 17, 8 + b, 5, 1)
    R(dark, 3, 12 + b, 3, 6); R(dark, 18, 12 + b, 3, 6)
    R((220, 226, 240), 22, 0, 1, 14); R((255, 215, 90), 21, 14, 3, 1); R((120, 70, 40), 22, 15, 1, 3)
    R(steel, 8, 1 + b, 8, 8)
    R(light, 8, 1 + b, 8, 1)
    R(dark, 8, 5 + b, 8, 1)
    R((120, 220, 255), 9, 4 + b, 6, 1)
    R((190, 40, 60), 11, -1 + b if b else 0, 2, 2)
    R((255, 255, 255, 170), 3 + f * 17, 2, 1, 1)
    return s


def _boss_acid(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 70), 2, 21, 20, 3)
    pygame.draw.ellipse(s, (60, 130, 24), (1, 6 + b, 22, 16 - b))
    pygame.draw.ellipse(s, (110, 205, 40), (2, 7 + b, 20, 14 - b))
    pygame.draw.ellipse(s, (170, 240, 90), (5, 8 + b, 8, 4))
    for x, y in ((6, 15), (16, 13), (12, 18)):
        pygame.draw.circle(s, (210, 255, 140), (x, y), 1)
    R((220, 230, 200), 15, 14 + b, 4, 3); R((20, 40, 10), 16, 15 + b, 1, 1); R((20, 40, 10), 18, 15 + b, 1, 1)
    R((255, 255, 255), 6, 10 + b, 4, 4); R((255, 255, 255), 12, 10 + b, 4, 4)
    R((30, 60, 10), 8, 12 + b, 2, 2); R((30, 60, 10), 14, 12 + b, 2, 2)
    R((30, 60, 10), 9, 17 + b, 6, 1)
    for x in (6, 11, 16):
        R((240, 200, 70), x, 4 + b + (f if x == 11 else 0), 2, 3)
    R((240, 200, 70), 6, 6 + b, 12, 1)
    R((120, 230, 40), 3, 20, 1, 3 + f)
    return s


def _boss_ice(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 70), 2, 21, 20, 3)
    fur, ice, light = (200, 226, 244), (110, 170, 214), (250, 255, 255)
    R(ice, 6, 18, 5, 4); R(ice, 13, 18, 5, 4)
    R(fur, 5, 8 + b, 14, 11)
    R(light, 7, 10 + b, 10, 2)
    R(ice, 1, 8 + b, 4, 11); R(ice, 19, 8 + b, 4, 11)
    R(fur, 0, 17 + b, 5, 3); R(fur, 19, 17 + b, 5, 3)
    R((120, 90, 60), 22, 1, 2, 17); R((190, 236, 255), 20, 0, 5, 5)
    R((235, 248, 255), 21, 1, 3, 2)
    R((226, 214, 190), 8, 2 + b, 8, 6)
    R((90, 130, 190), 7, 1 + b, 10, 2)
    R((226, 214, 190), 5, 0 + b, 2, 3); R((226, 214, 190), 17, 0 + b, 2, 3)
    R((60, 140, 255), 9, 4 + b, 2, 2); R((60, 140, 255), 13, 4 + b, 2, 2)
    for x in (8, 10, 12, 14):
        R(light, x, 8 + b, 2, 3 + (x % 3))
    return s


def _boss_diamond(f):
    s, R = _boss_canvas()
    b = f
    R((0, 0, 0, 60), 3, 21, 18, 3)
    c1, c2, c3 = (120, 180, 220), (190, 235, 255), (255, 255, 255)
    pygame.draw.polygon(s, c1, [(12, 6 + b), (4, 11), (7, 21), (17, 21), (20, 11)])
    pygame.draw.polygon(s, c2, [(12, 6 + b), (8, 11), (9, 20), (15, 20), (16, 11)])
    pygame.draw.polygon(s, c3, [(12, 8 + b), (10, 12), (12, 19), (14, 12)])
    for x, y in ((1, 9), (20, 8)):
        pygame.draw.polygon(s, c2, [(x, y + 8), (x + 1, y - 1 + f), (x + 3, y + 8)])
        R(c3, x + 1, y + 2, 1, 3)
    pygame.draw.polygon(s, c1, [(12, 0 + b), (7, 5 + b), (12, 9 + b), (17, 5 + b)])
    pygame.draw.polygon(s, c2, [(12, 1 + b), (9, 5 + b), (12, 8 + b), (15, 5 + b)])
    R((40, 90, 140), 10, 4 + b, 1, 2); R((40, 90, 140), 13, 4 + b, 1, 2)
    for x, y in (((2, 3), (21, 15), (5, 19)) if f == 0 else ((21, 3), (2, 15), (19, 19))):
        R(c3, x, y, 1, 1); R(c2, x - 1, y, 3, 1); R(c2, x, y - 1, 1, 3)
    return s


BOSS_DRAW = {"cave": _boss_cave, "quarry": _boss_quarry, "flooded": _boss_flooded, "lava": _boss_lava,
             "crystal": _boss_crystal, "crypt": _boss_crypt, "castle": _boss_castle, "acid": _boss_acid,
             "ice": _boss_ice, "diamond": _boss_diamond}


def boss_sprite(biome, f):
    return pygame.transform.scale(BOSS_DRAW[biome](f), (24 * SCALE, 24 * SCALE))


# ---------------------------------------------------------------- значки на зельях и свитках
ICON_GLYPH = {
    "plus":  ["..##..", "..##..", "######", "######", "..##..", "..##.."],
    "heart": [".##.##", "######", "######", ".####.", "..##..", "......"],
    "fist":  ["#.#.#.", "######", "######", "######", ".####.", "..##.."],
    "shield": ["######", "######", "######", ".####.", ".####.", "..##.."],
    "ghost": ["..##..", ".#..#.", "..##..", "#.##.#", ".#..#.", "#....#"],
    "drop":  ["..##..", "..##..", ".####.", "######", "######", ".####."],
    "flame": ["..#...", "..##..", ".###.#", "######", ".####.", "..##.."],
    "cross": ["#....#", ".#..#.", "..##..", "..##..", ".#..#.", "#....#"],
}


def _glyph(s, name, col, x0, y0):
    for j, row in enumerate(ICON_GLYPH[name]):
        for i, ch in enumerate(row):
            if ch == "#":
                s.set_at((x0 + i, y0 + j), col)


def potion_sprite(col, light, glyph=None, gcol=(255, 250, 240), alpha=255):
    s = new_sprite()
    c, l = (col[0], col[1], col[2], alpha), (light[0], light[1], light[2], alpha)
    shadow(s, 4, 8)
    rect(s, (150, 105, 60, alpha), 6, 3, 4, 2)
    rect(s, (200, 205, 225, alpha), 7, 5, 2, 2)
    rect(s, c, 5, 6, 6, 1)
    rect(s, c, 4, 7, 8, 7)
    if glyph:
        _glyph(s, glyph, (gcol[0], gcol[1], gcol[2], 255 if alpha == 255 else 235), 5, 8)
    else:
        rect(s, l, 5, 8, 1, 3)
    if alpha < 255:     # контур «призрачной» бутылки
        pygame.draw.rect(s, (220, 240, 255, 200), (4, 7, 8, 7), 1)
    return scaled(s, 2)


def scroll_sprite(col, glyph=None):
    s = new_sprite()
    shadow(s, 3, 10)
    rect(s, (225, 205, 160), 3, 4, 10, 9)
    rect(s, (170, 140, 90), 2, 3, 12, 2)
    rect(s, (170, 140, 90), 2, 12, 12, 2)
    if glyph:
        _glyph(s, glyph, (col[0], col[1], col[2], 255), 5, 6)
    else:
        rect(s, (150, 125, 85), 5, 7, 6, 1)
        rect(s, col, 7, 9, 3, 3)
    return scaled(s, 2)


# ---------------------------------------------------------------- меч и секира: вид зависит от уровня заточки
def sword_look(lvl):
    if lvl >= 10:
        return dict(blade=(255, 238, 168), edge=(255, 255, 235), guard=(255, 215, 80), glow=(255, 150, 40), ln=9, fire=True)
    if lvl >= 9:
        return dict(blade=(255, 170, 70), edge=(255, 225, 150), guard=(255, 215, 80), glow=(255, 100, 30), ln=9, fire=True)
    if lvl >= 7:
        return dict(blade=(190, 130, 255), edge=(238, 205, 255), guard=(255, 215, 80), glow=(150, 255, 255), ln=9)
    if lvl >= 6:
        return dict(blade=(250, 210, 90), edge=(255, 242, 175), guard=(230, 60, 60), ln=9)
    if lvl >= 4:
        return dict(blade=(110, 215, 235), edge=(190, 250, 255), guard=(255, 215, 80), ln=8)
    if lvl >= 2:
        return dict(blade=(160, 190, 232), edge=(216, 232, 252), guard=(255, 215, 80), ln=8)
    return dict(blade=(205, 210, 225), edge=(238, 242, 252), guard=(255, 230, 120), ln=8)


def axe_look(lvl):
    tier = min(5, lvl // 2)
    return [((170, 176, 195), (70, 72, 90), (240, 245, 255)),
            ((150, 190, 232), (50, 70, 110), (225, 240, 255)),
            ((110, 215, 235), (30, 90, 110), (210, 255, 255)),
            ((250, 210, 90), (120, 80, 20), (255, 245, 190)),
            ((190, 130, 255), (70, 36, 120), (240, 215, 255)),
            ((255, 160, 60), (130, 50, 10), (255, 240, 170))][tier]


def draw_sword(s, hand, ang, lvl=0):
    hx, hy = hand
    L = sword_look(lvl)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    pygame.draw.line(s, (120, 70, 40), ip(hx, hy), ip(hx - ca * 2, hy - sa * 2))             # рукоять
    for i in range(1, L["ln"] + 1):                                                          # клинок
        col = L["blade"] if i % 2 else L["edge"]
        s.set_at(ip(hx + ca * i, hy + sa * i), col)
        if "glow" in L and i % 3 == 0:
            s.set_at(ip(hx + ca * i - sa, hy + sa * i + ca), L["glow"])
    if L.get("fire"):
        tx, ty = hx + ca * (L["ln"] + 1), hy + sa * (L["ln"] + 1)
        s.set_at(ip(tx, ty), (255, 170, 40))
        s.set_at(ip(tx - sa, ty + ca), (255, 90, 20))
    pygame.draw.line(s, L["guard"], ip(hx - sa * 1.6, hy + ca * 1.6), ip(hx + sa * 1.6, hy - ca * 1.6))   # гарда


def draw_axe(s, hand, ang, lvl=0):
    hx, hy = hand
    head, outl, edge = axe_look(lvl)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    d, p = (ca, sa), (-sa, ca)
    pygame.draw.line(s, (120, 80, 45), ip(hx - ca * 2, hy - sa * 2), ip(hx + ca * 8, hy + sa * 8))
    cx, cy = hx + ca * 6, hy + sa * 6
    pts = [ip(cx - d[0] * 2, cy - d[1] * 2),
           ip(cx - d[0] * 2 + p[0] * 3.2, cy - d[1] * 2 + p[1] * 3.2),
           ip(cx + d[0] * 2 + p[0] * 3.8, cy + d[1] * 2 + p[1] * 3.8),
           ip(cx + d[0] * 2.5, cy + d[1] * 2.5)]
    pygame.draw.polygon(s, head, pts)
    pygame.draw.polygon(s, outl, pts, 1)
    pygame.draw.line(s, edge, pts[1], pts[2])


def weapon_icon(kind, lvl=0):
    s = new_sprite()
    if kind == "axe":
        head, outl, edge = axe_look(lvl)
        pygame.draw.line(s, (120, 80, 45), (3, 14), (11, 4))
        pygame.draw.line(s, (120, 80, 45), (4, 14), (12, 4))
        pts = [(8, 3), (14, 2), (14, 8), (11, 7)]
        pygame.draw.polygon(s, head, pts)
        pygame.draw.polygon(s, outl, pts, 1)
        pygame.draw.line(s, edge, (14, 2), (14, 8))
    else:
        L = sword_look(lvl)
        pygame.draw.line(s, L["blade"], (5, 11), (13, 3))
        pygame.draw.line(s, L["edge"], (6, 11), (14, 3))
        pygame.draw.line(s, L["guard"], (3, 9), (7, 13))
        pygame.draw.line(s, (120, 70, 40), (2, 14), (4, 12))
        if L.get("fire"):
            s.set_at((14, 2), (255, 160, 40))
            s.set_at((15, 1), (255, 90, 20))
    return scaled(s, 2)


class Assets:
    def __init__(self):
        self._torch = {}
        self._pb, self._pf, self._pbig = {}, {}, {}          # кеши кадров героя
        self._mobs, self._mobs_w, self._boss, self._boss_w = {}, {}, {}, {}
        self._wicons = {}
        self.player = self.pframe("idle", 0, 0, "sword")
        _ts = make_tileset("cave", 7, 0)
        self.floor, self.wall = _ts["floor"][0], _ts["wall"][0][0]      # плитки для фона меню
        self.chest = chest_sprite()
        self.spikes = spikes_sprite()
        self.barrel = barrel_sprite()
        self.fountain = fountain_sprite()
        self.fountain_dry = fountain_sprite(True)
        self.exit = exit_sprite()
        self.elder = elder_sprite()
        self.merchant = merchant_sprite()
        self.haz = {k: [hazard_sprite(k, 0), hazard_sprite(k, 1)] for k in ("lava", "water", "acid", "ice")}
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
            if d["kind"] == "potion":
                ic = potion_sprite(d["col"], d["light"], d.get("glyph"), d.get("gcol", (255, 250, 240)),
                                   d.get("alpha", 255))
            else:
                ic = scroll_sprite(d["col"], d.get("glyph"))
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
            "torch": [pygame.transform.scale(t, (TILE * 2, TILE * 2)) for t in self.torch_set("cave")],
        }
        self.dim = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        self.dim.fill((6, 4, 12, 170))
        self.tele = pygame.Surface((TILE, TILE), pygame.SRCALPHA)     # подсветка дуги секиры
        self.tele.fill((255, 120, 40, 95))
        pygame.draw.rect(self.tele, (255, 190, 90, 230), (0, 0, TILE, TILE), 3)
        self.tele_boss = pygame.Surface((TILE, TILE), pygame.SRCALPHA)   # предупреждение об ударе босса
        self.tele_boss.fill((235, 40, 40, 100))
        pygame.draw.rect(self.tele_boss, (255, 110, 90, 240), (0, 0, TILE, TILE), 3)
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

    # ---- факелы своего цвета в каждой локации
    def torch_set(self, biome):
        if biome not in self._torch:
            c1, c2 = BIOMES[biome]["torch"]
            self._torch[biome] = [torch_sprite(0, c1, c2), torch_sprite(1, c1, c2)]
        return self._torch[biome]

    # ---- герой
    def pframe(self, anim, f, armor, weapon, white=False, left=False, wl=0):
        """Кадр героя из кеша. Кадры рисуются один раз, потом переиспользуются."""
        key = (anim, f, armor, weapon, wl, white, left)
        img = self._pf.get(key)
        if img is None:
            bk = (anim, f, armor, weapon, wl)
            base = self._pb.get(bk)
            if base is None:
                base = self._pb[bk] = build_player(anim, f, armor, weapon, wl)
            img = whiten(base) if white else base
            if left:
                img = pygame.transform.flip(img, True, False)
            self._pf[key] = img
        return img

    def pframe_big(self, anim, f, armor, weapon, wl, k=4):
        key = (anim, f, armor, weapon, wl, k)
        if key not in self._pbig:
            self._pbig[key] = pygame.transform.scale(self.pframe(anim, f, armor, weapon, wl=wl), (PX * k * SCALE // 1,) * 2)
        return self._pbig[key]

    def weapon_icon(self, kind, lvl):
        key = (kind, lvl)
        if key not in self._wicons:
            self._wicons[key] = weapon_icon(kind, lvl)
        return self._wicons[key]

    # ---- монстры в «шкурках» локации
    def mob_frames(self, kind, biome, white=False):
        if biome == "cave" or kind not in ("goblin", "bat", "slime", "archer", "mage", "ogre"):
            return (self.mob_w if white else self.mob)[kind]
        key = (kind, biome)
        if key not in self._mobs:
            self._mobs[key] = skin_frames(self.mob[kind], biome, kind)
            self._mobs_w[key] = [whiten(f) for f in self._mobs[key]]
        return (self._mobs_w if white else self._mobs)[key]

    def mob_img(self, kind, t, white=False, biome="cave"):
        frames = self.mob_frames(kind, biome, white)
        return frames[(t // 140) % len(frames)]

    def boss_frames(self, biome, white=False):
        if biome not in self._boss:
            self._boss[biome] = [boss_sprite(biome, 0), boss_sprite(biome, 1)]
            self._boss_w[biome] = [whiten(f) for f in self._boss[biome]]
        return (self._boss_w if white else self._boss)[biome]

    def light(self, radius):
        if radius not in self._lights:
            self._lights[radius] = [make_light(int((radius + 1.5) * 2 * TILE) + d) for d in (-16, 0, 16)]
        return self._lights[radius]


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
    def __init__(self, kind, x, y, depth, biome="cave"):
        d = MOBS[kind]
        boss = bool(d.get("boss"))
        self.kind = kind
        self.biome = biome
        self.x, self.y = x, y
        self.rx, self.ry = float(x), float(y)
        hs = 1 + (0.10 if boss else 0.18) * (depth - 1)
        ds = 1 + (0.08 if boss else 0.10) * (depth - 1)
        self.max = self.hp = int(d["hp"] * hs)
        self.dmg = (max(1, int(d["dmg"][0] * ds)), max(2, int(d["dmg"][1] * ds)))
        names = BIOME_NAMES.get(biome, {}).get(kind)
        self.name = names[0] if names else d["name"]
        skin = BIOMES[biome]["skin"] if names else None
        self.col = skin[1] if skin else d["col"]
        self.awake = False
        self.cd = 0
        self.charge = False
        self.summon_cd = 3
        self.flash = 0
        self.lunge = None
        self.seed = random.random() * 10
        self.pend = None                      # подготовленный удар босса (предупреждение на полу)
        self.split_stage = 0
        self.cds = {n: random.randint(1, 3) for n, _ in d.get("kit", [])}


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
        self.buy_t = -999
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
            if key == "weapon" and lvl < cap:
                desc = f"{desc}. Новый вид: {SWORD_STAGES[lvl + 1]}"
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
        self.buy_t = self.t
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
            if key == "weapon":
                g.toast(f"Клинок: {SWORD_STAGES[g.up['weapon']]}", (255, 225, 140))
            self.msg = "Отличный выбор! Теперь ты сильнее."
        g.sfx.play("coin")
        px, py = tc(g.px, g.py)
        g.burst(px, py, GOLD, 14, 3)

    def draw(self, screen, A, F):
        g = self.g
        r = pygame.Rect(14, 14, 640, MAP_H - 28)
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
        draw_text(screen, F["small"], fit_text(F["small"], e[3], r.w - 36), BLUE, r.x + 20, r.bottom - 64)
        draw_text(screen, F["small"], f"«{self.msg}»", GRAY, r.x + 20, r.bottom - 42)
        draw_text(screen, F["small"], "W/S выбрать • Enter купить • Esc выйти", GRAY, r.right - 16, r.bottom - 22, "r")
        self.draw_hero(screen, A, F)

    def draw_hero(self, screen, A, F):
        """Справа — наш герой «как в инвентаре»: видно, как меняются броня и оружие."""
        g = self.g
        cr = pygame.Rect(666, 14, MAP_W - 666 - 14, MAP_H - 28)
        panel(screen, cr)
        draw_text(screen, F["normal_b"], g.name, GOLD, cr.centerx, cr.y + 8, "c")
        cx, cy = cr.centerx, cr.y + 178
        glow = pygame.Surface((220, 220), pygame.SRCALPHA)
        for rr in range(100, 0, -10):
            pygame.draw.circle(glow, (120, 90, 190, 6 + (100 - rr) // 9), (110, 110), rr)
        screen.blit(glow, (cx - 110, cy - 86))
        pygame.draw.ellipse(screen, (40, 32, 56), (cx - 78, cy + 66, 156, 34))
        pygame.draw.ellipse(screen, (96, 76, 138), (cx - 78, cy + 66, 156, 34), 2)
        age = self.t - self.buy_t
        if 0 <= age < 26:                                   # вспышка после покупки
            rad = 40 + age * 5
            pygame.draw.circle(screen, GOLD, (cx, cy + 10), rad, max(1, 5 - age // 6))
        wp = g.weapon
        wl = g.up["weapon"] if wp == "sword" else g.up["axe"]
        frame = (pygame.time.get_ticks() // 520) % 2
        img = A.pframe_big("idle", frame, g.up["armor"], wp, wl, 4)
        screen.blit(img, (cx - img.get_width() // 2, cy - 100 + (frame if age > 26 else 0)))
        lo, hi = g.atk_range()
        a = g.up["armor"]
        weapon_line = SWORD_STAGES[g.up["weapon"]] if wp == "sword" else f"Секира, ур. {g.up['axe']}"
        lines = [(f"Уровень {g.lvl}", TEXT), (f"Здоровье {g.hp}/{g.max_hp}", GREEN),
                 (f"Атака {lo}–{hi}   Крит {int(g.crit_chance() * 100)}%", TEXT),
                 (f"Броня {g.armor_val()}  (ур. {a}/10)", (190, 200, 225)),
                 (ARMOR_STAGES[a].capitalize() if a else "Простая ряса", GRAY),
                 (weapon_line, (255, 225, 140)), (f"Свет {g.light_radius()}", GRAY)]
        yy = cr.y + 308
        for i, (s, col) in enumerate(lines):
            draw_text(screen, F["small"], fit_text(F["small"], s, cr.w - 24), col, cr.centerx, yy + i * 22, "c")


# ============================================================ игра
class Game:
    def __init__(self, name, sfx, rec, data=None):
        self.name, self.sfx, self.rec = name, sfx, rec
        self.lvl, self.xp = 1, 0
        self.up = {k: 0 for k in ("weapon", "armor", "vit", "lamp", "crit", "axe")}
        self.hp = self.max_hp
        self.gold = self.total_gold = self.kills = self.turn = self.done_quests = 0
        self.depth = 1
        self.biome = "cave"             # текущая локация
        self.biome_hist = ["cave"]      # какие локации уже были (чтобы не повторялись подряд)
        self.new_biome = False
        self.inv = {k: 0 for k in ORDER}
        self.inv["heal"] = 2
        self.weapon = "sword"           # sword / axe
        self.has_axe = False
        self.axe_pending = None         # [dx, dy, x, y, задержка] — замах секиры
        self.st = {}
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
        self.cut = None                 # катсцена: заход в локацию / появление босса
        self.bars = 0.0                 # чёрные полосы кино
        self.reveal = None
        self.walk_from = None
        self.haz, self.tele = {}, []    # лава/вода/кислота/лёд и предупреждения об ударах боссов
        self.focus = (0.0, 0.0)
        self.camx = self.camy = 0
        self.tile_seed, self.tile_alt, self.crypt_var, self.grad = 1, 0, 0, 0.0
        if data:
            self.load_data(data)
        else:
            self.new_floor()
            self.snap_camera()
            self.say(f"Приветствуем, {name}! Спускайся глубже, копи золото и становись сильнее.", TEXT)
            self.say("Загляни к торговцу и старцу — на первом этаже они рядом.", GRAY)
            self.start_cutscene(intro=True)

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
                or (x, y) in self.npcs or (x, y) in self.fountains or (x, y) in self.barrels
                or self.haz_kind(x, y) in ("lava", "acid"))

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
    def build_tiles(self):
        self.tiles = make_tileset(self.biome, self.tile_seed, self.tile_alt, self.crypt_var)
        ca, sa = math.cos(self.grad), math.sin(self.grad)
        cs = [0, COLS * ca, ROWS * sa, COLS * ca + ROWS * sa]
        p0, p1 = min(cs), max(cs)
        self.vmap = [[min(NV - 1, int(((x * ca + y * sa) - p0) / (p1 - p0) * NV * 0.999))
                      for x in range(COLS)] for y in range(ROWS)]

    def haz_kind(self, x, y):
        h = self.haz.get((x, y))
        return h[0] if h else None

    def pick_door(self, room):
        """Дверь вниз — внутри комнаты, подальше от входов-проходов (чтобы не стояла на пути)."""
        tiles = self.room_tiles(room)
        cand = [t for t in tiles if all(self.grid[t[1] + dy][t[0] + dx] == 0
                                        for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
        mouths = [(x, y) for y in range(room.top - 1, room.bottom + 1) for x in range(room.left - 1, room.right + 1)
                  if 0 <= x < COLS and 0 <= y < ROWS and not room.collidepoint(x, y) and self.grid[y][x] == 0]
        if cand:
            def score(t):
                return min([max(abs(t[0] - m[0]), abs(t[1] - m[1])) for m in mouths] or [9])
            best = max(score(t) for t in cand)
            return random.choice([t for t in cand if score(t) == best])
        return random.choice([t for t in tiles if self.interior(*t)] or tiles)

    def place_hazards(self, rooms, taken):
        kind = BIOMES[self.biome]["haz"]
        if not kind:
            return
        total = sum(len(self.room_tiles(r)) for r in rooms)
        want = int(total * HAZ_FRAC[kind])
        near = set()
        for cx, cy in ((self.px, self.py), self.exit_pos):
            near |= {(cx + dx, cy + dy) for dx in range(-2, 3) for dy in range(-2, 3)}

        def roomy(x, y):       # только «широкие» места комнат: туннели и проходы не затрагиваем
            return (0 < x < COLS - 1 and 0 < y < ROWS - 1 and
                    all(self.grid[y + dy][x + dx] == 0 for dx in (-1, 0, 1) for dy in (-1, 0, 1)))

        cand = [t for r in rooms for t in self.room_tiles(r) if roomy(*t) and t not in taken and t not in near]
        random.shuffle(cand)
        placed = 0
        for (x, y) in cand:
            if placed >= want:
                break
            if (x, y) in self.haz or (x, y) in taken:
                continue
            blob = [(x, y)]
            for _ in range(random.randint(0, 3)):
                bx, by = random.choice(blob)
                dx, dy = random.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
                n = (bx + dx, by + dy)
                if (n not in blob and roomy(*n) and n not in taken and n not in near and n not in self.haz):
                    blob.append(n)
            for t in blob:
                self.haz[t] = [kind, None]
                placed += 1

    def new_floor(self):
        d = self.depth
        biome = self.biome
        self.grid, rooms, self.deco, self.torches = generate_level()
        self.explored = [[False] * COLS for _ in range(ROWS)]
        self.visible = [[False] * COLS for _ in range(ROWS)]
        self.mobs, self.npcs, self.chests, self.barrels = [], {}, set(), set()
        self.fountains, self.traps = {}, {}
        self.haz, self.tele = {}, []
        self.axe_pending = None
        self.cut = None
        self.reveal = None
        for lst in (self.parts, self.floaters, self.rings, self.slashes, self.projs, self.swings):
            lst.clear()
        self.mini = pygame.Surface((COLS * 2, ROWS * 2), pygame.SRCALPHA)
        self.mini_dirty = True
        self.tile_seed = random.randrange(10 ** 6)       # у каждого этажа свой оттенок и градиент цвета
        self.tile_alt = random.randrange(3)
        self.crypt_var = random.randrange(3)
        self.grad = random.uniform(0, math.tau)
        self.build_tiles()

        start = random.choice(rooms)
        self.px, self.py = start.center
        self.prx, self.pry = float(self.px), float(self.py)
        dm = self.bfs(self.px, self.py, 999)
        others = [r for r in rooms if r is not start]
        exit_room = max(others, key=lambda r: dm.get(r.center, 0))
        taken = {(self.px, self.py)}
        self.exit_pos = self.pick_door(exit_room)
        taken.add(self.exit_pos)
        self.boss_alive = (d % 10 == 0 or d % 10 == 5)
        boss_kind = ("boss_" + biome) if d % 10 == 0 else "king"

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

        pool = mob_pool(d, biome)
        kinds, weights = [k for k, _ in pool], [w for _, w in pool]
        trap_n, trap_p = {"castle": (3, 0.65), "crypt": (2, 0.55), "quarry": (2, 0.55)}.get(biome, (0, 0))
        barrel_choices = [1, 2, 3, 4] if biome == "quarry" else [0, 0, 1, 2, 3]
        chest_bonus = 0.3 if biome in ("crystal", "diamond") else 0.15
        for r in rooms:
            if random.random() < 0.55:
                t = self.take_tile(r, taken)
                if t:
                    self.chests.add(t)
            if random.random() < chest_bonus:
                t = self.take_tile(r, taken)
                if t:
                    self.chests.add(t)
            for _ in range(random.choice(barrel_choices)):
                t = self.take_tile(r, taken)
                if t:
                    self.barrels.add(t)
            if r is start:
                continue
            if trap_n:                                    # замок, склепы и камнеломня — больше ловушек
                for _ in range(trap_n):
                    if random.random() < trap_p:
                        t = self.take_tile(r, taken)
                        if t:
                            self.traps[t] = "hidden"
            else:
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
                    self.mobs.append(Mob(random.choices(kinds, weights)[0], t[0], t[1], d, biome))
        if self.boss_alive:
            t = self.take_tile(exit_room, taken)
            if t:
                self.mobs.append(Mob(boss_kind, t[0], t[1], d, biome))
            else:
                self.boss_alive = False
        self.place_hazards(rooms, taken)
        self.compute_fov()
        if self.boss_alive:
            self.say(f"Дверь вниз запечатана магией. Победи: {MOBS[boss_kind]['name']}!", RED)

    def change_biome(self):
        """Новая локация каждые 10 этажей: не такая же, как сейчас, и не такая же, как была перед ней."""
        banned = set(self.biome_hist[-2:])
        cands = [b for b in BIOME_ORDER if b not in banned]
        self.biome = random.choice(cands)
        self.biome_hist.append(self.biome)
        self.new_biome = True

    def descend(self):
        self.depth += 1
        self.quest_event("descend")
        self.heal(self.max_hp // 10, quiet=True)
        self.sfx.play("stairs")
        self.new_biome = False
        while (self.depth - 1) // 10 > len(self.biome_hist) - 1:      # каждые 10 этажей — новая локация
            self.change_biome()
        self.new_floor()
        self.snap_camera()
        self.fade, self.banner = 255, 170
        if self.new_biome:
            self.say(f"Новая локация: {BIOMES[self.biome]['name']}!", BIOMES[self.biome]["color"])
            self.toast(f"Новая локация: {BIOMES[self.biome]['name']}", BIOMES[self.biome]["color"])
        else:
            self.say(f"Ты спустился на этаж {self.depth}. Враги становятся сильнее...", ORANGE)
        self.start_cutscene(intro=False)
        self.autosave()


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

    def cam_for(self, x, y):
        return (max(0, min(COLS * TILE - MAP_W, x * TILE + TILE / 2 - MAP_W / 2)),
                max(0, min(ROWS * TILE - MAP_H, y * TILE + TILE / 2 - MAP_H / 2)))

    def snap_camera(self):
        self.prx, self.pry = float(self.px), float(self.py)
        self.camx, self.camy = self.cam_for(self.prx, self.pry)
        self.focus = (self.prx, self.pry)

    # ---- катсцены: заход в локацию и появление босса
    def revealed(self, x, y):
        r = self.reveal
        return bool(r) and abs(x - r[0]) <= r[2] and abs(y - r[1]) <= r[2]

    def set_reveal(self, boss):
        self.reveal = (boss.x, boss.y, 4)
        for yy in range(max(0, boss.y - 4), min(ROWS, boss.y + 5)):
            for xx in range(max(0, boss.x - 4), min(COLS, boss.x + 5)):
                self.explored[yy][xx] = True
        self.mini_dirty = True

    def start_cutscene(self, intro=False):
        steps = []
        if intro:
            best = None
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = 0
                while n < 4:
                    x, y = self.px - dx * (n + 1), self.py - dy * (n + 1)
                    if not (0 < x < COLS - 1 and 0 < y < ROWS - 1) or self.grid[y][x] == 1:
                        break
                    n += 1
                if best is None or n > best[0]:
                    best = (n, dx, dy)
            n, dx, dy = best
            if n > 0:                                   # герой заходит в пещеру
                self.walk_from = (self.px - dx * n, self.py - dy * n)
                self.prx, self.pry = float(self.walk_from[0]), float(self.walk_from[1])
                self.facing = dx or self.facing
                steps.append(["walk", 34 * n + 30])
        boss = next((m for m in self.mobs if is_boss(m)), None)
        if boss:                                        # камера -> босс -> имя -> обратно
            steps += [["pan", 52], ["hold", 200], ["pan_back", 52]]
            self.set_reveal(boss)
        if steps:
            self.cut = {"steps": steps, "i": 0, "t": 0, "boss": boss}

    def update_cut(self):
        c = self.cut
        step, dur = c["steps"][c["i"]]
        c["t"] += 1
        boss = c.get("boss")
        p = clamp01(c["t"] / dur)
        if step == "walk":
            fx, fy = self.walk_from
            self.prx = fx + (self.px - fx) * p
            self.pry = fy + (self.py - fy) * p
            tx, ty = self.cam_for(self.prx, self.pry)
            self.camx += (tx - self.camx) * 0.2
            self.camy += (ty - self.camy) * 0.2
            self.focus = (self.prx, self.pry)
        elif boss:
            self.prx, self.pry = float(self.px), float(self.py)
            c0, c1 = self.cam_for(self.px, self.py), self.cam_for(boss.x, boss.y)
            k = ease(p) if step == "pan" else (1.0 if step == "hold" else 1 - ease(p))
            self.camx = c0[0] + (c1[0] - c0[0]) * k
            self.camy = c0[1] + (c1[1] - c0[1]) * k
            self.focus = (self.px + (boss.x - self.px) * k, self.py + (boss.y - self.py) * k)
            if step == "hold" and c["t"] == 1:
                bx, by = tc(boss.x, boss.y)
                self.sfx.play("boom")
                self.shake = max(self.shake, 14)
                self.ring(bx, by, MOBS[boss.kind]["col"], 200, 36)
                self.burst(bx, by, MOBS[boss.kind]["col"], 40, 6, 36)
        if c["t"] >= dur:
            c["i"] += 1
            c["t"] = 0
            if c["i"] >= len(c["steps"]):
                self.end_cut()

    def end_cut(self):
        self.cut = None
        self.reveal = None
        self.prx, self.pry = float(self.px), float(self.py)

    def skip_cut(self):
        self.end_cut()
        self.camx, self.camy = self.cam_for(self.px, self.py)
        self.focus = (self.prx, self.pry)
        self.banner = min(self.banner, 60)

    def update(self):
        k = 0.35
        walking_in = bool(self.cut) and self.cut["steps"][self.cut["i"]][0] == "walk"
        if not walking_in:
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
        if self.cut:
            self.update_cut()
        else:
            tx, ty = self.cam_for(self.prx, self.pry)
            self.camx += (tx - self.camx) * 0.18
            self.camy += (ty - self.camy) * 0.18
            self.focus = (self.prx, self.pry)
        self.bars += ((1.0 if self.cut else 0.0) - self.bars) * 0.14
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
            col = PROJ_COL.get(p[6], (255, 150, 40))
            if p[6] != "arrow":
                t = p[4] / p[5]
                self.burst(p[0] + (p[2] - p[0]) * t, p[1] + (p[3] - p[1]) * t, col, 1, 0.6, 12, 0, 3)
            if p[4] >= p[5]:
                self.burst(p[2], p[3], col if p[6] != "arrow" else (230, 230, 210), 8, 2.5, 16)
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
        delete_save()
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
            sub = random.choice([k for k, _ in mob_pool(d, self.biome)])
            n = random.randint(2, 4) + d // 4
            q["sub"] = sub
            q["text"] = f"Убей {n} {mob_plural(sub, self.biome)}"
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
        if self.over or self.ui or self.cut:
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
            if self.haz_kind(self.px, self.py) == "ice" and not self.over:   # скольжение по льду
                sx, sy = self.px + dx, self.py + dy
                if self.grid[sy][sx] == 0 and not self.blocked(sx, sy):
                    self.px, self.py = sx, sy
                    self.say("Ты скользишь по льду!", BLUE)
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
        self.say(("КРИТ! " if crit else "") + f"Ты нанёс {m.name} {dmg} урона.",
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
        info = MOBS[m.kind]
        arm = info.get("armor", 0)
        if arm:
            dmg = max(1, dmg - arm)                  # броня босса гасит часть урона
        m.hp -= dmg
        m.flash = 6
        m.awake = True
        x, y = tc(m.x, m.y)
        self.float_text(("КРИТ " if crit else "") + str(dmg), m.x, m.y, (255, 220, 120), crit)
        self.burst(x, y, m.col, 18 if crit else 9, 4 if crit else 3)
        if info.get("reflect") and not self.over:
            back = max(1, int(dmg * info["reflect"]))
            self.say(f"{m.name} отражает часть урона: -{back} HP!", PURPLE)
            self.hurt_player(back, "отражённый урон", pierce=True)
        if m.hp <= 0:
            self.kill_mob(m)

    def kill_mob(self, m):
        if m in self.mobs:
            self.mobs.remove(m)
        info = MOBS[m.kind]
        d = self.depth
        x, y = tc(m.x, m.y)
        self.burst(x, y, m.col, 30, 5, 34)
        self.ring(x, y, m.col, 70, 16)
        gold = int(random.randint(*info["gold"]) * (1 + 0.1 * (d - 1)))
        self.add_gold(gold)
        self.float_text(f"+{gold}", m.x, m.y - 1, GOLD)
        for _ in range(6):
            self.burst(x, y, GOLD, 1, 4, 30, 0.2, 3)
        self.say(f"{m.name} повержен! +{gold} золота.", GOLD)
        self.sfx.play("coin")
        self.kills += 1
        self.gain_xp(int(info["xp"] * (1 + 0.08 * (d - 1))))
        if random.random() < 0.25:
            self.give_item(self.drop_item())
        if m.kind == "ogre" and not self.has_axe and random.random() < AXE_DROP:
            self.get_axe()
        if is_boss(m):
            self.boss_alive = False
            self.tele = []
            self.ring(x, y, GOLD, 220, 40)
            self.shake = 20
            self.give_item("elixir")
            self.give_item(self.drop_item())
            if info.get("boss"):
                self.give_item(self.drop_item())
            self.say(f"{m.name} пал! Дверь вниз открыта!", GOLD)
            self.toast(f"{m.name} повержен!", GOLD)
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
            found = int(random.randint(15, 35) * (1 + 0.12 * (self.depth - 1)) * (1.5 if self.biome in ("crystal", "diamond") else 1))
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
                self.say("Дверь заперта магией: " + next((m.name for m in self.mobs if is_boss(m)), "босса") + " ещё жив!", RED)
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
    def on_slow(self):
        return self.haz_kind(self.px, self.py) == "water" or "frost" in self.st

    def hazard_tick(self):
        hk = self.haz_kind(self.px, self.py)
        if hk == "lava":
            dmg = 3 + self.depth // 6
            self.say(f"Ты стоишь в лаве! -{dmg} HP.", ORANGE)
            self.hurt_player(dmg, "лава", pierce=True)
        elif hk == "acid":
            dmg = 2 + self.depth // 8
            self.say(f"Кислота разъедает ноги: -{dmg} HP.", GREEN)
            self.hurt_player(dmg, "кислота", pierce=True)
            if not self.over:
                self.add_status("poison", 3)
        elif hk == "water" and self.turn % 4 == 0:
            self.say("Ты бредёшь по воде — движения замедлены.", BLUE)

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
        self.hazard_tick()
        if self.over:
            return
        for pos in list(self.haz):                  # временные лужи (след босса, потоп) высыхают
            h = self.haz[pos]
            if h[1] is not None:
                h[1] -= 1
                if h[1] <= 0:
                    del self.haz[pos]
        if self.axe_pending:                # задержка секиры: 1 -> 0, а на следующем ходу — удар
            if self.axe_pending[4] > 0:
                self.axe_pending[4] -= 1
            else:
                self.resolve_axe()
        self.mobs_turn()
        if not self.over and self.on_slow():
            self.mobs_turn()                # вода и холод замедляют героя: враги успевают сходить ещё раз

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
        dmg = int(random.randint(*m.dmg) * mult)
        m.lunge = [sign(self.px - m.x), sign(self.py - m.y), 10]
        real = self.hurt_player(max(1, dmg), m.name)
        self.say(f"{m.name} бьёт тебя: -{real} HP!", RED)
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
                g = Mob("goblin", x, y, self.depth, self.biome)
                g.awake = True
                self.mobs.append(g)
                px, py = tc(x, y)
                self.burst(px, py, g.col, 14, 3)
                n += 1
        self.ring(*tc(m.x, m.y), RED, 100, 20)
        self.say(f"{m.name} призывает подданных!", RED)
        self.sfx.play("boom")

    # ---- боссы: у каждого свой набор способностей (kit в таблице BOSSES)
    def line_cells(self, m, dx, dy, length, width=0):
        cells = []
        for i in range(1, length + 1):
            cx, cy = m.x + dx * i, m.y + dy * i
            if not (0 < cx < COLS - 1 and 0 < cy < ROWS - 1) or self.grid[cy][cx] == 1:
                break
            for w in range(-width, width + 1):
                lx, ly = cx - dy * w, cy + dx * w
                if 0 < lx < COLS - 1 and 0 < ly < ROWS - 1 and self.grid[ly][lx] == 0:
                    cells.append((lx, ly))
        return cells

    def dir_to_player(self, m):
        ddx, ddy = self.px - m.x, self.py - m.y
        return (sign(ddx), 0) if abs(ddx) >= abs(ddy) else (0, sign(ddy))

    def set_tele(self, m, kind, cells):
        m.pend = {"kind": kind, "cells": cells}
        self.tele = list(cells)
        self.float_text("!", m.x, m.y, RED, True)

    def boss_can(self, name, m, dist, sees):
        if name == "slam":
            return dist <= 2
        if name in ("rock", "shard", "spit", "curse", "freeze"):
            return sees and 2 <= dist <= 8
        if name in ("rockfall", "flood"):
            return sees and dist <= 8
        if name == "summon":
            return sees and len(self.mobs) < 8
        if name == "blink":
            return dist <= 2 or dist >= 7
        if name in ("breath", "charge"):
            dx, dy = self.dir_to_player(m)
            cells = self.line_cells(m, dx, dy, 7, 0 if name == "charge" else 1)
            if name == "charge":
                return sees and dist >= 2 and (self.px, self.py) in cells
            return sees and dist <= 6 and (self.px, self.py) in cells
        return False

    def boss_use(self, name, m):
        px, py = self.px, self.py
        if name == "slam":
            cells = [(m.x + dx, m.y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                     if (dx or dy) and self.grid[m.y + dy][m.x + dx] == 0]
            self.set_tele(m, "slam", cells)
            self.say(f"{m.name} замахивается для удара по площади! Отойди!", ORANGE)
        elif name == "rockfall":
            cand = [(x, y) for x in range(px - 3, px + 4) for y in range(py - 3, py + 4)
                    if 0 < x < COLS - 1 and 0 < y < ROWS - 1 and self.grid[y][x] == 0]
            random.shuffle(cand)
            cells = list(dict.fromkeys([(px, py)] + cand[:6]))
            self.set_tele(m, "rockfall", cells)
            self.say(f"{m.name} обрушивает потолок! Уходи с красных клеток!", ORANGE)
        elif name in ("breath", "charge"):
            dx, dy = self.dir_to_player(m)
            cells = self.line_cells(m, dx, dy, 7, 0 if name == "charge" else 1)
            self.set_tele(m, name, cells)
            self.say(f"{m.name} готовится {'дохнуть огнём' if name == 'breath' else 'таранить'}! Сойди с линии!", ORANGE)
        elif name in ("rock", "shard", "spit", "curse", "freeze"):
            kind = {"rock": "rock", "shard": "shard", "spit": "spit", "curse": "curse", "freeze": "ice"}[name]
            self.add_proj(m.x, m.y, px, py, kind)
            real = self.hurt_player(int(random.randint(*m.dmg) * 0.8), m.name)
            self.say(f"{m.name} метает {'камень' if name == 'rock' else 'заряд'}: -{real} HP!", RED)
            if not self.over:
                if name in ("spit", "curse"):
                    self.add_status("poison", 3)
                elif name == "freeze":
                    self.add_status("frost", 4)
        elif name == "summon":
            n = 0
            spots = [(m.x + dx, m.y + dy) for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2) if dx or dy]
            random.shuffle(spots)
            for x, y in spots:
                if n >= 2:
                    break
                if 0 < x < COLS - 1 and 0 < y < ROWS - 1 and not self.blocked(x, y):
                    g = Mob(random.choice(["goblin", "goblin", "archer", "bat"]), x, y, self.depth, self.biome)
                    g.awake = True
                    self.mobs.append(g)
                    gx, gy = tc(x, y)
                    self.burst(gx, gy, g.col, 14, 3)
                    n += 1
            self.ring(*tc(m.x, m.y), m.col, 110, 22)
            self.say(f"{m.name} призывает слуг!", RED)
            self.sfx.play("boom")
        elif name == "flood":
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    x, y = px + dx, py + dy
                    if (0 < x < COLS - 1 and 0 < y < ROWS - 1 and self.grid[y][x] == 0
                            and (x, y) != self.exit_pos and (x, y) not in self.haz):
                        self.haz[(x, y)] = ["water", 22]
            self.ring(*tc(px, py), BLUE, 130, 24)
            self.say(f"{m.name} затопляет пол вокруг тебя — вода замедляет!", BLUE)
            self.sfx.play("potion")
        elif name == "blink":
            cand = [(x, y) for x in range(px - 5, px + 6) for y in range(py - 5, py + 6)
                    if 0 < x < COLS - 1 and 0 < y < ROWS - 1 and self.grid[y][x] == 0 and not self.blocked(x, y)
                    and (x, y) != self.exit_pos and 2 <= max(abs(x - px), abs(y - py)) <= 4]
            if cand:
                self.burst(*tc(m.x, m.y), m.col, 20, 4, 24)
                m.x, m.y = random.choice(cand)
                m.rx, m.ry = float(m.x), float(m.y)
                self.burst(*tc(m.x, m.y), m.col, 20, 4, 24)
                self.ring(*tc(m.x, m.y), m.col, 90, 18)
                self.say(f"{m.name} телепортируется!", PURPLE)

    def boss_resolve(self, m):
        p = m.pend
        m.pend = None
        self.tele = []
        kind, cells = p["kind"], p["cells"]
        px, py = self.px, self.py
        if kind == "charge":
            last, hit = (m.x, m.y), False
            for (x, y) in cells:
                if (x, y) == (px, py):
                    hit = True
                    break
                if (self.grid[y][x] == 1 or self.mob_at(x, y) or (x, y) in self.npcs
                        or (x, y) in self.barrels or (x, y) in self.fountains):
                    break
                last = (x, y)
            m.x, m.y = last
            self.sfx.play("boom")
            self.shake = max(self.shake, 12)
            if hit:
                real = self.hurt_player(int(random.randint(*m.dmg) * 1.5), m.name)
                self.say(f"{m.name} врезается в тебя: -{real} HP!", RED)
            else:
                self.say(f"{m.name} промахнулся и пролетел мимо.", GRAY)
            return
        col = {"slam": (230, 190, 120), "rockfall": (160, 150, 130), "breath": (255, 140, 40)}.get(kind, (255, 200, 100))
        for (x, y) in cells:
            self.burst(*tc(x, y), col, 6, 3, 18)
        self.ring(*tc(m.x, m.y), col, 130, 20)
        self.shake = max(self.shake, 14)
        self.sfx.play("boom")
        if (px, py) in cells:
            mult = {"slam": 1.4, "rockfall": 1.2, "breath": 1.1}.get(kind, 1.2)
            real = self.hurt_player(int(random.randint(*m.dmg) * mult), m.name)
            self.say(f"{m.name} попадает по тебе: -{real} HP!", RED)
            if kind == "breath" and not self.over:
                self.add_status("burn", 3)
        else:
            self.say("Ты увернулся от удара!", GREEN)

    def leave_trail(self, x, y, kind):
        cur = self.haz.get((x, y))
        if (x, y) == self.exit_pos or (cur and cur[1] is None):
            return
        self.haz[(x, y)] = [kind, 16]

    def boss_split(self, m):
        n = 0
        spots = [(m.x + dx, m.y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
        random.shuffle(spots)
        for x, y in spots:
            if n >= 2:
                break
            if not self.blocked(x, y):
                s = Mob("slime", x, y, self.depth, self.biome)
                s.awake = True
                self.mobs.append(s)
                self.burst(*tc(x, y), s.col, 14, 3)
                n += 1
        self.ring(*tc(m.x, m.y), m.col, 110, 22)
        self.say(f"{m.name} разделяется на слизней!", GREEN)
        self.sfx.play("boom")

    def boss_act(self, m, dm, sees, dist):
        info = MOBS[m.kind]
        if m.pend:                                   # удар, о котором предупреждали, срабатывает сейчас
            self.boss_resolve(m)
            return
        if info.get("regen") and m.hp < m.max:
            m.hp = min(m.max, m.hp + max(1, int(m.max * info["regen"])))
        if info.get("split"):
            while m.split_stage < 2 and m.hp / m.max < (0.66, 0.33)[m.split_stage]:
                m.split_stage += 1
                self.boss_split(m)
        for k in m.cds:
            if m.cds[k] > 0:
                m.cds[k] -= 1
        for name, cd in info["kit"]:
            if m.cds.get(name, 0) <= 0 and self.boss_can(name, m, dist, sees) and random.random() < 0.75:
                self.boss_use(name, m)
                m.cds[name] = cd
                return
        if dist == 1:
            real = self.mob_attack(m)
            if info.get("drain") and real:
                m.hp = min(m.max, m.hp + real // 2)
                self.float_text(f"+{real // 2}", m.x, m.y, PURPLE)
        else:
            ox, oy = m.x, m.y
            if self.step_toward(m, dm) and info.get("trail"):
                self.leave_trail(ox, oy, info["trail"])

    def mob_act(self, m, dm):
        info = MOBS[m.kind]
        if self.haz_kind(m.x, m.y) == "water" and self.turn % 2 == 0:
            return                                   # вода замедляет и врагов
        dist = abs(m.x - self.px) + abs(m.y - self.py)
        inv = "invis" in self.st
        sees = dist <= info["sight"] and self.los(m.x, m.y, self.px, self.py)
        if inv and dist > 1:
            sees = False                             # невидимого героя замечают только вплотную
        if not m.awake:
            if sees:
                m.awake = True
                self.float_text("!", m.x, m.y, RED, True)
            return
        if inv and dist > 1:
            if random.random() < 0.5:
                self.random_step(m)
            return
        k = m.kind
        if info.get("boss"):
            self.boss_act(m, dm, sees, dist)
            return
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
                real = self.hurt_player(dmg, m.name)
                self.say(f"{m.name} стреляет: -{real} HP!", RED)
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
                    self.say(f"{m.name} заносит дубину! Отойди!", ORANGE)
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

    # ---- сохранение и загрузка забега
    def dump(self):
        npc_list = list(self.npcs.values())

        def qd(q):
            d = {k: v for k, v in q.items() if k != "npc"}
            n = q.get("npc")
            d["npc_idx"] = npc_list.index(n) if n in npc_list else None
            return d

        npcs = []
        for n in npc_list:
            ref = next((i for i, q in enumerate(self.quests) if q is n.quest), None)
            npcs.append(dict(x=n.x, y=n.y, kind=n.kind, name=n.name, state=n.state, qref=ref,
                             quest=qd(n.quest) if (n.quest and ref is None) else None))
        mobs = [dict(kind=m.kind, x=m.x, y=m.y, hp=m.hp, max=m.max, dmg=list(m.dmg), awake=m.awake, cd=m.cd,
                     charge=m.charge, summon_cd=m.summon_cd, biome=m.biome, name=m.name, col=list(m.col),
                     cds=m.cds, split_stage=m.split_stage) for m in self.mobs]
        return dict(
            version=2, name=self.name, lvl=self.lvl, xp=self.xp, up=self.up, hp=self.hp, gold=self.gold,
            total_gold=self.total_gold, kills=self.kills, turn=self.turn, done_quests=self.done_quests,
            depth=self.depth, biome=self.biome, biome_hist=self.biome_hist, inv=self.inv, weapon=self.weapon,
            has_axe=self.has_axe, st=self.st, facing=self.facing, quests=[qd(q) for q in self.quests],
            floor=dict(grid=self.grid, deco=self.deco, explored=self.explored, torches=[list(t) for t in self.torches],
                       px=self.px, py=self.py, exit_pos=list(self.exit_pos), boss_alive=self.boss_alive,
                       chests=[list(c) for c in self.chests], barrels=[list(b) for b in self.barrels],
                       fountains=[[x, y, u] for (x, y), u in self.fountains.items()],
                       traps=[[x, y, s] for (x, y), s in self.traps.items()],
                       haz=[[x, y, h[0], h[1]] for (x, y), h in self.haz.items()],
                       npcs=npcs, mobs=mobs, tile_seed=self.tile_seed, tile_alt=self.tile_alt,
                       crypt_var=self.crypt_var, grad=self.grad))

    def load_data(self, d):
        for k in ("name", "lvl", "xp", "up", "hp", "gold", "total_gold", "kills", "turn", "done_quests", "depth",
                  "biome", "biome_hist", "inv", "weapon", "has_axe", "st", "facing"):
            setattr(self, k, d[k])
        for k in ORDER:
            self.inv.setdefault(k, 0)
        for k in ("weapon", "armor", "vit", "lamp", "crit", "axe"):
            self.up.setdefault(k, 0)
        f = d["floor"]
        self.grid, self.deco, self.explored = f["grid"], f["deco"], f["explored"]
        self.visible = [[False] * COLS for _ in range(ROWS)]
        self.torches = {tuple(t) for t in f["torches"]}
        self.px, self.py = f["px"], f["py"]
        self.exit_pos = tuple(f["exit_pos"])
        self.boss_alive = f["boss_alive"]
        self.chests = {tuple(c) for c in f["chests"]}
        self.barrels = {tuple(b) for b in f["barrels"]}
        self.fountains = {(x, y): u for x, y, u in f["fountains"]}
        self.traps = {(x, y): s for x, y, s in f["traps"]}
        self.haz = {(x, y): [k, t] for x, y, k, t in f["haz"]}
        self.tile_seed, self.tile_alt, self.crypt_var, self.grad = f["tile_seed"], f["tile_alt"], f["crypt_var"], f["grad"]
        self.build_tiles()
        self.mini = pygame.Surface((COLS * 2, ROWS * 2), pygame.SRCALPHA)
        self.mini_dirty = True
        self.mobs = []
        for md in f["mobs"]:
            m = Mob(md["kind"], md["x"], md["y"], self.depth, md["biome"])
            m.hp, m.max, m.dmg = md["hp"], md["max"], tuple(md["dmg"])
            m.awake, m.cd, m.charge, m.summon_cd = md["awake"], md["cd"], md["charge"], md["summon_cd"]
            m.name, m.col, m.cds, m.split_stage = md["name"], tuple(md["col"]), md["cds"], md["split_stage"]
            self.mobs.append(m)
        self.quests = []
        for qd_ in d["quests"]:
            q = dict(qd_)
            q["npc"] = None
            self.quests.append(q)
        self.npcs = {}
        for i, nd in enumerate(f["npcs"]):
            n = NPC(nd["kind"], nd["x"], nd["y"], nd["name"])
            n.state = nd["state"]
            if nd["qref"] is not None and nd["qref"] < len(self.quests):
                n.quest = self.quests[nd["qref"]]
            elif nd["quest"]:
                n.quest = dict(nd["quest"])
                n.quest["npc"] = n
            self.npcs[(n.x, n.y)] = n
        npc_list = list(self.npcs.values())
        for q, qd_ in zip(self.quests, d["quests"]):
            idx = qd_.get("npc_idx")
            if idx is not None and idx < len(npc_list):
                q["npc"] = npc_list[idx]
        self.hp_lag = float(self.hp)
        self.xp_disp = float(self.xp)
        self.gold_disp = float(self.gold)
        self.snap_camera()
        self.compute_fov()
        self.fade, self.banner = 255, 120
        self.say(f"С возвращением, {self.name}! Игра продолжена: этаж {self.depth}.", GOLD)
        self.say(f"Локация: {BIOMES[self.biome]['name']}.", BIOMES[self.biome]["color"])

    def autosave(self):
        if not self.over:
            save_game_to_disk(self)


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
    B = BIOMES[g.biome]
    TS = g.tiles
    torches = A.torch_set(g.biome)
    cx, cy = int(g.camx), int(g.camy)
    w = A.view
    w.fill((8, 6, 12))
    tx0, ty0 = cx // TILE, cy // TILE
    glows = []
    for ty in range(ty0, min(ROWS, ty0 + VIEW_ROWS + 2)):
        row, exr, vis, vrow = g.grid[ty], g.explored[ty], g.visible[ty], g.vmap[ty]
        for tx in range(tx0, min(COLS, tx0 + VIEW_COLS + 2)):
            if not exr[tx]:
                continue
            sx, sy = tx * TILE - cx, ty * TILE - cy
            v = vrow[tx]
            if row[tx] == 1:
                w.blit(TS["wall"][v][(tx * 5 + ty * 3) % 2], (sx, sy))
                if (tx, ty) in g.torches:
                    w.blit(torches[(t // 110 + tx) % 2], (sx, sy))
                    if vis[tx]:
                        glows.append((sx, sy))
            else:
                dc = g.deco[ty][tx]
                w.blit(TS["deco"][v][dc - 1] if dc else TS["floor"][v][(tx * 7 + ty * 13) % 4], (sx, sy))
                hz = g.haz.get((tx, ty))
                if hz:
                    w.blit(A.haz[hz[0]][(t // 350 + tx + ty) % 2], (sx, sy))
                    if hz[0] == "lava" and vis[tx]:
                        glows.append((sx, sy))
            if not vis[tx] and not g.revealed(tx, ty):
                w.blit(A.dim, (sx, sy))

    def seen(x, y):
        return g.visible[y][x] or g.revealed(x, y)

    def S(rx, ry):
        return int(rx * TILE) - cx, int(ry * TILE) - cy

    # подсветка дуги замаха секиры (телеграф удара)
    if g.axe_pending:
        dx, dy, ox, oy, _ = g.axe_pending
        A.tele.set_alpha(int(150 + 105 * math.sin(t / 90)))
        for (x, y) in g.axe_cells(ox, oy, dx, dy):
            if 0 <= x < COLS and 0 <= y < ROWS and g.grid[y][x] == 0:
                w.blit(A.tele, S(x, y))
    # красные клетки — босс готовит удар
    if g.tele:
        A.tele_boss.set_alpha(int(150 + 105 * math.sin(t / 70)))
        for (x, y) in g.tele:
            w.blit(A.tele_boss, S(x, y))

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
        info = MOBS[m.kind]
        top = sy
        if info.get("boss"):
            img = A.boss_frames(m.kind[5:], m.flash > 0)[(t // 320) % 2]
            top = sy - (img.get_height() - TILE) + 6 + bob
            w.blit(img, (sx - (img.get_width() - TILE) // 2, top))
        elif m.kind == "slime":
            img = A.mob_img(m.kind, t, m.flash > 0, m.biome)
            sq = int((math.sin(t / 160 + m.seed) + 1) * 2.5)
            img = pygame.transform.scale(img, (TILE + sq, TILE - sq))
            w.blit(img, (sx - sq // 2, sy + sq))
        else:
            w.blit(A.mob_img(m.kind, t, m.flash > 0, m.biome), (sx, sy + bob))
        if m.charge:
            pygame.draw.ellipse(w, (220, 60, 40), (sx + 2, sy + TILE - 12, TILE - 4, 12), 3)
            draw_text(w, F["big"], "!", RED, sx + TILE // 2, top - 32, "c")
        elif not m.awake:
            draw_text(w, F["small"], "z", GRAY, sx + TILE - 8, top - 6 + bob)
        if m.hp < m.max and not info.get("boss"):
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
                         ("invis", (190, 225, 255)), ("vamp", PURPLE), ("frost", (150, 210, 255))):
            if key in g.st:
                pulse = int(2 + math.sin(t / 120) * 2)
                pygame.draw.ellipse(w, col, (sx + 4 - pulse, sy + TILE - 14, TILE - 8 + pulse * 2, 12), 2)
        anim, f, wp = player_anim(g, t)
        wl = g.up["weapon"] if wp == "sword" else g.up["axe"]
        img = A.pframe(anim, f, g.up["armor"], wp, g.pflash > 0, g.facing < 0, wl)
        if "invis" in g.st:                                   # невидимость: герой полупрозрачный
            img = img.copy()
            img.set_alpha(105 + int(math.sin(t / 200) * 25))
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
            col = PROJ_COL.get(p[6], (255, 120, 30))
            pygame.draw.circle(w, col, (int(x), int(y)), 9)
            pygame.draw.circle(w, lerpc(col, (255, 255, 255), 0.65), (int(x), int(y)), 5)

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

    # тьма + круг света факела (в катсцене свет следует за камерой)
    ov = A.overlay
    ov.fill((0, 0, 0, 228))
    rad = g.light_radius() + (2 if (g.cut and g.cut.get("boss")) else 0)
    light = A.light(rad)[(t // 120) % 3]
    pcx, pcy = int(g.focus[0] * TILE) - cx + TILE // 2, int(g.focus[1] * TILE) - cy + TILE // 2
    ov.blit(light, (pcx - light.get_width() // 2, pcy - light.get_height() // 2),
            special_flags=pygame.BLEND_RGBA_MIN)
    w.blit(ov, (0, 0))
    for sx, sy in glows:
        w.blit(A.glow, (sx + TILE // 2 - 55, sy + TILE // 2 - 55), special_flags=pygame.BLEND_RGB_ADD)
    tint = B["tint"]
    if tint[3]:                                            # цветная дымка локации
        A.flashsurf.fill(tint[:3])
        A.flashsurf.set_alpha(tint[3])
        w.blit(A.flashsurf, (0, 0))

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

    # миникарта и название локации
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
    label = B["name"]
    if g.biome == "crypt":
        label += " (" + ("костяной", "песчаный", "королевский")[g.crypt_var] + ")"
    draw_text(screen, F["small"], label, B["color"], 10, 98)

    # статусы
    chips = [(f"{STATUS_NAME[k]} {v}", STATUS_COL[k]) for k, v in g.st.items()]
    if chips:
        total = sum(F["small"].size(c[0])[0] + 18 for c in chips)
        x = MAP_W // 2 - total // 2
        for label_, col in chips:
            wd = F["small"].size(label_)[0] + 12
            pygame.draw.rect(screen, (20, 17, 28), (x, 8, wd, 24))
            pygame.draw.rect(screen, col, (x, 8, wd, 24), 2)
            draw_text(screen, F["small"], label_, col, x + 6, 10, shadow=False)
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

    # полоса здоровья босса
    boss = next((m for m in g.mobs if is_boss(m) and m.awake), None)
    if boss and not g.over and not g.cut:
        info = MOBS[boss.kind]
        bw = 460
        bx = MAP_W // 2 - bw // 2
        draw_text(screen, F["small"], f"{boss.name} — {info.get('title', '')}", info["col"], MAP_W // 2, 38, "c")
        pygame.draw.rect(screen, (30, 10, 14), (bx, 58, bw, 14))
        pygame.draw.rect(screen, (210, 44, 56), (bx, 58, int(bw * max(0, boss.hp) / boss.max), 14))
        pygame.draw.rect(screen, info["col"], (bx, 58, bw, 14), 2)

    # уведомления: вылетают слева, потом уезжают обратно
    ty = 124
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

    draw_cut(screen, g, F)

    if g.fade > 0:
        A.blacksurf.set_alpha(g.fade)
        screen.blit(A.blacksurf, (0, 0), (0, 0, MAP_W, MAP_H))
    if g.banner > 0 and not (g.cut and g.cut["steps"][g.cut["i"]][0] in ("hold",)):
        a = max(0, min(255, g.banner * 5, (170 - g.banner) * 10))
        if g.new_biome:
            lab = F["normal_b"].render("НОВАЯ ЛОКАЦИЯ", True, TEXT)
            lab.set_alpha(a)
            screen.blit(lab, (MAP_W // 2 - lab.get_width() // 2, MAP_H // 2 - 112))
        title = F["title"].render(f"ЭТАЖ {g.depth}", True, GOLD)
        title.set_alpha(a)
        screen.blit(title, (MAP_W // 2 - title.get_width() // 2, MAP_H // 2 - 70))
        sub = F["big"].render(B["name"], True, B["color"])
        sub.set_alpha(a)
        screen.blit(sub, (MAP_W // 2 - sub.get_width() // 2, MAP_H // 2 + 6))
        if g.boss_alive:
            bn = MOBS["boss_" + g.biome]["name"] if g.depth % 10 == 0 else MOBS["king"]["name"]
            sub2 = F["big"].render(f"БОСС: {bn}", True, RED)
            sub2.set_alpha(a)
            screen.blit(sub2, (MAP_W // 2 - sub2.get_width() // 2, MAP_H // 2 + 44))

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


def draw_cut(screen, g, F):
    """Кино-полосы и титры: заход в локацию и представление босса."""
    k = ease(g.bars)
    if k < 0.01:
        return
    h = int(64 * k)
    pygame.draw.rect(screen, (0, 0, 0), (0, 0, MAP_W, h))
    pygame.draw.rect(screen, (0, 0, 0), (0, MAP_H - h, MAP_W, h))
    c = g.cut
    if not c:
        return
    step, dur = c["steps"][c["i"]]
    t = c["t"]
    if step == "walk":
        a = ease(t / 30) * clamp01((dur - t) / 24)
        B = BIOMES[g.biome]
        draw_text(screen, F["big"], B["name"], B["color"], MAP_W // 2, MAP_H - 112, "c", alpha=int(255 * a))
    elif step == "hold" and c.get("boss"):
        m = c["boss"]
        info = MOBS[m.kind]
        fo = clamp01((dur - t) / 24)
        a1, a2 = ease(t / 28) * fo, ease((t - 22) / 28) * fo
        y = MAP_H - 64 - 160
        draw_text(screen, F["huge"], info["name"], info["col"], MAP_W // 2, y + int((1 - ease(t / 28)) * 36), "c",
                  alpha=int(255 * a1))
        lw = int(260 * ease((t - 22) / 28) * fo)
        pygame.draw.line(screen, info["col"], (MAP_W // 2 - lw, y + 108), (MAP_W // 2 + lw, y + 108), 2)
        draw_text(screen, F["big"], info.get("title", ""), TEXT, MAP_W // 2, y + 114 + int((1 - ease((t - 22) / 28)) * 20),
                  "c", alpha=int(255 * a2))
    if c["t"] > 6:
        draw_text(screen, F["small"], "Enter — пропустить", GRAY, MAP_W - 16, MAP_H - 30, "r",
                  alpha=int(160 * ease(c["t"] / 40)))


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
        pygame.draw.rect(screen, ITEM_COL.get(key, ITEMS[key]["col"]) if n else (70, 62, 90), slot, 2)
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

    # оружие (вид и название меняются с заточкой)
    wx = 745
    wl = g.up["weapon"] if g.weapon == "sword" else g.up["axe"]
    wname = "Секира" if g.weapon == "axe" else "Меч"
    screen.blit(A.weapon_icon(g.weapon, wl), (wx, y0 + 6))
    draw_text(screen, F["normal_b"], wname + (" [Q]" if g.has_axe else ""),
              ORANGE if g.weapon == "axe" else TEXT, wx + 38, y0 + 4)
    stage = SWORD_STAGES[g.up["weapon"]] if g.weapon == "sword" else f"Секира, ур. {g.up['axe']}"
    draw_text(screen, F["small"], fit_text(F["small"], stage, 170), (255, 225, 140), wx + 38, y0 + 28, shadow=False)
    if g.axe_pending and (t // 200) % 2 == 0:
        draw_text(screen, F["small"], "ЗАМАХ!", ORANGE, wx + 150, y0 + 8, shadow=False)
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


def menu_items(sfx, save=None):
    items = []
    if save:
        items.append(("continue", f"Продолжить • этаж {save['depth']}"))
    items += [("new", "Новая игра"), ("help", "Как играть"), ("records", "Рекорды"), ("credits", "Создатели"),
              ("sound", "Звук: " + ("вкл" if sfx.on else "выкл")), ("exit", "Выход")]
    return items


def draw_menu(screen, A, F, bg, fx, sel, sfx, rec, age, hov, items):
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
    for i, (mid, label) in enumerate(items):
        base = pygame.Rect(WIN_W // 2 - 190, 258 + i * 48, 380, 40)
        rects.append(base)
        on = i == sel
        hov[i] += ((1.0 if on else 0.0) - hov[i]) * 0.25          # плавное наведение
        k = ease((age - 350 - i * 80) / 450)                       # кнопки влетают по очереди
        xoff = (-1 if i % 2 == 0 else 1) * int((1 - k) * 560)
        r = base.move(xoff, 0).inflate(int(hov[i] * 18), int(hov[i] * 4))
        mix = hov[i]
        fill = tuple(int(a + (b - a) * mix) for a, b in ((28, 70), (23, 48), (40, 95)))
        border = tuple(int(a + (b - a) * mix) for a, b in (((110, 240)), ((85, 200)), ((140, 70))))
        pygame.draw.rect(screen, fill, r)
        pygame.draw.rect(screen, border, r, 3 if on else 2)
        txt = tuple(int(a + (b - a) * mix) for a, b in ((225, 240), (220, 200), (235, 70)))
        draw_text(screen, F["big"], label, txt, r.centerx, r.y + 3, "c")
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
        ("WASD / стрелки — ходьба, идти во врага — удар", TEXT),
        ("Пробел — пропустить ход,  Esc — пауза", TEXT),
        ("Q — сменить оружие (меч / секира)", TEXT),
        ("H — лечение,  1–8 — предметы и свитки", TEXT),
        ("M — звук,  F11 — полный экран", TEXT),
        ("", TEXT),
        ("Локации", GOLD),
        ("Каждые 10 этажей — новая локация со своими", TEXT),
        ("врагами и боссом на 10-м этаже. Лава жжёт,", TEXT),
        ("вода замедляет, на льду герой скользит.", TEXT),
        ("", TEXT),
        ("Секира", GOLD),
        ("Редко выпадает из огра. Бьёт дугой по 3", TEXT),
        ("клеткам, но с задержкой в один ход.", TEXT),
        ("", TEXT),
        ("Советы", GOLD),
        ("Босс держит дверь вниз запертой. Красные", TEXT),
        ("клетки на полу — туда скоро ударят.", TEXT),
        ("Игра сохраняется при выходе: «Продолжить».", TEXT),
    ]
    y = 84
    for s, c in lines:
        draw_text(screen, F["normal_b"] if c == GOLD else F["normal"], s, c, 40, y)
        y += 28
    draw_text(screen, F["big"], "Бестиарий", GOLD, 600, 84)
    y = 124
    for k, d in [(k, d) for k, d in MOBS.items() if not d.get("boss")]:
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


# ===== [DEBUG-START] ========================================================================
# ЧИТ-ПАНЕЛЬ РАЗРАБОТЧИКА — один отдельный блок.
#
# Куда вставить: в game.py СРАЗУ ПЕРЕД строкой
#     # ============================================================ главный цикл
# (после всех функций draw_* и перед def view_info / def main). ВСЁ. Больше ничего менять не надо:
# блок сам подключается к игре (оборачивает draw_hud, pygame.event.get, Game.hurt_player, Game.try_move).
# Если раньше ты добавлял в main() строки с пометкой [DEBUG] — УДАЛИ их, они больше не нужны.
#
# Как удалить при релизе: удалить ВСЁ от "[DEBUG-START]" до "[DEBUG-END]" (больше нигде следов нет).
# Либо просто поставить DEBUG_ENABLED = False — тогда панель вообще не включается.
#
# Как пользоваться: в игре нажми J, введи пароль 1337 и Enter. Повторное J закрывает/открывает панель.
# Читы включаются мышкой или горячими клавишами, пока панель открыта.
# При запуске игры в консоли должна появиться строка "[DEBUG] чит-панель загружена" — если её нет,
# блок вставлен не туда / не сохранён файл.

DEBUG_ENABLED = True
DEBUG_PASSWORD = "1337"
DEBUG_ASK_EVERY_TIME = False     # True = спрашивать пароль при КАЖДОМ открытии панели
DEBUG_KEY = "J"                  # буква для открытия/закрытия панели (работает и на русской раскладке)


def _dbg_hit(ev, letter):
    """Нажата ли клавиша-буква (работает и на русской раскладке)."""
    return (ev.scancode == getattr(pygame, "KSCAN_" + letter, -2)
            or ev.key == getattr(pygame, "K_" + letter.lower(), -3))


class DebugPanel:
    def __init__(self):
        self.visible = False
        self.unlocked = False
        self.asking = False
        self.buf = ""
        self.msg = ""
        self.god = False
        self.noclip = False
        self.rects = []
        # (клавиша, название, действие(g), функция-состояние или None)
        self.actions = [
            ("G", "Бессмертие (god mode)", self.a_god, lambda: self.god),
            ("N", "Проход сквозь стены", self.a_noclip, lambda: self.noclip),
            ("T", "Телепорт к двери", self.a_tp_door, None),
            ("K", "Убить всех врагов", self.a_kill_all, None),
            ("X", "Пропустить этаж", self.a_skip_floor, None),
            ("Z", "К боссу (ближайший 5/10-й этаж)", self.a_to_boss, None),
            ("C", "Следующая локация (этаж 11, 21...)", self.a_next_biome, None),
            ("H", "Полное лечение", self.a_heal, None),
            ("B", "+1000 золота", self.a_gold, None),
            ("L", "+1 уровень", self.a_level, None),
            ("I", "Все предметы x9", self.a_items, None),
            ("V", "Открыть карту этажа", self.a_map, None),
        ]

    # ---------------------------------------------------------------- действия
    def a_god(self, g):
        self.god = not self.god
        g.say("[DEBUG] Бессмертие: " + ("ВКЛ" if self.god else "выкл"), RED)

    def a_noclip(self, g):
        self.noclip = not self.noclip
        g.say("[DEBUG] Проход сквозь стены: " + ("ВКЛ" if self.noclip else "выкл"), RED)

    def a_tp_door(self, g):
        ex, ey = g.exit_pos
        spots = [(ex + dx, ey + dy) for dx, dy in
                 ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1))]
        for x, y in spots:
            if g.grid[y][x] == 0 and not g.blocked(x, y):
                g.px, g.py = x, y
                break
        else:
            g.px, g.py = ex, ey
        g.snap_camera()
        g.compute_fov()
        g.say("[DEBUG] Телепорт к двери.", RED)

    def a_kill_all(self, g):
        n = len(g.mobs)
        for m in list(g.mobs):
            g.kill_mob(m)
        g.say(f"[DEBUG] Убито врагов: {n}.", RED)

    def a_skip_floor(self, g):
        g.descend()

    def a_to_boss(self, g):
        """Прыжок на этаж перед ближайшим боссом (5, 10, 15, ...) и спуск на него."""
        nxt = (g.depth // 5 + 1) * 5
        g.depth = nxt - 1
        g.descend()
        g.say(f"[DEBUG] Этаж босса: {g.depth}.", RED)

    def a_next_biome(self, g):
        """Прыжок на первый этаж следующей локации (11, 21, 31, ...)."""
        nxt = ((g.depth - 1) // 10 + 1) * 10 + 1
        g.depth = nxt - 1
        g.descend()
        g.say(f"[DEBUG] Локация: {BIOMES[g.biome]['name']} (этаж {g.depth}).", RED)

    def a_heal(self, g):
        g.st.pop("poison", None)
        g.st.pop("burn", None)
        g.heal(g.max_hp)
        g.say("[DEBUG] Полное лечение.", RED)

    def a_gold(self, g):
        g.add_gold(1000)
        g.say("[DEBUG] +1000 золота.", RED)

    def a_level(self, g):
        g.gain_xp(g.xp_need())

    def a_items(self, g):
        for k in ORDER:
            g.inv[k] = max(g.inv[k], 9)
        g.say("[DEBUG] Предметы: по 9 штук.", RED)

    def a_map(self, g):
        for yy in range(ROWS):
            for xx in range(COLS):
                if g.grid[yy][xx] == 0:
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            g.explored[yy + dy][xx + dx] = True
        g.mini_dirty = True
        g.say("[DEBUG] Карта открыта.", RED)

    # ---------------------------------------------------------------- ввод
    def _toggle(self):
        if self.visible:
            self.visible = False
            if DEBUG_ASK_EVERY_TIME:
                self.unlocked = False
        elif self.unlocked:
            self.visible = True
        else:
            self.asking, self.buf, self.msg = True, "", ""

    def _type(self, ev):
        if ev.key == pygame.K_ESCAPE:
            self.asking, self.buf, self.msg = False, "", ""
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.buf == DEBUG_PASSWORD:
                self.unlocked, self.asking, self.visible = True, False, True
                self.buf = self.msg = ""
            else:
                self.buf, self.msg = "", "Неверный пароль"
        elif ev.key == pygame.K_BACKSPACE:
            self.buf = self.buf[:-1]
        elif ev.unicode and ev.unicode.isprintable() and len(self.buf) < 12:
            self.buf += ev.unicode

    def _run(self, i, g):
        name, fn = self.actions[i][1], self.actions[i][2]
        if g.over and fn not in (self.a_god, self.a_noclip):
            return                      # на экране смерти действия не нужны
        if g.cut:
            g.skip_cut()
        fn(g)

    def handle_event(self, ev, g, mpos):
        """True = событие обработано панелью (игре его передавать не надо)."""
        if not DEBUG_ENABLED or g is None:
            return False
        if ev.type == pygame.KEYDOWN:
            if self.asking:
                self._type(ev)
                return True
            if _dbg_hit(ev, DEBUG_KEY):
                self._toggle()
                return True
            if self.visible and not g.ui:
                for i, a in enumerate(self.actions):
                    if _dbg_hit(ev, a[0]):
                        self._run(i, g)
                        return True
            return False
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.visible and not self.asking:
            p = mpos(ev.pos)
            for i, r in enumerate(self.rects):
                if r.collidepoint(p):
                    self._run(i, g)
                    return True
        return False

    # ---------------------------------------------------------------- рисование
    def draw(self, screen, g, F):
        if not DEBUG_ENABLED or g is None:
            return
        if self.asking:
            r = pygame.Rect(WIN_W // 2 - 190, MAP_H // 2 - 70, 380, 140)
            panel(screen, r, (200, 60, 60))
            draw_text(screen, F["normal_b"], "DEBUG — введите пароль", RED, r.centerx, r.y + 12, "c")
            draw_text(screen, F["big"], "*" * len(self.buf), TEXT, r.centerx, r.y + 50, "c")
            draw_text(screen, F["small"], self.msg or "Enter — ок   •   Esc — отмена",
                      RED if self.msg else GRAY, r.centerx, r.y + 104, "c")
            return
        if not self.visible:           # панель закрыта, но читы включены — напоминаем
            tags = [n for n, on in (("GOD", self.god), ("NOCLIP", self.noclip)) if on]
            if tags:
                draw_text(screen, F["small"], "DEBUG: " + " ".join(tags), RED, 10, 118)
            return
        w = 330
        r = pygame.Rect(10, 120, w, 40 + 26 * len(self.actions) + 28)
        panel(screen, r, (200, 60, 60), 225)
        draw_text(screen, F["normal_b"], "DEBUG PANEL", RED, r.x + 10, r.y + 6)
        self.rects = []
        for i, (key, name, fn, state) in enumerate(self.actions):
            row = pygame.Rect(r.x + 8, r.y + 36 + i * 26, w - 16, 24)
            self.rects.append(row)
            pygame.draw.rect(screen, (45, 30, 40), row)
            draw_text(screen, F["small"], key, GOLD, row.x + 6, row.y + 3, shadow=False)
            draw_text(screen, F["small"], name, TEXT, row.x + 28, row.y + 3, shadow=False)
            if state:
                on = state()
                draw_text(screen, F["small"], "ВКЛ" if on else "выкл", GREEN if on else GRAY,
                          row.right - 6, row.y + 3, "r", shadow=False)
        draw_text(screen, F["small"], "J — закрыть панель", GRAY, r.x + 10, r.bottom - 22, shadow=False)


DBG = DebugPanel()

if DEBUG_ENABLED:
    # --- God mode: оборачиваем получение урона (яд, огонь, ловушки тоже проходят через него)
    _orig_hurt_player = Game.hurt_player

    def _dbg_hurt_player(self, dmg, src, pierce=False):
        if DBG.god:
            return 0
        return _orig_hurt_player(self, dmg, src, pierce)

    Game.hurt_player = _dbg_hurt_player

    # --- Проход сквозь стены: если впереди стена, просто шагаем в неё (границу карты не пересекаем)
    _orig_try_move = Game.try_move

    def _dbg_try_move(self, dx, dy):
        if DBG.noclip and not self.over and not self.ui and not self.cut:
            nx, ny = self.px + dx, self.py + dy
            if 1 <= nx < COLS - 1 and 1 <= ny < ROWS - 1 and self.grid[ny][nx] == 1:
                if dx:
                    self.facing = dx
                self.px, self.py = nx, ny
                self.end_turn()
                return
        _orig_try_move(self, dx, dy)

    Game.try_move = _dbg_try_move

    # --- Автоподключение к игре (чтобы не править main()) ---
    DBG.game = None
    DBG.last_hud = -10 ** 9

    def _dbg_mpos(p):
        """Координаты мыши окна -> координаты игры (учёт масштаба и чёрных полос)."""
        ww, wh = pygame.display.get_surface().get_size()
        k = max(0.1, min(ww / WIN_W, wh / WIN_H))
        sw, sh = int(WIN_W * k), int(WIN_H * k)
        return int((p[0] - (ww - sw) // 2) / k), int((p[1] - (wh - sh) // 2) / k)

    # draw_hud вызывается каждый кадр только во время игры: запоминаем игру и рисуем панель поверх
    _orig_draw_hud = draw_hud

    def draw_hud(screen, g, A, F):
        _orig_draw_hud(screen, g, A, F)
        DBG.game = g
        DBG.last_hud = pygame.time.get_ticks()
        DBG.draw(screen, g, F)

    # перехватываем события: если панель их «съела», игра их не увидит
    _orig_event_get = pygame.event.get

    def _dbg_event_get(*a, **k):
        evs = _orig_event_get(*a, **k)
        g = DBG.game
        if g is None or pygame.time.get_ticks() - DBG.last_hud > 400:   # не в режиме игры
            return evs
        return [e for e in evs if not DBG.handle_event(e, g, _dbg_mpos)]

    pygame.event.get = _dbg_event_get
    print("[DEBUG] чит-панель загружена: в игре нажми " + DEBUG_KEY + ", пароль " + DEBUG_PASSWORD)
# ===== [DEBUG-END] ==========================================================================

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

    save_info = load_save_file()             # есть ли сохранённый забег (кнопка «Продолжить»)
    state, sel, typed, game = "menu", 0, "", None
    state_t0 = pygame.time.get_ticks()
    rects = []
    hov = [0.0] * 8
    held = {}                # зажатые клавиши движения: scancode -> (dx, dy)
    buffered = [None, 0]     # «запомненное» нажатие, чтобы короткие тапы не терялись
    fade, fade_dir, pending = 0.0, 0, None
    dt = 16
    last_save_turn = 0

    def items_now():
        return menu_items(sfx, save_info)

    def save_now():
        if state == "play" and game is not None and not game.over:
            game.autosave()

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
        nonlocal game, last_save_turn
        pygame.key.set_repeat()
        held.clear()
        buffered[0] = None
        game = Game(typed.strip().capitalize() or "Безымянный Герой", sfx, rec)
        last_save_turn = 0

    def setup_continue():
        nonlocal game, save_info, last_save_turn
        held.clear()
        buffered[0] = None
        try:
            game = Game(save_info["name"], sfx, rec, data=save_info)
        except Exception:                      # повреждённое сохранение — начинаем заново
            delete_save()
            save_info = None
            game = Game("Безымянный Герой", sfx, rec)
        last_save_turn = game.turn

    def setup_restart():
        nonlocal game, last_save_turn
        held.clear()
        buffered[0] = None
        game = Game(game.name, sfx, rec)
        last_save_turn = 0

    def setup_menu():
        nonlocal save_info, sel
        save_now()                             # выход из забега в меню сохраняет игру
        save_info = load_save_file()
        sel = 0
        held.clear()

    def activate(i):
        nonlocal sel
        its = items_now()
        if i >= len(its):
            return
        mid = its[i][0]
        sfx.play("ui")
        if mid == "continue":
            go("play", setup_continue)
        elif mid == "new":
            go("name", setup_name)
        elif mid == "help":
            go("help")
        elif mid == "records":
            go("records")
        elif mid == "credits":
            go("credits")
        elif mid == "sound":
            sfx.on = not sfx.on
        else:
            pygame.quit()
            sys.exit()

    def quit_game():
        save_now()                             # закрыли окно — забег сохранён
        pygame.quit()
        sys.exit()

    while True:
        _, vk, vox, voy, _, _ = view_info()
        now = pygame.time.get_ticks()
        age = now - state_t0
        n_items = len(items_now())
        sel = min(sel, n_items - 1)

        def mpos(p):
            return int((p[0] - vox) / vk), int((p[1] - voy) / vk)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                quit_game()
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
                        sel = (sel - 1) % n_items
                        sfx.play("ui")
                    elif ev.key in (pygame.K_DOWN, pygame.K_s) or ev.scancode == ks("S"):
                        sel = (sel + 1) % n_items
                        sfx.play("ui")
                    elif ev.key in ENTER or ev.key == pygame.K_SPACE:
                        activate(sel)
                    elif ev.key == pygame.K_ESCAPE:
                        quit_game()
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
                    go("menu", setup_menu)
                continue
            if game.cut:                           # катсцену можно пропустить
                if ev.key in ENTER or ev.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                    game.skip_cut()
                continue
            if game.ui:
                game.ui.key(ev)
                continue
            if game.over:
                if ev.key == pygame.K_r or ev.scancode == SC_R:
                    go(None, setup_restart)
                elif ev.key in ENTER or ev.key == pygame.K_ESCAPE:
                    go("menu", setup_menu)
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
            if game.ui or game.over or game.paused or game.cut:
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
            if not game.over and game.turn - last_save_turn >= 20:      # автосохранение каждые 20 ходов
                game.autosave()
                last_save_turn = game.turn

        # ---- какая музыка должна играть
        if state in ("menu", "name", "help", "records", "credits"):
            music.play("menu")
        elif game is None or game.over:
            music.play(None)
        elif any(is_boss(m) and m.awake for m in game.mobs):
            music.play("boss")                       # бой с боссом
        else:
            music.play(None)
        music.update(dt)

        # ---- отрисовка
        if state == "menu":
            rects = draw_menu(screen, A, F, bg, fx, sel, sfx, rec, age, hov, items_now())
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
                draw_text(screen, F["normal"], "Esc — продолжить   •   Enter — в меню (игра сохранится)",
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
