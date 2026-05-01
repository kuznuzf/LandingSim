import pygame
import math
import random
import os
from perlin_noise import PerlinNoise
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import socket
import select

SCALE = 25000
G = 6.67e-11

def NameToCoords(name):
    a, b = name.split("_")
    return a, b

def CoordsToName(a, b):
    return str(a)+"_"+str(b)

def scalar_product(a, b): #Скалярное произведение Vector3 a * b
    return a.x * b.x + a.y * b.y + a.z * b.z

def vector_product(a, b): #Векторное произведение Vector3 a х b
    return Vector3(a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y*b.x)

def summa(a, b):
    return Vector3(a.x + b.x, a.y + b.y, a.z + b.z)

def number_product(n, v):
    return Vector3(v.x * n, v.y * n, v.z * n)

def angle(a, b):
    cos_angle = scalar_product(a, b) / (a.length() * b.length())
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.acos(cos_angle)

def projection_vector_on_vector(a, v):
    return number_product(scalar_product(v, a)/v.length(), v.normalized())

def rotate_vector(a, alpha, beta, gamma):
    sin_a = math.sin(alpha)
    sin_b = math.sin(beta)
    sin_g = math.sin(gamma)
    cos_a = math.cos(alpha)
    cos_b = math.cos(beta)
    cos_g = math.cos(gamma)
    r_x = a.x*cos_b*cos_g - a.y*sin_g*cos_b + a.z*sin_b
    r_y = a.x*(sin_a*sin_b*cos_g + sin_g*cos_a) + a.y*(-sin_a*sin_b*sin_g + cos_a*cos_g) - a.z*(sin_a*cos_b)
    r_z = a.x*(sin_a*sin_g - cos_a*sin_b*cos_g) + a.y*(sin_a*cos_g + sin_b*sin_g*cos_a) + a.z*(cos_a*cos_b)
    return Vector3(r_x, r_y, r_z)

def rotate_around_axis(a, axis, angle_rad):
    k = axis.normalized()
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    v_rot = summa(number_product(cos_a, a), number_product(sin_a, vector_product(k, a)))
    dot = scalar_product(k, a)
    if abs(dot) > 1e-12:
        v_rot = summa(v_rot, number_product((1 - cos_a) * dot, k))
    return v_rot

def normal_3_point(a, b, c):
    ab = Vector3(b.x - a.x, b.y - a.y, b.z - a.z)
    ac = Vector3(c.x - a.x, c.y - a.y, c.z - a.z)
    return vector_product(ab, ac)

class Vector3:
    def __init__(self, x, y, z): #force = Vector3(x, y, z)
        self.x = x
        self.y = y
        self.z = z
    def length(self): return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    def sqrlength(self): return self.x**2 + self.y**2 + self.z**2

    def normalized(self):
        l = self.length()
        return Vector3(self.x/l, self.y/l, self.z/l)
    
def get_radius(equ, pol, latitude):
    return math.sqrt((equ*math.cos(latitude))**2 + (pol*math.sin(latitude))**2)

class Planet:
    def __init__(self, radius_render=1, longitude=0, latitude=0, equ_radius=7, pol_radius=6.6, details=32, mass=1, angular_velocity=0):
        self.radius_render = radius_render
        self.longitude = longitude 
        self.latitude = latitude
        self.equ_radius = equ_radius
        self.pol_radius = pol_radius
        self.details = details
        self.mass = mass
        self.angular_velocity = angular_velocity
        
        self.gradient_settings = {
            'green_angle': 5,
            'yellow_angle': 15,
            'orange_angle': 30,
            'red_angle': 90
        }
        
        self.craters = self._generate_craters(10, 70, longitude, latitude, radius_render)
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
    def _generate_craters(self, big_c=10, small_c=20, longit=0, latit=0, radiu=1):
        craters = []
        for _ in range(big_c):
            lon = random.uniform(math.radians(longit - radiu), math.radians(longit + radiu))
            lat = random.uniform(math.radians(latit - radiu), math.radians(latit + radiu))
            radius = random.uniform(0.002 * self.radius_render, 0.01 * self.radius_render)
            planet_radius = get_radius(self.equ_radius, self.pol_radius, lat)
            noise_cr = random.randint(2, 1000)
            crater = {
                'lon': lon,
                'lat': lat,
                'R': radius,                     # полный радиус
                'D': (planet_radius * radius) / 7, # глубина (линейная)
                'Rc': 0.85 * radius,              # радиус впадины
                'Rp': 0.2 * radius,               # радиус пика
                'h_peak': 0.2 * (planet_radius * radius) / 5,
                'h_rim': 0.075 * (planet_radius * radius) / 5,
                'N': noise_cr
            }
            craters.append(crater)
        for _ in range(small_c):
            lon = random.uniform(math.radians(longit - radiu), math.radians(longit + radiu))
            lat = random.uniform(math.radians(latit - radiu), math.radians(latit + radiu))
            radius = random.uniform(0.0003 * self.radius_render, 0.003 * self.radius_render)
            planet_radius = get_radius(self.equ_radius, self.pol_radius, lat)
            noise_cr = random.randint(2, 1000)
            crater = {
                'lon': lon,
                'lat': lat,
                'R': radius,                     # полный радиус
                'D': (planet_radius * radius) / 7, # глубина (линейная)
                'Rc': 0.85 * radius,              # радиус впадины
                'Rp': 0.2 * radius,               # радиус пика
                'h_peak': 0.2 * (planet_radius * radius) / 5,
                'h_rim': 0.075 * (planet_radius * radius) / 5,
                'N': noise_cr
            }
            craters.append(crater)
        return craters

def crater_effect(crater, r, long, lat):
    R = crater['R']
    if r > R:
        return 0.0
    Rc = crater.get('Rc', 0.7 * R)
    Rp = crater.get('Rp', 0.2 * R)
    h_peak = crater.get('h_peak', 0.0)
    h_crater = crater.get('D', 0.0)
    h_rim = crater.get('h_rim', 0.0)
    crater_noise = PerlinNoise(4, crater.get('N'))
    deborder = (R**6 - r**6)/R**6
    scale = 1.0 / (R + 0.001)
    noise = crater_noise([long * scale, lat * scale]) * h_crater * deborder / 3
    
    if r <= Rp:
        t = (math.pi * r) / (2 * Rp)
        return h_peak * math.cos(t)**2 - h_crater * (1 - (r/Rc)**2) + noise
    elif r <= Rc:
        return -h_crater * (1 - (r/Rc)**2) + noise
    else:
        t = (math.pi * (r - Rc)) / (1.75 * (R - Rc))
        return h_rim * math.sin(t**2) + noise

def noise_surface(sector, longitude, latitude):
    radius = get_radius(sector.equ_radius, sector.pol_radius, latitude)
    noise_base = PerlinNoise(octaves=2, seed=4522)
    noise_mountaines = PerlinNoise(octaves=5, seed=3435)
    noise_micro = PerlinNoise(octaves=10, seed=6522)
    h = 0.01 * noise_base([longitude*5, latitude*5])
    mountaines = noise_mountaines([longitude*4, latitude*4]) + 0.2 * noise_base([longitude*20, latitude*20])
    if mountaines > 0.2:
        h += 0.06 * (mountaines - 0.2)
    
    if sector.craters:
        total_delta = 0.0
        sin_lat = math.sin(latitude)
        cos_lat = math.cos(latitude)
        for crater in sector.craters:
            clon = crater['lon']
            clat = crater['lat']
            sin_clat = math.sin(clat)
            cos_clat = math.cos(clat)
            cos_dlon = math.cos(longitude - clon)
            cos_angle = sin_lat * sin_clat + cos_lat * cos_clat * cos_dlon
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle = math.acos(cos_angle)
            delta = crater_effect(crater, angle, longitude, latitude)
            total_delta += delta
        h += total_delta
    h += 0.014 * noise_micro([longitude*10, latitude*10])
    depolarizator = 1 - latitude**12/225.652
    return radius + h * depolarizator

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
        self._height_color_cashe = []
        self.craters = craters if craters is not None else []
        self.center_x, self.center_y, self.center_z = self.spherical_to_cartesian(self.longitude, self.latitude, noise_surface(self,self.longitude,self.latitude)/SCALE+0.1)
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
    
    def generate_height_color(self):
        if len(self._height_color_cashe) != 0:
            return self._height_color_cashe
        
        cols = []
        vertices, _ = self.get_vertices_and_normals()
        indices = self.generate_indices()
        for i in range(0, len(indices), 3):
            rho = vertices[indices[i]][0]**2 + vertices[indices[i]][1]**2 + vertices[indices[i]][2]**2
            cols.append(1 - 10*(abs(rho - (self.equ_radius/SCALE)**2)/rho)**0.5)
        self._height_color_cashe = cols
        return cols
    
    def generate_stones(self, count):
        res = [] #[(longitude, latitude, height), (..., ..., ...), ...]
        for _ in range(count):
            lg = random.uniform(self.min_lon, self.max_lon)
            lt = random.uniform(self.min_lat, self.max_lat)
            res.append((lg, lt, noise_surface(self, lg, lt)))
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
                height = noise_surface(self, longitude, latitude)
                
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
        vertices, _ = self.get_vertices_and_normals()
        indices = self.generate_indices()
    
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
    
        glBegin(GL_TRIANGLES)
        for i in range(0, len(indices), 3):
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
    
    def draw_mono_color(self):
        vertices, _ = self.get_vertices_and_normals()
        indices = self.generate_indices()
        cols = self.generate_height_color()
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glBegin(GL_TRIANGLES)
        for i in range(0, len(indices), 3):
            
            glColor3f(cols[i//3], cols[i//3], cols[i//3])
            glVertex3f(*vertices[indices[i]])

            glVertex3f(*vertices[indices[i+1]])

            glVertex3f(*vertices[indices[i+2]])
        glEnd()
        glEnable(GL_LIGHTING)
        glEnable(GL_CULL_FACE)
        
    
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
        if mode == 'polygons':
            self.draw_polygons() 
        elif mode == 'wireframe':
            self.draw_wireframe()
        elif mode == 'squares':
            self.draw_squares()
        elif mode == 'mono': 
            self.draw_mono_color()
    
    def draw_stones(self, camera):
        scale = 20 / (camera.distance + 1)
        glDisable(GL_LIGHTING)
        for i in range(len(self.stones)):
            glPointSize(scale)
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
def get_cartesian_position(lon, lat, heig):
        cos_lat = math.cos(lat)
        x = heig * cos_lat * math.cos(lon)
        y = heig * math.sin(lat)
        z = heig * cos_lat * math.sin(lon)
        return (x, y, z)
class Lander: 
    def __init__(self, lon=0, lat=0, heig=1.0, rotation=[0,0,0], vel=Vector3(0,0,0), mass=1, mass_propell=0.5, thrust=0.1, size=0.1, heig_planet=1.0):
        x, y, z = get_cartesian_position(lon, lat, heig)
        self.pos = Vector3(x, y, z)
        self.rotation = rotation
        self.vectors_rotation = [rotate_vector(Vector3(1,0,0),rotation[0],rotation[1],rotation[2]), 
                                 rotate_vector(Vector3(0,1,0),rotation[0],rotation[1],rotation[2]), 
                                 rotate_vector(Vector3(0,0,1),rotation[0],rotation[1],rotation[2])] #Это направление вперёд
        self.vel = vel
        self.acc = Vector3(0, 0, 0)
        self.mass = mass
        self.mass_propell = mass_propell
        self.mass_propell_max = mass_propell
        self.I = 3300
        self.usage_propell = thrust/self.I
        self.size = size
        self.heig_planet = heig_planet
        self.thrust_force = Vector3(0,0,0)
        self.manevr = None
        self.exists = True
        
    def update_physic(self, planet, is_thrust, dt):
        if self.pos.length() - 0.5 < self.heig_planet:
            if self.vel.length() != 0:
                print("Посадка совершена")
                print(f"Скорость {self.vel.length()} м/с")
            self.vel = Vector3(0, 0, 0)
            return
        def acceleration(pos, vel, mass, thrust_on):
            r = pos.length()
            a_grav = number_product(- G * planet.mass / r**3, pos)
            omega = -planet.angular_velocity
            a_cf = Vector3(omega**2 * pos.x, 0, omega**2 * pos.z)
            v_omega = Vector3(0, omega, 0)
            a_cor = vector_product(v_omega, vel)
            a_cor = number_product(-2, a_cor)
            a = summa(a_grav, summa(a_cf, a_cor))
            if thrust_on and self.mass_propell > 0:
                dmdt = self.usage_propell
                thrust_force = number_product(self.I * dmdt, self.vectors_rotation[2])
                a = summa(a, number_product(1/mass, thrust_force))
            return a
        a_o = acceleration(self.pos, self.vel, self.mass, is_thrust)
        self.acc = a_o
        self.pos = summa(self.pos, summa(number_product(dt, self.vel), number_product(0.5*dt*dt, a_o)))
        v_half = summa(self.vel, number_product(0.5*dt, a_o))
        if is_thrust and self.mass_propell > 0:
            dm = self.usage_propell * dt
            self.mass_propell -= dm
            self.mass -= dm
            if self.mass_propell < 0:
                self.mass_propell = 0
                self.mass = self.mass + self.mass_propell
        self.vel = summa(v_half, number_product(0.5*dt,acceleration(self.pos, v_half, self.mass, is_thrust) ))
    
    def update_height(self, heig_planet):
        self.heig_planet = heig_planet
    
    def draw(self, mass_planet):
        if not self.exists:
            return
        glDisable(GL_LIGHTING)
        x, y, z = self.pos.x/SCALE, self.pos.y/SCALE, self.pos.z/SCALE
        s = self.size
        local_vertices = [
            Vector3(0, s, 0),
            Vector3(-s/2, -s, -s/2),
            Vector3( s/2, -s, -s/2),
            Vector3( s/2, -s,  s/2),
            Vector3(-s/2, -s,  s/2) 
        ]
        i = self.vectors_rotation[0]
        k = self.vectors_rotation[1]
        j = self.vectors_rotation[2]
        vertices = []
        for v in local_vertices:
            wx = x + v.x * i.x + v.y * j.x + v.z * k.x
            wy = y + v.x * i.y + v.y * j.y + v.z * k.y
            wz = z + v.x * i.z + v.y * j.z + v.z * k.z
            vertices.append((wx, wy, wz))
        faces = [
            (0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1),
            (1, 3, 2), (1, 4, 3) 
        ]
        glBegin(GL_TRIANGLES)
        color_face = [(0.75+i/20, 0, 0) for i in range(6)]
        for j in range(6):
            glColor3f(color_face[j][0],color_face[j][1],color_face[j][2])
            for vertex_idx in faces[j]:
                glVertex3f(*vertices[vertex_idx])
        glEnd()
        glBegin(GL_LINE_STRIP)
        glColor(1, 1, 0)
        glVertex3f(x, y, z)
        glVertex3f(x + self.vel.x, y + self.vel.y, z + self.vel.z)
        glEnd()
        glBegin(GL_LINE_STRIP)
        glColor(0, 1, 1)
        glVertex3f(x, y, z)
        glVertex3f(x + self.acc.x, y + self.acc.y, z + self.acc.z)
        glEnd()

        angularMomentum = vector_product(self.pos, self.vel);
        if angularMomentum.sqrlength() == 0: return
        eccentricityV = summa(number_product(1/(G * mass_planet), vector_product(self.vel, angularMomentum)), number_product(-1, self.pos.normalized()))
        e = eccentricityV.length()
        if e < 1:
            dist = self.pos.length()
            v2 = self.vel.length()**2
            specificEnergy = v2 / 2 - G * mass_planet / dist
            a = -G * mass_planet / (2 * specificEnergy)

            glBegin(GL_LINE_LOOP)
            glColor3f(1, 0.2, 0.2)
            if e == 0:
                axisX = self.pos.normalized()
            else:
                axisX = eccentricityV.normalized()
            axisY = vector_product(angularMomentum.normalized(), axisX).normalized()
            for i in range(1500):
                theta = 2 * math.pi * i / 1500
                r = a * (1 - e * e) / (1 + e * math.cos(theta))
                x = r * math.cos(theta)
                y = r * math.sin(theta)
                pos = summa(number_product(x, axisX), number_product(y, axisY))
                glVertex3f(pos.x / SCALE, pos.y / SCALE, pos.z / SCALE)
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
            x, y, z = self.lander.pos.x/SCALE, self.lander.pos.y/SCALE, self.lander.pos.z/SCALE
            glTranslatef(-x, -y, -z)
        else:
            glTranslatef(0.0, 0.0, -self.distance)
            
            glRotatef(self.rotation_x, 1, 0, 0)
            glRotatef(self.rotation_y, 0, 1, 0)
            sector_center = self.planet.sectors[self.planet.radius_render-1][self.planet.radius_render-1]
            glTranslatef(-sector_center.center_x, -sector_center.center_y, -sector_center.center_z)
    
    def zoom(self, delta):
        self.distance = max(self.min_distance, min(self.max_distance, self.distance + delta/5))
    
    def rotate(self, delta_x, delta_y):
        self.rotation_y += delta_x * 0.5
        self.rotation_x = max(-90, min(90, self.rotation_x + delta_y * 0.5))

def rotate_lander(lander, angular_speed, dt, pitch_up, pitch_down, yaw_left, yaw_right):
    v_i = Vector3(1, 0, 0)
    v_j = Vector3(0, 1, 0)
    v_k = Vector3(0, 0, 1)
    if pitch_down:
        lander.vectors_rotation[1] = rotate_around_axis(lander.vectors_rotation[1], lander.vectors_rotation[0], angular_speed * dt)
        lander.vectors_rotation[2] = rotate_around_axis(lander.vectors_rotation[2], lander.vectors_rotation[0], angular_speed * dt)
        lander.vectors_rotation[1] = lander.vectors_rotation[1].normalized()
        lander.vectors_rotation[2] = lander.vectors_rotation[2].normalized()
        lander.rotation = [angle(v_i, lander.vectors_rotation[0]),
                           angle(v_j, lander.vectors_rotation[1]),
                           angle(v_k, lander.vectors_rotation[2])]
    if pitch_up:
        lander.vectors_rotation[1] = rotate_around_axis(lander.vectors_rotation[1], lander.vectors_rotation[0], -angular_speed * dt)
        lander.vectors_rotation[2] = rotate_around_axis(lander.vectors_rotation[2], lander.vectors_rotation[0], -angular_speed * dt)
        lander.vectors_rotation[1] = lander.vectors_rotation[1].normalized()
        lander.vectors_rotation[2] = lander.vectors_rotation[2].normalized()
        lander.rotation = [angle(v_i, lander.vectors_rotation[0]),
                           angle(v_j, lander.vectors_rotation[1]),
                           angle(v_k, lander.vectors_rotation[2])]
    if yaw_right:
        lander.vectors_rotation[0] = rotate_around_axis(lander.vectors_rotation[0], lander.vectors_rotation[1], angular_speed * dt)
        lander.vectors_rotation[2] = rotate_around_axis(lander.vectors_rotation[2], lander.vectors_rotation[1], angular_speed * dt)
        lander.vectors_rotation[0] = lander.vectors_rotation[0].normalized()
        lander.vectors_rotation[2] = lander.vectors_rotation[2].normalized()
        lander.rotation = [angle(v_i, lander.vectors_rotation[0]),
                           angle(v_j, lander.vectors_rotation[1]),
                           angle(v_k, lander.vectors_rotation[2])]
    if yaw_left:
        lander.vectors_rotation[0] = rotate_around_axis(lander.vectors_rotation[0], lander.vectors_rotation[1], -angular_speed * dt)
        lander.vectors_rotation[2] = rotate_around_axis(lander.vectors_rotation[2], lander.vectors_rotation[1], -angular_speed * dt)
        lander.vectors_rotation[0] = lander.vectors_rotation[0].normalized()
        lander.vectors_rotation[2] = lander.vectors_rotation[2].normalized()
        lander.rotation = [angle(v_i, lander.vectors_rotation[0]),
                           angle(v_j, lander.vectors_rotation[1]),
                           angle(v_k, lander.vectors_rotation[2])]
    return lander
def rotate_lander_manevr(lander, dir, angular_speed, dt):
    v_i = Vector3(1, 0, 0)
    v_j = Vector3(0, 1, 0)
    v_k = Vector3(0, 0, 1)
    if angle(lander.vectors_rotation[2], dir) < 0.001:
        return lander
    axis_rot = vector_product(lander.vectors_rotation[2], dir).normalized()
    lander.vectors_rotation[0] = rotate_around_axis(lander.vectors_rotation[0], axis_rot, angular_speed * dt)
    lander.vectors_rotation[1] = rotate_around_axis(lander.vectors_rotation[1], axis_rot, angular_speed * dt)
    lander.vectors_rotation[2] = rotate_around_axis(lander.vectors_rotation[2], axis_rot, angular_speed * dt)
    lander.vectors_rotation[0] = lander.vectors_rotation[0].normalized()
    lander.vectors_rotation[1] = lander.vectors_rotation[1].normalized()
    lander.vectors_rotation[2] = lander.vectors_rotation[2].normalized()
    lander.rotation = [angle(v_i, lander.vectors_rotation[0]),
                        angle(v_j, lander.vectors_rotation[1]),
                        angle(v_k, lander.vectors_rotation[2])]
    return lander

def draw_coordinate_frame(axes_cashe, e_rad, p_rad, n=100):
    if len(axes_cashe) != 0:
        glDisable(GL_LIGHTING)
        for i in range(180):
            glBegin(GL_LINE_LOOP)
            glColor3f(0.2, 0.2, 1)
            for j in range(n):
                glVertex3f(axes_cashe[i][j][0], axes_cashe[i][j][1], axes_cashe[i][j][2])
            glEnd()
        for i in range(161):
            glBegin(GL_LINE_LOOP)
            glColor3f(0.2, 0.2, 1)
            for j in range(n):
                glVertex3f(axes_cashe[180 + i][j][0], axes_cashe[180 + i][j][1], axes_cashe[180 + i][j][2])
            glEnd()
        glEnable(GL_LIGHTING)
    else:
        glDisable(GL_LIGHTING)
        vertexs = [[] for _ in range(341)]
        for i in range(180):
            long = math.radians(i - 0.5)
            glBegin(GL_LINE_LOOP)
            glColor3f(0.2, 0.2, 1)
            for j in range(n):
                lat = 2*math.pi/n * j
                heig = get_radius(e_rad, p_rad, lat)
                x = heig * math.cos(lat) * math.cos(long)
                y = heig * math.sin(lat)
                z = heig * math.cos(lat) * math.sin(long)
                glVertex3f(x, y, z)
                vertexs[i].append((x, y, z))
            glEnd()
        for i in range(161):
            lat = math.radians(i - 80.5)
            glBegin(GL_LINE_LOOP)
            glColor3f(0.2, 0.2, 1)
            for j in range(n):
                long = 2*math.pi/n * j
                heig = get_radius(e_rad, p_rad, lat)
                x = heig * math.cos(lat) * math.cos(long)
                y = heig * math.sin(lat)
                z = heig * math.cos(lat) * math.sin(long)
                glVertex3f(x, y, z)
                vertexs[180 + i].append((x, y, z))
            glEnd()
        glEnable(GL_LIGHTING)
        axes_cashe.clear()
        axes_cashe.extend(vertexs)

def draw_target_ray(pos, target_pos):
    target_dir = target_pos.normalized()
    ray_length = pos.length()
    end_point = number_product(ray_length, target_dir)
    glDisable(GL_LIGHTING)
    glBegin(GL_LINES)
    glColor3f(1.0, 1.0, 0.0)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(end_point.x / SCALE, end_point.y / SCALE, end_point.z / SCALE)
    glEnd()
    glEnable(GL_LIGHTING)

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
    lon, lat = 0, 0
    heig = noise_surface(planet.sectors[0][0], lon, lat) + 40000
    modul = math.sqrt(G * planet.mass / heig)
    velocity = Vector3(0, 0, modul)
    massa = 1750
    mass_propellant = 1750 - 161
    size = 0.01
    heig_planet = 0
    new_lander = Lander(lon, lat, heig, [0,0,0], velocity, massa, mass_propellant, 2*4800, size, heig_planet)
    
    return new_lander

def create_lander_custom(planet):
    print("\n=== Создание лендера с ручным вводом параметров ===")
    print("Введите значения:")
    try:
        lon_lat_heig = input("Долгота, широта, высота (над поверхностью): ")
        if lon_lat_heig.strip():
            lon, lat, heig = map(float, lon_lat_heig.split())
        else:
            lon, lat, heig = 0, 0, 40000
        lon_rad = math.radians(lon)
        lat_rad = math.radians(lat)
        surface_height = noise_surface(planet.sectors[0][0], lon_rad, lat_rad)
        heig = surface_height + heig
        modul = math.sqrt(G * planet.mass/heig)
        x, y, z = get_cartesian_position(lon_rad, lat_rad, heig)
        r = Vector3(x, y, z)
        east = vector_product(r, Vector3(0, 1, 0))
        if east.sqrlength() < 1e-12:
            east = Vector3(1, 0, 0)
        else:
            east = east.normalized()
        velocity = number_product(modul, east)
        massa = input("Полная и сухая масса аппарата: ")
        if massa.strip():
            mass, mass_s = map(float, massa.split())
        else:
            mass, mass_s = 1750.0, 615.0
        size = input("Размер лендера [0.1]: ")
        size = float(size) if size.strip() else 0.1
        thru = input("Тяга: ")
        thru = float(size) if size.strip() else 5000
        heig_planet = surface_height
        new_lander = Lander(lon_rad, lat_rad, heig, [0,0,0], velocity, mass, mass-mass_s, thru, size, heig_planet)
        print("Новый лендер создан!")
        return new_lander 
    except ValueError as e:
        print(f"Ошибка ввода: {e}")
        return None

def planet_menu(planet, lander, camera):
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
            ERadiu = int(ERadiu) if ERadiu.strip() else 1738140
            PRadiu = input("Полярный радиус Планеты: ")
            PRadiu = int(PRadiu) if PRadiu.strip() else 1735970
            
            Details = input("Детализация [8]: ")
            Details = int(Details) if Details.strip() else 24
            massa = input("Масса: ")
            massa = float(massa) if massa.strip() else 1e22
            a_v = input("Угловая скорость вращения: ")
            a_v = int(a_v) if a_v.strip() else 2.6617e-10
            
            new_planet = Planet(Radius_sectors, Long, Lat, ERadiu, PRadiu, Details, massa, a_v)
            
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

def control_functions(lander, planet, camera, manual_operation, time_speed, data):
    parts = data.split()
    try:
        if parts[0] == "s_l":
            if lander and lander.exists:
                print("Сначала удалите существующий лендер!")
            else:
                new_lander = create_lander_standard(planet)
                if new_lander:
                    lander = new_lander
                    camera.set_lander(lander)
        elif parts[0] == "d_l":
            if lander and lander.exists:
                lander.exists = False
                print("Лендер удален")
                lander = None
                camera.set_lander(None)
            else:
                print("Лендер не существует")
        elif parts[0] == "m_o":
            manual_operation = not manual_operation
        elif parts[0] == "ts_":
            time_speed = 2 * int(parts[1])
    except: print("G")
    return lander, camera, manual_operation, time_speed

def get_naklon_dv(r, v, r_target):
    n_orbit = vector_product(r, v).normalized()
    e_target = r_target.normalized()
    abs_cos_phi = abs(scalar_product(n_orbit, e_target))
    dangle = math.pi/2 - math.acos(abs_cos_phi)
    pr_target_on_n = number_product(scalar_product(n_orbit, e_target), n_orbit)
    e_apsid = summa(e_target, number_product(-1, pr_target_on_n)).normalized()
    e_nodes = vector_product(e_target, e_apsid).normalized()
    pr1, pr2 = scalar_product(e_nodes, v), scalar_product(number_product(-1, e_nodes), v)
    if pr1 > 0:
        return (dangle, e_nodes)
    elif pr1 == 0 or pr2 > 0:
        return (dangle, number_product(-1, e_nodes))
def predict_node_time(lander, planet, r_target, t0, max_time, dt=1.0, threshold=0.99):
    global FIXED_NODE
    r_inert = lander.pos
    v_inert = lander.vel

    FIXED_NODE = get_naklon_dv(r_inert, v_inert, r_target)
    if FIXED_NODE[1].sqrlength() < 1e-12:
        return None, 0
    best_node = FIXED_NODE[1]

    def step(p, v, dt):
        massa = lander.mass
        Force = number_product(- G * planet.mass * massa / p.length()**3 , p)
        omega = -planet.angular_velocity
        centrifugal = Vector3(omega**2 * p.x, 0, omega**2 * p.z)
        centrifugal = number_product(massa, centrifugal)
        v_omega = Vector3(0, omega, 0)
        coriolis = vector_product(v_omega, v)
        coriolis = number_product(-2 * massa, coriolis)
        Force = summa(Force, centrifugal)
        Force = summa(Force, coriolis)
        acc = number_product(1/massa, Force)
        v_new = summa(v, number_product(dt, acc))
        p_new = summa(p, number_product(dt, v_new))
        return  p_new, v_new

    r_dir = r_inert.normalized()
    dot = abs(scalar_product(r_dir, best_node))
    inside = dot > threshold
    t_pred = 0.0
    pos, vel = r_inert, v_inert
    while inside and t_pred < max_time:
        pos, vel = step(pos, vel, dt)
        t_pred += dt
        r_dir = pos.normalized()
        dot = abs(scalar_product(r_dir, best_node))
        inside = dot > threshold

    while t_pred < max_time:
        pos, vel = step(pos, vel, dt)
        t_pred += dt
        r_dir = pos.normalized()
        dot = abs(scalar_product(r_dir, best_node))
        if dot > threshold:
            dv = 2 * v_inert.length() * math.sin(FIXED_NODE[0]/2)
            return t_pred, FIXED_NODE[0], dv

    print(f"Узел не найден за {max_time:.1f} c")
    return None

def direction_naklon_manevr(n, r):
    return number_product(-1, projection_vector_on_vector(r, n).normalized())

def verticalization(lander, planet, r_target, dt):
    def step(p, v, dt):
        massa = lander.mass
        Force = number_product(- G * planet.mass * massa / p.length()**3 , p)
        omega = -planet.angular_velocity
        centrifugal = Vector3(omega**2 * p.x, 0, omega**2 * p.z)
        centrifugal = number_product(massa, centrifugal)
        v_omega = Vector3(0, omega, 0)
        coriolis = vector_product(v_omega, v)
        coriolis = number_product(-2 * massa, coriolis)
        Force = summa(Force, centrifugal)
        Force = summa(Force, coriolis)
        acc = number_product(1/massa, Force)
        v_new = summa(v, number_product(dt, acc))
        p_new = summa(p, number_product(dt, v_new))
        return  p_new, v_new
    def step_thrust(p, v, dt, m_p, m, u_p, I, foward):
        Force = number_product(- G * planet.mass * m / p.length()**3 , p)
        omega = -planet.angular_velocity
        centrifugal = Vector3(omega**2 * p.x, 0, omega**2 * p.z)
        centrifugal = number_product(m, centrifugal)
        v_omega = Vector3(0, omega, 0)
        coriolis = vector_product(v_omega, v)
        coriolis = number_product(-2 * m, coriolis)
        Force = summa(Force, centrifugal)
        Force = summa(Force, coriolis)
        if m_p > 0:
            dm = u_p * dt
            m_p -= dm
            m -= dm
            dmdt = u_p
            thrust_force = number_product(I * dmdt, foward)
            Force = summa(Force, thrust_force)
            if m_p < 0:
                m_p = 0
                m += m_p
        acc = number_product(1/m, Force)
        v_new = summa(v, number_product(dt, acc))
        p_new = summa(p, number_product(dt, v_new))
        return p_new, v_new, m, m_p
    e_target = r_target.normalized()
    p, v, m, m_p, u_p, I = lander.pos, lander.vel, lander.mass, lander.mass_propell, lander.usage_propell, lander.I
    rezerv = (p, v, m, m_p)
    last = (1e20, 1e20, 1e20)
    T = 0
    if scalar_product(projection_vector_on_vector(vector_product(e_target, vector_product(p, v)), p), p) > 0:
        T = p.length() * (angle(p, e_target))/(v.length())
    else:
        T = p.length() * (2*math.pi - angle(p, e_target))/(v.length())
    i = T
    print(f"T: {T:.2f}")
    while i > 0:
        j = 0 
        p, v, m, m_p = rezerv
        while j <= i:
            p, v = step(p, v, dt)
            j += dt
        t = 0
        max_t = m_p/u_p
        while v.length() > 0.1 and t <= max_t:
            p, v, m, m_p = step_thrust(p, v, dt, m_p, m, u_p, I, number_product(-1, v).normalized())
            t += dt
        t2 = 0
        e_end = p.normalized()
        l1, l2 = p.length(), r_target.length()
        distance = math.sqrt(l1*l1 + l2*l2 - 2*l1*l2*scalar_product(e_end, e_target))
        print (f"t {t:.2f}, t2 {t2:.2f}, dist {distance:.2f}")
        if last[2] < distance:
            return last
        i -= dt
        last = (i, t, distance)  
    print("No manevr")
    return 1000000, 10000000, Vector3(1,0,0)
def verticalization_analitic(lander, planet, r_target, dt):
    def step_thrust(p, v, dt, m_p, m, u_p, I, foward):
        Force = number_product(- G * planet.mass * m / p.length()**3 , p)
        omega = -planet.angular_velocity
        centrifugal = Vector3(omega**2 * p.x, 0, omega**2 * p.z)
        centrifugal = number_product(m, centrifugal)
        v_omega = Vector3(0, omega, 0)
        coriolis = vector_product(v_omega, v)
        coriolis = number_product(-2 * m, coriolis)
        Force = summa(Force, centrifugal)
        Force = summa(Force, coriolis)
        if m_p > 0:
            dm = u_p * dt
            m_p -= dm
            m -= dm
            dmdt = u_p
            thrust_force = number_product(I * dmdt, foward)
            Force = summa(Force, thrust_force)
            if m_p < 0:
                m_p = 0
                m += m_p
        acc = number_product(1/m, Force)
        v_new = summa(v, number_product(dt, acc))
        p_new = summa(p, number_product(dt, v_new))
        return p_new, v_new, m, m_p
    p0, v0 = lander.pos, lander.vel
    r0 = p0.length()
    angle_to_target = angle(p0.normalized(), r_target.normalized())
    if scalar_product(v0, summa(r_target, number_product(-1, p0))) < 0:
        angle_to_target = 2*math.pi - angle_to_target
    p, v, m, mp = p0, v0, lander.mass, lander.mass_propell
    t_brake = 0.0
    while v.length() > 0.1 and t_brake < mp / lander.usage_propell:
        p, v, m, mp = step_thrust(p, v, dt, mp, m, lander.usage_propell, lander.I, number_product(-1, v.normalized()))
        t_brake += dt
    theta_brake = (v0.length() * t_brake) / (2 * r0)
    # Более точно – проинтегрировать угол отдельно или взять из изменения направления радиус-вектора
    # Можно сохранить начальный угол и конечный при моделировании, но для простоты оставим так.
    t_wait = (angle_to_target - theta_brake) / (v0.length() / r0)
    if t_wait < 0:
        t_wait = 0.0
    return t_wait, t_brake

def delta_t(dv, dmdt, m0, i):
    return (1 - 1/math.exp(dv/i)) * m0/dmdt

class Manevr:
    def __init__(self, duration, remain_time, direction):
        self.duration = duration
        self.remain_time = remain_time
        self.direction = direction
        self.is_work = False

def get_info_manevr(man):
    if man != None:
        print(f"remain: {man.remain_time}, duration {man.duration}, work: {man.is_work}")
FIXED_NODE = None
def main():
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("LandingSim")
    planet = Planet(1, 0, 0, 1738140, 1735970, 64, 7.36e22, 2.6617e-10)
    
    updating_sectors = False
    manual_operation = True
    pitch_up = False
    pitch_down = False
    yaw_left = False
    yaw_right = False
    is_thrusting = False
    is_pause = True

    lander = None
    camera = SectorCamera(planet, lander)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    
    clock = pygame.time.Clock()
    show_axes = True
    axes_cashe = []
    Time = 0
    time_speed = 256
    mission_stage = 1
    render_mode = 'polygons'

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('localhost', 5000))
    server_socket.listen(1)
    server_socket.setblocking(False)
    clients = []  
    sector_0 = planet.sectors[0][0]
    
    print("=== LandingSim ===")
    print("Управление:")
    print("R - переключить режим (полигоны/линии/квадраты)")
    print("H - показать/скрыть оси координат")
    print("C - меню управления планетой")
    print("G - меню настройки градиента")
    print("U - Переключить обновление секторов")
    print("L - меню управления лендером")
    print("SPACE - Pause")
    print("Колесо мыши - приближение/отдаление")
    
    while True:
        if not is_pause:
            dt = 0.025
        else: dt = 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                elif event.key == pygame.K_r:
                    if render_mode == 'polygons':
                        render_mode = 'wireframe'
                    elif render_mode == 'wireframe':
                        render_mode = 'squares'
                    elif render_mode == 'squares':
                        render_mode = 'mono'
                    else:
                        render_mode = 'polygons'
                    mode_names = {
                        'polygons': 'ПОЛИГОНЫ',
                        'wireframe': 'ЛИНИИ',
                        'squares': 'КВАДРАТЫ',
                        'mono': 'СЕРЫЙ'
                    }
                    print(f"Режим изменен на: {mode_names[render_mode]}")
                elif event.key == pygame.K_h:
                    show_axes = not show_axes
                    print(f"Оси координат: {'ВКЛ' if show_axes else 'ВЫКЛ'}")
                elif event.key == pygame.K_f:
                    camera.toggle_follow_lander()
                elif event.key == pygame.K_c:
                    planet, lander, camera = planet_menu(planet, lander, camera)
                elif event.key == pygame.K_g:
                    planet = gradient_menu(planet)
                elif event.key == pygame.K_l:
                    planet, lander, camera = lander_menu(planet, lander, camera)
                elif event.key == pygame.K_u:
                    updating_sectors = not updating_sectors
                elif event.key == pygame.K_SPACE:
                    is_pause = not is_pause
                if manual_operation == True and not is_pause:
                    if event.key == pygame.K_w:
                        pitch_up = True
                    elif event.key == pygame.K_s:
                        pitch_down = True
                    elif event.key == pygame.K_a:
                        yaw_left = True
                    elif event.key == pygame.K_d:
                        yaw_right = True
                    elif event.key == pygame.K_t:
                        is_thrusting = True
                    elif event.key == pygame.K_k:
                        if lander and lander.exists:
                            if lander.manevr != None: 
                                print(f"time_to={lander.manevr.remain_time:.1f} dt={lander.manevr.duration:.2f}")
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: 
                    camera.zoom(-1.0)
                elif event.button == 5: 
                    camera.zoom(1.0)
            elif event.type == pygame.KEYUP:
                if manual_operation == True:
                    if event.key == pygame.K_w:
                        pitch_up = False
                    elif event.key == pygame.K_s:
                        pitch_down = False
                    elif event.key == pygame.K_a:
                        yaw_left = False
                    elif event.key == pygame.K_d:
                        yaw_right = False
                    elif event.key == pygame.K_t:
                        is_thrusting = False
                        lander.thrust_force = Vector3(0,0,0)
        
        if pygame.mouse.get_pressed()[0]:
            rel_x, rel_y = pygame.mouse.get_rel()
            camera.rotate(rel_x, rel_y)
        else:
            pygame.mouse.get_rel()
        
        try:
            client_sock, addr = server_socket.accept()
            client_sock.setblocking(False)
            clients.append(client_sock)
            print(f"Подключён клиент {addr}")
        except BlockingIOError:
            pass

        for sock in clients[:]:
            try:
                data = sock.recv(1024).decode().strip()
                if data:
                    lander, camera, manual_operation, time_speed = control_functions(lander, planet, camera, manual_operation, time_speed, data)
            except BlockingIOError:
                continue
            except ConnectionResetError:
                print("Клиент отключился")
                sock.close()
                clients.remove(sock)
        
        vel_text = 0
        heig_text = 0
        if lander and lander.exists and not is_pause:
            if lander.manevr == None:
                if mission_stage == 1:
                    xt, yt, zt = sector_0.spherical_to_cartesian(sector_0.stones[0][0], sector_0.stones[0][1], sector_0.stones[0][2])
                    r_target = Vector3(xt,yt,zt)
                    time_usel, dangle, dv = predict_node_time(lander, planet, r_target, Time, int(2*math.pi*lander.pos.length()/lander.vel.length()))
                    deltat = delta_t(dv, lander.usage_propell, lander.mass, lander.I)
                    lander.manevr = Manevr(deltat, time_usel - deltat/2, direction_naklon_manevr(vector_product(lander.pos,lander.vel), r_target))
                elif mission_stage == 2:
                    xt, yt, zt = sector_0.spherical_to_cartesian(sector_0.stones[0][0], sector_0.stones[0][1], sector_0.stones[0][2])
                    r_target = Vector3(xt,yt,zt)
                    remain_t, t_manevr = verticalization_analitic(lander, planet, Vector3(xt,yt,zt), 0.025)
                    lander.manevr = Manevr(t_manevr, remain_t, Vector3(0,0,0))
                    get_info_manevr(lander.manevr)
            for i in range(time_speed):
                if lander.manevr != None:
                    if lander.manevr.direction.length() != 0:
                        lander = rotate_lander_manevr(lander, lander.manevr.direction, 0.1, dt)
                    else:
                        lander = rotate_lander_manevr(lander, number_product(-1, lander.vel).normalized(), 0.1, dt)
                    if lander.manevr.remain_time <= 0 and not lander.manevr.is_work:
                        lander.manevr.is_work = True
                        print("Start engine")
                    elif not lander.manevr.is_work:
                        lander.manevr.remain_time -= dt
                    if lander.manevr.is_work:
                        is_thrusting = True
                        lander.manevr.duration -= dt
                        if lander.manevr.duration <= 0:
                            is_thrusting = False
                            mission_stage += 1
                            lander.manevr = None
                latitude_l = math.asin(lander.pos.z/lander.pos.length())
                if manual_operation:
                    lander = rotate_lander(lander, 1, dt, pitch_up, pitch_down, yaw_left, yaw_right)
                lander.update_physic(planet, is_thrusting, dt)
                surface_height = noise_surface(sector_0, math.atan2(lander.pos.y, lander.pos.x), latitude_l)
                lander.update_height(surface_height)
                Time += dt
            vel_text = lander.vel.length()
            heig_text = lander.pos.length()
            surf_text = heig_text - lander.heig_planet
            if clients:
                for sock in clients:
                    try:
                        sock.sendall(bytes(f"v{vel_text:.3f} h{heig_text:.0f} f{100*lander.mass_propell/lander.mass_propell_max:.0f} s{surf_text:.1f}", "utf-8"))
                    except:
                        pass
        else: 
            vel_text = 0
            heig_text = 0
            if clients:
                for sock in clients:
                    try:
                        sock.sendall(bytes(f"v***** h***** f***** s*****", "utf-8"))
                    except:
                        pass
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        camera.update_camera_position()
        
        for i in range(len(planet.sectors)):
            for j in range(len(planet.sectors[i])):
                planet.sectors[i][j].draw_optimized(mode=render_mode)
                planet.sectors[i][j].draw_stones(camera)
        
        if lander and lander.exists:
            lander.draw(planet.mass)
            xt, yt, zt = sector_0.spherical_to_cartesian(sector_0.stones[0][0], sector_0.stones[0][1], sector_0.stones[0][2])
            draw_target_ray(lander.pos, Vector3(xt, yt, zt))
        
        if lander and lander.exists and updating_sectors and not is_pause:
            ceil_lon = math.ceil(math.degrees(lander.lon))
            ceil_lat = math.ceil(math.degrees(lander.lat))
            delta_lon = ceil_lon - planet.longitude
            delta_lat = ceil_lat - planet.latitude
            if math.fabs(delta_lon) > 0.5 or math.fabs(delta_lat) > 0.5:
                planet.longitude = ceil_lon
                planet.latitude = ceil_lat
                planet = update_sectors(planet, delta_lon, delta_lat)
        if show_axes:
            draw_coordinate_frame(axes_cashe, planet.equ_radius/SCALE, planet.pol_radius/SCALE, 100)
        
        mode_names = {
            'polygons': 'ПОЛИГОНЫ',
            'wireframe': 'ЛИНИИ',
            'squares': 'КВАДРАТЫ',
            'mono': 'СЕРЫЙ'
        }
        pygame.display.set_caption(f"LandingSim - Time: {Time:.1f} c - Vel: {vel_text:.0f} м/c - Heig: {heig_text:.0f} м")
        pygame.display.flip()

if __name__ == "__main__":
    main()
