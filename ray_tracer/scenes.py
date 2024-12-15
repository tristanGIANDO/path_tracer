import time
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

from configs.configs import RenderConfig, SceneConfig
from denoiser import denoise
from evaluation.utils import create_csv_file, populate_csv_file
from ray_tracer.objects import Light, Sphere
from ray_tracer.ray_tracing import render
from ray_tracer.utils import HDRIEnvironment
from ray_tracer.vectors import Vector3D


def build_scene(config: SceneConfig) -> tuple[list[Sphere], list[Light]]:
    objects = []
    lights = []

    for settings in config.data.values():
        if settings["type"] == "Light":
            lights.append(
                Light(Vector3D(*settings["position"]), Vector3D(*settings["intensity"]))
            )

        elif settings["type"] == "Sphere":
            texture = (
                np.array(Image.open(settings["texture"]))
                if "texture" in settings
                else None
            )
            objects.append(
                Sphere(
                    center=Vector3D(*settings["center"]),
                    radius=settings["radius"],
                    color=Vector3D(*settings["color"]),
                    reflection=settings["reflection"],
                    roughness=settings["roughness"],
                    texture=texture,
                )
            )

    return objects, lights


def batch_render(scene_content, config: RenderConfig, log_results: bool):
    objects, lights = scene_content

    if log_results:
        render_times_file = Path("dataset/render_times.csv")
        render_times_file.parent.mkdir(parents=True, exist_ok=True)
        columns = (
            ["uuid"]
            + list(list(config.data.values())[0].keys())
            + ["render_time_seconds", "file_path"]
        )
        create_csv_file(render_times_file, columns=columns)

    for settings in list(config.data.values()):
        if log_results:
            start_time = time.time()

        environment_image = (
            HDRIEnvironment(settings["hdri"]) if settings.get("hdri") else None
        )
        image = render(
            objects, lights, settings["width"], settings["height"], environment_image
        )
        if settings.get("denoise", False):
            image = denoise(image)
        timestamp = int(time.time())
        unique_id = f"{timestamp}-{uuid.uuid4()}"
        # output_file = Path("data") / f"{unique_id}.png"
        output_file = Path("data/output.png")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray((image * 255).astype(np.uint8)).save(output_file)

        if log_results:
            elapsed_time = time.time() - start_time
            populate_csv_file(
                render_times_file,
                [unique_id] + list(settings.values()) + [elapsed_time, output_file],
            )
