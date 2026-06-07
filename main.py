from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math

app = Ursina()

# Daftar kata istilah IT
IT_WORDS_EASY   = ['DATA', 'CODE', 'RIM', 'BENAR', 'AYO', 'PING', 'LINK']
IT_WORDS_MEDIUM = ['PYTHON', 'SERVER', 'ROUTER', 'MATRIX', 'COOKIE', 'BACKEND']
IT_WORDS_HARD   = ['COMPILER', 'DATABASE', 'ALGORITHM', 'FIREWALL', 'ENCRYPTION']

# ── Game State ──────────────────────────────────────────────────────────────
current_wave       = 1
enemies_list       = []
active_target      = None
current_input_index = 0
player_hp          = 3
game_over          = False

# FIX BUG 2 — flag agar auto_lock tidak dipanggil berulang dalam satu frame
_lock_requested    = False

# ── Lingkungan ───────────────────────────────────────────────────────────────
ground = Entity(
    model='plane', scale=(100, 1, 100),
    color=color.dark_gray, texture='white_cube', collider='box'
)

# ── Player ───────────────────────────────────────────────────────────────────
player = FirstPersonController()
player.position         = (0, 2, 0)
player.cursor.visible   = True
player.gravity          = 0
player.speed            = 0
player.mouse_sensitivity = Vec2(0, 0)  # Kunci mouse/trackpad

Sky()
DirectionalLight(y=10, z=-10, rotation=(45, 30, 0))

# ── UI ───────────────────────────────────────────────────────────────────────
ui_target_box     = Text(text='', position=(0, -0.3),  origin=(0, 0), scale=2.5, background=True, color=color.yellow)
ui_typing_progress = Text(text='', position=(0, -0.05), origin=(0, 0), scale=1.8, color=color.green)
ui_stats          = Text(text=f'HP: {player_hp} | WAVE: {current_wave}', position=(-0.85, 0.45), scale=2, background=True, color=color.cyan)
ui_announcement   = Text(text='', position=(0, 0.1),  origin=(0, 0), scale=4,   background=True, color=color.orange)

# ── Mini-map ─────────────────────────────────────────────────────────────────
minimap_bg     = Entity(parent=camera.ui, model='quad', color=color.black66, scale=(0.25, 0.25), position=(0.7, 0.35))
minimap_player = Entity(parent=minimap_bg, model='circle', color=color.green, scale=(0.05, 0.05), position=(0, 0))
minimap_dots   = {}

# ── Damage Flash ─────────────────────────────────────────────────────────────
damage_flash = Entity(parent=camera.ui, model='quad', scale=(2, 2), color=color.rgba(255, 0, 0, 0), z=-1)

# ── Senjata Player ───────────────────────────────────────────────────────────
player_weapon = Entity(
    parent=camera.ui, model='quad', texture='Senjata.png',
    scale=(0.4, 0.4), position=(0.4, -0.3), z=-2
)

# ── Spawn Safety Constants ────────────────────────────────────────────────────
SPAWN_MIN_DIST   = 18    # Jarak minimum dari player saat spawn
SPAWN_MAX_DIST   = 26    # Jarak maksimum dari player saat spawn
SPAWN_MIN_SEP    = 3.5   # Jarak minimum antar sesama enemy saat spawn
SPAWN_MAX_TRIES  = 30    # Batas percobaan cari posisi aman (hindari infinite loop)
GRACE_PERIOD     = 2.5   # Detik sebelum enemy mulai bergerak setelah wave spawn

# ── Grace Period State ────────────────────────────────────────────────────────
wave_grace_active = False

def find_safe_spawn_position():
    """
    Cari posisi spawn yang:
    1. Cukup jauh dari player (>= SPAWN_MIN_DIST)
    2. Tidak terlalu dekat dengan enemy lain (>= SPAWN_MIN_SEP)
    Jika tidak ditemukan dalam SPAWN_MAX_TRIES percobaan, paksa posisi minimum safe.
    """
    for _ in range(SPAWN_MAX_TRIES):
        angle        = random.uniform(0, 2 * math.pi)
        dist_val     = random.uniform(SPAWN_MIN_DIST, SPAWN_MAX_DIST)
        candidate_x  = player.x + math.sin(angle) * dist_val
        candidate_z  = player.z + math.cos(angle) * dist_val
        candidate    = Vec3(candidate_x, 2, candidate_z)

        # Cek jarak ke player
        if distance_2d(candidate, player.position) < SPAWN_MIN_DIST:
            continue

        # Cek jarak ke enemy yang sudah ada
        too_close = False
        for existing in enemies_list:
            if distance_2d(candidate, existing.position) < SPAWN_MIN_SEP:
                too_close = True
                break

        if not too_close:
            return candidate

    # Fallback: paksa spawn di titik aman paling jauh jika semua percobaan gagal
    angle = random.uniform(0, 2 * math.pi)
    return Vec3(
        player.x + math.sin(angle) * SPAWN_MAX_DIST,
        2,
        player.z + math.cos(angle) * SPAWN_MAX_DIST
    )


# ============================================================
# Enemy Class
# ============================================================
class Enemy(Entity):
    def __init__(self, word):
        spawn_pos = find_safe_spawn_position()

        super().__init__(
            model='quad',
            texture='musuh.png',
            position=spawn_pos,
            scale=(2, 2.5),
            billboard=True
        )

        self.word        = word
        self.speed       = random.uniform(0.4, 0.7) + (current_wave * 0.05)
        self.alive       = True   # flag eksplisit (anti-destroy race condition)
        self.can_move    = False  # grace period — enemy diam dulu saat baru spawn

        self.text_label = Text(
            text=self.word, parent=self, position=(0, 0.6, 0),
            scale=3, origin=(0, 0), background=True,
            color=color.white, billboard=True
        )

        minimap_dots[self] = Entity(
            parent=minimap_bg, model='circle', color=color.red, scale=(0.04, 0.04)
        )

    def update(self):
        if game_over or not self.alive:
            return

        # Grace period — tunggu sinyal can_move sebelum mulai maju
        if not self.can_move:
            return

        target_pos = Vec3(player.x, self.y, player.z)   # kejar posisi player aktual
        self.look_at_2d(target_pos, 'y')
        self.position += self.forward * self.speed * time.dt

        # Mini-map update
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

# ============================================================
# Helper Functions
# ============================================================
def remove_enemy_completely(enemy_obj):
    """Hapus enemy dengan aman — set flag .alive lebih dulu."""
    if not enemy_obj.alive:
        return                      # FIX BUG 1 — sudah dihancurkan, skip
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

    damage_flash.color = color.rgba(255, 0, 0, 130)
    damage_flash.animate_color(color.rgba(255, 0, 0, 0), duration=0.4)

    player_weapon.y = -0.35
    player_weapon.animate_y(-0.3, duration=0.2)

    if player_hp <= 0:
        game_over = True
        ui_announcement.text  = "GAME OVER"
        ui_announcement.color = color.red
        for e in list(enemies_list):
            remove_enemy_completely(e)


def shoot_bullet(target_enemy):
    """
    FIX BUG 1 — rekam target_pos SEKARANG (bukan pakai referensi entity).
    Dengan ini, animasi peluru tetap valid meski enemy di-destroy lebih cepat.
    """
    if not target_enemy or not target_enemy.alive:
        return

    # Rekam posisi saat ini sebelum enemy mungkin di-destroy
    frozen_target_pos = Vec3(target_enemy.position) + Vec3(0, 0.5, 0)

    # Muzzle flash
    player_weapon.texture = 'efeksenjata.png'
    invoke(setattr, player_weapon, 'texture', 'Senjata.png', delay=0.08)

    # Recoil UI
    player_weapon.x = 0.38
    player_weapon.y = -0.35
    player_weapon.animate_x(0.4, duration=0.05)
    player_weapon.animate_y(-0.3, duration=0.05)

    # Spawn peluru
    spawn_pos = player.position + Vec3(0, 1.2, 0) + player.forward * 1.5

    bullet = Entity(
        model='quad',
        texture='peluru.png',
        position=spawn_pos,
        scale=(0.3, 0.3),
        billboard=True,
        color=color.white
    )

    dist        = distance(spawn_pos, frozen_target_pos)
    travel_time = dist / 60.0   # Peluru makin cepat → naikkan angka ini

    bullet.animate_position(frozen_target_pos, duration=travel_time, curve=curve.linear)
    destroy(bullet, delay=travel_time)


# ============================================================
# Targeting
# ============================================================
def auto_lock_nearest_enemy():
    """
    FIX BUG 2 — fungsi ini hanya boleh dipanggil via request, bukan tiap frame.
    """
    global active_target, current_input_index, _lock_requested
    _lock_requested = False     # reset flag

    if enemies_list and not game_over:
        active_target       = min(enemies_list, key=lambda e: distance_2d(e.position, player.position))
        current_input_index = 0
        update_text_visual()
    else:
        active_target = None


def request_lock():
    """Jadwalkan auto_lock hanya jika belum ada request pending."""
    global _lock_requested
    if not _lock_requested:
        _lock_requested = True
        invoke(auto_lock_nearest_enemy, delay=0)   # jalankan di frame berikutnya


def reset_targeting():
    global active_target, current_input_index
    if active_target and active_target in enemies_list:
        active_target.text_label.text = active_target.word
    active_target       = None
    current_input_index = 0
    ui_target_box.text       = ''
    ui_typing_progress.text  = ''


# ============================================================
# Main Update
# ============================================================
def update():
    if game_over:
        return

    # Idle breathing senjata
    player_weapon.y = -0.3 + (math.sin(time.time() * 2) * 0.01)

    # FIX BUG 2 — gunakan request_lock(), bukan panggil langsung tiap frame
    if active_target is None or (active_target not in enemies_list):
        request_lock()

    # FIX BUG 3 — smooth camera rotation (lerp), bukan snap langsung
    if active_target and active_target in enemies_list:
        target_dir   = active_target.position - player.position
        target_angle = math.degrees(math.atan2(target_dir.x, target_dir.z))
        current_y    = player.rotation_y
        delta        = (target_angle - current_y + 180) % 360 - 180
        player.rotation_y += delta * min(time.dt * 8, 1.0)  # lerp faktor = 8


# ============================================================
# Input
# ============================================================
def input(key):
    global active_target, current_input_index, game_over

    if game_over or len(key) != 1 or key == ' ':
        return

    pressed_letter = key.upper()

    if active_target and active_target in enemies_list and active_target.alive:
        target_word = active_target.word

        if pressed_letter == target_word[current_input_index]:
            current_input_index += 1
            update_text_visual()

            # FIX BUG 1 — tembak SEBELUM cek apakah kata sudah selesai
            shoot_bullet(active_target)

            if current_input_index == len(target_word):
                # Tandai selesai SETELAH peluru dikirim
                finished = active_target
                active_target = None
                remove_enemy_completely(finished)
                check_wave_clear()
        else:
            current_input_index = 0
            update_text_visual()


def update_text_visual():
    if active_target and active_target.alive:
        done   = active_target.word[:current_input_index]
        remain = active_target.word[current_input_index:]
        active_target.text_label.text = f"<span color='#00FF00'>{done}</span>{remain}"
        ui_target_box.text      = f"TARGET: {active_target.word}"
        ui_typing_progress.text = done


# ============================================================
# Wave Management
# ============================================================
def activate_all_enemies():
    """Dipanggil setelah grace period — semua enemy mulai bergerak serentak."""
    global wave_grace_active
    wave_grace_active = False
    for e in enemies_list:
        if e.alive:
            e.can_move = True
    ui_announcement.text = ''


def spawn_wave():
    global current_wave, game_over, wave_grace_active
    if game_over:
        return

    wave_grace_active        = True
    ui_stats.text            = f'HP: {player_hp} | WAVE: {current_wave}'
    ui_announcement.color    = color.orange
    ui_announcement.text     = f'WAVE {current_wave}\nBERSIAP...'

    num_enemies = current_wave * 3
    for _ in range(num_enemies):
        if current_wave == 1:
            word = random.choice(IT_WORDS_EASY)
        elif current_wave == 2:
            word = random.choice(IT_WORDS_EASY + IT_WORDS_MEDIUM)
        else:
            word = random.choice(IT_WORDS_MEDIUM + IT_WORDS_HARD)

        enemy = Enemy(word)          # can_move = False saat spawn
        enemies_list.append(enemy)

    invoke(auto_lock_nearest_enemy, delay=0.1)
    # Setelah GRACE_PERIOD detik, semua enemy mulai bergerak
    invoke(activate_all_enemies, delay=GRACE_PERIOD)


def check_wave_clear():
    global current_wave
    if len(enemies_list) == 0 and not game_over:
        current_wave += 1
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
spawn_wave()
app.run()