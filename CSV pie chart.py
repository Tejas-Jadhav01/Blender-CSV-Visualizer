import bpy
import csv
import math
import random
from mathutils import Vector, Euler
import os

bl_info = {
    "name": "CSV Pie Chart Visualizer",
    "author": "Percy",
    "version": (1, 22), # Updated version for fixed animation easing
    "blender": (3, 0, 0),
    "location": "3D Viewport > Sidebar > CSV Pie Chart Tab",
    "description": "Visualizes CSV data as a 3D pie chart with scene setup, sorting, title, auto-detection, and advanced animations.",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

class CSV_OT_AutodetectColumns(bpy.types.Operator):
    """Autodetect Label and Value Columns from CSV"""
    bl_idname = "csv.autodetect_columns"
    bl_label = "Autodetect Columns"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only enable if a CSV file path is set and the file exists
        return context.scene.csv_pie_chart_props.csv_file_path != "" and \
               os.path.exists(bpy.path.abspath(context.scene.csv_pie_chart_props.csv_file_path))

    def execute(self, context):
        props = context.scene.csv_pie_chart_props
        csv_file_path = bpy.path.abspath(props.csv_file_path)

        if not csv_file_path:
            self.report({'ERROR'}, "Please select a CSV file first.")
            return {'CANCELLED'}

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                header = next(reader) # Read header row
                
                # Read a few sample rows to infer types
                sample_rows = []
                for _ in range(5): # Sample first 5 data rows
                    try:
                        sample_rows.append(next(reader))
                    except StopIteration:
                        break # End of file

                numeric_cols = []
                string_cols = []

                for i, col_name in enumerate(header):
                    is_numeric_candidate = True
                    if not sample_rows: # If no data rows, assume string for all
                        is_numeric_candidate = False
                    else:
                        numeric_count = 0
                        for row in sample_rows:
                            if i < len(row): # Ensure column exists in this row
                                try:
                                    float(row[i])
                                    numeric_count += 1
                                except ValueError:
                                    pass
                        # If more than 80% of sampled values are numeric, consider it a numeric column
                        if numeric_count / len(sample_rows) < 0.8:
                            is_numeric_candidate = False

                    if is_numeric_candidate:
                        numeric_cols.append(col_name)
                    else:
                        string_cols.append(col_name)

                # Prioritize common names for value and label columns
                value_keywords = ['sales', 'amount', 'value', 'count', 'total']
                label_keywords = ['category', 'item', 'name', 'description', 'type']

                found_value_col = None
                for col in numeric_cols:
                    if col.lower() in value_keywords:
                        found_value_col = col
                        break
                if not found_value_col and numeric_cols:
                    found_value_col = numeric_cols[0] # Fallback to first numeric

                found_label_col = None
                for col in string_cols:
                    if col.lower() in label_keywords:
                        found_label_col = col
                        break
                if not found_label_col and string_cols:
                    found_label_col = string_cols[0] # Fallback to first string

                if found_label_col:
                    props.label_column = found_label_col
                if found_value_col:
                    props.value_column = found_value_col

                if not found_label_col and not found_value_col:
                    self.report({'WARNING'}, "Could not confidently autodetect columns. Please set manually.")
                elif not found_label_col:
                    self.report({'WARNING'}, "Could not autodetect label column. Please set manually.")
                elif not found_value_col:
                    self.report({'WARNING'}, "Could not autodetect value column. Please set manually.")
                else:
                    self.report({'INFO'}, f"Autodetected: Label='{found_label_col}', Value='{found_value_col}'")

        except FileNotFoundError:
            self.report({'ERROR'}, f"File not found: {csv_file_path}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error processing CSV for autodetection: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class CSV_OT_GeneratePieChart(bpy.types.Operator):
    """Generate a 3D Pie Chart from CSV data and set up the scene"""
    bl_idname = "csv.generate_pie_chart"
    bl_label = "Generate Pie Chart"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Ensure a CSV file path is set before allowing the operator to run
        return context.scene.csv_pie_chart_props.csv_file_path != ""

    def execute(self, context):
        props = context.scene.csv_pie_chart_props
        csv_file_path = bpy.path.abspath(props.csv_file_path)
        label_col_name = props.label_column
        value_col_name = props.value_column
        pie_radius = props.pie_radius
        pie_height = props.pie_height
        text_size = props.text_size
        text_offset = props.text_offset
        segment_subdivisions = props.segment_subdivisions
        camera_distance = props.camera_distance
        light_power = props.light_power
        sort_by = props.sort_by
        chart_title = props.chart_title
        label_horizontal_orientation = props.label_horizontal_orientation
        
        # Animation Properties
        animate_creation = props.animate_creation
        animation_duration = props.animation_duration
        animation_offset = props.animation_offset
        creation_ease_type = props.creation_ease_type
        
        explode_animation_enabled = props.explode_animation_enabled
        explode_animation_duration = props.explode_animation_duration
        explode_animation_delay = props.explode_animation_delay

        rotate_animation_enabled = props.rotate_animation_enabled
        rotate_speed = props.rotate_speed
        rotate_loops = props.rotate_loops


        if not csv_file_path:
            self.report({'ERROR'}, "Please select a CSV file.")
            return {'CANCELLED'}

        data = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                if label_col_name not in reader.fieldnames or value_col_name not in reader.fieldnames:
                    self.report({'ERROR'}, f"Column names not found. Available: {', '.join(reader.fieldnames)}")
                    return {'CANCELLED'}

                for row in reader:
                    try:
                        label = row[label_col_name]
                        value = float(row[value_col_name])
                        if value < 0:
                            self.report({'WARNING'}, f"Skipping negative value: {value} for label {label}")
                            continue
                        data.append({'label': label, 'value': value})
                    except ValueError:
                        self.report({'WARNING'}, f"Skipping non-numeric value: '{row[value_col_name]}' for label '{row[label_col_name]}'")
                    except KeyError as e:
                        self.report({'ERROR'}, f"Missing column in row: {e}. Check column names.")
                        return {'CANCELLED'}

        except FileNotFoundError:
            self.report({'ERROR'}, f"File not found: {csv_file_path}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error reading CSV: {e}")
            return {'CANCELLED'}

        if not data:
            self.report({'ERROR'}, "No valid data found in CSV to create pie chart.")
            return {'CANCELLED'}

        total_value = sum(item['value'] for item in data)
        if total_value == 0:
            self.report({'ERROR'}, "Total value of data is zero. Cannot create pie chart.")
            return {'CANCELLED'}

        # --- Sort Data based on user selection ---
        if sort_by == 'VALUE_DESCENDING':
            data.sort(key=lambda x: x['value'], reverse=True)
        elif sort_by == 'LABEL_ASCENDING':
            data.sort(key=lambda x: x['label'])

        # --- Scene Setup ---
        self.setup_scene(context, camera_distance, light_power)

        # Create a new collection for the pie chart objects
        pie_chart_collection_name = "CSV_Pie_Chart"
        if pie_chart_collection_name in bpy.data.collections:
            pie_collection = bpy.data.collections[pie_chart_collection_name]
            # Clear existing objects in the collection
            for obj in list(pie_collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        else:
            pie_collection = bpy.data.collections.new(pie_chart_collection_name)
            bpy.context.scene.collection.children.link(pie_collection)

        # Create a parent empty for the entire pie chart for rotation animation
        # This empty will also serve as the common origin for all slices/labels
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
        chart_parent_empty = bpy.context.active_object
        chart_parent_empty.name = "PieChart_Parent"
        pie_collection.objects.link(chart_parent_empty)
        bpy.context.collection.objects.unlink(chart_parent_empty) # Unlink from scene collection

        start_angle = 0
        
        # Calculate overall animation end frame for scene frame_end
        max_animation_end_frame = bpy.context.scene.frame_current

        # End frame for creation animation (if enabled)
        if animate_creation:
            max_animation_end_frame_creation = bpy.context.scene.frame_current + len(data) * animation_offset + animation_duration
            max_animation_end_frame = max(max_animation_end_frame, max_animation_end_frame_creation)

        # End frame for explode animation (if enabled)
        if explode_animation_enabled and props.explode_factor > 0:
            # Calculate the start frame for the LAST slice's explode animation
            latest_explode_start_frame = bpy.context.scene.frame_current
            if animate_creation:
                latest_explode_start_frame += (len(data) - 1) * animation_offset + animation_duration
            latest_explode_start_frame += (len(data) - 1) * explode_animation_delay
            
            max_animation_end_frame_explode = latest_explode_start_frame + explode_animation_duration
            max_animation_end_frame = max(max_animation_end_frame, max_animation_end_frame_explode)

        # End frame for rotation animation (if enabled)
        if rotate_animation_enabled:
            # Rotation starts after all other animations finish, plus a small buffer
            rotate_start_frame = max_animation_end_frame + 10 
            total_rotation_frames = abs(props.rotate_loops * 360 / props.rotate_speed) if props.rotate_speed != 0 else 1 # Avoid division by zero
            max_animation_end_frame_rotate = rotate_start_frame + total_rotation_frames
            max_animation_end_frame = max(max_animation_end_frame, max_animation_end_frame_rotate)

        # Set scene frame end to encompass all animations
        bpy.context.scene.frame_end = int(max_animation_end_frame + 10) # Add some buffer

        for i, item in enumerate(data):
            percentage = item['value'] / total_value
            angle = percentage * 2 * math.pi # Angle in radians for the slice

            # Create the pie slice mesh
            verts = []
            faces = []

            # Center vertex for the base and top
            verts.append(Vector((0, 0, 0))) # Base center (index 0)
            verts.append(Vector((0, 0, pie_height))) # Top center (index 1)

            # Vertices for the base and top circumference
            base_start_idx = len(verts)
            for j in range(segment_subdivisions + 1):
                theta = start_angle + (j / segment_subdivisions) * angle
                x = pie_radius * math.cos(theta)
                y = pie_radius * math.sin(theta)
                verts.append(Vector((x, y, 0))) # Base circumference
                verts.append(Vector((x, y, pie_height))) # Top circumference

            # Create faces
            # Base face
            base_face_verts = [0] + [base_start_idx + k*2 for k in range(segment_subdivisions + 1)][::-1] # Reverse for correct normal
            faces.append(base_face_verts)

            # Top face
            top_face_verts = [1] + [base_start_idx + k*2 + 1 for k in range(segment_subdivisions + 1)]
            faces.append(top_face_verts)

            # Side faces
            for j in range(segment_subdivisions):
                v0 = base_start_idx + j*2
                v1 = base_start_idx + j*2 + 1
                v2 = base_start_idx + (j+1)*2 + 1
                v3 = base_start_idx + (j+1)*2
                faces.append([v0, v1, v2, v3])

            # Inner and outer radial faces (if not a full circle)
            if angle < 2 * math.pi - 0.001: # Avoid adding these for a full circle
                # Inner radial face (at start_angle)
                faces.append([0, 1, base_start_idx + 1, base_start_idx])
                # Outer radial face (at start_angle + angle)
                faces.append([0, base_start_idx + segment_subdivisions*2, base_start_idx + segment_subdivisions*2 + 1, 1])


            mesh_name = f"PieSlice_{item['label'].replace(' ', '_')}"
            mesh = bpy.data.meshes.new(mesh_name)
            mesh.from_pydata(verts, [], faces)
            mesh.update()

            obj = bpy.data.objects.new(mesh_name, mesh)
            pie_collection.objects.link(obj)
            obj.parent = chart_parent_empty # Parent to the main chart empty

            # Set a random color for the slice
            mat_name = f"SliceMaterial_{item['label'].replace(' ', '_')}"
            if mat_name in bpy.data.materials:
                mat = bpy.data.materials[mat_name]
            else:
                mat = bpy.data.materials.new(name=mat_name)
                mat.diffuse_color = (random.uniform(0.1, 0.9), random.uniform(0.1, 0.9), random.uniform(0.1, 0.9), 1.0)
            
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

            # Initial position of the slice (un-exploded, relative to parent empty)
            obj.location = Vector((0, 0, 0))
            
            # Add text label
            mid_angle = start_angle + angle / 2
            text_x = (pie_radius + text_offset) * math.cos(mid_angle)
            text_y = (pie_radius + text_offset) * math.sin(mid_angle)

            # Set Z-location explicitly slightly above the pie slice to ensure visibility
            label_z_location = pie_height / 2 + 0.01 # Slightly above the middle of the slice height

            bpy.ops.object.text_add(enter_editmode=False, location=(text_x, text_y, label_z_location))
            text_obj = bpy.context.active_object
            text_obj.data.body = f"{item['label']} ({percentage:.1%})"
            text_obj.data.size = text_size
            text_obj.data.align_x = 'CENTER'
            text_obj.data.align_y = 'CENTER' 

            # Apply label orientation
            if label_horizontal_orientation:
                text_obj.rotation_euler.z = math.radians(0) # Always horizontal
            else:
                text_obj.rotation_euler.z = mid_angle + math.pi / 2 # Radial

            text_obj.rotation_euler.x = math.radians(90) # Make text stand upright

            # Link text object to the pie chart collection and parent to the main chart empty
            pie_collection.objects.link(text_obj)
            bpy.context.collection.objects.unlink(text_obj) # Unlink from current collection
            text_obj.parent = chart_parent_empty # Parent to the main chart empty


            # --- Animation Logic ---
            current_frame = bpy.context.scene.frame_current

            # 1. Creation Animation (Scale)
            if animate_creation:
                start_frame_creation = current_frame + i * animation_offset
                end_frame_creation = start_frame_creation + animation_duration

                obj.scale = Vector((0.001, 0.001, 0.001))
                obj.keyframe_insert(data_path="scale", frame=start_frame_creation)
                text_obj.scale = Vector((0.001, 0.001, 0.001))
                text_obj.keyframe_insert(data_path="scale", frame=start_frame_creation)

                obj.scale = Vector((1.0, 1.0, 1.0))
                obj.keyframe_insert(data_path="scale", frame=end_frame_creation)
                text_obj.scale = Vector((1.0, 1.0, 1.0))
                text_obj.keyframe_insert(data_path="scale", frame=end_frame_creation)

                # Set interpolation for creation animation
                if obj.animation_data and obj.animation_data.action:
                    for fcurve in obj.animation_data.action.fcurves:
                        if fcurve.data_path.startswith('scale'): # Apply to all scale components
                            for kp in fcurve.keyframe_points:
                                kp.interpolation = creation_ease_type
                                # Set handle types based on the interpolation type chosen
                                if creation_ease_type == 'LINEAR':
                                    kp.handle_left_type = 'VECTOR'
                                    kp.handle_right_type = 'VECTOR'
                                else: # For BEZIER, SINE, QUAD, etc., use AUTO handles
                                    kp.handle_left_type = 'AUTO'
                                    kp.handle_right_type = 'AUTO'
                
                if text_obj.animation_data and text_obj.animation_data.action:
                    for fcurve in text_obj.animation_data.action.fcurves:
                        if fcurve.data_path.startswith('scale'): # Apply to all scale components
                            for kp in fcurve.keyframe_points:
                                kp.interpolation = creation_ease_type
                                if creation_ease_type == 'LINEAR':
                                    kp.handle_left_type = 'VECTOR'
                                    kp.handle_right_type = 'VECTOR'
                                else:
                                    kp.handle_left_type = 'AUTO'
                                    kp.handle_right_type = 'AUTO'

            # 2. Explode Animation (Location)
            # Calculate the final exploded position for this slice
            final_exploded_location = Vector((
                pie_radius * math.cos(mid_angle) * props.explode_factor,
                pie_radius * math.sin(mid_angle) * props.explode_factor,
                0
            ))

            if explode_animation_enabled and props.explode_factor > 0:
                # Determine when this slice's explode animation should start
                explode_animation_start_frame_for_this_slice = current_frame
                if animate_creation: # If creation animation is also enabled, explode starts after it
                    explode_animation_start_frame_for_this_slice = current_frame + i * animation_offset + animation_duration
                
                # Add the per-slice delay for explode animation
                explode_animation_start_frame_for_this_slice += i * explode_animation_delay

                explode_animation_end_frame_for_this_slice = explode_animation_start_frame_for_this_slice + explode_animation_duration

                # Keyframe from (0,0,0) to final_exploded_location
                # obj.location is already (0,0,0) from initial setup
                obj.keyframe_insert(data_path="location", frame=explode_animation_start_frame_for_this_slice)
                
                obj.location = final_exploded_location
                obj.keyframe_insert(data_path="location", frame=explode_animation_end_frame_for_this_slice)

                # Set interpolation for explode animation (e.g., EASE_IN_OUT)
                if obj.animation_data and obj.animation_data.action:
                    for fcurve in obj.animation_data.action.fcurves:
                        if fcurve.data_path.startswith('location'): # Apply to all location components
                            for kp in fcurve.keyframe_points:
                                kp.interpolation = 'BEZIER' # Use Bezier for smoother movement
                                kp.handle_left_type = 'AUTO'
                                kp.handle_right_type = 'AUTO'

            elif not explode_animation_enabled and props.explode_factor > 0:
                # If explode animation is NOT enabled but explode_factor is > 0, set instantly
                obj.location = final_exploded_location
            # Else (explode_factor is 0), obj.location remains (0,0,0) as initialized


            start_angle += angle
        
        # 3. Rotate Animation (on chart_parent_empty)
        if rotate_animation_enabled:
            rotate_start_frame = bpy.context.scene.frame_current
            # If other animations are present, start rotation after they finish, plus a small buffer
            if animate_creation or (explode_animation_enabled and props.explode_factor > 0):
                rotate_start_frame = max_animation_end_frame + 10 # Start after all other animations + buffer

            total_rotation_degrees = rotate_loops * 360
            # Ensure rotate_speed is not zero to avoid division by zero
            total_rotation_frames = abs(total_rotation_degrees / rotate_speed) if rotate_speed != 0 else 1 

            chart_parent_empty.rotation_euler = Euler((0, 0, 0), 'XYZ')
            chart_parent_empty.keyframe_insert(data_path="rotation_euler", index=2, frame=rotate_start_frame) # Z-axis rotation

            chart_parent_empty.rotation_euler = Euler((0, 0, math.radians(total_rotation_degrees)), 'XYZ')
            chart_parent_empty.keyframe_insert(data_path="rotation_euler", index=2, frame=rotate_start_frame + total_rotation_frames)

            # Set interpolation to linear for continuous rotation
            if chart_parent_empty.animation_data and chart_parent_empty.animation_data.action:
                fcurves_rot = chart_parent_empty.animation_data.action.fcurves.find('rotation_euler', index=2)
                if fcurves_rot:
                    for kp in fcurves_rot.keyframe_points:
                        kp.interpolation = 'LINEAR'
        
        # --- Add Chart Title ---
        if chart_title:
            # Set Z-location explicitly slightly above the pie chart
            title_z_location = pie_height + text_size * 2 + 0.01
            bpy.ops.object.text_add(enter_editmode=False, location=(0, 0, title_z_location))
            title_obj = bpy.context.active_object
            title_obj.data.body = chart_title
            title_obj.data.size = text_size * 1.5
            title_obj.data.align_x = 'CENTER'
            title_obj.data.align_y = 'CENTER'
            title_obj.rotation_euler.x = math.radians(90)
            pie_collection.objects.link(title_obj)
            bpy.context.collection.objects.unlink(title_obj)
            title_obj.parent = chart_parent_empty # Parent to the main chart empty

            # Animation for title
            if animate_creation:
                title_obj.scale = Vector((0.001, 0.001, 0.001))
                # Title animation starts after all slices have begun their animation
                title_obj.keyframe_insert(data_path="scale", frame=current_frame + len(data) * animation_offset)
                title_obj.scale = Vector((1.0, 1.0, 1.0))
                title_obj.keyframe_insert(data_path="scale", frame=current_frame + len(data) * animation_offset + animation_duration)
                
                # Set interpolation for title creation animation
                if title_obj.animation_data and title_obj.animation_data.action:
                    for fcurve in title_obj.animation_data.action.fcurves:
                        if fcurve.data_path.startswith('scale'): # Apply to all scale components
                            for kp in fcurve.keyframe_points:
                                kp.interpolation = creation_ease_type
                                if creation_ease_type == 'LINEAR':
                                    kp.handle_left_type = 'VECTOR'
                                    kp.handle_right_type = 'VECTOR'
                                else:
                                    kp.handle_left_type = 'AUTO'
                                    kp.handle_right_type = 'AUTO'


        self.report({'INFO'}, "Pie chart and scene generated successfully!")
        return {'FINISHED'}

    def setup_scene(self, context, camera_distance, light_power): 
        # Clear existing cameras
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA':
                bpy.data.objects.remove(obj, do_unlink=True)
        # Clear existing lights
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT':
                bpy.data.objects.remove(obj, do_unlink=True)

        # --- Camera Setup ---
        cam_data = bpy.data.cameras.new("PieChartCam")
        cam_obj = bpy.data.objects.new("PieChartCam", cam_data)
        context.collection.objects.link(cam_obj)

        cam_obj.location = (0, -camera_distance, camera_distance * 0.75)
        
        direction = Vector((0,0,0)) - cam_obj.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()

        context.scene.camera = cam_obj

        # --- Light Setup (Sun Light) ---
        light_data = bpy.data.lights.new("PieChartLight", type='SUN')
        light_obj = bpy.data.objects.new("PieChartLight", light_data)
        context.collection.objects.link(light_obj)

        light_obj.data.energy = light_power
        light_obj.location = (5, -5, 10)
        light_obj.rotation_euler = Euler((math.radians(45), 0, math.radians(45)), 'XYZ')

        # --- Background ---
        world = context.scene.world
        if not world:
            world = bpy.data.worlds.new("World")
            context.scene.world = world
        
        world.use_nodes = True
        bg_node = world.node_tree.nodes.get('Background')
        if not bg_node:
            bg_node = world.node_tree.nodes.new('ShaderNodeBackground')
            world.node_tree.links.new(bg_node.outputs['Background'], world.node_tree.nodes['World Output'].inputs['Surface'])
        bg_node.inputs['Strength'].default_value = 1.0


class CSV_PieChartProperties(bpy.types.PropertyGroup):
    # UI Visibility Toggles
    show_pie_appearance: bpy.props.BoolProperty(name="Pie Chart Appearance & Labels", default=True)
    show_scene_settings: bpy.props.BoolProperty(name="Scene Settings", default=True)
    show_animations: bpy.props.BoolProperty(name="Animations", default=True) # New toggle for animations section

    csv_file_path: bpy.props.StringProperty(
        name="CSV File",
        subtype='FILE_PATH',
        description="Path to the CSV file"
    )
    label_column: bpy.props.StringProperty(
        name="Label Column",
        description="Name of the column for labels (e.g., 'Category')",
        default="Category"
    )
    value_column: bpy.props.StringProperty(
        name="Value Column",
        description="Name of the column for values (e.g., 'Amount')",
        default="Amount"
    )
    pie_radius: bpy.props.FloatProperty(
        name="Pie Radius",
        description="Radius of the pie chart",
        default=2.0,
        min=0.1
    )
    pie_height: bpy.props.FloatProperty(
        name="Pie Height",
        description="Height/thickness of the pie chart slices",
        default=0.5,
        min=0.01
    )
    explode_factor: bpy.props.FloatProperty(
        name="Explode Factor",
        description="Factor to separate slices (0 for no separation)",
        default=0.0,
        min=0.0,
        max=1.0
    )
    text_size: bpy.props.FloatProperty(
        name="Text Size",
        description="Size of the label text",
        default=0.5,
        min=0.01
    )
    text_offset: bpy.props.FloatProperty(
        name="Text Offset",
        description="Distance of text labels from the pie edge",
        default=0.5,
        min=0.0
    )
    segment_subdivisions: bpy.props.IntProperty(
        name="Segment Subdivisions",
        description="Number of subdivisions for each pie slice (smoother slices)",
        default=32,
        min=4,
        max=128
    )
    camera_distance: bpy.props.FloatProperty(
        name="Camera Distance",
        description="Distance of the camera from the pie chart center",
        default=10.0,
        min=1.0
    )
    light_power: bpy.props.FloatProperty(
        name="Light Power",
        description="Strength of the scene light",
        default=10.0,
        min=0.1
    )
    sort_by: bpy.props.EnumProperty(
        name="Sort Slices By",
        items=[
            ('NONE', 'None', 'Do not sort slices (use CSV order)'),
            ('VALUE_DESCENDING', 'Value (Descending)', 'Sort slices by value in descending order'),
            ('LABEL_ASCENDING', 'Label (Ascending)', 'Sort slices by label in ascending order')
        ],
        default='NONE',
        description="Method to sort the pie chart slices"
    )
    chart_title: bpy.props.StringProperty(
        name="Chart Title",
        description="Title to display above the pie chart",
        default="My Pie Chart"
    )
    label_horizontal_orientation: bpy.props.BoolProperty(
        name="Horizontal Labels",
        description="Display labels horizontally instead of radially",
        default=False
    )

    # --- Animation Properties ---
    animate_creation: bpy.props.BoolProperty(
        name="Animate Creation (Scale)",
        description="Animate slices and labels growing into place",
        default=False
    )
    animation_duration: bpy.props.FloatProperty(
        name="Creation Duration (frames)",
        description="Duration of each slice's growth animation in frames",
        default=30.0,
        min=1.0
    )
    animation_offset: bpy.props.FloatProperty(
        name="Creation Offset (frames)",
        description="Delay between each slice's creation animation start, in frames",
        default=5.0,
        min=0.0
    )
    creation_ease_type: bpy.props.EnumProperty(
        name="Creation Ease Type",
        items=[
            ('AUTO', 'Auto', 'Automatic interpolation'),
            ('LINEAR', 'Linear', 'Linear interpolation'),
            ('BEZIER', 'Bezier', 'Bezier interpolation'),
            ('SINE', 'Sine', 'Sinusoidal interpolation'),
            ('QUAD', 'Quad', 'Quadratic interpolation'),
            ('CUBIC', 'Cubic', 'Cubic interpolation'),
            ('QUART', 'Quart', 'Quartic interpolation'),
            ('QUINT', 'Quint', 'Quintic interpolation'),
            ('EXPO', 'Expo', 'Exponential interpolation'),
            ('CIRC', 'Circ', 'Circular interpolation'),
            ('BACK', 'Back', 'Back interpolation (slight overshoot)'),
            ('BOUNCE', 'Bounce', 'Bounce interpolation'),
            ('ELASTIC', 'Elastic', 'Elastic interpolation (springy)')
        ],
        default='BEZIER',
        description="Type of easing for the creation animation"
    )

    explode_animation_enabled: bpy.props.BoolProperty(
        name="Animate Explode",
        description="Animate slices moving to their exploded position",
        default=False
    )
    explode_animation_duration: bpy.props.FloatProperty(
        name="Explode Duration (frames)",
        description="Duration of the explode animation in frames",
        default=20.0,
        min=1.0
    )
    explode_animation_delay: bpy.props.FloatProperty(
        name="Explode Offset (frames)",
        description="Delay between each slice's explode animation start, in frames",
        default=2.0,
        min=0.0
    )

    rotate_animation_enabled: bpy.props.BoolProperty(
        name="Animate Rotation",
        description="Animate the entire pie chart rotating",
        default=False
    )
    rotate_speed: bpy.props.FloatProperty(
        name="Rotation Speed (deg/frame)",
        description="Speed of rotation in degrees per frame",
        default=0.5,
        min=0.01
    )
    rotate_loops: bpy.props.IntProperty(
        name="Rotation Loops",
        description="Number of full 360-degree rotations",
        default=1,
        min=1
    )


class CSV_PT_PieChartPanel(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport Sidebar"""
    bl_label = "CSV Pie Chart"
    bl_idname = "CSV_PT_PieChartPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CSV Pie Chart"

    def draw(self, context):
        layout = self.layout
        props = context.scene.csv_pie_chart_props

        # --- CSV Data Section (Always visible) ---
        box = layout.box()
        box.label(text="CSV Data", icon='FILE_FOLDER')
        box.prop(props, "csv_file_path")
        row = box.row()
        row.prop(props, "label_column")
        row.prop(props, "value_column")
        box.operator(CSV_OT_AutodetectColumns.bl_idname, text="Autodetect Columns", icon='PREFERENCES')

        layout.separator()

        # --- Pie Chart Appearance & Labels Section ---
        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "show_pie_appearance", toggle=True, icon='TRIA_DOWN' if props.show_pie_appearance else 'TRIA_RIGHT', text="Pie Chart Appearance & Labels")
        if props.show_pie_appearance:
            # Pie Chart Appearance properties
            box.prop(props, "pie_radius")
            box.prop(props, "pie_height")
            box.prop(props, "explode_factor")
            box.prop(props, "segment_subdivisions")
            box.prop(props, "sort_by")
            
            box.separator() # Visual separator within the merged section
            box.label(text="Labels & Title Settings:")
            box.prop(props, "text_size")
            box.prop(props, "text_offset")
            box.prop(props, "label_horizontal_orientation")
            box.prop(props, "chart_title")
            
        layout.separator()

        # --- Scene Settings Section ---
        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "show_scene_settings", toggle=True, icon='TRIA_DOWN' if props.show_scene_settings else 'TRIA_RIGHT', text="Scene Settings")
        if props.show_scene_settings:
            box.prop(props, "camera_distance")
            box.prop(props, "light_power")

        layout.separator()

        # --- Animations Section ---
        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "show_animations", toggle=True, icon='TRIA_DOWN' if props.show_animations else 'TRIA_RIGHT', text="Animations")
        if props.show_animations:
            # Creation Animation
            box.prop(props, "animate_creation")
            if props.animate_creation:
                box.prop(props, "animation_duration")
                box.prop(props, "animation_offset")
                box.prop(props, "creation_ease_type")

            box.separator()

            # Explode Animation
            box.prop(props, "explode_animation_enabled")
            if props.explode_animation_enabled:
                box.prop(props, "explode_animation_duration")
                box.prop(props, "explode_animation_delay")

            box.separator()

            # Rotate Animation
            box.prop(props, "rotate_animation_enabled")
            if props.rotate_animation_enabled:
                box.prop(props, "rotate_speed")
                box.prop(props, "rotate_loops")

        layout.separator()

        # --- Generate Button ---
        layout.operator(CSV_OT_GeneratePieChart.bl_idname, icon='RENDER_STILL')


classes = (
    CSV_OT_AutodetectColumns,
    CSV_OT_GeneratePieChart,
    CSV_PieChartProperties,
    CSV_PT_PieChartPanel
)

def register():
    # Ensure unregister is called first for clean re-registration in text editor
    try:
        unregister()
    except Exception:
        pass # Ignore error if not already registered

    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.csv_pie_chart_props = bpy.props.PointerProperty(type=CSV_PieChartProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    # Check if the pointer property exists before deleting
    if hasattr(bpy.types.Scene, 'csv_pie_chart_props'):
        del bpy.types.Scene.csv_pie_chart_props

if __name__ == "__main__":
    register()
