import bpy
import csv
import os
import mathutils # For color operations
import math # Import the math module for math.radians

# --- Operator to Visualize CSV Data ---
class CSV_OT_VisualizeData(bpy.types.Operator):
    """Visualize CSV data as 3D objects with options"""
    bl_idname = "csv.visualize_data"
    bl_label = "Visualize CSV Data"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(
        name="CSV File",
        subtype='FILE_PATH',
        description="Path to the CSV file"
    )

    # Chart Type Preset
    chart_type: bpy.props.EnumProperty(
        items=[
            ('CUSTOM', "Custom", "Manually configure all visualization settings"),
            ('BAR_CHART', "Bar Chart (X-Cat, Y-Num)", "Visualizes data as a bar chart (X-axis categorical, Y-axis numerical)"),
            ('SCATTER_PLOT_3D', "3D Scatter Plot (X,Y,Z-Num)", "Visualizes data as a 3D scatter plot with numerical axes"),
        ],
        name="Chart Type Preset",
        description="Choose a preset to quickly configure visualization settings",
        default='CUSTOM'
    )

    x_column: bpy.props.IntProperty(
        name="X Column",
        description="Index of the column for X-axis (0-indexed)",
        default=0,
        min=0
    )
    x_is_categorical: bpy.props.BoolProperty(
        name="X is Categorical",
        description="Treat X-axis column as categorical data (maps to integer positions)",
        default=False
    )
    y_column: bpy.props.IntProperty(
        name="Y Column",
        description="Index of the column for Y-axis (0-indexed)",
        default=1,
        min=0
    )
    y_is_categorical: bpy.props.BoolProperty(
        name="Y is Categorical",
        description="Treat Y-axis column as categorical data (maps to integer positions)",
        default=False
    )
    z_column: bpy.props.IntProperty(
        name="Z Column",
        description="Index of the column for Z-axis (0-indexed). Only used if Z is not constant.",
        default=2,
        min=0
    )
    z_is_categorical: bpy.props.BoolProperty(
        name="Z is Categorical",
        description="Treat Z-axis column as categorical data (maps to integer positions). Only used if Z is not constant.",
        default=False
    )
    z_is_constant: bpy.props.BoolProperty(
        name="Z is Constant",
        description="Set Z-axis to a constant value (e.g., 0) instead of reading from a column",
        default=True # Set default to True for easier 2D plots
    )
    z_constant_value: bpy.props.FloatProperty(
        name="Constant Z Value",
        description="The fixed value for the Z-axis if 'Z is Constant' is checked",
        default=0.0
    )
    scale_column: bpy.props.IntProperty(
        name="Scale Column",
        description="Index of the column for object scale (0-indexed). Use -1 to disable.",
        default=-1,
        min=-1
    )
    primitive_type: bpy.props.EnumProperty(
        items=[
            ('CUBE', "Cube", "Visualize data as cubes"),
            ('SPHERE', "Sphere", "Visualize data as UV Spheres"),
            ('CONE', "Cone", "Visualize data as Cones"),
            ('CYLINDER', "Cylinder", "Visualize data as Cylinders"),
        ],
        name="Primitive Type",
        description="Choose the type of 3D primitive to visualize the data",
        default='CUBE'
    )
    enable_color_mapping: bpy.props.BoolProperty(
        name="Enable Color Mapping",
        description="Color objects based on a data column",
        default=False
    )
    color_column: bpy.props.IntProperty(
        name="Color Column",
        description="Index of the column for color mapping (0-indexed)",
        default=0,
        min=0
    )
    # New property for categorical spacing
    categorical_spacing: bpy.props.FloatProperty(
        name="Categorical Spacing",
        description="Spacing between categorical items on an axis",
        default=2.0,
        min=0.1
    )
    # New property to enable/disable labels
    enable_labels: bpy.props.BoolProperty(
        name="Enable Labels",
        description="Generate text labels for categorical axes",
        default=True
    )
    label_size: bpy.props.FloatProperty(
        name="Label Size",
        description="Size of the generated text labels",
        default=0.5,
        min=0.1
    )
    # New property to enable/disable axis line
    enable_axis_line: bpy.props.BoolProperty(
        name="Enable X-Axis Line",
        description="Generate a simple line for the X-axis",
        default=True
    )
    
    # Camera and Lighting Presets
    camera_preset: bpy.props.EnumProperty(
        items=[
            ('NONE', "None", "Do not change camera"),
            ('FRONT', "Front View", "Set camera to look from the front (Y-axis)"),
            ('TOP', "Top View", "Set camera to look from the top (Z-axis)"),
            ('ISOMETRIC', "Isometric View", "Set camera to an isometric perspective"),
        ],
        name="Camera Preset",
        description="Automatically set up camera angle",
        default='NONE'
    )
    lighting_preset: bpy.props.EnumProperty(
        items=[
            ('NONE', "None", "Do not change lighting"),
            ('SUN_LAMP', "Sun Lamp", "Add a sun lamp for directional lighting"),
            ('POINT_LAMP', "Point Lamp", "Add a point lamp for omnidirectional lighting"),
        ],
        name="Lighting Preset",
        description="Automatically set up scene lighting",
        default='NONE'
    )
    
    # New: Alternating Bar Colors
    enable_alternating_colors: bpy.props.BoolProperty(
        name="Enable Alternating Colors",
        description="Apply alternating colors to bars (for bar charts)",
        default=False
    )
    color_a: bpy.props.FloatVectorProperty(
        name="Color A",
        subtype='COLOR',
        default=(0.2, 0.4, 0.8, 1.0), # Blue
        min=0.0, max=1.0, size=4
    )
    color_b: bpy.props.FloatVectorProperty(
        name="Color B",
        subtype='COLOR',
        default=(0.8, 0.2, 0.4, 1.0), # Reddish
        min=0.0, max=1.0, size=4
    )

    # New: Y-axis offset
    y_offset: bpy.props.FloatProperty(
        name="Y Offset",
        description="Adjust the global Y position of the visualization",
        default=0.0
    )

    # --- Helper Methods for Code Cleanliness ---

    def _clear_previous_visualization(self, context):
        """Clears existing visualization objects, materials, cameras, and lights."""
        if "CSV_Viz" in bpy.data.collections:
            viz_collection = bpy.data.collections["CSV_Viz"]
            for obj in list(viz_collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            if not viz_collection.objects:
                bpy.data.collections.remove(viz_collection)
        
        for material in list(bpy.data.materials):
            if material.name.startswith("CSV_Material_") or material.name.startswith("Alternating_Color_") or material.name == "CSV_Label_Material":
                bpy.data.materials.remove(material)

        if self.camera_preset != 'NONE':
            for obj in context.scene.objects:
                if obj.type == 'CAMERA':
                    bpy.data.objects.remove(obj, do_unlink=True)
        if self.lighting_preset != 'NONE':
            for obj in context.scene.objects:
                if obj.type == 'LIGHT':
                    bpy.data.objects.remove(obj, do_unlink=True)

        # Ensure the collection exists for new objects
        if "CSV_Viz" not in bpy.data.collections:
            viz_collection = bpy.data.collections.new("CSV_Viz")
            bpy.context.scene.collection.children.link(viz_collection)
        return bpy.data.collections["CSV_Viz"]

    def _load_and_validate_data(self):
        """Loads CSV data and performs initial column validation."""
        if not self.filepath or not os.path.exists(self.filepath):
            self.report({'ERROR'}, "Error: Please select a valid CSV file.")
            return None, None

        try:
            with open(self.filepath, 'r') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader)
                data_rows = list(reader)

                num_columns = len(header)
                required_cols = [self.x_column, self.y_column]
                if not self.z_is_constant:
                    required_cols.append(self.z_column)
                if self.scale_column != -1:
                    required_cols.append(self.scale_column)
                if self.enable_color_mapping:
                    required_cols.append(self.color_column)

                for col_name, col_idx in [
                    ("X Column", self.x_column),
                    ("Y Column", self.y_column),
                    ("Z Column", self.z_column if not self.z_is_constant else -1),
                    ("Scale Column", self.scale_column if self.scale_column != -1 else -1),
                    ("Color Column", self.color_column if self.enable_color_mapping else -1)
                ]:
                    if col_idx != -1 and col_idx >= num_columns:
                        self.report({'ERROR'}, f"Error: {col_name} index ({col_idx}) is out of range. Your CSV has {num_columns} columns. Please check your column settings.")
                        return None, None
            return header, data_rows
        except Exception as e:
            self.report({'ERROR'}, f"Error loading CSV file: {e}")
            return None, None

    def _preprocess_categorical_data(self, data_rows):
        """Builds maps for categorical data to numerical indices."""
        x_category_map = {}
        y_category_map = {}
        z_category_map = {}
        x_cat_counter = 0
        y_cat_counter = 0
        z_cat_counter = 0

        for i, row in enumerate(data_rows):
            if len(row) <= max(self.x_column, self.y_column):
                self.report({'WARNING'}, f"Warning: Row {i+2} skipped for categorical processing: Not enough columns for X/Y.")
                continue

            if self.x_is_categorical:
                x_val = row[self.x_column]
                if x_val not in x_category_map:
                    x_category_map[x_val] = x_cat_counter
                    x_cat_counter += 1
            if self.y_is_categorical:
                y_val = row[self.y_column]
                if y_val not in y_category_map:
                    y_category_map[y_val] = y_cat_counter
                    y_cat_counter += 1
            
            if not self.z_is_constant and self.z_is_categorical:
                if len(row) > self.z_column:
                    z_val = row[self.z_column]
                    if z_val not in z_category_map:
                        z_category_map[z_val] = z_cat_counter
                        z_cat_counter += 1
                else:
                    self.report({'WARNING'}, f"Warning: Row {i+2} skipped for Z-categorical processing: Missing Z column data.")
        return x_category_map, y_category_map, z_category_map, x_cat_counter, y_cat_counter, z_cat_counter

    def _calculate_color_range(self, data_rows):
        """Calculates min/max values for color mapping."""
        min_color_val = float('inf')
        max_color_val = float('-inf')
        valid_color_data_found = False

        if self.enable_color_mapping:
            for i, row in enumerate(data_rows):
                if len(row) > self.color_column:
                    try:
                        val = float(row[self.color_column])
                        min_color_val = min(min_color_val, val)
                        max_color_val = max(max_color_val, val)
                        valid_color_data_found = True
                    except ValueError:
                        self.report({'WARNING'}, f"Warning: Row {i+2} skipped for color calculation: Non-numeric data in Color Column.")
                else:
                    self.report({'WARNING'}, f"Warning: Row {i+2} skipped for color calculation: Missing Color Column data.")

            if not valid_color_data_found or max_color_val == float('-inf') or min_color_val == float('inf'):
                self.report({'WARNING'}, "Warning: No valid numeric data found in the selected Color Column for mapping. Color mapping disabled.")
                self.enable_color_mapping = False
        return min_color_val, max_color_val

    def _create_primitive(self, location, scale):
        """Creates a 3D primitive based on selected type and applies scale."""
        if self.primitive_type == 'CUBE':
            bpy.ops.mesh.primitive_cube_add(size=1, enter_editmode=False, align='WORLD', location=location)
        elif self.primitive_type == 'SPHERE':
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, enter_editmode=False, align='WORLD', location=location)
        elif self.primitive_type == 'CONE':
            bpy.ops.mesh.primitive_cone_add(radius1=0.5, depth=1, enter_editmode=False, align='WORLD', location=location)
        elif self.primitive_type == 'CYLINDER':
            bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1, enter_editmode=False, align='WORLD', location=location)
        
        obj = bpy.context.active_object
        obj.scale = scale
        return obj

    def _apply_material(self, obj, data_index, color_val=None, min_color=None, max_color=None):
        """Applies material based on color mapping or alternating colors."""
        if self.enable_color_mapping and min_color is not None and max_color is not None and max_color > min_color and color_val is not None:
            try:
                normalized_val = (color_val - min_color) / (max_color - min_color)
                r, g, b, a = normalized_val, 0.0, 1.0 - normalized_val, 1.0 # Blue to Red gradient
                
                mat_name = f"CSV_Material_{data_index}"
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True
                if mat.node_tree.nodes.get("Principled BSDF"):
                    principled_node = mat.node_tree.nodes["Principled BSDF"]
                    principled_node.inputs['Base Color'].default_value = (r, g, b, a)
                else:
                    mat.diffuse_color = (r, g, b, a)
                
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
            except ValueError:
                self.report({'WARNING'}, f"Warning: Object {obj.name} skipped for color: Non-numeric data in Color Column.")
        elif self.enable_alternating_colors and self.primitive_type == 'CUBE':
            mat_name = f"Alternating_Color_{data_index % 2}"
            if mat_name not in bpy.data.materials:
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True
                principled_node = mat.node_tree.nodes.get("Principled BSDF")
                if principled_node:
                    principled_node.inputs['Base Color'].default_value = self.color_a if data_index % 2 == 0 else self.color_b
                else:
                    mat.diffuse_color = self.color_a if data_index % 2 == 0 else self.color_b
            else:
                mat = bpy.data.materials[mat_name]
            
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

    def _create_label(self, text, location, size, viz_collection):
        """Creates a text label object and ensures it's renderable."""
        bpy.ops.object.text_add(enter_editmode=False, align='WORLD', location=location)
        text_obj = bpy.context.active_object
        text_obj.data.body = text
        text_obj.scale = (size, size, size)
        text_obj.rotation_euler = (mathutils.Euler((math.radians(90), 0, 0), 'XYZ'))
        text_obj.name = f"CSV_Label_{text}" # Give a more descriptive name

        # Ensure label is visible in render
        text_obj.hide_render = False

        # Assign a simple white material to the label
        label_material_name = "CSV_Label_Material"
        if label_material_name not in bpy.data.materials:
            label_mat = bpy.data.materials.new(name=label_material_name)
            label_mat.use_nodes = True
            if label_mat.node_tree.nodes.get("Principled BSDF"):
                principled_node = label_mat.node_tree.nodes["Principled BSDF"]
                principled_node.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0) # White color
            else:
                label_mat.diffuse_color = (1.0, 1.0, 1.0, 1.0) # Fallback for older Blender versions
        else:
            label_mat = bpy.data.materials[label_material_name]
        
        if text_obj.data.materials:
            text_obj.data.materials[0] = label_mat
        else:
            text_obj.data.materials.append(label_mat)

        viz_collection.objects.link(text_obj)
        bpy.context.collection.objects.unlink(text_obj)
        return text_obj

    def _create_axis_line(self, viz_collection, x_cat_counter, y_base_coord):
        """Generates a simple X-axis line."""
        if self.enable_axis_line and self.x_is_categorical and x_cat_counter > 0:
            axis_start_x = -0.5
            axis_end_x = (x_cat_counter - 1) * self.categorical_spacing + 0.5
            
            mesh = bpy.data.meshes.new("X_Axis_Mesh")
            obj = bpy.data.objects.new("X_Axis_Line", mesh)
            viz_collection.objects.link(obj)

            verts = [(axis_start_x, 0, self.z_constant_value), (axis_end_x, 0, self.z_constant_value)]
            edges = [(0, 1)]
            mesh.from_pydata(verts, edges, [])
            mesh.update()

            obj.location.y = y_base_coord # Apply y_base_coord to axis line
            obj.location.z = self.z_constant_value

    def setup_camera(self, context, viz_collection):
        """Sets up the scene camera based on preset and object bounding box."""
        bpy.ops.object.camera_add(location=(0,0,0))
        camera_obj = bpy.context.active_object
        camera_obj.name = "CSV_Viz_Camera"
        viz_collection.objects.link(camera_obj)
        bpy.context.collection.objects.unlink(camera_obj)
        context.scene.camera = camera_obj

        min_x, max_x = float('inf'), float('-inf')
        min_y, max_y = float('inf'), float('-inf')
        min_z, max_z = float('inf'), float('-inf')

        for obj in viz_collection.objects:
            if obj.type == 'MESH':
                bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
                for corner in bbox_corners:
                    min_x = min(min_x, corner.x)
                    max_x = max(max_x, corner.x)
                    min_y = min(min_y, corner.y)
                    max_y = max(max_y, corner.y)
                    min_z = min(min_z, corner.z)
                    max_z = max(max_z, corner.z)
            elif obj.type == 'FONT':
                if obj.dimensions.x > 0:
                    text_center = obj.matrix_world.translation
                    text_half_x = obj.dimensions.x / 2
                    text_half_y = obj.dimensions.y / 2
                    text_half_z = obj.dimensions.z / 2
                    
                    min_x = min(min_x, text_center.x - text_half_x)
                    max_x = max(max_x, text_center.x + text_half_x)
                    min_y = min(min_y, text_center.y - text_half_y)
                    max_y = max(max_y, text_center.y + text_half_y)
                    min_z = min(min_z, text_center.z - text_half_z)
                    max_z = max(max_z, text_center.z + text_half_z)

        if min_x == float('inf'):
            self.report({'WARNING'}, "No objects found in CSV_Viz collection for camera framing.")
            return

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        dim_x = max_x - min_x
        dim_y = max_y - min_y
        dim_z = max_z - min_z
        max_dim = max(dim_x, dim_y, dim_z)

        if self.camera_preset == 'FRONT':
            camera_obj.location = (center_x, center_y - max_dim * 1.5 + self.y_offset, center_z)
            camera_obj.rotation_euler = (math.radians(90), 0, 0)
        elif self.camera_preset == 'TOP':
            camera_obj.location = (center_x, center_y + self.y_offset, center_z + max_dim * 1.5)
            camera_obj.rotation_euler = (0, 0, 0)
        elif self.camera_preset == 'ISOMETRIC':
            camera_obj.location = (center_x + max_dim * 1.5, center_y - max_dim * 1.5 + self.y_offset, center_z + max_dim * 1.5)
            look_at = mathutils.Vector((center_x, center_y + self.y_offset, center_z))
            camera_obj.rotation_euler = (look_at - camera_obj.location).to_track_quat('-Z', 'Y').to_euler()

        camera_obj.data.clip_end = max_dim * 3

    def setup_lighting(self, context, viz_collection):
        """Sets up scene lighting based on preset."""
        if self.lighting_preset == 'SUN_LAMP':
            bpy.ops.object.light_add(type='SUN', location=(5, -5 + self.y_offset, 10))
            light_obj = bpy.context.active_object
            light_obj.name = "CSV_Viz_Sun"
            light_obj.data.energy = 5
            viz_collection.objects.link(light_obj)
            bpy.context.collection.objects.unlink(light_obj)
        elif self.lighting_preset == 'POINT_LAMP':
            bpy.ops.object.light_add(type='POINT', location=(0, 0 + self.y_offset, 5))
            light_obj = bpy.context.active_object
            light_obj.name = "CSV_Viz_Point"
            light_obj.data.energy = 1000
            viz_collection.objects.link(light_obj)
            bpy.context.collection.objects.unlink(light_obj)

    def execute(self, context):
        """Main execution logic for visualizing CSV data."""
        # 1. Apply Chart Preset settings
        if self.chart_type == 'BAR_CHART':
            self.x_is_categorical = True
            self.y_is_categorical = False
            self.z_is_constant = True
            self.z_constant_value = 0.0
            self.primitive_type = 'CUBE'
            self.enable_labels = True
            self.enable_axis_line = True
            self.camera_preset = 'FRONT'
            self.lighting_preset = 'SUN_LAMP'
            if self.scale_column == -1:
                self.scale_column = self.y_column
            if not self.enable_color_mapping:
                self.enable_alternating_colors = True
            self.y_offset = 0.0 # Align to XZ plane

        elif self.chart_type == 'SCATTER_PLOT_3D':
            self.x_is_categorical = False
            self.y_is_categorical = False
            self.z_is_constant = False
            self.primitive_type = 'SPHERE'
            self.enable_labels = False
            self.enable_axis_line = False
            self.camera_preset = 'ISOMETRIC'
            self.lighting_preset = 'POINT_LAMP'
            self.enable_alternating_colors = False
            self.y_offset = 0.0

        elif self.chart_type == 'CUSTOM':
            pass

        # 2. Clear previous visualization and get/create collection
        viz_collection = self._clear_previous_visualization(context)

        # 3. Load and validate data
        header, data_rows = self._load_and_validate_data()
        if data_rows is None: # Error occurred during loading/validation
            return {'CANCELLED'}

        # 4. Pre-process categorical data
        x_category_map, y_category_map, z_category_map, x_cat_counter, _, _ = self._preprocess_categorical_data(data_rows)

        # 5. Calculate color range if color mapping is enabled
        min_color_val, max_color_val = self._calculate_color_range(data_rows)

        # 6. Create objects based on data
        y_base_coord = self.y_offset # Base Y coordinate for all objects

        for i, row in enumerate(data_rows):
            # Skip row if it doesn't have enough columns for the selected properties
            current_row_max_col = max(self.x_column, self.y_column, 
                                      self.scale_column if self.scale_column != -1 else 0,
                                      self.color_column if self.enable_color_mapping else 0)
            if not self.z_is_constant:
                current_row_max_col = max(current_row_max_col, self.z_column)

            if len(row) <= current_row_max_col:
                self.report({'WARNING'}, f"Warning: Row {i+2} skipped for object creation: Not enough columns for selected data.")
                continue

            try:
                # Determine X coordinate
                x = x_category_map.get(row[self.x_column], 0) * self.categorical_spacing if self.x_is_categorical else float(row[self.x_column])

                # Determine Z coordinate (height of bar)
                z_data_val = self.z_constant_value
                if not self.z_is_constant:
                    z_data_val = z_category_map.get(row[self.z_column], 0) * self.categorical_spacing if self.z_is_categorical else float(row[self.z_column])

                # Determine scale value (for Z-height of bar)
                scale_val = 1.0
                if self.scale_column != -1:
                    try:
                        scale_val = float(row[self.scale_column])
                        if scale_val <= 0:
                            scale_val = 0.01
                    except ValueError:
                        self.report({'WARNING'}, f"Warning: Row {i+2} skipped for scale: Non-numeric data in Scale Column. Defaulting scale to 1.0.")
                        scale_val = 1.0

                # Define scale for X, Y, Z axes of the primitive
                scale_x = 1.0
                scale_y = 1.0
                scale_z = 1.0

                if self.primitive_type == 'CUBE':
                    scale_z = scale_val # Z is height
                    scale_x = 1.0 # Fixed width
                    scale_y = 1.0 # Fixed depth
                    adjusted_z_location = self.z_constant_value + (scale_z / 2.0) # Base at Z_constant_value
                    primitive_location = (x, y_base_coord, adjusted_z_location)
                else: # For other primitives, uniform scaling is typical
                    scale_x = scale_val
                    scale_y = scale_val
                    scale_z = scale_val
                    primitive_location = (x, y_base_coord, z_data_val) # Use z_data_val for sphere/cone/cylinder center

                # Create primitive
                obj = self._create_primitive(primitive_location, (scale_x, scale_y, scale_z))
                obj.name = f"CSV_{self.primitive_type}_{i+1}"

                # Apply material
                color_for_material = float(row[self.color_column]) if self.enable_color_mapping and len(row) > self.color_column else None
                self._apply_material(obj, i, color_for_material, min_color_val, max_color_val)

                # Link the object to visualization collection
                bpy.context.collection.objects.unlink(obj)
                viz_collection.objects.link(obj)

                # Add label if X is categorical and labels are enabled
                if self.x_is_categorical and self.enable_labels:
                    label_text = row[self.x_column]
                    label_y_pos = y_base_coord - (self.categorical_spacing / 4.0) # Position below bar, at its base
                    label_location = (x, label_y_pos, self.z_constant_value - 0.5)
                    self._create_label(label_text, label_location, self.label_size, viz_collection)

            except ValueError as ve:
                self.report({'WARNING'}, f"Warning: Row {i+2} skipped due to data type mismatch. Ensure numerical columns contain only numbers. Error: {ve}")
            except IndexError as ie:
                self.report({'WARNING'}, f"Warning: Row {i+2} skipped: Missing data for specified columns. Error: {ie}")

        # 7. Create X-Axis Line
        self._create_axis_line(viz_collection, x_cat_counter, y_base_coord)

        # 8. Setup Camera and Lighting
        if self.camera_preset != 'NONE':
            self.setup_camera(context, viz_collection)
        if self.lighting_preset != 'NONE':
            self.setup_lighting(context, viz_collection)

        self.report({'INFO'}, f"Successfully visualized data from {os.path.basename(self.filepath)}")
        return {'FINISHED'}

# --- Operator to Preview CSV Data ---
class CSV_OT_PreviewData(bpy.types.Operator):
    """Preview CSV data (header and first few rows) in the console"""
    bl_idname = "csv.preview_data"
    bl_label = "Preview CSV Data"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(
        name="CSV File",
        subtype='FILE_PATH',
        description="Path to the CSV file to preview"
    )

    def execute(self, context):
        if not self.filepath or not os.path.exists(self.filepath):
            self.report({'ERROR'}, "Error: Please select a valid CSV file for preview.")
            return {'CANCELLED'}

        try:
            with open(self.filepath, 'r') as csvfile:
                reader = csv.reader(csvfile)
                
                # Print Header
                header = next(reader)
                print("\n--- CSV Data Preview ---")
                print(f"File: {os.path.basename(self.filepath)}")
                print(f"Header ({len(header)} columns): {', '.join(header)}")
                
                print("\nFirst 5 Data Rows:")
                for i, row in enumerate(reader):
                    if i >= 5: # Print only first 5 data rows
                        break
                    print(f"Row {i+1}: {', '.join(row)}")
                print("------------------------\n")
            
            self.report({'INFO'}, "CSV data preview printed to Blender console (Window > Toggle System Console).")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error during CSV preview: {e}")
            return {'CANCELLED'}


# --- Panel UI ---
class CSV_PT_DataVizPanel(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport Sidebar"""
    bl_label = "CSV Data Visualizer"
    bl_idname = "CSV_PT_DataVizPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CSV Viz" # This is the tab name in the N-panel

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.csv_viz_props

        # Section: CSV File Selection
        box = layout.box()
        box.label(text="CSV File Selection:", icon='FILE_FOLDER')
        row = box.row(align=True)
        row.prop(props, "filepath")
        preview_op = row.operator("csv.preview_data", text="", icon='FILE_REFRESH')
        preview_op.filepath = props.filepath

        # Section: Chart Type Preset
        box = layout.box()
        box.label(text="Chart Type Preset:", icon='GRAPH')
        box.prop(props, "chart_type")

        # Section: Custom Axis Mapping (Conditional Visibility)
        if props.chart_type == 'CUSTOM':
            box = layout.box()
            box.label(text="Custom Axis Mapping (0-indexed):", icon='AXIS_TOP')
            
            col = box.column(align=True)
            row = col.row(align=True)
            row.prop(props, "x_column")
            row.prop(props, "x_is_categorical", text="Categorical")

            row = col.row(align=True)
            row.prop(props, "y_column")
            row.prop(props, "y_is_categorical", text="Categorical")

            row = col.row(align=True)
            row.prop(props, "z_is_constant", text="Z is Constant")
            if props.z_is_constant:
                row.prop(props, "z_constant_value", text="")
            else:
                row.prop(props, "z_column")
                row.prop(props, "z_is_categorical", text="Categorical")
            
            box.prop(props, "scale_column")
            box.prop(props, "primitive_type")

        # Section: Common Visualization Options (Collapsible)
        box = layout.box()
        # Use a property to control the collapse state of this section
        # We'll use a boolean property on the scene for this, e.g., scene.csv_viz_props.show_common_options
        # First, add this property to CSVVizProperties
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(props, "show_common_options",
                 icon="TRIA_DOWN" if props.show_common_options else "TRIA_RIGHT",
                 icon_only=True, emboss=False)
        row.label(text="Common Visualization Options:", icon='SETTINGS')
        
        if props.show_common_options:
            # Primitive type is always shown, but read-only if a preset is active
            row = col.row()
            if props.chart_type != 'CUSTOM':
                row.enabled = False
                row.prop(props, "primitive_type")
                row.enabled = True
            else:
                row.prop(props, "primitive_type")

            col.prop(props, "enable_color_mapping")
            if props.enable_color_mapping:
                col.prop(props, "color_column")

            col.prop(props, "categorical_spacing")
            
            col.prop(props, "enable_labels")
            if props.enable_labels:
                col.prop(props, "label_size")
            
            col.prop(props, "enable_axis_line")

        # Section: Colors (Collapsible)
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(props, "show_colors_options",
                 icon="TRIA_DOWN" if props.show_colors_options else "TRIA_RIGHT",
                 icon_only=True, emboss=False)
        row.label(text="Colors:", icon='COLOR')
        
        if props.show_colors_options:
            col.prop(props, "enable_alternating_colors")
            if props.enable_alternating_colors:
                sub_col = col.column(align=True)
                sub_col.prop(props, "color_a")
                sub_col.prop(props, "color_b")

        # Section: Scene Setup Presets (Collapsible)
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(props, "show_scene_options",
                 icon="TRIA_DOWN" if props.show_scene_options else "TRIA_RIGHT",
                 icon_only=True, emboss=False)
        row.label(text="Scene Setup Presets:", icon='SCENE_DATA')
        
        if props.show_scene_options:
            col.prop(props, "camera_preset")
            col.prop(props, "lighting_preset")
            col.prop(props, "y_offset")


        # Visualize button
        layout.separator()
        op = layout.operator("csv.visualize_data", icon='IMPORT')
        # Pass all properties to the operator
        op.filepath = props.filepath
        op.chart_type = props.chart_type
        op.x_column = props.x_column
        op.y_column = props.y_column
        op.z_column = props.z_column
        op.scale_column = props.scale_column
        op.primitive_type = props.primitive_type
        op.enable_color_mapping = props.enable_color_mapping
        op.color_column = props.color_column
        op.x_is_categorical = props.x_is_categorical
        op.y_is_categorical = props.y_is_categorical
        op.z_is_categorical = props.z_is_categorical
        op.z_is_constant = props.z_is_constant
        op.z_constant_value = props.z_constant_value
        op.categorical_spacing = props.categorical_spacing
        op.enable_labels = props.enable_labels
        op.label_size = props.label_size
        op.enable_axis_line = props.enable_axis_line
        op.camera_preset = props.camera_preset
        op.lighting_preset = props.lighting_preset
        op.enable_alternating_colors = props.enable_alternating_colors
        op.color_a = props.color_a
        op.color_b = props.color_b
        op.y_offset = props.y_offset


# --- Properties Group for Scene ---
class CSVVizProperties(bpy.types.PropertyGroup):
    filepath: bpy.props.StringProperty(
        name="CSV File",
        subtype='FILE_PATH',
        description="Path to the CSV file"
    )
    chart_type: bpy.props.EnumProperty(
        items=[
            ('CUSTOM', "Custom", "Manually configure all visualization settings"),
            ('BAR_CHART', "Bar Chart (X-Cat, Y-Num)", "Visualizes data as a bar chart (X-axis categorical, Y-axis numerical)"),
            ('SCATTER_PLOT_3D', "3D Scatter Plot (X,Y,Z-Num)", "Visualizes data as a 3D scatter plot with numerical axes"),
        ],
        name="Chart Type Preset",
        description="Choose a preset to quickly configure visualization settings",
        default='CUSTOM',
        update=lambda self, context: update_chart_type_preset(self, context) # Update function
    )

    x_column: bpy.props.IntProperty(
        name="X Column",
        description="Index of the column for X-axis (0-indexed)",
        default=0,
        min=0
    )
    x_is_categorical: bpy.props.BoolProperty(
        name="X is Categorical",
        description="Treat X-axis column as categorical data (maps to integer positions)",
        default=False
    )
    y_column: bpy.props.IntProperty(
        name="Y Column",
        description="Index of the column for Y-axis (0-indexed)",
        default=1,
        min=0
    )
    y_is_categorical: bpy.props.BoolProperty(
        name="Y is Categorical",
        description="Treat Y-axis column as categorical data (maps to integer positions)",
        default=False
    )
    z_column: bpy.props.IntProperty(
        name="Z Column",
        description="Index of the column for Z-axis (0-indexed). Only used if Z is not constant.",
        default=2,
        min=0
    )
    z_is_categorical: bpy.props.BoolProperty(
        name="Z is Categorical",
        description="Treat Z-axis column as categorical data (maps to integer positions). Only used if Z is not constant.",
        default=False
    )
    z_is_constant: bpy.props.BoolProperty(
        name="Z is Constant",
        description="Set Z-axis to a constant value (e.g., 0) instead of reading from a column",
        default=True
    )
    z_constant_value: bpy.props.FloatProperty(
        name="Constant Z Value",
        description="The fixed value for the Z-axis if 'Z is Constant' is checked",
        default=0.0
    )
    scale_column: bpy.props.IntProperty(
        name="Scale Column",
        description="Index of the column for object scale (0-indexed). Use -1 to disable.",
        default=-1,
        min=-1
    )
    primitive_type: bpy.props.EnumProperty(
        items=[
            ('CUBE', "Cube", "Visualize data as cubes"),
            ('SPHERE', "Sphere", "Visualize data as UV Spheres"),
            ('CONE', "Cone", "Visualize data as Cones"),
            ('CYLINDER', "Cylinder", "Visualize data as Cylinders"),
        ],
        name="Primitive Type",
        description="Choose the type of 3D primitive to visualize the data",
        default='CUBE'
    )
    enable_color_mapping: bpy.props.BoolProperty(
        name="Enable Color Mapping",
        description="Color objects based on a data column",
        default=False
    )
    color_column: bpy.props.IntProperty(
        name="Color Column",
        description="Index of the column for color mapping (0-indexed)",
        default=0,
        min=0
    )
    categorical_spacing: bpy.props.FloatProperty(
        name="Categorical Spacing",
        description="Spacing between categorical items on an axis",
        default=2.0,
        min=0.1
    )
    enable_labels: bpy.props.BoolProperty(
        name="Enable Labels",
        description="Generate text labels for categorical axes",
        default=True
    )
    label_size: bpy.props.FloatProperty(
        name="Label Size",
        description="Size of the generated text labels",
        default=0.5,
        min=0.1
    )
    enable_axis_line: bpy.props.BoolProperty(
        name="Enable X-Axis Line",
        description="Generate a simple line for the X-axis",
        default=True
    )
    camera_preset: bpy.props.EnumProperty(
        items=[
            ('NONE', "None", "Do not change camera"),
            ('FRONT', "Front View", "Set camera to look from the front (Y-axis)"),
            ('TOP', "Top View", "Set camera to look from the top (Z-axis)"),
            ('ISOMETRIC', "Isometric View", "Set camera to an isometric perspective"),
        ],
        name="Camera Preset",
        description="Automatically set up camera angle",
        default='NONE'
    )
    lighting_preset: bpy.props.EnumProperty(
        items=[
            ('NONE', "None", "Do not change lighting"),
            ('SUN_LAMP', "Sun Lamp", "Add a sun lamp for directional lighting"),
            ('POINT_LAMP', "Point Lamp", "Add a point lamp for omnidirectional lighting"),
        ],
        name="Lighting Preset",
        description="Automatically set up scene lighting",
        default='NONE'
    )
    enable_alternating_colors: bpy.props.BoolProperty(
        name="Enable Alternating Colors",
        description="Apply alternating colors to bars (for bar charts)",
        default=False
    )
    color_a: bpy.props.FloatVectorProperty(
        name="Color A",
        subtype='COLOR',
        default=(0.2, 0.4, 0.8, 1.0), # Blue
        min=0.0, max=1.0, size=4
    )
    color_b: bpy.props.FloatVectorProperty(
        name="Color B",
        subtype='COLOR',
        default=(0.8, 0.2, 0.4, 1.0), # Reddish
        min=0.0, max=1.0, size=4
    )
    y_offset: bpy.props.FloatProperty(
        name="Y Offset",
        description="Adjust the global Y position of the visualization",
        default=0.0
    )
    # New properties for controlling collapse state
    show_common_options: bpy.props.BoolProperty(
        name="Show Common Options",
        description="Toggle visibility of common visualization options",
        default=True # Start open
    )
    show_colors_options: bpy.props.BoolProperty(
        name="Show Colors Options",
        description="Toggle visibility of color options",
        default=False # Start collapsed
    )
    show_scene_options: bpy.props.BoolProperty(
        name="Show Scene Options",
        description="Toggle visibility of scene setup options",
        default=False # Start collapsed
    )


# Update function for Chart Type Preset
def update_chart_type_preset(self, context):
    if self.chart_type == 'BAR_CHART':
        self.x_is_categorical = True
        self.y_is_categorical = False
        self.z_is_constant = True
        self.z_constant_value = 0.0
        self.primitive_type = 'CUBE'
        self.enable_labels = True
        self.enable_axis_line = True
        self.camera_preset = 'FRONT'
        self.lighting_preset = 'SUN_LAMP'
        self.enable_alternating_colors = True
        self.enable_color_mapping = False
        self.y_offset = 0.0 # Set Y offset to 0 for bar chart to align to XZ plane
        # Open relevant sections for bar chart
        self.show_common_options = True
        self.show_colors_options = True
        self.show_scene_options = True
    elif self.chart_type == 'SCATTER_PLOT_3D':
        self.x_is_categorical = False
        self.y_is_categorical = False
        self.z_is_constant = False
        self.primitive_type = 'SPHERE'
        self.enable_labels = False
        self.enable_axis_line = False
        self.camera_preset = 'ISOMETRIC'
        self.lighting_preset = 'POINT_LAMP'
        self.enable_alternating_colors = False
        self.y_offset = 0.0 # Reset Y offset for preset
        # Open relevant sections for scatter plot
        self.show_common_options = True
        self.show_colors_options = False # Color mapping is usually data-driven for scatter
        self.show_scene_options = True
    elif self.chart_type == 'CUSTOM':
        # Leave as is, user will manually adjust
        pass

# --- Registration ---
classes = (
    CSV_OT_VisualizeData,
    CSV_OT_PreviewData,
    CSV_PT_DataVizPanel,
    CSVVizProperties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.csv_viz_props = bpy.props.PointerProperty(type=CSVVizProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.csv_viz_props

if __name__ == "__main__":
    register()
    # Example usage:
    # You can run this script directly in Blender's text editor.
    # After running, go to the 3D Viewport, press 'N' to open the sidebar,
    # and find the "CSV Viz" tab.
    # Select a CSV file and click "Visualize CSV Data".
