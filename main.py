from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math

app = Ursina()

# ═══════════════════════════════════════════════════════════════════════════════
# APP STATE  —  'home' | 'settings' | 'playing'
# ═══════════════════════════════════════════════════════════════════════════════
app_state = 'home'

# ── Kosakata IT ───────────────────────────────────────────────────────────────
IT_WORDS_EASY   = ['DATA', 'CODE', 'RAM', 'BOOLEAN', 'SHELL', 'PING', 'LINK']
IT_WORDS_MEDIUM = ['PYTHON', 'SERVER', 'ROUTER', 'MATRIX', 'COOKIE', 'BACKEND']
IT_WORDS_HARD   = ['COMPILER', 'DATABASE', 'ALGORITHM', 'FIREWALL', 'ENCRYPTION']

# ── FIX 2: Kamus arti kata untuk feedback edukasi ─────────────────────────────
WORD_DEFINITIONS = {
    # Easy
    'DATA'       : 'Fakta/angka mentah yang belum diolah',
    'CODE'       : 'Instruksi tertulis yang dijalankan komputer',
    'RAM'        : 'Singkatan: Random-access / Read-in Memory',
    'BOOLEAN'    : 'Output valid dari suatu operasi logika',
    'SHELL'      : 'Prompt interaktif di command-line shell',
    'PING'       : 'Uji latensi jaringan ke host tujuan',
    'LINK'       : 'Tautan atau referensi ke sumber daya lain',
    # Medium
    'PYTHON'     : 'Bahasa pemrograman tingkat tinggi, populer di AI',
    'SERVER'     : 'Komputer yang menyediakan layanan ke klien',
    'ROUTER'     : 'Perangkat yang meneruskan paket antar jaringan',
    'MATRIX'     : 'Susunan data dalam baris dan kolom (array 2D)',
    'COOKIE'     : 'Data kecil yang disimpan browser dari server',
    'BACKEND'    : 'Sisi server: logika, DB, API — tidak terlihat user',
    # Hard
    'COMPILER'   : 'Program yang mengubah kode sumber ke kode mesin',
    'DATABASE'   : 'Kumpulan data terstruktur yang bisa diquery',
    'ALGORITHM'  : 'Langkah logis untuk menyelesaikan suatu masalah',
    'FIREWALL'   : 'Sistem keamanan yang menyaring lalu lintas jaringan',
    'ENCRYPTION' : 'Proses mengacak data agar hanya pihak berwenang bisa membaca',
}

# ── Paragraf Boss (dipecah menjadi list kata) ─────────────────────────────────
BOSS_PARAGRAPHS = [
    "KOMPUTER ADALAH MESIN YANG DAPAT DIPROGRAM UNTUK MEMPROSES DATA SECARA OTOMATIS",
    "JARINGAN KOMPUTER ADALAH SEKUMPULAN PERANGKAT YANG TERHUBUNG UNTUK BERBAGI INFORMASI DAN SUMBER DAYA",
    "ALGORITMA ADALAH LANGKAH LANGKAH LOGIS DAN SISTEMATIS YANG DIGUNAKAN UNTUK MENYELESAIKAN SUATU MASALAH KOMPUTASI",
    "KEAMANAN SIBER BERTUJUAN MELINDUNGI SISTEM JARINGAN DAN PROGRAM DARI SERANGAN DIGITAL YANG MERUSAK DATA",
]

# ── Game State ────────────────────────────────────────────────────────────────
current_wave        = 1
enemies_list        = []
active_target       = None
current_input_index = 0
player_hp           = 3
game_over           = False

# Boss state
is_boss_wave        = False
boss_entity         = None
boss_words          = []
boss_word_index     = 0
boss_letter_index   = 0
boss_total_words    = 0

_lock_requested     = False

# ── Audio State ───────────────────────────────────────────────────────────────
vol_musik = 0.5
vol_sfx   = 0.7

bg_music = Audio('musik.mp3', loop=True, autoplay=False, volume=vol_musik)

# ── FIX 5: Audio SFX — akan dipakai di shoot_bullet ──────────────────────────
# Buat satu objek Audio per SFX, putar ulang tiap tembakan
def play_sfx_shoot():
    """Putar SFX tembakan dengan volume vol_sfx saat ini."""
    sfx = Audio('tembak.mp3', loop=False, autoplay=True, volume=vol_sfx)
    destroy(sfx, delay=2.0)   # bersihkan entity setelah selesai

# ── Lingkungan ────────────────────────────────────────────────────────────────
ground = Entity(
    model='plane', scale=(100, 1, 100),
    color=color.dark_gray, texture='white_cube', collider='box'
)

# ── Player ────────────────────────────────────────────────────────────────────
player = FirstPersonController()
player.position          = (0, 2, 0)
player.cursor.visible    = True
player.gravity           = 0
player.speed             = 0
player.mouse_sensitivity = Vec2(0, 0)

mouse.locked  = False
mouse.visible = True

Sky()
DirectionalLight(y=10, z=-10, rotation=(45, 30, 0))

# ── UI Dasar ─────────────────────────────────────────────────────────────────
ui_target_box      = Text(text='', position=(0, -0.3),  origin=(0, 0), scale=2.5, background=False, color=color.yellow)
ui_typing_progress = Text(text='', position=(0, -0.05), origin=(0, 0), scale=1.8, color=color.green)
ui_stats           = Text(text=f'HP: {player_hp} | WAVE: {current_wave}', position=(-0.85, 0.45), scale=2, background=True, color=color.cyan)
ui_announcement    = Text(text='', position=(0, 0.1),  origin=(0, 0), scale=4,   background=False, color=color.orange)

ui_target_box.visible      = False
ui_typing_progress.visible = False
ui_stats.visible           = False
ui_announcement.visible    = False

# ── FIX 2: UI Definisi kata ───────────────────────────────────────────────────
ui_word_def = Text(
    text='', position=(0, -0.42), origin=(0, 0),
    scale=1.4, background=True, color=color.lime,
    word_wrap=55
)
ui_word_def.visible = False

def show_word_definition(word):
    """Tampilkan arti kata selama 2.5 detik setelah kata berhasil diketik."""
    definition = WORD_DEFINITIONS.get(word.upper(), '')
    if not definition:
        return
    ui_word_def.text    = f'{word}: {definition}'
    ui_word_def.visible = True
    ui_word_def.color   = color.lime
    invoke(lambda: setattr(ui_word_def, 'visible', False), delay=2.5)

# ── UI Boss ───────────────────────────────────────────────────────────────────
ui_boss_paragraph = Text(
    text='', position=(0, -0.18), origin=(0, 0),
    scale=1.2, background=True, color=color.white,
    word_wrap=60
)
ui_boss_paragraph.visible = False

boss_hp_bar_bg   = Entity(parent=camera.ui, model='quad',
                          color=color.rgba(40, 40, 40, 220),
                          scale=(0.7, 0.035), position=(0, 0.43))
boss_hp_bar_fill = Entity(parent=camera.ui, model='quad',
                          color=color.rgba(220, 30, 30, 255),
                          scale=(0.7, 0.035), position=(0, 0.43))
boss_hp_label    = Text(text='', position=(0, 0.46), origin=(0, 0),
                        scale=1.6, color=color.red)
boss_hp_bar_bg.visible   = False
boss_hp_bar_fill.visible = False
boss_hp_label.visible    = False

# ── Mini-map ──────────────────────────────────────────────────────────────────
minimap_bg     = Entity(parent=camera.ui, model='quad', color=color.black66,
                        scale=(0.25, 0.25), position=(0.7, 0.35))
minimap_player = Entity(parent=minimap_bg, model='circle', color=color.green,
                        scale=(0.05, 0.05), position=(0, 0))
minimap_dots   = {}
minimap_bg.visible = False

# ── Damage Overlay ────────────────────────────────────────────────────────────
damage_overlay = Entity(
    parent=camera.ui, model='quad', texture='darah.png',
    scale=(2, 2), color=color.rgba(255, 255, 255, 0), z=-1
)

_typo_active = False

# ── Senjata ───────────────────────────────────────────────────────────────────
player_weapon = Entity(
    parent=camera.ui, model='quad', texture='Senjata.png',
    scale=(0.4, 0.4), position=(0.4, -0.3), z=-2
)
player_weapon.visible = False

# ── Spawn Constants ───────────────────────────────────────────────────────────
SPAWN_MIN_DIST  = 18
SPAWN_MAX_DIST  = 26
SPAWN_MIN_SEP   = 3.5
SPAWN_MAX_TRIES = 30
GRACE_PERIOD    = 2.5
MAX_ENEMIES     = 15       # FIX 4: batas musuh per wave
wave_grace_active = False

# ═══════════════════════════════════════════════════════════════════════════════
# HOME SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

# FIX 3: home_bg di z=2, elemen teks di z=0 (lebih dekat kamera = nilai z lebih kecil/negatif di Ursina UI)
# Ursina UI: z lebih kecil = lebih depan. bg harus DI BELAKANG teks → z lebih besar.
home_bg = Entity(
    parent=camera.ui, model='quad',
    color=color.rgba(0, 0, 0, 220), scale=(2, 2), z=2   # FIX 3: z=2 (di belakang teks)
)

home_title = Text(
    text='FPS TYPER\nEDUKASI IT',
    parent=camera.ui,
    origin=(0, 0), position=(0, 0.22),
    scale=5, color=color.cyan,
    background=False, z=0   # FIX 3: z=0 (di depan bg)
)

home_subtitle = Text(
    text='Ketik kata untuk mengalahkan musuh',
    parent=camera.ui,
    origin=(0, 0), position=(0, 0.08),
    scale=1.8, color=color.light_gray, z=0   # FIX 3
)

class MenuButton(Button):
    def __init__(self, label, pos, action):
        super().__init__(
            parent=camera.ui,
            text=label,
            position=pos,
            scale=(0.30, 0.072),
            z=0
        )
        # Set warna setelah init agar tidak di-override default Ursina
        self.color           = color.rgba(15, 15, 15, 230)
        self.highlight_color = color.rgba(0, 190, 230, 220)
        self.pressed_color   = color.rgba(0, 130, 170, 255)
        self.text_entity.color = color.cyan
        self.on_click = action

btn_mulai    = MenuButton('MULAI GAME', (0, -0.08), lambda: start_game())
btn_settings = MenuButton('SETTING',    (0, -0.20), lambda: open_settings())
btn_keluar   = MenuButton('KELUAR',     (0, -0.32), application.quit)

home_elements = [home_bg, home_title, home_subtitle, btn_mulai, btn_settings, btn_keluar]

# ═══════════════════════════════════════════════════════════════════════════════
# FIX 1: GAME OVER SCREEN — tombol Main Lagi & Kembali ke Menu
# ═══════════════════════════════════════════════════════════════════════════════

gameover_bg = Entity(
    parent=camera.ui, model='quad',
    color=color.rgba(0, 0, 0, 200), scale=(2, 2), z=1
)
gameover_bg.visible = False

gameover_title = Text(
    text='GAME OVER', parent=camera.ui,
    origin=(0, 0), position=(0, 0.18),
    scale=6, color=color.red, z=0
)
gameover_title.visible = False

gameover_score = Text(
    text='', parent=camera.ui,
    origin=(0, 0), position=(0, 0.04),
    scale=2.2, color=color.white, z=0
)
gameover_score.visible = False

btn_main_lagi = MenuButton('MAIN LAGI',       (0, -0.10), lambda: restart_game())
btn_ke_menu   = MenuButton('KEMBALI KE MENU', (0, -0.22), lambda: back_to_menu())
btn_main_lagi.visible = False
btn_ke_menu.visible   = False

gameover_elements = [gameover_bg, gameover_title, gameover_score, btn_main_lagi, btn_ke_menu]


def show_gameover_screen():
    """Tampilkan layar Game Over dengan skor wave terakhir."""
    global app_state
    app_state = 'gameover'
    mouse.locked  = False
    mouse.visible = True
    _set_game_ui_visible(False)
    hide_boss_ui()
    ui_word_def.visible = False
    gameover_score.text = f'Kamu bertahan sampai WAVE {current_wave}'
    for e in gameover_elements:
        e.visible = True


def restart_game():
    """Reset semua variabel dan mulai ulang dari wave 1."""
    global current_wave, enemies_list, active_target, current_input_index
    global player_hp, game_over, is_boss_wave, boss_entity
    global boss_words, boss_word_index, boss_letter_index, boss_total_words
    global _lock_requested, wave_grace_active, _typo_active

    # Sembunyikan gameover screen
    for e in gameover_elements:
        e.visible = False

    # Reset state
    current_wave        = 1
    enemies_list        = []
    active_target       = None
    current_input_index = 0
    player_hp           = 3
    game_over           = False
    is_boss_wave        = False
    boss_entity         = None
    boss_words          = []
    boss_word_index     = 0
    boss_letter_index   = 0
    boss_total_words    = 0
    _lock_requested     = False
    wave_grace_active   = False
    _typo_active        = False

    # Reset minimap dots — pastikan entity yang tersisa dihapus
    for dot in list(minimap_dots.values()):
        destroy(dot)
    minimap_dots.clear()

    # Reset UI
    ui_stats.text         = f'HP: {player_hp} | WAVE: {current_wave}'
    ui_announcement.text  = ''
    ui_target_box.text    = ''
    ui_typing_progress.text = ''
    ui_target_box.color   = color.yellow
    damage_overlay.color  = color.rgba(255, 255, 255, 0)

    # Mulai bermain
    start_game()


def back_to_menu():
    """Kembali ke home screen dari gameover."""
    global current_wave, enemies_list, active_target, current_input_index
    global player_hp, game_over, is_boss_wave, boss_entity
    global boss_words, boss_word_index, boss_letter_index, boss_total_words
    global _lock_requested, wave_grace_active, _typo_active

    for e in gameover_elements:
        e.visible = False

    # Bersihkan sisa musuh
    for en in list(enemies_list):
        remove_enemy_completely(en)
    enemies_list.clear()
    for dot in list(minimap_dots.values()):
        destroy(dot)
    minimap_dots.clear()
    if boss_entity:
        remove_enemy_completely(boss_entity)

    # Reset state
    current_wave        = 1
    active_target       = None
    current_input_index = 0
    player_hp           = 3
    game_over           = False
    is_boss_wave        = False
    boss_entity         = None
    boss_words          = []
    boss_word_index     = 0
    boss_letter_index   = 0
    boss_total_words    = 0
    _lock_requested     = False
    wave_grace_active   = False
    _typo_active        = False

    _set_game_ui_visible(False)
    hide_boss_ui()
    ui_word_def.visible = False
    damage_overlay.color = color.rgba(255, 255, 255, 0)

    _set_home_visible(True)
    global app_state
    app_state = 'home'
    mouse.locked  = False
    mouse.visible = True
    bg_music.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

settings_bg = Entity(
    parent=camera.ui, model='quad',
    color=color.rgba(0, 0, 0, 230), scale=(2, 2), z=1
)
settings_bg.visible = False

settings_title = Text(
    text='SETTING', parent=camera.ui,
    origin=(0, 0), position=(0, 0.3),
    scale=4, color=color.cyan, z=0
)
settings_title.visible = False

class VolumeSlider(Entity):
    def __init__(self, label_text, pos, initial_value, on_change):
        super().__init__(parent=camera.ui, position=pos, z=0)
        self.on_change    = on_change
        self.value        = initial_value
        self.dragging     = False
        self.track_width  = 0.35

        self.lbl = Text(
            text=label_text, parent=camera.ui,
            position=(pos[0] - 0.22, pos[1] + 0.005),
            origin=(1, 0), scale=2, color=color.white, z=0
        )
        self.track = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(80, 80, 80, 200),
            scale=(self.track_width, 0.018),
            position=pos, z=0
        )
        self.fill = Entity(
            parent=camera.ui, model='quad',
            color=color.cyan,
            scale=(self.track_width * initial_value, 0.018),
            position=(pos[0] - self.track_width/2 * (1 - initial_value), pos[1]),
            z=0
        )
        self.handle = Entity(
            parent=camera.ui, model='circle',
            color=color.white,
            scale=(0.022, 0.022),
            position=(pos[0] - self.track_width/2 + self.track_width * initial_value, pos[1]),
            z=0
        )
        self.pct_label = Text(
            text=f'{int(initial_value*100)}%',
            parent=camera.ui,
            position=(pos[0] + self.track_width/2 + 0.04, pos[1] + 0.005),
            origin=(0, 0), scale=1.8, color=color.white, z=0
        )
        self._base_x = pos[0]

    def set_visible(self, v):
        self.lbl.visible       = v
        self.track.visible     = v
        self.fill.visible      = v
        self.handle.visible    = v
        self.pct_label.visible = v

    def update_from_mouse(self):
        left  = self._base_x - self.track_width / 2
        raw   = (mouse.x - left) / self.track_width
        self.value = clamp(raw, 0.0, 1.0)
        self._refresh()
        self.on_change(self.value)

    def _refresh(self):
        v = self.value
        self.fill.scale_x   = self.track_width * v
        self.fill.x         = self._base_x - self.track_width/2 * (1 - v)
        self.handle.x       = self._base_x - self.track_width/2 + self.track_width * v
        self.pct_label.text = f'{int(v*100)}%'

    def input(self, key):
        if not self.track.visible:
            return
        if key == 'left mouse down':
            hx = self.handle.x
            hy = self.handle.y
            if abs(mouse.x - hx) < 0.04 and abs(mouse.y - hy) < 0.04:
                self.dragging = True
        if key == 'left mouse up':
            self.dragging = False

    def update(self):
        if self.dragging and self.track.visible:
            self.update_from_mouse()


def _set_vol_musik(v):
    global vol_musik
    vol_musik = v
    bg_music.volume = v

def _set_vol_sfx(v):
    global vol_sfx
    vol_sfx = v   # FIX 5: nilai ini sekarang dipakai di play_sfx_shoot()

slider_musik = VolumeSlider('MUSIK',  (0.08, 0.1),  vol_musik, _set_vol_musik)
slider_sfx   = VolumeSlider('SFX',   (0.08, 0.0),  vol_sfx,   _set_vol_sfx)
slider_musik.set_visible(False)
slider_sfx.set_visible(False)

btn_back = MenuButton('KEMBALI', (0, -0.18), lambda: close_settings())
btn_back.visible = False

settings_elements = [settings_bg, settings_title, btn_back]

# ═══════════════════════════════════════════════════════════════════════════════
# TRANSISI STATE
# ═══════════════════════════════════════════════════════════════════════════════

def _set_home_visible(v):
    for e in home_elements:
        e.visible = v

def _set_settings_visible(v):
    for e in settings_elements:
        e.visible = v
    slider_musik.set_visible(v)
    slider_sfx.set_visible(v)

def _set_game_ui_visible(v):
    ui_target_box.visible      = v
    ui_typing_progress.visible = v
    ui_stats.visible           = v
    ui_announcement.visible    = v
    minimap_bg.visible         = v
    player_weapon.visible      = v


def start_game():
    global app_state
    app_state = 'playing'
    _set_home_visible(False)
    _set_settings_visible(False)
    _set_game_ui_visible(True)
    mouse.locked  = True
    mouse.visible = False
    bg_music.play()
    spawn_wave()


def open_settings():
    global app_state
    app_state = 'settings'
    _set_home_visible(False)
    _set_settings_visible(True)
    mouse.locked  = False
    mouse.visible = True


def close_settings():
    global app_state
    app_state = 'home'
    _set_settings_visible(False)
    _set_home_visible(True)
    mouse.locked  = False
    mouse.visible = True


# ─────────────────────────────────────────────────────────────────────────────
# TYPO INDICATOR
# ─────────────────────────────────────────────────────────────────────────────
def trigger_typo_indicator():
    global _typo_active
    _typo_active = True
    ui_target_box.color = color.red

    def restore_typo():
        global _typo_active
        ui_target_box.color = color.yellow
        _typo_active = False

    invoke(restore_typo, delay=0.4)


def show_typo_on_label(entity_with_label, word, done_count, wrong_letter):
    done  = word[:done_count]
    wrong = wrong_letter
    rest  = word[done_count + 1:]
    entity_with_label.text_label.text = (
        f"<green>{done}</green>"
        f"<red>{wrong}</red>"
        f"{rest}"
    )
    invoke(lambda: update_text_visual(), delay=0.35)


def show_typo_on_boss_label(word, done_count, wrong_letter):
    done  = word[:done_count]
    wrong = wrong_letter
    rest  = word[done_count + 1:]
    if boss_entity and boss_entity.alive:
        boss_entity.text_label.text = (
            f"<green>{done}</green>"
            f"<red>{wrong}</red>"
            f"{rest}"
        )
        invoke(lambda: update_boss_ui(), delay=0.35)

# ─────────────────────────────────────────────────────────────────────────────
# SPAWN HELPER
# ─────────────────────────────────────────────────────────────────────────────
def find_safe_spawn_position():
    for _ in range(SPAWN_MAX_TRIES):
        angle     = random.uniform(0, 2 * math.pi)
        dist_val  = random.uniform(SPAWN_MIN_DIST, SPAWN_MAX_DIST)
        cx        = player.x + math.sin(angle) * dist_val
        cz        = player.z + math.cos(angle) * dist_val
        candidate = Vec3(cx, 2, cz)

        if distance_2d(candidate, player.position) < SPAWN_MIN_DIST:
            continue

        too_close = any(
            distance_2d(candidate, e.position) < SPAWN_MIN_SEP
            for e in enemies_list
        )
        if not too_close:
            return candidate

    angle = random.uniform(0, 2 * math.pi)
    return Vec3(
        player.x + math.sin(angle) * SPAWN_MAX_DIST,
        2,
        player.z + math.cos(angle) * SPAWN_MAX_DIST
    )

# ─────────────────────────────────────────────────────────────────────────────
# ENEMY (Normal)
# ─────────────────────────────────────────────────────────────────────────────
class Enemy(Entity):
    def __init__(self, word):
        spawn_pos = find_safe_spawn_position()
        super().__init__(
            model='quad', texture='zombie.png',
            position=spawn_pos, scale=(2, 2.5), billboard=True
        )
        self.word     = word
        self.speed    = random.uniform(0.4, 0.7) + (current_wave * 0.05)
        self.alive    = True
        self.can_move = False

        self.text_label = Text(
            text=self.word, parent=self, position=(0, 0.6, 0),
            scale=3, origin=(0, 0), background=True,
            color=color.white, billboard=True
        )
        minimap_dots[self] = Entity(
            parent=minimap_bg, model='circle', color=color.red, scale=(0.04, 0.04)
        )

    def update(self):
        if game_over or not self.alive or not self.can_move:
            return

        target_pos = Vec3(player.x, self.y, player.z)
        self.look_at_2d(target_pos, 'y')
        self.position += self.forward * self.speed * time.dt

        rel_x = clamp(self.x * 0.02, -0.45, 0.45)
        rel_z = clamp(self.z * 0.02, -0.45, 0.45)
        if self in minimap_dots:
            minimap_dots[self].position = (rel_x, rel_z)

        if distance_2d(self.position, player.position) < 1.5:
            reduce_player_hp()
            remove_enemy_completely(self)
            global active_target
            if active_target == self:
                reset_targeting()
            check_wave_clear()

# ─────────────────────────────────────────────────────────────────────────────
# BOSS ENTITY
# ─────────────────────────────────────────────────────────────────────────────
class Boss(Entity):
    def __init__(self, paragraph_str):
        spawn_pos = find_safe_spawn_position()
        super().__init__(
            model='quad', texture='pokeball.png',
            position=spawn_pos, scale=(4, 5), billboard=True,
            color=color.rgba(255, 60, 60, 255)
        )
        self.alive    = True
        self.can_move = False
        self.speed    = 0.15

        self.words       = paragraph_str.upper().split()
        self.total_words = len(self.words)

        self.text_label = Text(
            text='BOSS', parent=self, position=(0, 0.75, 0),
            scale=2.5, origin=(0, 0), background=True,
            color=color.red, billboard=True
        )
        minimap_dots[self] = Entity(
            parent=minimap_bg, model='circle', color=color.magenta, scale=(0.07, 0.07)
        )

    def update(self):
        if game_over or not self.alive or not self.can_move:
            return

        target_pos = Vec3(player.x, self.y, player.z)
        self.look_at_2d(target_pos, 'y')
        self.position += self.forward * self.speed * time.dt

        rel_x = clamp(self.x * 0.02, -0.45, 0.45)
        rel_z = clamp(self.z * 0.02, -0.45, 0.45)
        if self in minimap_dots:
            minimap_dots[self].position = (rel_x, rel_z)

        if distance_2d(self.position, player.position) < 1.5:
            reduce_player_hp()
            self.position = find_safe_spawn_position()

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def remove_enemy_completely(enemy_obj):
    if not enemy_obj.alive:
        return
    enemy_obj.alive = False
    if enemy_obj in enemies_list:
        enemies_list.remove(enemy_obj)
    if enemy_obj in minimap_dots:
        destroy(minimap_dots[enemy_obj])
        del minimap_dots[enemy_obj]
    destroy(enemy_obj)


def reduce_player_hp():
    global player_hp, game_over
    if game_over:
        return
    player_hp -= 1
    ui_stats.text = f'HP: {player_hp} | WAVE: {current_wave}'

    damage_overlay.color = color.rgba(255, 255, 255, 200)
    damage_overlay.animate_color(color.rgba(255, 255, 255, 0), duration=0.6)

    player_weapon.y = -0.35
    player_weapon.animate_y(-0.3, duration=0.2)

    if player_hp <= 0:
        game_over = True
        # FIX 1: tampilkan layar Game Over, bukan hanya teks
        invoke(show_gameover_screen, delay=0.5)


def shoot_bullet(target_entity):
    if not target_entity or not target_entity.alive:
        return
    frozen_target_pos = Vec3(target_entity.position) + Vec3(0, 0.5, 0)

    # FIX 5: putar SFX tembakan
    play_sfx_shoot()

    player_weapon.texture = 'efeksenjata.png'
    invoke(setattr, player_weapon, 'texture', 'Senjata.png', delay=0.08)
    player_weapon.x = 0.38
    player_weapon.y = -0.35
    player_weapon.animate_x(0.4, duration=0.05)
    player_weapon.animate_y(-0.3, duration=0.05)

    spawn_pos   = player.position + Vec3(0, 1.2, 0) + player.forward * 1.5
    bullet      = Entity(model='quad', texture='peluru.png', position=spawn_pos,
                         scale=(0.3, 0.3), billboard=True, color=color.white)
    dist        = distance(spawn_pos, frozen_target_pos)
    travel_time = dist / 60.0
    bullet.animate_position(frozen_target_pos, duration=travel_time, curve=curve.linear)
    destroy(bullet, delay=travel_time)

# ─────────────────────────────────────────────────────────────────────────────
# BOSS UI
# ─────────────────────────────────────────────────────────────────────────────
def show_boss_ui():
    boss_hp_bar_bg.visible    = True
    boss_hp_bar_fill.visible  = True
    boss_hp_label.visible     = True
    ui_boss_paragraph.visible = True
    ui_target_box.position    = (0, 0.35)
    ui_typing_progress.position = (0, 0.28)
    update_boss_ui()


def hide_boss_ui():
    boss_hp_bar_bg.visible    = False
    boss_hp_bar_fill.visible  = False
    boss_hp_label.visible     = False
    ui_boss_paragraph.visible = False
    ui_target_box.position    = (0, -0.3)
    ui_typing_progress.position = (0, -0.05)
    ui_target_box.text        = ''
    ui_typing_progress.text   = ''


def update_boss_ui():
    global boss_entity, boss_words, boss_word_index, boss_letter_index

    if not boss_entity or not boss_entity.alive:
        return

    total  = boss_entity.total_words
    done_n = boss_word_index
    ratio  = (total - done_n) / total if total > 0 else 0

    bar_full   = 0.7
    fill_w     = bar_full * ratio
    fill_x     = -bar_full / 2 + fill_w / 2
    boss_hp_bar_fill.scale_x = fill_w
    boss_hp_bar_fill.x       = fill_x

    boss_hp_label.text = f'BOSS HP: {total - done_n}/{total} KATA'

    parts = []
    for i, w in enumerate(boss_words):
        if i < boss_word_index:
            parts.append(f"<green>{w}</green>")
        elif i == boss_word_index:
            done_letters   = w[:boss_letter_index]
            remain_letters = w[boss_letter_index:]
            next_ch  = f"<yellow>{remain_letters[0]}</yellow>" if remain_letters else ''
            rest     = remain_letters[1:] if len(remain_letters) > 1 else ''
            parts.append(f"<green>{done_letters}</green>{next_ch}{rest}")
        else:
            parts.append(w)
    ui_boss_paragraph.text = ' '.join(parts)

    current_word = boss_words[boss_word_index] if boss_word_index < len(boss_words) else ''
    ui_target_box.text      = f'BOSS WORD: {current_word}'
    ui_typing_progress.text = current_word[:boss_letter_index]

# ─────────────────────────────────────────────────────────────────────────────
# TARGETING (Normal Enemy)
# ─────────────────────────────────────────────────────────────────────────────
def auto_lock_nearest_enemy():
    global active_target, current_input_index, _lock_requested
    _lock_requested = False
    if enemies_list and not game_over and not is_boss_wave:
        active_target       = min(enemies_list, key=lambda e: distance_2d(e.position, player.position))
        current_input_index = 0
        update_text_visual()
    else:
        active_target = None


def request_lock():
    global _lock_requested
    if not _lock_requested and not is_boss_wave:
        _lock_requested = True
        invoke(auto_lock_nearest_enemy, delay=0)


def reset_targeting():
    global active_target, current_input_index
    if active_target and active_target in enemies_list:
        active_target.text_label.text = active_target.word
    active_target       = None
    current_input_index = 0
    ui_target_box.text       = ''
    ui_typing_progress.text  = ''

# ─────────────────────────────────────────────────────────────────────────────
# MAIN UPDATE
# ─────────────────────────────────────────────────────────────────────────────
def update():
    global boss_entity

    if app_state not in ('playing',):
        return

    if game_over:
        return

    player_weapon.y = -0.3 + (math.sin(time.time() * 2) * 0.01)

    if is_boss_wave:
        if boss_entity and boss_entity.alive:
            target_dir   = boss_entity.position - player.position
            target_angle = math.degrees(math.atan2(target_dir.x, target_dir.z))
            current_y    = player.rotation_y
            delta        = (target_angle - current_y + 180) % 360 - 180
            player.rotation_y += delta * min(time.dt * 6, 1.0)
        return

    if active_target is None or (active_target not in enemies_list):
        request_lock()

    if active_target and active_target in enemies_list:
        target_dir   = active_target.position - player.position
        target_angle = math.degrees(math.atan2(target_dir.x, target_dir.z))
        current_y    = player.rotation_y
        delta        = (target_angle - current_y + 180) % 360 - 180
        player.rotation_y += delta * min(time.dt * 8, 1.0)

# ─────────────────────────────────────────────────────────────────────────────
# INPUT
# ─────────────────────────────────────────────────────────────────────────────
def input(key):
    global active_target, current_input_index
    global boss_word_index, boss_letter_index, boss_entity

    if app_state != 'playing':
        return

    if game_over:
        return

    # ── INPUT BOSS WAVE ────────────────────────────────────────────────────
    if is_boss_wave and boss_entity and boss_entity.alive:
        current_word = boss_words[boss_word_index]

        if key == 'space':
            if boss_letter_index == len(current_word):
                shoot_bullet(boss_entity)
                boss_word_index  += 1
                boss_letter_index = 0

                if boss_word_index >= boss_total_words:
                    defeat_boss()
                else:
                    update_boss_ui()
            else:
                trigger_typo_indicator()
            return

        if len(key) != 1:
            return

        if boss_letter_index >= len(current_word):
            ui_target_box.color = color.cyan
            invoke(lambda: setattr(ui_target_box, 'color', color.yellow), delay=0.3)
            return

        pressed  = key.upper()
        expected = current_word[boss_letter_index]

        if pressed == expected:
            boss_letter_index += 1
            shoot_bullet(boss_entity)
            update_boss_ui()
        else:
            show_typo_on_boss_label(current_word, boss_letter_index, expected)
            boss_letter_index = 0
            trigger_typo_indicator()
        return

    # ── INPUT NORMAL WAVE ──────────────────────────────────────────────────
    if key == 'space' or len(key) != 1:
        return

    pressed_letter = key.upper()

    if active_target and active_target in enemies_list and active_target.alive:
        target_word = active_target.word

        if pressed_letter == target_word[current_input_index]:
            current_input_index += 1
            update_text_visual()
            shoot_bullet(active_target)

            if current_input_index == len(target_word):
                finished_word = active_target.word   # simpan sebelum destroy
                finished      = active_target
                active_target = None
                remove_enemy_completely(finished)
                # FIX 2: tampilkan definisi kata yang baru saja diketik
                show_word_definition(finished_word)
                check_wave_clear()
        else:
            wrong_char = target_word[current_input_index]
            show_typo_on_label(active_target, target_word, current_input_index, wrong_char)
            current_input_index = 0
            trigger_typo_indicator()


def update_text_visual():
    if active_target and active_target.alive:
        done   = active_target.word[:current_input_index]
        remain = active_target.word[current_input_index:]
        if not _typo_active:
            active_target.text_label.text = f"<green>{done}</green>{remain}"
        ui_target_box.text      = f"TARGET: {active_target.word}"
        ui_typing_progress.text = done

# ─────────────────────────────────────────────────────────────────────────────
# BOSS LOGIC
# ─────────────────────────────────────────────────────────────────────────────
def defeat_boss():
    global boss_entity, is_boss_wave
    if boss_entity:
        remove_enemy_completely(boss_entity)
        boss_entity = None
    is_boss_wave = False
    hide_boss_ui()
    check_wave_clear()


def spawn_boss():
    global boss_entity, boss_words, boss_word_index, boss_letter_index, boss_total_words, wave_grace_active

    wave_grace_active = False

    boss_wave_index = max(0, (current_wave - 3) // 2)
    boss_wave_index = min(boss_wave_index, len(BOSS_PARAGRAPHS) - 1)
    paragraph       = BOSS_PARAGRAPHS[boss_wave_index]

    boss_entity       = Boss(paragraph)
    boss_words        = boss_entity.words
    boss_word_index   = 0
    boss_letter_index = 0
    boss_total_words  = boss_entity.total_words

    ui_announcement.text  = ''
    ui_stats.text         = f'HP: {player_hp} | WAVE: {current_wave} [BOSS]'

    show_boss_ui()

    invoke(lambda: setattr(boss_entity, 'can_move', True), delay=GRACE_PERIOD)

# ─────────────────────────────────────────────────────────────────────────────
# WAVE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
def activate_all_enemies():
    global wave_grace_active
    wave_grace_active = False
    for e in enemies_list:
        if e.alive:
            e.can_move = True
    ui_announcement.text = ''


def spawn_wave():
    global current_wave, game_over, wave_grace_active, is_boss_wave

    if game_over:
        return

    is_boss_wave = (current_wave >= 3 and current_wave % 2 == 1)

    wave_grace_active     = True
    ui_stats.text         = f'HP: {player_hp} | WAVE: {current_wave}'
    ui_announcement.color = color.orange

    if is_boss_wave:
        ui_announcement.text = f'WAVE {current_wave}\nBOSS WAVE!\nBERSIAP...'
        invoke(spawn_boss, delay=GRACE_PERIOD)
    else:
        ui_announcement.text = f'WAVE {current_wave}\nBERSIAP...'
        # FIX 4: batasi jumlah musuh maksimal MAX_ENEMIES
        num_enemies = min(current_wave * 3, MAX_ENEMIES)
        for _ in range(num_enemies):
            if current_wave <= 2:
                word = random.choice(IT_WORDS_EASY)
            elif current_wave == 4:
                word = random.choice(IT_WORDS_EASY + IT_WORDS_MEDIUM)
            else:
                word = random.choice(IT_WORDS_MEDIUM + IT_WORDS_HARD)

            enemy = Enemy(word)
            enemies_list.append(enemy)

        invoke(auto_lock_nearest_enemy, delay=0.1)
        invoke(activate_all_enemies, delay=GRACE_PERIOD)


def check_wave_clear():
    global current_wave
    # FIX 3 (terkait): pastikan cek ini tidak jalan saat boss masih hidup
    if is_boss_wave and boss_entity is not None:
        return
    all_dead = (len(enemies_list) == 0)
    if all_dead and not game_over:
        current_wave         += 1
        ui_announcement.text  = "WAVE CLEAR!"
        ui_announcement.color = color.green
        reset_targeting()
        invoke(show_next_wave_ready, delay=2)


def show_next_wave_ready():
    if game_over:
        return
    ui_announcement.text  = f"WAVE {current_wave} STARTING..."
    ui_announcement.color = color.orange
    invoke(spawn_wave, delay=1.5)


# ── Start ─────────────────────────────────────────────────────────────────────
_set_home_visible(True)
app.run()