import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="RenderIt!", layout="wide")

st.title("RenderIt!")
st.sidebar.header("Options")

# Store the position, color, and size of each sphere in the session state
if "spheres" not in st.session_state:
    st.session_state["spheres"] = []

# Button to add a new sphere
if st.sidebar.button("Create new sphere"):
    st.session_state["spheres"].append(
        {"x": 0.0, "y": 0.0, "z": 0.0, "radius": 1.0, "color": "Viridis"}
    )

# Menu to edit or delete each sphere
for i, sphere in enumerate(st.session_state["spheres"]):
    st.sidebar.subheader(f"Sphere {i + 1}")
    sphere["x"] = st.sidebar.slider(
        f"Position X (Sphere {i + 1})", -10.0, 10.0, sphere["x"], 0.1
    )
    sphere["y"] = st.sidebar.slider(
        f"Position Y (Sphere {i + 1})", -10.0, 10.0, sphere["y"], 0.1
    )
    sphere["z"] = st.sidebar.slider(
        f"Position Z (Sphere {i + 1})", -10.0, 10.0, sphere["z"], 0.1
    )
    sphere["radius"] = st.sidebar.slider(
        f"Radius (Sphere {i + 1})", 0.5, 5.0, sphere["radius"], 0.1
    )
    sphere["color"] = st.sidebar.selectbox(
        f"Color (Sphere {i + 1})",
        ["Viridis", "Cividis", "Plasma", "Inferno", "Magma", "Greens"],
        index=["Viridis", "Cividis", "Plasma", "Inferno", "Magma", "Greens"].index(
            sphere["color"]
        ),
    )
    if st.sidebar.button(f"Delete Sphere {i + 1}"):
        st.session_state["spheres"].pop(i)
        st.experimental_rerun()  # Rerun to update the UI immediately

# Create the 3D plot
fig = go.Figure()

for i, sphere in enumerate(st.session_state["spheres"]):
    u, v = np.mgrid[0 : 2 * np.pi : 20j, 0 : np.pi : 10j]
    x = sphere["x"] + sphere["radius"] * np.cos(u) * np.sin(v)
    y = sphere["y"] + sphere["radius"] * np.sin(u) * np.sin(v)
    z = sphere["z"] + sphere["radius"] * np.cos(v)

    fig.add_trace(
        go.Surface(
            x=x,
            y=y,
            z=z,
            colorscale=sphere["color"],
            showscale=False,
            name=f"Sphere {i + 1}",
        )
    )

fig.update_layout(
    scene=dict(
        xaxis=dict(title="X"),
        yaxis=dict(title="Y"),
        zaxis=dict(title="Z"),
    ),
    margin=dict(l=0, r=0, b=0, t=0),
)

# Display the 3D plot
st.plotly_chart(fig, use_container_width=True)
