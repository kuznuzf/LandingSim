import pygame
import math
import random
import os
from perlin_noise import PerlinNoise
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

SCALE = 25000

def NameToCoords(name):
    a, b = name.split("_")
    return a, b

def CoordsToName(a, b):
    return str(a)+"_"+str(b)

def scalar_product(a, b): #Скалярное произведение Vector3 a * b
    return a.x * b.x + a.y * b.y + a.z * b.z

def vector_product(a, b): #Векторное произведение Vector3 a х b
    return Vector3(a.y*b.z - a.z*b.y, a.x*b.z - a.z*b.x, a.x*b.y - a.y*b.x)

class Vector3:
    def __init__(self, x, y, z): #force = Vector3(x, y, z)
        self.x = x
        self.y = y
        self.z = z
        self.length = math.sqrt(x**2 + y**2 + z**2)

    def normalized(self):
        return Vector3(self.x/self.length, self.y/self.length, self.z/self.length)
    
def get_radius(equ, pol, latitude):
    return pol + 2*latitude/math.pi * (equ - pol)

class Planet:
    def __init__(self, radius_render=1, longitude=0, latitude=0, equ_radius=7, pol_radius=6.6, details=32):
        self.radius_render = radius_render
        self.longitude = longitude 
        self.latitude = latitude
        self.equ_radius = equ_radius
        self.pol_radius = pol_radius
        self.details = details
        
        self.gradient_settings = {
            'green_angle': 5,
            'yellow_angle': 15,
            'orange_angle': 30,
            'red_angle': 90
        }
        
        self.craters = self._generate_craters(25, longitude, latitude, radius_render)
        self.sectors = []
        for i in range((radius_render-1)*2+1):
            self.sectors.append([])
            longi = longitude + i - (radius_render-1)
            for j in range((radius_render-1)*2+1):
                latj = latitude + j - (radius_render-1)
                nameij = CoordsToName(longi, latj)
                self.sectors[i].append(SphereSector(equ_radius, pol_radius, math.radians(longi), math.radians(latj), 
                                                   longi, latj, details, 
                                                   gradient_settings=self.gradient_settings,
                                                   craters=self.craters))
    def _generate_craters(self, num_craters=1000, longit=0, latit=0, radiu=1):
        craters = []
        for _ in range(num_craters):
            lon = random.uniform(math.radians(longit - radiu), math.radians(longit + radiu))
            lat = random.uniform(math.radians(latit - radiu), math.radians(latit + radiu))
            radius = random.uniform(0.00004 * self.radius_render, 0.01 * self.radius_render)  # угловой радиус
            planet_radius = get_radius(self.equ_radius, self.pol_radius, lat)
            crater = {
                'lon': lon,
                'lat': lat,
                'R': radius,                     # полный радиус
                'D': (planet_radius * radius) / 7, # глубина (линейная)
                'Rc': 0.85 * radius,              # радиус впадины
                'Rp': 0.2 * radius,               # радиус пика
                'h_peak': 0.2 * (planet_radius * radius) / 5,
                'h_rim': 0.025 * (planet_radius * radius) / 5
            }
            craters.append(crater)
        return craters

class SphereSector:
    def __init__(self, equ_radius, pol_radius, longitude=0, latitude=0, deg_longitude=0, deg_latitude=0, details=32, 
                 gradient_settings=None, craters=None):
        self.equ_radius = equ_radius
        self.pol_radius = pol_radius
        self.longitude = longitude
        self.latitude = latitude
        self.deg_longitude = deg_longitude
        self.deg_latitude = deg_latitude
        self.scale_lon = math.pi/180
        self.scale_lat = math.pi/180
        self.details = details
        self.sectorName = CoordsToName(deg_longitude, deg_latitude)
        
        self.gradient_settings = gradient_settings or {
            'green_angle': 5,
            'yellow_angle': 15,
            'orange_angle': 30,
            'red_angle': 90
        }
        
        self.min_lat = self.latitude - self.scale_lat/2
        self.max_lat = self.latitude + self.scale_lat/2
        self.min_lon = self.longitude - self.scale_lon/2
        self.max_lon = self.longitude + self.scale_lon/2
        
        self._vertices_cache = {}
        self._normals_cache = {}
        self._indices_cache = None
        self._gradient_cache = {}
        self.craters = craters if craters is not None else []
        self.center_x, self.center_y, self.center_z = self.spherical_to_cartesian(self.longitude, self.latitude, self.noise_surface(self.longitude,self.latitude)/SCALE+0.1)
        self.stones = self.generate_stones(random.randint(5, 20))
        
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
        effective_radius = height
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
                
                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])
                
        self._indices_cache = indices
        return indices
    
    def crater_effect(self, crater, r):
        R = crater['R']
        if r > R:
            return 0.0
        Rc = crater.get('Rc', 0.7 * R)
        Rp = crater.get('Rp', 0.2 * R)
        h_peak = crater.get('h_peak', 0.0)
        h_crater = crater.get('D', 0.0)  # глубина
        h_rim = crater.get('h_rim', 0.0)
    
        if r <= Rp:
            t = (math.pi * r) / (2 * Rp)
            return h_peak * math.cos(t)**2 - h_crater * (1 - (r/Rc)**2)
        elif r <= Rc:
            return -h_crater * (1 - (r/Rc)**2)
        else:
        # вал
            t = (math.pi * (r - Rc)) / (2 * (R - Rc))
            return h_rim * math.sin(t)**2
    
    def noise_surface(self, longitude, latitude):
        radius = get_radius(self.equ_radius, self.pol_radius, latitude)
        noise_base = PerlinNoise(octaves=2, seed=4522)
        noise_mountaines = PerlinNoise(octaves=5, seed=3435)
        noise_micro = PerlinNoise(octaves=10, seed=6522)
        h = 0.01 * noise_base([longitude*5, latitude*5])
        mountaines = noise_mountaines([longitude*4, latitude*4]) + 0.2 * noise_base([longitude*20, latitude*20])
        if mountaines > 0.2:
            h += 0.06 * (mountaines - 0.2)
    
        # Учёт кратеров (суммирование)
        if self.craters:
            total_delta = 0.0
            sin_lat = math.sin(latitude)
            cos_lat = math.cos(latitude)
            for crater in self.craters:
                clon = crater['lon']
                clat = crater['lat']
                sin_clat = math.sin(clat)
                cos_clat = math.cos(clat)
                cos_dlon = math.cos(longitude - clon)
                cos_angle = sin_lat * sin_clat + cos_lat * cos_clat * cos_dlon
                cos_angle = max(-1.0, min(1.0, cos_angle))
                angle = math.acos(cos_angle)
                delta = self.crater_effect(crater, angle)
                total_delta += delta
            h += total_delta
        h += 0.014 * noise_micro([longitude*10, latitude*10])
        depolarizator = 1 - latitude**12/225.652
        return radius + h * depolarizator
    
    def generate_stones(self, count):
        res = [] #[(longitude, latitude, height), (..., ..., ...), ...]
        for _ in range(count):
            lg = random.uniform(self.min_lon, self.max_lon)
            lt = random.uniform(self.min_lat, self.max_lat)
            res.append((lg, lt, self.noise_surface(lg, lt)))
        return res
    
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
                
                effective_radius = height/SCALE
                cos_lon = math.cos(longitude)
                sin_lon = math.sin(longitude)
                
                x = effective_radius * cos_lat * cos_lon
                y = effective_radius * sin_lat
                z = effective_radius * cos_lat * sin_lon
                
                vertices.append((x, y, z))
                
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
    
    def calculate_square_gradient(self, vertices, i, j):
        grid_size = self.details + 1
        
        v00 = vertices[i * grid_size + j]
        v01 = vertices[i * grid_size + (j + 1)]
        v10 = vertices[(i + 1) * grid_size + j]
        v11 = vertices[(i + 1) * grid_size + (j + 1)]
        
        v1 = (v10[0] - v00[0], v10[1] - v00[1], v10[2] - v00[2])
        v2 = (v01[0] - v00[0], v01[1] - v00[1], v01[2] - v00[2])
        
        nx = v1[1] * v2[2] - v1[2] * v2[1]
        ny = v1[2] * v2[0] - v1[0] * v2[2]
        nz = v1[0] * v2[1] - v1[1] * v2[0]
        
        length = math.sqrt(nx*nx + ny*ny + nz*nz)
        if length == 0:
            return 0
            
        nx /= length
        ny /= length
        nz /= length
        
        center = (
            (v00[0] + v01[0] + v10[0] + v11[0]) / 4,
            (v00[1] + v01[1] + v10[1] + v11[1]) / 4,
            (v00[2] + v01[2] + v10[2] + v11[2]) / 4
        )
        
        r_length = math.sqrt(center[0]**2 + center[1]**2 + center[2]**2)
        if r_length == 0:
            return 0
            
        rx = center[0] / r_length
        ry = center[1] / r_length
        rz = center[2] / r_length
        
        dot_product = nx * rx + ny * ry + nz * rz
        dot_product = max(-1.0, min(1.0, dot_product))
        
        angle = math.degrees(math.acos(abs(dot_product)))
        
        return angle
    
    def get_color_for_gradient(self, angle):
        green_angle = self.gradient_settings['green_angle']
        yellow_angle = self.gradient_settings['yellow_angle']
        orange_angle = self.gradient_settings['orange_angle']
        red_angle = self.gradient_settings['red_angle']
        
        if angle <= green_angle:
            return (0.0, 1.0, 0.0)
        elif angle <= yellow_angle:
            t = (angle - green_angle) / (yellow_angle - green_angle)
            return (t, 1.0, 0.0)
        elif angle <= orange_angle:
            t = (angle - yellow_angle) / (orange_angle - yellow_angle)
            return (1.0, 1.0 - t * 0.5, 0.0)
        else:
            t = min(1.0, (angle - orange_angle) / (red_angle - orange_angle))
            return (1.0, 0.5 - t * 0.5, 0.0)
        
    def draw_polygons(self):
        vertices, normals = self.get_vertices_and_normals()
        indices = self.generate_indices()
    
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
    
        glBegin(GL_TRIANGLES)
        for i in range(0, len(indices), 3):
            # вычисляем цвет для треугольника
            v1 = vertices[indices[i]]
            v2 = vertices[indices[i+1]]
            v3 = vertices[indices[i+2]]
            
            center = (
                (v1[0] + v2[0] + v3[0]) / 3,
                (v1[1] + v2[1] + v3[1]) / 3,
                (v1[2] + v2[2] + v3[2]) / 3
            )
            
            v1v2 = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
            v1v3 = (v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2])
            
            nx = v1v2[1] * v1v3[2] - v1v2[2] * v1v3[1]
            ny = v1v2[2] * v1v3[0] - v1v2[0] * v1v3[2]
            nz = v1v2[0] * v1v3[1] - v1v2[1] * v1v3[0]
            
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            if length > 0:
                nx /= length
                ny /= length
                nz /= length
            
            r_length = math.sqrt(center[0]**2 + center[1]**2 + center[2]**2)
            if r_length > 0:
                rx = center[0] / r_length
                ry = center[1] / r_length
                rz = center[2] / r_length
                
            dot_product = nx * rx + ny * ry + nz * rz
            dot_product = max(-1.0, min(1.0, dot_product))
                
            angle = math.degrees(math.acos(abs(dot_product)))
            
            color = self.get_color_for_gradient(angle)
            glColor3f(*color)
        
            glVertex3f(*v1)
            glVertex3f(*v2)
            glVertex3f(*v3)
        glEnd()
    
        glEnable(GL_CULL_FACE)
        glEnable(GL_LIGHTING)
    
    def draw_wireframe(self):
        vertices, _ = self.get_vertices_and_normals()
        indices = self.generate_indices()
        
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)  
        
        # Рисуем треугольники линиями с цветами градиента
        for i in range(0, len(indices), 3):
            # Получаем три вершины треугольника
            idx1, idx2, idx3 = indices[i], indices[i+1], indices[i+2]
            v1 = vertices[idx1]
            v2 = vertices[idx2]
            v3 = vertices[idx3]
            
            # Вычисляем градиент для этого треугольника
            # Для простоты используем среднее положение
            center = (
                (v1[0] + v2[0] + v3[0]) / 3,
                (v1[1] + v2[1] + v3[1]) / 3,
                (v1[2] + v2[2] + v3[2]) / 3
            )
            
            # Аппроксимируем нормаль треугольника
            v1v2 = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
            v1v3 = (v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2])
            
            nx = v1v2[1] * v1v3[2] - v1v2[2] * v1v3[1]
            ny = v1v2[2] * v1v3[0] - v1v2[0] * v1v3[2]
            nz = v1v2[0] * v1v3[1] - v1v2[1] * v1v3[0]
            
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            if length > 0:
                nx /= length
                ny /= length
                nz /= length
            
            r_length = math.sqrt(center[0]**2 + center[1]**2 + center[2]**2)
            if r_length > 0:
                rx = center[0] / r_length
                ry = center[1] / r_length
                rz = center[2] / r_length
                
                dot_product = nx * rx + ny * ry + nz * rz
                dot_product = max(-1.0, min(1.0, dot_product))
                
                angle = math.degrees(math.acos(abs(dot_product)))
                color = self.get_color_for_gradient(angle)
                glColor3f(*color)
            else:
                glColor3f(0.5, 0.5, 0.5)
            
            glBegin(GL_LINE_LOOP)
            glVertex3f(*v1)
            glVertex3f(*v2)
            glVertex3f(*v3)
            glEnd()
        
        glEnable(GL_CULL_FACE)  # Включаем culling обратно
        glEnable(GL_LIGHTING)
    
    def draw_squares(self):
        vertices, _ = self.get_vertices_and_normals()
        grid_size = self.details + 1
        
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)  # Отключаем culling для видимости с обеих сторон
        
        for i in range(self.details):
            for j in range(self.details):
                v00 = vertices[i * grid_size + j]
                v01 = vertices[i * grid_size + (j + 1)]
                v10 = vertices[(i + 1) * grid_size + j]
                v11 = vertices[(i + 1) * grid_size + (j + 1)]
                
                # Вычисляем градиент для квадрата
                gradient = self.calculate_square_gradient(vertices, i, j)
                color = self.get_color_for_gradient(gradient)
                glColor3f(*color)
                
                # Рисуем квадрат (два треугольника) одним цветом
                glBegin(GL_TRIANGLES)
                glVertex3f(*v00)
                glVertex3f(*v10)
                glVertex3f(*v11)
                
                glVertex3f(*v00)
                glVertex3f(*v11)
                glVertex3f(*v01)
                glEnd()
        
        glEnable(GL_CULL_FACE)  # Включаем culling обратно
        glEnable(GL_LIGHTING)
    
    def draw_optimized(self, mode='polygons'):
        if mode == 'wireframe':
            self.draw_wireframe()
        elif mode == 'squares':
            self.draw_squares()
        else:  # 'polygons' по умолчанию
            self.draw_polygons() 
    
    def draw_stones(self):
        glDisable(GL_LIGHTING)
        for i in range(len(self.stones)):
            glPointSize(10.0)
            glBegin(GL_POINTS)
            xx, yy, zz = self.spherical_to_cartesian(self.stones[i][0], self.stones[i][1], self.stones[i][2] + 200)
            glColor(0.7, 0, 0.7)
            glVertex3f(xx/SCALE, yy/SCALE, zz/SCALE)
            glEnd()
        glEnable(GL_LIGHTING)
    
    def set_gradient_settings(self, gradient_settings):
        self.gradient_settings = gradient_settings
    
    def set_terrain_params(self, terrain_params):
        self.terrain_params = terrain_params
    
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
            self.heig = self.heig_planet
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
        
        x, y, z = self.get_cartesian_position(self.heig/SCALE)
        
        s = self.size
        
        vertices = [
            (x, y + s, z),
            (x - s, y - s, z - s),
            (x + s, y - s, z - s),
            (x, y - s, z + s)
        ]
        
        faces = [
            (0, 1, 2),
            (0, 2, 3),
            (0, 3, 1),
            (1, 3, 2)
        ]
        
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
        self.min_distance = 0.05
        self.max_distance = 1000.0
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
        gluPerspective(45, 800/600, self.min_distance, self.max_distance)
        
        if self.follow_lander and self.lander and self.lander.exists:
            glTranslatef(0.0, 0.0, -self.distance)
            
            glRotatef(self.rotation_x, 1, 0, 0)
            glRotatef(self.rotation_y, 0, 1, 0)
            x, y, z = self.lander.get_cartesian_position(self.lander.heig/SCALE)
            glTranslatef(-x, -y, -z)
        else:
            glTranslatef(0.0, 0.0, -self.distance)
            
            glRotatef(self.rotation_x, 1, 0, 0)
            glRotatef(self.rotation_y, 0, 1, 0)
            sector_center = self.planet.sectors[self.planet.radius_render-1][self.planet.radius_render-1]
            glTranslatef(-sector_center.center_x, -sector_center.center_y, -sector_center.center_z)
    
    def zoom(self, delta):
        #if not self.follow_lander:
            self.distance = max(self.min_distance, min(self.max_distance, self.distance + delta/5))
    
    def rotate(self, delta_x, delta_y):
        self.rotation_y += delta_x * 0.5
        self.rotation_x = max(-90, min(90, self.rotation_x + delta_y * 0.5))

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
                
                new_sector = SphereSector(planet.equ_radius, planet.pol_radius, math.radians(new_lon), math.radians(new_lat), 
                                         new_lon, new_lat, planet.details,
                                         gradient_settings=planet.gradient_settings,
                                         craters=planet.craters)
                new_sectors[i][j] = new_sector
    
    planet.sectors = new_sectors
    return planet

def show_gradient_settings(planet):
    """Показать текущие настройки градиента"""
    print("\n=== Текущие настройки градиента наклона ===")
    settings = planet.gradient_settings
    print("Цветовые пороги (в градусах):")
    print(f"  Зелёный (ровный): 0° - {settings['green_angle']}°")
    print(f"  Жёлтый (пологий): {settings['green_angle']}° - {settings['yellow_angle']}°")
    print(f"  Оранжевый (средний): {settings['yellow_angle']}° - {settings['orange_angle']}°")
    print(f"  Красный (крутой): {settings['orange_angle']}° - {settings['red_angle']}°")
    return True

def adjust_gradient_settings(planet):
    """Настройка градиента наклона"""
    print("\n=== Изменение настроек градиента наклона ===")
    print("Введите новые значения (оставьте пустым для сохранения текущего):")
    
    try:
        current_settings = planet.gradient_settings
        
        green = input(f"Угол для зелёного цвета (0-90) [{current_settings['green_angle']}]: ")
        green = float(green) if green.strip() else current_settings['green_angle']
        
        yellow = input(f"Угол для жёлтого цвета (0-90) [{current_settings['yellow_angle']}]: ")
        yellow = float(yellow) if yellow.strip() else current_settings['yellow_angle']
        
        orange = input(f"Угол для оранжевого цвета (0-90) [{current_settings['orange_angle']}]: ")
        orange = float(orange) if orange.strip() else current_settings['orange_angle']
        
        red = input(f"Угол для красного цвета (0-90) [{current_settings['red_angle']}]: ")
        red = float(red) if red.strip() else current_settings['red_angle']
        
        if not (0 < green < yellow < orange < red <= 90):
            print("Ошибка: значения должны увеличиваться: 0 < зеленый < желтый < оранжевый < красный <= 90")
            return
        
        new_settings = {
            'green_angle': green,
            'yellow_angle': yellow,
            'orange_angle': orange,
            'red_angle': red
        }
        
        planet.gradient_settings = new_settings
        
        for i in range(len(planet.sectors)):
            for j in range(len(planet.sectors[i])):
                planet.sectors[i][j].set_gradient_settings(new_settings)
        
        print("Настройки градиента обновлены!")
        
    except ValueError as e:
        print(f"Ошибка ввода: {e}. Настройки не изменены.")

def show_lander_info(lander):
    """Показать информацию о лендере"""
    print("\n=== Информация о лендере ===")
    if lander and lander.exists:
        print(f"Положение: долгота={math.degrees(lander.lon):.1f}°, широта={math.degrees(lander.lat):.1f}°")
        print(f"Высота: {lander.heig:.2f}")
        print(f"Скорость: по долготе={lander.v_lon:.3f}, по широте={lander.v_lat:.3f}, вертикальная={lander.v_heig:.3f}")
        print(f"Размер: {lander.size}")
    else:
        print("Лендер отсутствует")
    return True

def create_lander_standard(planet):
    """Создание лендера в стандартном режиме"""
    print("\n=== Создание лендера в стандартном режиме ===")
    
    # Стандартные параметры
    lon, lat = 0, 0  # старт в центре
    heig = planet.equ_radius + 20000
    v_lon, v_lat, v_heig = 0.001, 0, 0 
    size = 0.05
    
    lon_rad = math.radians(lon)
    lat_rad = math.radians(lat)
    
    surface_height = planet.sectors[0][0].noise_surface(0, 0)
    heig_planet = surface_height
    
    new_lander = Lander(lon_rad, lat_rad, heig, v_lon, v_lat, v_heig, size, heig_planet)
    
    print(f"Создан лендер в стандартном режиме:")
    print(f"  Положение: долгота={lon}°, широта={lat}°")
    print(f"  Высота: {heig:.2f}")
    print(f"  Скорость: по долготе={v_lon}, по широте={v_lat}, вертикальная={v_heig}")
    print(f"  Размер: {size}")
    
    return new_lander

def create_lander_custom(planet):
    """Создание лендера с ручным вводом параметров"""
    print("\n=== Создание лендера с ручным вводом параметров ===")
    print("Введите значения (оставьте пустым для значения по умолчанию):")
    
    try:
        lon_lat_heig = input("Долгота, широта, высота [0 0 9]: ")
        if lon_lat_heig.strip():
            lon, lat, heig = map(float, lon_lat_heig.split())
        else:
            lon, lat, heig = 0, 0, planet.equ_radius + 2
        
        v_lon_lat_heig = input("Скорость по долготе, широте, высоте: ")
        if v_lon_lat_heig.strip():
            v_lon, v_lat, v_heig = map(float, v_lon_lat_heig.split())
        else:
            v_lon, v_lat, v_heig = 0.01, 0, 0
        
        size = input("Размер лендера [0.1]: ")
        size = float(size) if size.strip() else 0.1
        
        lon_rad = math.radians(lon)
        lat_rad = math.radians(lat)
        
        # Получаем высоту поверхности в указанной точке
        surface_height = planet.sectors[0][0].noise_surface(lon_rad, lat_rad)
        heig_planet = surface_height
        
        new_lander = Lander(lon_rad, lat_rad, heig, v_lon, v_lat, v_heig, size, heig_planet)
        
        print("Новый лендер создан!")
        return new_lander
        
    except ValueError as e:
        print(f"Ошибка ввода: {e}")
        return None

def planet_menu(planet, lander, camera):
    """Меню управления планетой"""
    while True:
        print("\n=== Меню управления планетой ===")
        print("1. Показать текущие параметры планеты")
        print("2. Создать новую планету")
        print("3. Вернуться в главное меню")
        
        choice = input("Выберите действие (1-3): ").strip()
        
        if choice == '1':
            print("\n=== Текущие параметры планеты ===")
            print(f"Радиус прорисовки: {planet.radius_render}")
            print(f"Текущий центр: долгота={planet.longitude}°, широта={planet.latitude}°")
            print(f"Радиус планеты: {(planet.equ_radius+planet.pol_radius)/2}")
            print(f"Детализация: {planet.details}")
            print(f"Количество секторов: {len(planet.sectors)}x{len(planet.sectors[0])}")
            
        elif choice == '2':
            print("\n=== Создание новой планеты ===")
            print("Оставьте значение пустым для значения по умолчанию")
            
            Radius_sectors = input("Радиус прорисовки [3]: ")
            Radius_sectors = int(Radius_sectors) if Radius_sectors.strip() else 3
            
            long_lat = input("Долгота и широта центра [0 0]: ")
            if long_lat.strip():
                Long, Lat = map(int, long_lat.split())
            else:
                Long, Lat = 0, 0
            
            ERadiu = input("Экваториальный радиус Планеты: ")
            ERadiu = int(ERadiu) if ERadiu.strip() else 7
            PRadiu = input("Полярный радиус Планеты: ")
            PRadiu = int(PRadiu) if PRadiu.strip() else 6.6
            
            Details = input("Детализация [8]: ")
            Details = int(Details) if Details.strip() else 8
            
            new_planet = Planet(Radius_sectors, Long, Lat, ERadiu, PRadiu, Details)
            
            new_planet.gradient_settings = planet.gradient_settings.copy()
            
            for i in range(len(new_planet.sectors)):
                for j in range(len(new_planet.sectors[i])):
                    new_planet.sectors[i][j].set_gradient_settings(new_planet.gradient_settings)
            
            planet = new_planet
            
            if lander and lander.exists:
                lander.exists = False
                print("Лендер удален при создании новой планеты")
            lander = None
            
            camera = SectorCamera(planet, lander)
            print("Новая планета создана!")
            break
            
        elif choice == '3':
            break
            
        else:
            print("Неверный выбор. Попробуйте снова.")
    
    return planet, lander, camera

def gradient_menu(planet):
    """Меню настройки градиента"""
    while True:
        print("\n=== Меню настройки градиента ===")
        print("1. Показать текущие настройки градиента")
        print("2. Изменить настройки градиента")
        print("3. Вернуться в главное меню")
        
        choice = input("Выберите действие (1-3): ").strip()
        
        if choice == '1':
            show_gradient_settings(planet)
            
        elif choice == '2':
            adjust_gradient_settings(planet)
            break
            
        elif choice == '3':
            break
            
        else:
            print("Неверный выбор. Попробуйте снова.")
    
    return planet

def lander_menu(planet, lander, camera):
    """Меню управления лендером"""
    while True:
        print("\n=== Меню управления лендером ===")
        print("1. Показать информацию о лендере")
        print("2. Создать лендер (стандартный режим)")
        print("3. Создать лендер (ручной ввод)")
        print("4. Удалить лендер")
        print("5. Вернуться в главное меню")
        
        choice = input("Выберите действие (1-5): ").strip()
        
        if choice == '1':
            show_lander_info(lander)
            
        elif choice == '2':
            if lander and lander.exists:
                print("Сначала удалите существующий лендер!")
            else:
                new_lander = create_lander_standard(planet)
                if new_lander:
                    lander = new_lander
                    camera.set_lander(lander)
                    break
            
        elif choice == '3':
            if lander and lander.exists:
                print("Сначала удалите существующий лендер!")
            else:
                new_lander = create_lander_custom(planet)
                if new_lander:
                    lander = new_lander
                    camera.set_lander(lander)
                    break
            
        elif choice == '4':
            if lander and lander.exists:
                lander.exists = False
                print("Лендер удален")
                lander = None
                camera.set_lander(None)
                break
            else:
                print("Лендер не существует")
            
        elif choice == '5':
            break
            
        else:
            print("Неверный выбор. Попробуйте снова.")
    
    return planet, lander, camera

def main():
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("LandingSim")
    
    planet = Planet(1, 0, 0, 1738140, 1735970, 45)
    
    updating_sectors = False

    lander = None
    camera = SectorCamera(planet, lander)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    
    clock = pygame.time.Clock()
    show_axes = True
    render_mode = 'polygons'  # 'polygons', 'wireframe', 'squares'

    
    print("=== LandingSim ===")
    print("Управление:")
    print("W - переключить режим (полигоны/линии/квадраты)")
    print("A - показать/скрыть оси координат")
    print("C - меню управления планетой")
    print("G - меню настройки градиента")
    print("R - Переключить обновление секторов")
    print("F - меню управления лендером")
    print("SPACE - переключить привязку камеры к лендеру")
    print("Колесо мыши - приближение/отдаление")
    print("ЛКМ + движение - вращение камеры")
    print(f"Текущий режим: {render_mode.upper()}")
    print("\nЦвета наклона рельефа:")
    print("Зелёный: 0-5° (ровный)")
    print("Жёлтый: 5-15° (пологий)")
    print("Оранжевый: 15-30° (средний)")
    print("Красный: 30°+ (крутой)")
    print("\nСтандартный режим лендера:")
    print("  - Положение: центр (0°, 0°)")
    print("  - Скорость: 0.01 по долготе")
    print("  - Размер: 0.1")
    
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
                    # Переключение между режимами: polygons -> wireframe -> squares -> polygons
                    if render_mode == 'polygons':
                        render_mode = 'wireframe'
                    elif render_mode == 'wireframe':
                        render_mode = 'squares'
                    else:  # squares
                        render_mode = 'polygons'
                    
                    mode_names = {
                        'polygons': 'ПОЛИГОНЫ',
                        'wireframe': 'ЛИНИИ',
                        'squares': 'КВАДРАТЫ'
                    }
                    print(f"Режим изменен на: {mode_names[render_mode]}")
                elif event.key == pygame.K_a:
                    show_axes = not show_axes
                    print(f"Оси координат: {'ВКЛ' if show_axes else 'ВЫКЛ'}")
                elif event.key == pygame.K_SPACE:
                    camera.toggle_follow_lander()
                elif event.key == pygame.K_c:
                    planet, lander, camera = planet_menu(planet, lander, camera)
                elif event.key == pygame.K_g:
                    planet = gradient_menu(planet)
                elif event.key == pygame.K_f:
                    planet, lander, camera = lander_menu(planet, lander, camera)
                elif event.key == pygame.K_r:
                    updating_sectors = not updating_sectors
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: 
                    camera.zoom(-1.0)
                elif event.button == 5: 
                    camera.zoom(1.0)
        
        if pygame.mouse.get_pressed()[0]:
            rel_x, rel_y = pygame.mouse.get_rel()
            camera.rotate(rel_x, rel_y)
        else:
            pygame.mouse.get_rel()
        
        if lander and lander.exists:
            lander.update_velocity(dt)
            surface_height = planet.sectors[0][0].noise_surface(lander.lon, lander.lat)
            lander.update_height(surface_height)
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        camera.update_camera_position()
        
        # Отрисовка секторов планеты
        for i in range(len(planet.sectors)):
            for j in range(len(planet.sectors[i])):
                planet.sectors[i][j].draw_optimized(mode=render_mode)
                planet.sectors[i][j].draw_stones()
        
        # Отрисовка лендера
        if lander and lander.exists:
            lander.draw()
        
        # Обновление секторов при движении лендера
        if lander and lander.exists and updating_sectors:
            ceil_lon = math.ceil(math.degrees(lander.lon))
            ceil_lat = math.ceil(math.degrees(lander.lat))
            delta_lon = ceil_lon - planet.longitude
            delta_lat = ceil_lat - planet.latitude
            if math.fabs(delta_lon) > 0.5 or math.fabs(delta_lat) > 0.5:
                planet.longitude = ceil_lon
                planet.latitude = ceil_lat
                planet = update_sectors(planet, delta_lon, delta_lat)
        
        # Отрисовка осей координат
        if show_axes:
            draw_coordinate_axes()
        
        # Обновление заголовка окна
        mode_names = {
            'polygons': 'ПОЛИГОНЫ',
            'wireframe': 'ЛИНИИ',
            'squares': 'КВАДРАТЫ'
        }
        mode_text = mode_names[render_mode]
        lander_text = " + LANDER" if lander and lander.exists else ""
        follow_text = " [FOLLOW]" if camera.follow_lander else ""
        pygame.display.set_caption(f"LandingSim - {mode_text}{lander_text}{follow_text}")
        pygame.display.flip()

if __name__ == "__main__":
    main()
