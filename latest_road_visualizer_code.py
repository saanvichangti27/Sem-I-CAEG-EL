import tkinter as tk
from tkinter import filedialog, ttk
import math
import os # Keep os for os.path.basename

# Note: All 'Pillow' (PIL) imports have been removed.

# --- Constants for our Coordinate System ---
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600
ORIGIN_X = CANVAS_WIDTH / 2
ORIGIN_Y = CANVAS_HEIGHT / 2
SCALE = 20  # Pixels per meter

# --- Transformation Functions ---

def to_canvas_x(offset):
    return ORIGIN_X + (offset * SCALE)

def to_canvas_y(elevation):
    return ORIGIN_Y - (elevation * SCALE)

# --- Analysis Helper Functions ---

def find_layer(layers_data, layer_type_name):
    """Finds the first layer with the matching type."""
    for layer in layers_data:
        if layer['type'] == layer_type_name:
            return layer
    return None

def find_y_at_x(data_coords, x_offset):
    """
    Finds the elevation (y) of a polygon at a specific offset (x)
    using linear interpolation.
    """
    for i in range(0, len(data_coords) - 2, 2):
        x1, y1 = data_coords[i], data_coords[i+1]
        x2, y2 = data_coords[i+2], data_coords[i+3]
        
        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            
        if x1 <= x_offset <= x2:
            if x2 - x1 == 0:  # Vertical line
                return min(y1, y2)
            
            t = (x_offset - x1) / (x2 - x1)
            y = y1 + t * (y2 - y1)
            return y
    return None # Not found

# --- Drawing Helper Functions ---

def draw_dim_label(canvas, offset, elevation, text, leader_len=30, anchor="s"):
    """Draws a text label with a small vertical leader line."""
    cx = to_canvas_x(offset)
    cy = to_canvas_y(elevation)
    
    leader_y_end = cy - leader_len
    text_y_pos = leader_y_end - 5
    
    if anchor == "n": # Draw leader down
        leader_y_end = cy + leader_len
        text_y_pos = leader_y_end + 5

    canvas.create_line(cx, cy, cx, leader_y_end, fill="gray50")
    canvas.create_text(cx, text_y_pos, text=text, anchor=anchor)

def draw_horizontal_dim(canvas, y_elev, x1_off, x2_off, text):
    """Draws a horizontal dimension line with text."""
    y_canvas = to_canvas_y(y_elev)
    x1_canvas = to_canvas_x(x1_off)
    x2_canvas = to_canvas_x(x2_off)
    
    # Main horizontal line
    canvas.create_line(x1_canvas, y_canvas, x2_canvas, y_canvas, fill="gray30", arrow=tk.BOTH)
    
    # Vertical ticks
    canvas.create_line(x1_canvas, y_canvas - 5, x1_canvas, y_canvas + 5, fill="gray30")
    canvas.create_line(x2_canvas, y_canvas - 5, x2_canvas, y_canvas + 5, fill="gray30")
    
    # Text
    mid_x = (x1_canvas + x2_canvas) / 2
    canvas.create_text(mid_x, y_canvas - 5, text=text, anchor="s", fill="gray30")


def draw_slope_label(canvas, p1, p2):
    """Draws a 1:N slope label between two data points."""
    offset1, elev1 = p1
    offset2, elev2 = p2
    
    mid_offset = (offset1 + offset2) / 2
    mid_elev = (elev1 + elev2) / 2
    
    run = abs(offset2 - offset1)
    rise = abs(elev2 - elev1)
    
    if rise == 0:
        slope_text = "Level"
    else:
        n = run / rise
        slope_text = f"1 : {n:.1f}"

    cx = to_canvas_x(mid_offset)
    cy = to_canvas_y(mid_elev)
    angle = math.degrees(math.atan2(to_canvas_y(elev2) - to_canvas_y(elev1), 
                                   to_canvas_x(offset2) - to_canvas_x(offset1)))
    
    canvas.create_text(cx, cy, text=slope_text, angle=-angle, fill="blue")
    
    if elev1 > elev2:
        zone = "FILL\n(Embankment)"
    else:
        zone = "CUT\n(Cutting)"
    
    canvas.create_text(cx, cy + 30, text=zone, fill="darkblue", font=("Arial", 9))

# --- Main Application Functions ---

def load_road_section():
    """Asks for a .road file, parses it, analyzes it, and renders it."""
    
    filepath = filedialog.askopenfilename(
        title="Open a Road Section file",
        filetypes=[("Road files", "*.road"), ("All files", "*.*")]
    )
    if not filepath:
        return

    canvas.delete("all")
    status_label.config(text=f"Loading {os.path.basename(filepath)}...")
    
    canvas.create_line(0, ORIGIN_Y, CANVAS_WIDTH, ORIGIN_Y, fill="grey", dash=(2, 2))
    canvas.create_line(ORIGIN_X, 0, ORIGIN_X, CANVAS_HEIGHT, fill="grey", dash=(2, 2))
    canvas.create_text(ORIGIN_X + 5, ORIGIN_Y + 5, text="(0, 0) Centerline", anchor="nw")

    global_chainage = "CHAINAGE: Unknown"
    layers_data = []

    try:
        with open(filepath, 'r') as f:
            for line_number, line in enumerate(f, 1):
                try:
                    line = line.strip()
                    if not line: continue
                    
                    if line.startswith('# CHAINAGE:'):
                        global_chainage = line.split(':', 1)[1].strip()
                        continue
                    if line.startswith('#'):
                        continue

                    parts = line.split(',')
                    if len(parts) < 8: continue

                    layer_type = parts[0]
                    color = parts[1]
                    data_coords = [float(coord) for coord in parts[2:]]
                    
                    layers_data.append({
                        "type": layer_type,
                        "color": color,
                        "data": data_coords
                    })
                except Exception as e:
                    print(f"[SKIPPING Line {line_number}]: {e}")
                    
        # --- DRAW LAYERS (Bottom-up) ---
        # Draw terrain first, with stippling
        terrain = find_layer(layers_data, "TERRAIN")
        if terrain:
            canvas_coords = []
            for i in range(0, len(terrain['data']), 2):
                canvas_coords.append(to_canvas_x(terrain['data'][i]))
                canvas_coords.append(to_canvas_y(terrain['data'][i+1]))
            canvas.create_polygon(canvas_coords, 
                                  fill=terrain['color'], 
                                  outline="darkgreen", 
                                  width=1,
                                  stipple="gray25")
        
        # Draw other layers (non-terrain)
        for layer in layers_data:
            if layer['type'] == "TERRAIN":
                continue
            
            canvas_coords = []
            for i in range(0, len(layer['data']), 2):
                canvas_coords.append(to_canvas_x(layer['data'][i]))
                canvas_coords.append(to_canvas_y(layer['data'][i+1]))
            
            canvas.create_polygon(canvas_coords, 
                                  fill=layer['color'], 
                                  outline="white", 
                                  width=1)

        # --- ADD LABELS AND DIMENSIONS ---
        
        canvas.create_text(CANVAS_WIDTH / 2, 25, 
                           text=f"Chainage: {global_chainage}", 
                           font=("Arial", 16, "bold"))
        
        # --- THIS LOGIC IS NOW SMARTER ---
        
        # Find all relevant layers
        asphalt = find_layer(layers_data, "ASPHALT")
        asphalt_l = find_layer(layers_data, "ASPHALT_L")
        asphalt_r = find_layer(layers_data, "ASPHALT_R")
        subbase = find_layer(layers_data, "SUBBASE")
        median = find_layer(layers_data, "MEDIAN")

        # Case 1: Simple Road (like sample.road)
        if asphalt:
            cl_elev = find_y_at_x(asphalt['data'], 0)
            if cl_elev is not None:
                draw_dim_label(canvas, 0, cl_elev, f"Centerline\n(Elev: {cl_elev:.2f}m)")

            # Label Edges of Pavement
            ep_left_off, ep_left_elev = asphalt['data'][0], asphalt['data'][1]
            ep_right_off, ep_right_elev = asphalt['data'][2], asphalt['data'][3]
            draw_dim_label(canvas, ep_left_off, ep_left_elev, 
                           f"E.P.\n({ep_left_off:.2f}, {ep_left_elev:.2f})")
            draw_dim_label(canvas, ep_right_off, ep_right_elev, 
                           f"E.P.\n({ep_right_off:.2f}, {ep_right_elev:.2f})")
            
            # Add horizontal dimension
            width = ep_right_off - ep_left_off
            draw_horizontal_dim(canvas, cl_elev + 1.0, ep_left_off, ep_right_off, f"Width: {width:.2f}m")

        # Case 2: Divided Highway (like complex_road.road)
        elif asphalt_l and asphalt_r:
            # Label Centerline (at y=0)
            draw_dim_label(canvas, 0, 0, "Centerline\n(Median)", anchor="n")

            # Label Left Carriageway
            ep_inner_l_off, ep_inner_l_elev = asphalt_l['data'][0], asphalt_l['data'][1]
            ep_outer_l_off, ep_outer_l_elev = asphalt_l['data'][2], asphalt_l['data'][3]
            draw_dim_label(canvas, ep_inner_l_off, ep_inner_l_elev, 
                           f"E.P.\n({ep_inner_l_off:.2f}, {ep_inner_l_elev:.2f})")
            draw_dim_label(canvas, ep_outer_l_off, ep_outer_l_elev, 
                           f"E.P.\n({ep_outer_l_off:.2f}, {ep_outer_l_elev:.2f})")
            width_l = abs(ep_outer_l_off - ep_inner_l_off)
            draw_horizontal_dim(canvas, ep_inner_l_elev + 0.5, ep_inner_l_off, ep_outer_l_off, f"Width: {width_l:.2f}m")

            # Label Right Carriageway
            ep_inner_r_off, ep_inner_r_elev = asphalt_r['data'][0], asphalt_r['data'][1]
            ep_outer_r_off, ep_outer_r_elev = asphalt_r['data'][2], asphalt_r['data'][3]
            draw_dim_label(canvas, ep_inner_r_off, ep_inner_r_elev, 
                           f"E.P.\n({ep_inner_r_off:.2f}, {ep_inner_r_elev:.2f})")
            draw_dim_label(canvas, ep_outer_r_off, ep_outer_r_elev, 
                           f"E.P.\n({ep_outer_r_off:.2f}, {ep_outer_r_elev:.2f})")
            width_r = abs(ep_outer_r_off - ep_inner_r_off)
            draw_horizontal_dim(canvas, ep_inner_r_elev + 0.5, ep_inner_r_off, ep_outer_r_off, f"Width: {width_r:.2f}m")
            
        if median:
            # Get median center (approx)
            m_off, m_elev = median['data'][0], median['data'][1]
            draw_dim_label(canvas, m_off + 0.5, m_elev, "Median\nBarrier", leader_len=15)


        # Label Slopes (This logic remains the same)
        if subbase and terrain:
            # Assumes first/last points of subbase are toes
            # and points next-to-first/last are road edges
            p_road_left = (subbase['data'][2], subbase['data'][3])
            p_terrain_left = (subbase['data'][0], subbase['data'][1])
            draw_slope_label(canvas, p_road_left, p_terrain_left)
            
            p_road_right = (subbase['data'][-4], subbase['data'][-3])
            p_terrain_right = (subbase['data'][-2], subbase['data'][-1])
            draw_slope_label(canvas, p_road_right, p_terrain_right)

        status_label.config(text="Ready.")

    except Exception as e:
        status_label.config(text=f"Error: {e}")
        canvas.create_text(ORIGIN_X, ORIGIN_Y, 
            text=f"Error reading file:\n{e}", fill="red", font=("Arial", 12))

# --- PNG Export Function REMOVED ---

# --- Set up the main application window ---
root = tk.Tk()
root.title("Road Cross-Section Visualizer")

control_frame = ttk.Frame(root)
control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

load_button = ttk.Button(control_frame, text="Load .road File", command=load_road_section)
load_button.pack(side=tk.LEFT, padx=5)

# --- Export Button REMOVED ---

status_label = ttk.Label(root, text="Ready.", relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(side=tk.BOTTOM, fill=tk.X)

canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="ivory")
canvas.pack(fill=tk.BOTH, expand=True)

root.mainloop()