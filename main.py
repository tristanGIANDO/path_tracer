import numpy as np
from PIL import Image
import time


def get_texture_color(texture, u, v):
    texture_data = np.array(texture)
    # Convertir UV en indices de pixel
    u = u % 1  # Répéter si u dépasse 1
    v = v % 1
    i = int(u * (texture_data.shape[1] - 1))
    j = int(v * (texture_data.shape[0] - 1))
    return Vec3(*texture_data[j, i, :3] / 255)  # Normaliser les couleurs


class Vec3:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        if isinstance(scalar, Vec3):  # Element-wise multiplication
            return Vec3(self.x * scalar.x, self.y * scalar.y, self.z * scalar.z)
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def norm(self):
        length = np.sqrt(self.dot(self))
        return self * (1.0 / max(length, 1e-6))

    def components(self):
        return self.x, self.y, self.z


class Sphere:
    def __init__(self, center, radius, color, reflection=0.5, texture=None):
        self.center = center
        self.radius = radius
        self.color = color
        self.reflection = reflection
        self.texture = texture  # Ajouter une texture optionnelle

    def get_surface_color(self, hit_point):
        if self.texture:
            # Calculer les coordonnées UV
            normal = (hit_point - self.center).norm()
            u = 0.5 + np.arctan2(normal.z, normal.x) / (2 * np.pi)
            v = 0.5 - np.arcsin(normal.y) / np.pi
            return get_texture_color(self.texture, u, v)
        return self.color

    def intersect(self, ray_origin, ray_dir):
        oc = ray_origin - self.center
        b = 2.0 * oc.dot(ray_dir)
        c = oc.dot(oc) - self.radius ** 2
        disc = b ** 2 - 4 * c
        if disc > 0:
            sqrtd = np.sqrt(disc)
            t0 = (-b - sqrtd) / 2
            t1 = (-b + sqrtd) / 2
            if t0 > 0:
                return t0
            if t1 > 0:
                return t1
        return None

def trace(ray_origin, ray_dir, scene, depth=0):
    nearest_t, nearest_obj = float('inf'), None
    for obj in scene:
        t = obj.intersect(ray_origin, ray_dir)
        if t and t < nearest_t:
            nearest_t, nearest_obj = t, obj

    if nearest_obj is None:
        return Vec3(0, 0, 0)  # Background color

    hit_point = ray_origin + ray_dir * nearest_t
    normal = (hit_point - nearest_obj.center).norm()
    light_dir = Vec3(5, 5, -10) - hit_point
    light_dir = light_dir.norm()

    # Diffuse shading
    diff = max(normal.dot(light_dir), 0)
    # color = nearest_obj.color * diff
    color = nearest_obj.get_surface_color(hit_point)


    # Reflection
    if depth < 3 and nearest_obj.reflection > 0:
        reflect_dir = ray_dir - normal * 2 * ray_dir.dot(normal)
        reflection_color = trace(hit_point + normal * 1e-4, reflect_dir, scene, depth + 1)
        color = color * (1 - nearest_obj.reflection) + reflection_color * nearest_obj.reflection

    return color

def render(scene, width, height):
    aspect_ratio = float(width) / height
    camera = Vec3(0, 0, -1)
    screen = (-1, 1 / aspect_ratio, 1, -1 / aspect_ratio)

    image = np.zeros((height, width, 3))
    for i, y in enumerate(np.linspace(screen[1], screen[3], height)):
        for j, x in enumerate(np.linspace(screen[0], screen[2], width)):
            pixel = Vec3(x, y, 0)
            ray_dir = (pixel - camera).norm()
            color = trace(camera, ray_dir, scene)
            image[i, j] = np.clip(color.components(), 0, 1)

    return image


earth_texture = Image.open("resource/2k_earth_daymap.jpg")

scene = [
    Sphere(Vec3(0, -0.5, 3), 0.5, Vec3(1, 1, 1), texture=earth_texture),  # Sphère texturée
    Sphere(Vec3(1, 0, 4), 1, Vec3(0, 1, 0)),  # Sphère colorée simple
    Sphere(Vec3(-1, 0, 2.5), 0.3, Vec3(0, 0, 1))
]


# Rendu
start = time.time()
width, height = 500, 500
image = render(scene, width, height)
Image.fromarray((image * 255).astype(np.uint8)).save("output/path_tracer.png")
print("Took", time.time() - start)