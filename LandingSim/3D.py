import pygame
import math
import random
import pickle
import os
from perlin_noise import PerlinNoise
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

class SphereSector:
    def __init__(self, radius=5.0, longitudes=64, latitudes=64, 
                 min_lat=-math.pi/4, max_lat=math.pi/4, 
                 min_lon=0, max_lon=math.pi/2,
                 planetName="Unnamed Planet"):
        self.radius = radius
        self.longitudes = longitudes
        self.latitudes = latitudes
        self.planetName = planetName
        
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        
        self.center_lat = (min_lat + max_lat) / 2
        self.center_lon = (min_lon + max_lon) / 2
        
        self.center_x, self.center_y, self.center_z = self.spherical_to_cartesian(self.center_lon, self.center_lat, 0.05)
        
        self._vertices_cache = {}
        self._normals_cache = {}
        self._indices_cache = None
        
        self._setup_geometry()
        
    def _setup_geometry(self):
        self.lat_angles = [
            self.min_lat + (i / self.latitudes) * (self.max_lat - self.min_lat) 
            for i in range(self.latitudes + 1)
        ]
        self.lon_angles = [
            self.min_lon + (i / self.longitudes) * (self.max_lon - self.min_lon) 
            for i in range(self.longitudes + 1)
        ]
    
    def spherical_to_cartesian(self, longitude, latitude, height=0):
        effective_radius = self.radius + height
        cos_lat = math.cos(latitude)
        x = effective_radius * cos_lat * math.cos(longitude)
        y = effective_radius * math.sin(latitude)
        z = effective_radius * cos_lat * math.sin(longitude)
        return (x, y, z)
    
    def generate_indices(self):
        if self._indices_cache is not None:
            return self._indices_cache
            
        indices = []
        longs = self.longitudes
        for lat in range(self.latitudes):
            lat_offset = lat * (longs + 1)
            next_lat_offset = (lat + 1) * (longs + 1)
            
            for lon in range(longs):
                first = lat_offset + lon
                second = next_lat_offset + lon
                
                # Два треугольника на квад
                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])
                
        self._indices_cache = indices
        return indices
    
    def get_vertices_and_normals(self):
        cache_key = f"{self.planetName}_sector_{self.min_lat}_{self.max_lat}_{self.min_lon}_{self.max_lon}"
        
        if cache_key in self._vertices_cache:
            return self._vertices_cache[cache_key], self._normals_cache[cache_key]
        
        vertices = []
        normals = []
        
        for latitude in self.lat_angles:
            sin_lat = math.sin(latitude)
            cos_lat = math.cos(latitude)
            
            for longitude in self.lon_angles:
                height = noise_surface(longitude, latitude)
                
                effective_radius = self.radius + height
                cos_lon = math.cos(longitude)
                sin_lon = math.sin(longitude)
                
                x = effective_radius * cos_lat * cos_lon
                y = effective_radius * sin_lat
                z = effective_radius * cos_lat * sin_lon
                
                vertices.append((x, y, z))
                
                # Нормаль
                normal_x = cos_lat * cos_lon
                normal_y = sin_lat
                normal_z = cos_lat * sin_lon
                length = math.sqrt(normal_x*normal_x + normal_y*normal_y + normal_z*normal_z)
                if length > 0:
                    normals.append((normal_x/length, normal_y/length, normal_z/length))
                else:
                    normals.append((normal_x, normal_y, normal_z))
        
        self._vertices_cache[cache_key] = vertices
        self._normals_cache[cache_key] = normals
        
        return vertices, normals
    
    def draw_solid(self):
        vertices, normals = self.get_vertices_and_normals()
        indices = self.generate_indices()
        
        glBegin(GL_TRIANGLES)
        for i in indices:
            vx, vy, vz = vertices[i]
            nx, ny, nz = normals[i]
            glNormal3f(nx, ny, nz)
            glVertex3f(vx, vy, vz)
        glEnd()
    
    def draw_wireframe(self):
        """Отрисовка каркаса"""
        vertices, _ = self.get_vertices_and_normals()
        indices = self.generate_indices()
        
        glDisable(GL_LIGHTING)
        glColor3f(0.8, 0.9, 1.0)
        
        glBegin(GL_LINES)
        for i in range(0, len(indices), 3):
            # Первый треугольник
            v1 = vertices[indices[i]]
            v2 = vertices[indices[i+1]]
            v3 = vertices[indices[i+2]]
            
            # Рёбра треугольника
            glVertex3f(*v1)
            glVertex3f(*v2)
            
            glVertex3f(*v2)
            glVertex3f(*v3)
            
            glVertex3f(*v3)
            glVertex3f(*v1)
        glEnd()
        
        glEnable(GL_LIGHTING)
    
    def draw_optimized(self, wireframe=False):
        if wireframe:
            self.draw_wireframe()
        else:
            self.draw_solid()
    
    def get_sector_info(self):
        lat_deg_min = math.degrees(self.min_lat)
        lat_deg_max = math.degrees(self.max_lat)
        lon_deg_min = math.degrees(self.min_lon)
        lon_deg_max = math.degrees(self.max_lon)
        
        return {
            'center_lat': math.degrees(self.center_lat),
            'center_lon': math.degrees(self.center_lon),
            'lat_range': f"{lat_deg_min:.1f}° - {lat_deg_max:.1f}°",
            'lon_range': f"{lon_deg_min:.1f}° - {lon_deg_max:.1f}°",
            'center_xyz': (self.center_x, self.center_y, self.center_z)
        }
    
    def save_to_file(self, filename=None):
        if filename is None:
            filename = f"{self.planetName}.bin"
        data = {
            'radius': self.radius,
            'longitudes': self.longitudes,
            'latitudes': self.latitudes,
            'planetName': self.planetName,
            'min_lat': self.min_lat,
            'max_lat': self.max_lat,
            'min_lon': self.min_lon,
            'max_lon': self.max_lon,
            'vertices_cache': self._vertices_cache,
            'normals_cache': self._normals_cache,
            'indices_cache': self._indices_cache
        }
        
        try:
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
            print(f"Сектор '{self.planetName}' сохранен в файл: {filename}")
            return True
        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filename):
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
            
            # Создаем новый объект SphereSector
            sector = cls(
                radius=data['radius'],
                longitudes=data['longitudes'],
                latitudes=data['latitudes'],
                min_lat=data['min_lat'],
                max_lat=data['max_lat'],
                min_lon=data['min_lon'],
                max_lon=data['max_lon'],
                planetName=data['planetName']
            )
            
            sector._vertices_cache = data.get('vertices_cache', {})
            sector._normals_cache = data.get('normals_cache', {})
            sector._indices_cache = data.get('indices_cache', None)
            
            print(f"Сектор '{sector.planetName}' загружен из файла: {filename}")
            return sector
            
        except Exception as e:
            print(f"Ошибка при загрузке: {e}")
            return None
    
    def get_save_data_size(self):
        data = {
            'radius': self.radius,
            'longitudes': self.longitudes,
            'latitudes': self.latitudes,
            'planetName': self.planetName,
            'min_lat': self.min_lat,
            'max_lat': self.max_lat,
            'min_lon': self.min_lon,
            'max_lon': self.max_lon,
            'vertices_cache': self._vertices_cache,
            'normals_cache': self._normals_cache,
            'indices_cache': self._indices_cache
        }
        return len(pickle.dumps(data))

class Lander:
    def __init__(self, lon=0, lat=0, heig=0, v_lon=0, v_lat=0, v_heig=0, size=0.1):
        self.lon = lon
        self.lat = lat
        self.heig = heig
        self.v_lon = v_lon
        self.v_lat = v_lat
        self.v_heig = v_heig
        self.size = size
        self.exists = True
        
    def update_position(self, dt):
        # Обновление позиции на основе скоростей
        self.lon += self.v_lon * dt
        self.lat += self.v_lat * dt
        self.heig += self.v_heig * dt
        
        # Ограничение высоты (не может уйти ниже поверхности)
        if self.heig < 0:
            self.heig = 0
            self.v_heig = 0
    
    def get_cartesian_position(self, radius):
        # Преобразование сферических координат в декартовы
        effective_radius = radius + self.heig
        cos_lat = math.cos(self.lat)
        x = effective_radius * cos_lat * math.cos(self.lon)
        y = effective_radius * math.sin(self.lat)
        z = effective_radius * cos_lat * math.sin(self.lon)
        return (x, y, z)
    
    def draw(self):
        if not self.exists:
            return
            
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 0.0, 0.0)  # Красный цвет для лендера
        
        # Получаем позицию лендера
        x, y, z = self.get_cartesian_position(5.0)  # Используем радиус планеты 5.0
        
        # Рисуем тетраэдр
        s = self.size
        
        # Вершины тетраэдра
        vertices = [
            (x, y + s, z),      # Верхняя вершина
            (x - s, y - s, z - s),  # Основание 1
            (x + s, y - s, z - s),  # Основание 2
            (x, y - s, z + s)       # Основание 3
        ]
        
        # Грани тетраэдра
        faces = [
            (0, 1, 2),
            (0, 2, 3),
            (0, 3, 1),
            (1, 3, 2)
        ]
        
        # Отрисовка тетраэдра
        glBegin(GL_TRIANGLES)
        for face in faces:
            for vertex_idx in face:
                glVertex3f(*vertices[vertex_idx])
        glEnd()
        
        glEnable(GL_LIGHTING)

class SectorCamera:
    def __init__(self, sector, lander=None):
        self.sector = sector
        self.lander = lander
        self.follow_lander = False
        self.distance = 8.0
        self.min_distance = 0.2
        self.max_distance = 30.0
        self.rotation_x = 0
        self.rotation_y = 0
        
        self.update_camera_position()
    
    def set_lander(self, lander):
        self.lander = lander
    
    def toggle_follow_lander(self):
        self.follow_lander = not self.follow_lander
        print(f"Камера {'следит' if self.follow_lander else 'не следит'} за лендером")
    
    def update_camera_position(self):
        glLoadIdentity()
        gluPerspective(45, 800/600, 0.1, 100.0)
        
        if self.follow_lander and self.lander and self.lander.exists:
            # Камера следует за лендером
            x, y, z = self.lander.get_cartesian_position(self.sector.radius)
            
            # Позиция камеры немного позади и выше лендера
            camera_distance = 3.0
            camera_height = 1.0
            
            # Вычисляем направление взгляда (противоположно нормали поверхности)
            normal_x = math.cos(self.lander.lat) * math.cos(self.lander.lon)
            normal_y = math.sin(self.lander.lat)
            normal_z = math.cos(self.lander.lat) * math.sin(self.lander.lon)
            
            # Позиция камеры
            camera_x = x - normal_x * camera_distance
            camera_y = y - normal_y * camera_distance + camera_height
            camera_z = z - normal_z * camera_distance
            
            # Направление взгляда на лендер
            gluLookAt(
                camera_x, camera_y, camera_z,  # Позиция камеры
                x, y, z,                       # Точка, на которую смотрим
                0, 1, 0                        # Вектор "вверх"
            )
        else:
            # Стандартная камера для сектора
            glTranslatef(0.0, 0.0, -self.distance)
            
            glRotatef(self.rotation_x, 1, 0, 0)
            glRotatef(self.rotation_y, 0, 1, 0)
            
            glTranslatef(-self.sector.center_x, -self.sector.center_y, -self.sector.center_z)
    
    def zoom(self, delta):
        if not self.follow_lander:
            self.distance = max(self.min_distance, min(self.max_distance, self.distance + delta/5))
    
    def rotate(self, delta_x, delta_y):
        if not self.follow_lander:
            self.rotation_y += delta_x * 0.5
            self.rotation_x = max(-90, min(90, self.rotation_x + delta_y * 0.5))

class WireframeMaterial:
    @staticmethod
    def setup_wireframe():
        glDisable(GL_LIGHTING)
        glColor3f(0.7, 0.8, 1.0)
        glLineWidth(1.0)
    
    @staticmethod
    def setup_solid():
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        
        glLightfv(GL_LIGHT0, GL_POSITION, [5.0, 5.0, 5.0, 1.0])
        
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.4, 0.4, 0.4, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.3, 0.3, 0.3, 1.0])
        
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.3, 0.4, 0.6, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.6, 0.7, 0.9, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 10.0)

def noise_surface(longitude, latitude):
    noise = PerlinNoise(octaves=2, seed=4522)
    noise2 = PerlinNoise(octaves=3, seed=345)
    noise3 = PerlinNoise(octaves=3, seed=235)
    return 0.03 * noise([longitude*5, latitude*5]) + 0.03 * noise2([longitude*20, latitude*20]) + 0.01 * noise3([longitude*80, latitude*80])

def draw_coordinate_axes():
    glDisable(GL_LIGHTING)
    glBegin(GL_LINES)
    
    glColor3f(1, 0, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(2, 0, 0)
    
    glColor3f(0, 1, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 2, 0)
    
    glColor3f(0, 0, 1)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, 2)
    
    glEnd()
    glEnable(GL_LIGHTING)

def list_saved_areas():
    bin_files = [f for f in os.listdir() if f.endswith('.bin')]
    if not bin_files:
        print("Нет сохраненных областей")
        return []
    
    print("\nСохраненные области:")
    for i, filename in enumerate(bin_files, 1):
        print(f"{i}. {filename}")
    return bin_files

def CustomSector():
    print("\n=== Создание новой области ===")
    ma_Long, mi_Long = map(int, input("Две долготы (-180;180): ").split())
    ma_Lat, mi_Lat = map(int, input("Две широты (-90;90): ").split())
    Radiu = int(input("Радиус Планеты (средний): "))
    Details = int(input("Детализация: "))
    areaname = input("Название зоны: ")
    
    if mi_Long > ma_Long: mi_Long, ma_Long = ma_Long, mi_Long
    if mi_Lat > ma_Lat: mi_Lat, ma_Lat = ma_Lat, mi_Lat
    
    sector = SphereSector(Radiu, Details, Details,
                    min_lat=math.radians(mi_Lat), max_lat=math.radians(ma_Lat),
                    min_lon=math.radians(mi_Long), max_lon=math.radians(ma_Long),
                    planetName=areaname)
    
    save = input("Сохранить область? (y/n): ").lower().strip()
    if save == 'y':
        sector.save_to_file()
    
    return sector

def load_sector_interactive():
    bin_files = list_saved_areas()
    if not bin_files:
        return None
    
    try:
        choice = int(input("Выберите номер области для загрузки: ")) - 1
        if 0 <= choice < len(bin_files):
            return SphereSector.load_from_file(bin_files[choice])
        else:
            print("Неверный выбор")
            return None
    except ValueError:
        print("Введите число")
        return None

def create_lander_interactive():
    print("\n=== Создание нового лендера ===")
    try:
        lon, lat, heig = map(float, input("Долгота, широта, высота: ").split())
        v_lon, v_lat, v_heig = map(float, input("Скорость по долготе, широте, высоте: ").split())
        size = float(input("Размер лендера: "))
        
        # Преобразование градусов в радианы
        lon_rad = math.radians(lon)
        lat_rad = math.radians(lat)
        
        return Lander(lon_rad, lat_rad, heig, v_lon, v_lat, v_heig, size)
    except ValueError:
        print("Ошибка ввода. Используйте числа.")
        return None

def main():
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("LandingSim")
    
    sector = SphereSector(radius=5.0, longitudes=64, latitudes=64,
                min_lat=math.radians(-5), max_lat=math.radians(5),
                min_lon=math.radians(5), max_lon=math.radians(10),
                planetName="Null Area")
    
    lander = None
    camera = SectorCamera(sector, lander)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    
    clock = pygame.time.Clock()
    show_axes = True
    wireframe_mode = True
    
    print("=== LandingSim ===")
    print("Управление:")
    print("1 - Камера к текущей области")
    print("W - переключить Wireframe/Solid режим")
    print("A - показать/скрыть оси координат")
    print("C - создать новую область")
    print("L - загрузить сохраненную область")
    print("S - сохранить текущую область")
    print("R - сброс камеры")
    print("SPACE - создать/удалить лендер")
    print("F - переключить привязку камеры к лендеру")
    print("Колесо мыши - приближение/отдаление")
    print("ЛКМ + движение - вращение камеры вокруг сектора")
    print(f"Текущий режим: {'WIREFRAME' if wireframe_mode else 'SOLID'}")
    
    while True:
        dt = clock.tick(60) / 1000.0  # Время в секундах с последнего кадра
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                elif event.key == pygame.K_1:
                    camera = SectorCamera(sector, lander)
                    info = sector.get_sector_info()
                    print(f"\nТекущая область: {sector.planetName}")
                    print(f"Широта: {info['lat_range']}")
                    print(f"Долгота: {info['lon_range']}")
                    print(f"Центр: ({info['center_lat']:.1f}°, {info['center_lon']:.1f}°)")
                    print(f"Размер данных: {sector.get_save_data_size()} байт")
                    print(f"Режим отображения: {'WIREFRAME' if wireframe_mode else 'SOLID'}")
                elif event.key == pygame.K_w:
                    wireframe_mode = not wireframe_mode
                    mode_name = "WIREFRAME" if wireframe_mode else "SOLID"
                    print(f"Режим изменен на: {mode_name}")
                elif event.key == pygame.K_a:
                    show_axes = not show_axes
                    print(f"Оси координат: {'ВКЛ' if show_axes else 'ВЫКЛ'}")
                elif event.key == pygame.K_r:
                    camera.rotation_x = 0
                    camera.rotation_y = 0
                    camera.distance = 8.0
                elif event.key == pygame.K_c:
                    sector = CustomSector()
                    camera = SectorCamera(sector, lander)
                elif event.key == pygame.K_l:
                    loaded_sector = load_sector_interactive()
                    if loaded_sector:
                        sector = loaded_sector
                        camera = SectorCamera(sector, lander)
                elif event.key == pygame.K_s:
                    sector.save_to_file()
                elif event.key == pygame.K_SPACE:
                    if lander and lander.exists:
                        lander.exists = False
                        print("Старый лендер удален")
                    
                    new_lander = create_lander_interactive()
                    if new_lander:
                        lander = new_lander
                        camera.set_lander(lander)
                        print("Новый лендер создан")
                elif event.key == pygame.K_f:
                    camera.toggle_follow_lander()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: camera.zoom(-1.0)
                elif event.button == 5: camera.zoom(1.0)
        
        if pygame.mouse.get_pressed()[0]:
            rel_x, rel_y = pygame.mouse.get_rel()
            camera.rotate(rel_x, rel_y)
        else:
            pygame.mouse.get_rel()
        
        # Обновление позиции лендера
        if lander and lander.exists:
            lander.update_position(dt)
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        camera.update_camera_position()
        
        if wireframe_mode:
            WireframeMaterial.setup_wireframe()
        else:
            WireframeMaterial.setup_solid()
        
        sector.draw_optimized(wireframe=wireframe_mode)
        
        # Отрисовка лендера
        if lander and lander.exists:
            lander.draw()
        
        if show_axes:
            draw_coordinate_axes()
        
        mode_text = "WIREFRAME" if wireframe_mode else "SOLID"
        lander_text = " + LANDER" if lander and lander.exists else ""
        follow_text = " [FOLLOW]" if camera.follow_lander else ""
        pygame.display.set_caption(f"LandingSim - {mode_text}{lander_text}{follow_text} - {sector.planetName}")
        
        pygame.display.flip()

if __name__ == "__main__":
    main()