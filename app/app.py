import json
import subprocess
from pathlib import Path

import streamlit as st

# Paths to configuration files and main script
render_config_path = Path("configs/render_config.json")
scene_config_path = Path("configs/scene_config.json")
main_script_path = Path("main.py")
output_image_path = Path("data/output.png")


# Helper function to write JSON to file
def write_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


# Header
st.title("Ray Tracing Dashboard")

# Create two columns for the dashboard
col1, col2 = st.columns([1, 1])

with col1:
    # Section for Render Configuration
    st.header("Render Configuration")
    width = st.number_input("Image Width", value=500, step=10)
    height = st.number_input("Image Height", value=500, step=10)
    hdri = st.text_input("HDRI Path", value="sourceimages/hdri_2.jpg")
    denoise = st.checkbox("Enable Denoise", value=False)

    if st.button("Save Render Config"):
        render_config = {
            "0": {"width": width, "height": height, "hdri": hdri, "denoise": denoise}
        }
        write_json(render_config_path, render_config)
        st.success(f"Render configuration saved to {render_config_path}")

    # Section for Scene Configuration
    st.header("Scene Configuration")
    scene_elements = st.text_area(
        "Scene Elements (JSON Format)",
        value=json.dumps(
            {
                "earth": {
                    "type": "Sphere",
                    "center": [0, 0, 1.5],
                    "radius": 1,
                    "color": [0.0, 0.0, 0.0],
                    "reflection": 1.0,
                    "roughness": 0.0,
                },
                "light1": {
                    "type": "Light",
                    "position": [5, 10, -10],
                    "intensity": [1, 1, 1],
                },
            },
            indent=4,
        ),
    )

    if st.button("Save Scene Config"):
        try:
            scene_config = json.loads(scene_elements)
            write_json(scene_config_path, scene_config)
            st.success(f"Scene configuration saved to {scene_config_path}")
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")

    # Section to Run Main Script
    st.header("Render Image")
    if st.button("Render Scene"):
        try:
            result = subprocess.run(
                ["python", str(main_script_path)], capture_output=True, text=True
            )

            if result.returncode == 0:
                st.success("Rendering completed successfully!")
                st.text(result.stdout)
                with col2:
                    st.header("Rendered Image")
                    if output_image_path.exists():
                        st.image(
                            str(output_image_path),
                            caption="Rendered Image",
                            use_column_width=True,
                        )
                    else:
                        st.write("Rendered image will appear here after rendering.")
            else:
                st.error(f"Error during rendering: {result.stderr}")

        except Exception as e:
            st.error(f"Failed to execute main script: {e}")
