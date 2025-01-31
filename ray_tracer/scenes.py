import time
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

from configs.configs import RenderConfig
from denoiser import denoise
from evaluation.utils import create_csv_file, populate_csv_file
from ray_tracer.objects import Light, Sphere
from ray_tracer.ray_tracing import render_monte_carlo_live
from ray_tracer.utils import HDRIEnvironment
from ray_tracer.vectors import Vector3D


def load_scene(scene_csv_file: str) -> tuple[list[Sphere], list[Light]]:
    df = pd.read_csv(scene_csv_file)

    spheres = []
    lights = []

    for _, row in df.iterrows():
        if row["type"] == "Sphere":
            texture = None
            if "texture" in row and not pd.isna(row["texture"]):
                texture = np.array(Image.open(row["texture"]))

            sphere = Sphere(
                center=Vector3D(row["positionX"], row["positionY"], row["positionZ"]),
                radius=row["radius"],
                color=Vector3D(row["colorR"], row["colorG"], row["colorB"]),
                reflection=row["reflection"],
                roughness=row["roughness"],
                texture=texture,
            )
            spheres.append(sphere)

        elif row["type"] == "Light":
            light = Light(
                position=Vector3D(row["positionX"], row["positionY"], row["positionZ"]),
                intensity=Vector3D(
                    row["intensityR"], row["intensityG"], row["intensityB"]
                ),
            )
            lights.append(light)

    return spheres, lights


def render_single_image(scene_content, render_config: RenderConfig, log_results: bool):
    objects, lights = scene_content

    if log_results:
        render_times_file = Path("dataset/render_times.csv")
        render_times_file.parent.mkdir(parents=True, exist_ok=True)
        columns = (
            ["image_name"]
            + list(asdict(render_config).keys())
            + ["render_time", "denoise_time", "path"]
        )
        create_csv_file(render_times_file, columns=columns)

    if log_results:
        start_time = time.time()

    environment_image = (
        HDRIEnvironment(render_config.hdri) if render_config.hdri else None
    )

    if render_config.render_algorithm == "monte_carlo":
        for partial_image in render_monte_carlo_live(
            objects,
            lights,
            render_config.width,
            render_config.height,
            environment_image,
            render_config.max_samples,
        ):
            plt.imshow(partial_image)
            plt.pause(0.01)

        image = partial_image

        if log_results:
            render_elapsed_time = time.time() - start_time
    else:
        raise ValueError("Invalid render algorithm")

    if render_config.denoise:
        if log_results:
            start_time = time.time()
        image = denoise(image)
        if log_results:
            denoise_elapsed_time = time.time() - start_time
    else:
        denoise_elapsed_time = 0

    output_path = render_config.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((image * 255).astype(np.uint8)).save(output_path)

    if log_results:
        populate_csv_file(
            render_times_file,
            [output_path.stem]
            + list(asdict(render_config).values())
            + [render_elapsed_time, denoise_elapsed_time, output_path],
        )
