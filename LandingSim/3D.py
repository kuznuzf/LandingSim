import pygame
import math
import random
import pickle
import os
from perlin_noise import PerlinNoise
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

def NameToCoords(name):
    a, b = name.split("_")
    return a, b

def CoordsToName(a, b):
    return str(a)+"_"+str(b)

class Planet:
    def __init__(self, radius_render=1, longitude=0, latitude=0, radius=7, details=32):
        self.radius_render = radius_render
        self.longitude = longitude 
        self.latitude = latitude
        self.radius = radius
        self.details = details
        self.sectors = []
        for i in range((radius_render-1)*2+1):
            self.sectors.append([])
            longi = longitude + i - (radius_render-1)
            for j in range((radius_render-1)*2+1):
                latj = latitude + j - (radius_render-1)
                nameij = CoordsToName(longi, latj)
                self.sectors[i].append(SphereSector(radius, math.radians(longi), math.radians(latj), longi, latj, details))

class SphereSector:
    def __init__(self, radius=7.0, longitude=0, latitude=0, deg_longitude=0, deg_latitude=0, details=32):
        self.radius = radius
        self.longitude = longitude
        self.latitude = latitude
        self.deg_longitude = deg_longitude
        self.deg_latitude = deg_latitude
        self.scale_lon = math.pi/180
        self.scale_lat = math.pi/180
        self.details = details
        self.sectorName = CoordsToName(deg_longitude, deg_latitude)
        self.color = 0.9 + 0.05*math.pow(-1, self.deg_longitude + self.deg_latitude)
        
        self.min_lat = self.latitude - self.scale_lat/2
        self.max_lat = self.latitude + self.scale_lat/2
        self.min_lon = self.longitude - self.scale_lon/2
        self.max_lon = self.longitude + self.scale_lon/2
        
        self.center_x, self.center_y, self.center_z = self.spherical_to_cartesian(self.longitude, self.latitude, 0.05)
        
        self._vertices_cache = {}
        self._normals_cache = {}
        self._indices_cache = None
        
        self._setup_geometry()
        
    def _setup_geometry(self):
        self.lat_angles = [
            self.min_lat + (i / self.details) * (self.max_lat - self.min_lat) 
            for i in range(self.details + 1)
        ]
        self.lon_angles = [
            self.min_lon + (i / self.details) * (self.max_lon - self.min_lon) 
            for i in range(self.details + 1)
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
        longs = self.details
        for lat in range(self.details):
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
        cache_key = CoordsToName(self.deg_longitude, self.deg_latitude)
        
        if cache_key in self._vertices_cache:
            return self._vertices_cache[cache_key], self._normals_cache[cache_key]
        
        vertices = []
        normals = []
        
        for latitude in self.lat_angles:
            sin_lat = math.sin(latitude)
            cos_lat = math.cos(latitude)
            
            for longitude in self.lon_angles:
                height = self.noise_surface(longitude, latitude)
                
                effective_radius = height
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
    
    def noise_surface(self, longitude, latitude):
        noise = PerlinNoise(octaves=2, seed=4522)
        noise2 = PerlinNoise(octaves=3, seed=345)
        noise3 = PerlinNoise(octaves=3, seed=235)
        return self.radius + 0.03 * noise([longitude*5, latitude*5]) + 0.03 * noise2([longitude*20, latitude*20]) + 0.01 * noise3([longitude*80, latitude*80])

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
        vertices, _ = self.get_vertices_and_normals()
        indices = self.generate_indices()
        
        glDisable(GL_LIGHTING)
        glColor3f(self.color, self.color, self.color)
        
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
            'center_lat': math.degrees(self.latitude),
            'center_lon': math.degrees(self.longitude),
            'lat_range': f"{lat_deg_min:.1f}° - {lat_deg_max:.1f}°",
            'lon_range': f"{lon_deg_min:.1f}° - {lon_deg_max:.1f}°",
            'center_xyz': (self.center_x, self.center_y, self.center_z)
        }
    
    def save_to_file(self, filename=None):
        if filename is None:
            filename = f"{self.sectorName}.bin"
        data = {
            'radius': self.radius,
            'details': self.details,
            'sectorName': self.sectorName,
            'longitude': self.longitude,
            'latitude': self.latitude,
            'scale_lon': self.scale_lon,
            'scale_lat': self.scale_lat,
            'vertices_cache': self._vertices_cache,
            'normals_cache': self._normals_cache,
            'indices_cache': self._indices_cache
        }
        
        try:
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
            print(f"Сектор '{self.sectorName}' сохранен в файл: {filename}")
            return True
        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filename):
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
            
            sector = cls(
                radius=data['radius'],
                longitude=data['longitude'],
                latitude=data['latitude'],
                scale_lon=data['scale_lon'],
                scale_lat=data['scale_lat'],
                details=data['details'],
                sectorName=data['sectorName']
            )
            
            sector._vertices_cache = data.get('vertices_cache', {})
            sector._normals_cache = data.get('normals_cache', {})
            sector._indices_cache = data.get('indices_cache', None)
            
            print(f"Сектор '{sector.sectorName}' загружен из файла: {filename}")
            return sector
            
        except Exception as e:
            print(f"Ошибка при загрузке: {e}")
            return None
    
    def get_save_data_size(self):
        data = {
            'radius': self.radius,
            'longitude': self.longitude,
            'latitude': self.latitude,
            'sectorName': self.sectorName,
            'scale_lat': self.scale_lat,
            'scale_lon': self.scale_lon,
            'details': self.details,
            'vertices_cache': self._vertices_cache,
            'normals_cache': self._normals_cache,
            'indices_cache': self._indices_cache
        }
        return len(pickle.dumps(data))

class Lander:
    def __init__(self, lon=0, lat=0, heig=1.0, v_lon=0, v_lat=0, v_heig=0, size=0.1, heig_planet=1.0):
        self.lon = lon
        self.lat = lat
        self.heig = heig
        self.v_lon = v_lon
        self.v_lat = v_lat
        self.v_heig = v_heig
        self.size = size
        self.heig_planet = heig_planet
        self.exists = True
        
    def update_velocity(self, dt):
        self.lon += self.v_lon * dt
        self.lat += self.v_lat * dt
        self.heig += self.v_heig * dt
        
        if self.heig < self.heig_planet:
            self.heig = 0
            self.v_heig = 0
    
    def update_height(self, heig_planet):
        self.heig_planet = heig_planet
    
    def get_cartesian_position(self, heig):
        cos_lat = math.cos(self.lat)
        x = heig * cos_lat * math.cos(self.lon)
        y = heig * math.sin(self.lat)
        z = heig * cos_lat * math.sin(self.lon)
        return (x, y, z)
    
    def draw(self):
        if not self.exists:
            return
            
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 0.0, 0.0)
        
        x, y, z = self.get_cartesian_position(self.heig)
        
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
    def __init__(self, planet, lander=None):
        self.planet = planet
        self.lander = lander
        self.follow_lander = False
        self.distance = 2.0
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
            glTranslatef(0.0, 0.0, -self.distance)
            
            glRotatef(self.rotation_x, 1, 0, 0)
            glRotatef(self.rotation_y, 0, 1, 0)
            x, y, z = self.lander.get_cartesian_position(self.lander.heig)
            glTranslatef(-x, -y, -z)
        else:
            glTranslatef(0.0, 0.0, -self.distance)
            
            glRotatef(self.rotation_x, 1, 0, 0)
            glRotatef(self.rotation_y, 0, 1, 0)
            sector_center = self.planet.sectors[self.planet.radius_render-1][self.planet.radius_render-1]
            glTranslatef(-sector_center.center_x, -sector_center.center_y, -sector_center.center_z)
    
    def zoom(self, delta):
        if not self.follow_lander:
            self.distance = max(self.min_distance, min(self.max_distance, self.distance + delta/5))
    
    def rotate(self, delta_x, delta_y):
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
    print("\n=== Создание новой планеты ===")
    Radius_sectors = int(input("Радиус прорисовки: "))
    Long, Lat = map(int, input("Долгота и широта центра: ").split())
    Radiu = int(input("Радиус Планеты (средний): "))
    Details = int(input("Детализация: "))
    
    planet = Planet(Radius_sectors, Long, Lat, Radiu, Details)
    
    """save = input("Сохранить область? (y/n): ").lower().strip()
    if save == 'y':
        planet.save_to_file()"""
    
    return planet

def load_sector_interactive():
    bin_files = list_saved_areas()
    if not bin_files:
        return None
    
    try:
        choice = int(input("Выберите номер планеты для загрузки: ")) - 1
        if 0 <= choice < len(bin_files):
            return Planet.load_from_file(bin_files[choice])
        else:
            print("Неверный выбор")
            return None
    except ValueError:
        print("Введите число")
        return None

def update_sectors(planet, delta_lon, delta_lat): 
    size_sectors = (planet.radius_render-1)*2+1
    new_sectors = [[None for _ in range(size_sectors)] for _ in range(size_sectors)]
    for i in range(len(planet.sectors)):
        for j in range(len(planet.sectors[i])):
            sector = planet.sectors[i][j]
            new_i = i - delta_lon
            new_j = j - delta_lat
            if 0 <= new_i < size_sectors and 0 <= new_j < size_sectors:
                new_sectors[new_i][new_j] = sector
    for i in range(size_sectors):
        for j in range(size_sectors):
            if new_sectors[i][j] is None:
                new_lon = planet.longitude + i - (planet.radius_render - 1)
                new_lat = planet.latitude + j - (planet.radius_render - 1)
                
                new_sectors[i][j] = SphereSector(planet.radius, math.radians(new_lon), math.radians(new_lat), new_lon, new_lat, planet.details)
    planet.sectors = new_sectors
    return planet



def main():
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("LandingSim")
    
    planet = Planet(3, 0, 0, 7, 8)
    
    lander = None
    camera = SectorCamera(planet, lander)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    
    clock = pygame.time.Clock()
    show_axes = True
    wireframe_mode = True
    
    print("=== LandingSim ===")
    print("Управление:")
    print("W - переключить Wireframe/Solid режим")
    print("A - показать/скрыть оси координат")
    #print("C - создать новую область")
    #print("L - загрузить сохраненную область")
    #print("S - сохранить текущую область")
    print("R - сброс камеры")
    print("F - создать/удалить лендер")
    print("SPACE - переключить привязку камеры к лендеру")
    print("Колесо мыши - приближение/отдаление")
    print("ЛКМ + движение - вращение камеры")
    print(f"Текущий режим: {'WIREFRAME' if wireframe_mode else 'SOLID'}")
    
    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
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
                    planet = CustomSector()
                    camera = SectorCamera(planet, lander)
                elif event.key == pygame.K_f:
                    if lander and lander.exists:
                        lander.exists = False
                        print("Старый лендер удален")
                    asco = input("Default? y/n ")
                    if asco == 'y':
                        new_lander = Lander(0, 0, 8, 0.01, 0, 0, 0.1, planet.sectors[0][0].noise_surface(0, 0))
                    else:
                        print("\n=== Создание нового лендера ===")
                        try:
                            lon, lat, heig = map(float, input("Долгота, широта, высота: ").split())
                            v_lon, v_lat, v_heig = map(float, input("Скорость по долготе, широте, высоте: ").split())
                            size = float(input("Размер лендера: "))
        
                            lon_rad = math.radians(lon)
                            lat_rad = math.radians(lat)
                            heig_planet = planet.sectors[0][0].noise_surface(lon, lat)
        
                            new_lander = Lander(lon_rad, lat_rad, heig, v_lon, v_lat, v_heig, size, heig_planet)
                        except ValueError:
                            print("Ошибка ввода")
                            new_lander = None
                    if new_lander != None:
                        lander = new_lander
                        camera.set_lander(lander)
                        print("Новый лендер создан")
                elif event.key == pygame.K_SPACE:
                    camera.toggle_follow_lander()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: camera.zoom(-1.0)
                elif event.button == 5: camera.zoom(1.0)
        
        if pygame.mouse.get_pressed()[0]:
            rel_x, rel_y = pygame.mouse.get_rel()
            camera.rotate(rel_x, rel_y)
        else:
            pygame.mouse.get_rel()
        
        if lander and lander.exists:
            lander.update_velocity(dt)
            lander.update_height(planet.sectors[0][0].noise_surface(lander.lon, lander.lat))
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        camera.update_camera_position()
        
        if wireframe_mode:
            WireframeMaterial.setup_wireframe()
        else:
            WireframeMaterial.setup_solid()
        for i in range(len(planet.sectors)):
            for j in range(len(planet.sectors[i])):
                planet.sectors[i][j].draw_optimized(wireframe=wireframe_mode)
        
        if lander and lander.exists:
            lander.draw()
        if lander != None:
            ceil_lon = math.ceil(math.degrees(lander.lon))
            ceil_lat = math.ceil(math.degrees(lander.lat))
            delta_lon = ceil_lon - planet.longitude
            delta_lat = ceil_lat - planet.latitude
            if math.fabs(delta_lon) > 0.5 or math.fabs(delta_lat) > 0.5:
                planet.longitude = ceil_lon
                planet.latitude = ceil_lat
                planet = update_sectors(planet, delta_lon, delta_lat)
                #camera = SectorCamera(planet, lander)
        if show_axes:
            draw_coordinate_axes()
        
        mode_text = "WIREFRAME" if wireframe_mode else "SOLID"
        lander_text = " + LANDER" if lander and lander.exists else ""
        follow_text = " [FOLLOW]" if camera.follow_lander else ""
        pygame.display.set_caption(f"LandingSim - {mode_text}{lander_text}{follow_text}")
        
        pygame.display.flip()

if __name__ == "__main__":
    main()
