from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math

app = Ursina()

# Daftar kata istilah IT
IT_WORDS_EASY = ['DATA', 'CODE', 'RIM', 'BUG', 'WEB', 'PING', 'LINK']
IT_WORDS_MEDIUM = ['PYTHON', 'SERVER', 'ROUTER', 'MATRIX', 'COOKIE', 'BACKEND']
IT_WORDS_HARD = ['COMPILER', 'DATABASE', 'ALGORITHM', 'FIREWALL', 'ENCRYPTION']

# Game State
current_wave = 1
enemies_list = []
active_target = None  
current_input_index = 0  
player_hp = 3
game_over = False

# Lingkungan Dasar
ground = Entity(model='plane', scale=(100, 1, 100), color=color.dark_gray, texture='white_cube', collider='box')

# Player Setup
player = FirstPersonController()
player.position = (0, 2, 0)                  
player.cursor.visible = True 
player.gravity = 0            
player.speed = 0              
player.mouse_sensitivity = Vec2(0, 0) # Kunci trackpad/mouse

Sky()
DirectionalLight(y=10, z=-10, rotation=(45, 30, 0))

# --- UI INDIKATOR ---
ui_target_box = Text(text='', position=(0, -0.3), origin=(0, 0), scale=2.5, background=True, color=color.yellow)
ui_typing_progress = Text(text='', position=(0, -0.05), origin=(0, 0), scale=1.8, color=color.green)

# UI HP & Wave Info
ui_stats = Text(text=f'HP: {player_hp} | WAVE: {current_wave}', position=(-0.85, 0.45), scale=2, background=True, color=color.cyan)

# UI Pemberitahuan Tengah Layar
ui_announcement = Text(text='', position=(0, 0.1), origin=(0, 0), scale=4, background=True, color=color.orange)

# --- UI MINI-MAP 2D ---
minimap_bg = Entity(parent=camera.ui, model='quad', color=color.black66, scale=(0.25, 0.25), position=(0.7, 0.35))
minimap_player = Entity(parent=minimap_bg, model='circle', color=color.green, scale=(0.05, 0.05), position=(0, 0))
minimap_dots = {}

# --- INDIKATOR TERKENA SERANGAN ---
damage_flash = Entity(parent=camera.ui, model='quad', scale=(2, 2), color=color.rgba(255, 0, 0, 0), z=-1)

# --- ASET SENJATA PLAYER ---
# Pastikan nama file gambar sesuai dengan yang ada di folder
player_weapon = Entity(parent=camera.ui, model='quad', texture='Senjata.png', scale=(0.4, 0.4), position=(0.4, -0.3), z=-2)

class Enemy(Entity):
    def __init__(self, word):
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(12, 18)  
        spawn_x = math.sin(angle) * distance
        spawn_z = math.cos(angle) * distance

        super().__init__(
            model='quad',            
            texture='.png',      
            position=(spawn_x, 2, spawn_z), 
            scale=(2, 2.5),          
            billboard=True            
        )
        
        self.word = word
        self.speed = random.uniform(0.4, 0.7) + (current_wave * 0.05)
        
        self.text_label = Text(
            text=self.word, parent=self, position=(0, 0.6, 0), scale=3, origin=(0, 0),
            background=True, color=color.white, billboard=True            
        )
        
        minimap_dots[self] = Entity(parent=minimap_bg, model='circle', color=color.red, scale=(0.04, 0.04))

    def update(self):
        if game_over:
            return
            
        target_pos = Vec3(0, self.y, 0)
        self.look_at_2d(target_pos, 'y')
        self.position += self.forward * self.speed * time.dt
        
        # Update Mini-map
        rel_x = self.x * 0.02
        rel_z = self.z * 0.02
        rel_x = clamp(rel_x, -0.45, 0.45)
        rel_z = clamp(rel_z, -0.45, 0.45)
        minimap_dots[self].position = (rel_x, rel_z)
        
        if distance_2d(self.position, player.position) < 1.5:
            reduce_player_hp()
            remove_enemy_completely(self)
            
            global active_target
            if active_target == self:
                reset_targeting()
                
            check_wave_clear()

def remove_enemy_completely(enemy_obj):
    if enemy_obj in enemies_list:
        enemies_list.remove(enemy_obj)
    if enemy_obj in minimap_dots:
        destroy(minimap_dots[enemy_obj])
        del minimap_dots[enemy_obj]
    destroy(enemy_obj)

def reduce_player_hp():
    global player_hp, game_over
    if game_over: return
    
    player_hp -= 1
    ui_stats.text = f'HP: {player_hp} | WAVE: {current_wave}'
    
    damage_flash.color = color.rgba(255, 0, 0, 130)
    damage_flash.animate_color(color.rgba(255, 0, 0, 0), duration=0.4)
    
    player_weapon.y = -0.35
    player_weapon.animate_y(-0.3, duration=0.2)
    
    if player_hp <= 0:
        game_over = True
        ui_announcement.text = "GAME OVER"
        ui_announcement.color = color.red
        for e in list(enemies_list):
            remove_enemy_completely(e)

# --- FUNGSI BARU: Animasi Senjata & Menembak Peluru ---
def shoot_bullet(target_enemy):
    # 1. Animasi Efek Senjata (Muzzle Flash)
    player_weapon.texture = 'efeksenjata.png'
    # Kembalikan ke senjata biasa setelah 0.08 detik
    invoke(setattr, player_weapon, 'texture', 'Senjata.png', delay=0.08)
    
    # 2. Animasi Recoil UI Senjata
    player_weapon.x = 0.38
    player_weapon.y = -0.35
    player_weapon.animate_x(0.4, duration=0.05)
    player_weapon.animate_y(-0.3, duration=0.05)

    # 3. Membuat Entitas Peluru di Ruang 3D
    # Spawn peluru sedikit di depan pemain
    spawn_pos = player.position + Vec3(0, 1.2, 0) + player.forward * 1.5
    target_pos = target_enemy.position + Vec3(0, 0.5, 0) # Mengarah ke badan musuh
    
    bullet = Entity(
        model='quad',
        texture='peluru.png',
        position=spawn_pos,
        scale=(0.3, 0.3), # Ukuran peluru, sesuaikan jika perlu
        billboard=True,   # Memastikan gambar peluru selalu menghadap kamera
        color=color.white
    )
    
    # 4. Animasikan Perjalanan Peluru
    dist = distance(spawn_pos, target_pos)
    travel_time = dist / 60.0 # Semakin besar angkanya (60.0), peluru semakin cepat
    
    bullet.animate_position(target_pos, duration=travel_time, curve=curve.linear)
    
    # Hancurkan entitas peluru tepat saat menyentuh musuh
    destroy(bullet, delay=travel_time)

def auto_lock_nearest_enemy():
    global active_target, current_input_index
    if enemies_list and not game_over:
        active_target = min(enemies_list, key=lambda e: distance_2d(e.position, player.position))
        current_input_index = 0
        update_text_visual()
    else:
        active_target = None

def update():
    global active_target
    if game_over:
        return
        
    # Animasi senjata bernafas (idle breathing)
    player_weapon.y = -0.3 + (math.sin(time.time() * 2) * 0.01)
    
    if active_target is None or active_target not in enemies_list:
        auto_lock_nearest_enemy()
    
    if active_target and active_target in enemies_list:
        player.look_at_2d(active_target.position, 'y')

def spawn_wave():
    global current_wave, game_over
    if game_over: return
    
    ui_announcement.text = "" 
    ui_stats.text = f'HP: {player_hp} | WAVE: {current_wave}'
    
    num_enemies = current_wave * 3  
    for _ in range(num_enemies):
        if current_wave == 1:
            word = random.choice(IT_WORDS_EASY)
        elif current_wave == 2:
            word = random.choice(IT_WORDS_EASY + IT_WORDS_MEDIUM)
        else:
            word = random.choice(IT_WORDS_MEDIUM + IT_WORDS_HARD)
            
        enemy = Enemy(word)
        enemies_list.append(enemy)
    
    invoke(auto_lock_nearest_enemy, delay=0.1)

def check_wave_clear():
    global current_wave
    if len(enemies_list) == 0 and not game_over:
        current_wave += 1
        ui_announcement.text = f"WAVE CLEAR!"
        ui_announcement.color = color.green
        reset_targeting()
        invoke(show_next_wave_ready, delay=2)

def show_next_wave_ready():
    if game_over: return
    ui_announcement.text = f"WAVE {current_wave} STARTING..."
    ui_announcement.color = color.orange
    invoke(spawn_wave, delay=1.5)

def reset_targeting():
    global active_target, current_input_index
    if active_target and active_target in enemies_list:
        active_target.text_label.text = active_target.word
    active_target = None
    current_input_index = 0
    ui_target_box.text = ''
    ui_typing_progress.text = ''

def input(key):
    global active_target, current_input_index, game_over
    
    if game_over or len(key) != 1 or key == ' ':
        return

    pressed_letter = key.upper()

    if active_target and active_target in enemies_list:
        target_word = active_target.word
        
        if pressed_letter == target_word[current_input_index]:
            current_input_index += 1
            update_text_visual()
            
            # Panggil fungsi menembak peluru yang baru
            shoot_bullet(active_target) 
            
            if current_input_index == len(target_word):
                remove_enemy_completely(active_target)
                active_target = None 
                check_wave_clear()
        else:
            print("TYPO! Progress Reset.")
            current_input_index = 0
            update_text_visual()

def update_text_visual():
    if active_target:
        done = active_target.word[:current_input_index]
        remain = active_target.word[current_input_index:]
        active_target.text_label.text = f"<span color='#00FF00'>{done}</span>{remain}"
        ui_target_box.text = f"TARGET: {active_target.word}"
        ui_typing_progress.text = done

spawn_wave()
app.run()