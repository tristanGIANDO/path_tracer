from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ray_tracer.objects import Light, Sphere
from ray_tracer.utils import HDRIEnvironment
from ray_tracer.vectors import Vector3D


def trace(
    ray_origin: Vector3D,
    ray_dir: Vector3D,
    scene: list[Sphere],
    lights: list[Light],
    depth: int = 0,
    max_depth: int = 3,
    environment: HDRIEnvironment | None = None,
) -> Vector3D:
    """
    Traces a ray through the scene to determine the color at a given point, including reflections.

    Args:
        ray_origin (Vector3D): The origin of the ray.
        ray_dir (Vector3D): The direction of the ray.
        scene (list): A list of objects in the scene.
        lights (list): A list of light sources in the scene.
        depth (int): Current recursion depth for reflections.
        max_depth (int): Maximum recursion depth for reflections.

    Returns:
        Vector3D: The color determined by tracing the ray.
    """
    nearest_t, nearest_obj = float("inf"), None
    for obj in scene:
        t = obj.intersect(ray_origin, ray_dir)
        if t and t < nearest_t:
            nearest_t, nearest_obj = t, obj

    if nearest_obj is None:
        # Retourner la couleur de l'environnement si aucune intersection
        if environment:
            return environment.get_color(ray_dir)
        return Vector3D(0, 0, 0)  # Couleur de fond noire

    # Point d'intersection
    hit_point = ray_origin + ray_dir * nearest_t
    normal = (hit_point - nearest_obj.center).norm()
    color = nearest_obj.get_surface_color(hit_point)

    # Calculate direct lighting (diffuse shading)
    light_contribution = Vector3D(0, 0, 0)
    for light in lights:
        light_dir = (light.position - hit_point).norm()
        shadow_ray_origin = hit_point + normal * 1e-4
        shadow_intersect = any(
            obj.intersect(shadow_ray_origin, light_dir)
            for obj in scene
            if obj != nearest_obj
        )
        if not shadow_intersect:
            intensity = max(normal.dot(light_dir), 0)
            light_contribution += light.intensity * intensity

    # Reflection
    reflection_contribution = Vector3D(0, 0, 0)
    if (
        depth < max_depth
        and hasattr(nearest_obj, "reflection")
        and nearest_obj.reflection > 0
    ):
        reflected_dir = (ray_dir - normal * (2 * normal.dot(ray_dir))).norm()

        # Appliquer la roughness si elle est définie
        if hasattr(nearest_obj, "roughness") and nearest_obj.roughness > 0:
            reflected_dir = reflected_dir.perturb(nearest_obj.roughness)

        reflected_origin = hit_point + normal * 1e-4
        reflection_color = trace(
            reflected_origin,
            reflected_dir,
            scene,
            lights,
            depth + 1,
            max_depth,
            environment,
        )
        reflection_contribution = reflection_color * nearest_obj.reflection

    # Combiner les contributions
    return color * light_contribution + reflection_contribution


def render(
    scene: list[Sphere],
    lights: list[Light],
    width: int,
    height: int,
    environment: HDRIEnvironment | None = None,
) -> np.ndarray:
    """
    Renders the scene to create an image.

    Args:
        scene (list): A list of objects in the scene.
        lights (list): A list of light sources in the scene.
        width (int): The width of the image.
        height (int): The height of the image.

    Returns:
        numpy.ndarray: The rendered image as an array of pixel values.

    This function represents the camera looking at the scene through a grid of pixels (the image).
    For each pixel, it sends a ray from the camera into the scene to determine what color that pixel should be.
    It calculates the direction of each ray and uses the `trace` function to determine the color based on object interactions.
    """
    aspect_ratio = float(width) / height
    camera = Vector3D(0, 0, -10)
    screen = (-1, 1 / aspect_ratio, 1, -1 / aspect_ratio)

    image = np.zeros((height, width, 3))
    for i, y in enumerate(np.linspace(screen[1], screen[3], height)):
        for j, x in enumerate(np.linspace(screen[0], screen[2], width)):
            pixel = Vector3D(x, y, 0)
            ray_dir = (pixel - camera).norm()
            color = trace(camera, ray_dir, scene, lights, environment=environment)
            image[i, j] = np.clip(color.components(), 0, 1)

    return image


def render_monte_carlo_live(
    scene: list[Sphere],
    lights: list[Light],
    width: int,
    height: int,
    environment: HDRIEnvironment | None = None,
    samples_per_pixel: int = 10,
) -> np.ndarray:
    aspect_ratio = float(width) / height
    camera = Vector3D(0, 0, -1)
    screen = (-1, 1 / aspect_ratio, 1, -1 / aspect_ratio)

    image = np.zeros((height, width, 3))
    accumulated_color = np.zeros((height, width, 3))

    for sample in range(1, samples_per_pixel + 1):
        for i, y in enumerate(np.linspace(screen[1], screen[3], height)):
            for j, x in enumerate(np.linspace(screen[0], screen[2], width)):
                # Ajouter une petite variation aléatoire pour chaque rayon
                u = np.random.uniform(-1 / width, 1 / width)
                v = np.random.uniform(-1 / height, 1 / height)
                pixel = Vector3D(x + u, y + v, 0)
                ray_dir = (pixel - camera).norm()
                color = trace(camera, ray_dir, scene, lights, environment=environment)
                accumulated_color[i, j] += color.components()

        # Mettre à jour l'image avec les moyennes actuelles
        image = np.clip(accumulated_color / sample, 0, 1)
        yield image


def render_pixel(
    i, j, x, y, samples_per_pixel, camera, scene, lights, environment, width, height
):
    pixel_color = Vector3D(0, 0, 0)
    for _ in range(samples_per_pixel):
        u = np.random.uniform(-1 / width, 1 / width)
        v = np.random.uniform(-1 / height, 1 / height)
        pixel = Vector3D(x + u, y + v, 0)
        ray_dir = (pixel - camera).norm()
        pixel_color += trace(camera, ray_dir, scene, lights, environment=environment)
    return i, j, np.clip((pixel_color / samples_per_pixel).components(), 0, 1)


def render_monte_carlo_processes(
    scene, lights, width, height, samples_per_pixel, environment=None
):
    aspect_ratio = float(width) / height
    camera = Vector3D(0, 0, 0)
    screen = (-1, 1 / aspect_ratio, 1, -1 / aspect_ratio)

    image = np.zeros((height, width, 3))

    with ProcessPoolExecutor() as executor:
        futures = []
        for i, y in enumerate(np.linspace(screen[1], screen[3], height)):
            for j, x in enumerate(np.linspace(screen[0], screen[2], width)):
                futures.append(
                    executor.submit(
                        render_pixel,
                        i,
                        j,
                        x,
                        y,
                        samples_per_pixel,
                        camera,
                        scene,
                        lights,
                        environment,
                        width,
                        height,
                    )
                )

        for future in futures:
            i, j, color = future.result()
            image[i, j] = color

    return image
