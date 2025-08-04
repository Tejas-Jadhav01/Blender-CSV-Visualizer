import bpy
import csv
import math
from mathutils import Vector, Euler

bl_info = {
    "name": "CSV Pie Chart Visualizer",
    "author": "Gemini",
    "version": (1, 1), # Updated version
    "blender": (3, 0, 0),
    "location": "3D Viewport > Sidebar > CSV Pie Chart Tab",
    "description": "Visualizes CSV data as a 3D pie chart with scene setup.",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

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
        background_color = props.background_color

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

        # --- Scene Setup ---
        self.setup_scene(context, camera_distance, light_power, background_color)

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

        start_angle = 0
        
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

            # Set a random color for the slice
            mat_name = f"SliceMaterial_{i}"
            if mat_name in bpy.data.materials:
                mat = bpy.data.materials[mat_name]
            else:
                mat = bpy.data.materials.new(name=mat_name)
                mat.diffuse_color = (
                    abs(math.sin(i * 0.7)),
                    abs(math.cos(i * 0.9)),
                    abs(math.sin(i * 1.1)),
                    1.0
                )
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

            # Position the slice
            obj.location = Vector((
                pie_radius * math.cos(start_angle + angle / 2) * props.explode_factor,
                pie_radius * math.sin(start_angle + angle / 2) * props.explode_factor,
                0
            ))

            # Add text label
            # Calculate the mid-angle for label positioning
            mid_angle = start_angle + angle / 2
            text_x = (pie_radius + text_offset) * math.cos(mid_angle)
            text_y = (pie_radius + text_offset) * math.sin(mid_angle)

            bpy.ops.object.text_add(enter_editmode=False, location=(text_x, text_y, pie_height / 2))
            text_obj = bpy.context.active_object
            text_obj.data.body = f"{item['label']} ({percentage:.1%})"
            text_obj.data.size = text_size
            text_obj.data.align_x = 'CENTER'
            text_obj.data.align_y = 'CENTER' 

            # Rotate text to face outwards and align with the slice
            text_obj.rotation_euler.z = mid_angle + math.pi / 2 # Rotate to face outwards
            text_obj.rotation_euler.x = math.radians(90) # Make text stand upright

            # Link text object to the pie chart collection
            pie_collection.objects.link(text_obj)
            bpy.context.collection.objects.unlink(text_obj) # Unlink from current collection

            start_angle += angle
            
        self.report({'INFO'}, "Pie chart and scene generated successfully!")
        return {'FINISHED'}

    def setup_scene(self, context, camera_distance, light_power, background_color):
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

        # Position the camera: looking at the origin, slightly above and forward
        cam_obj.location = (0, -camera_distance, camera_distance * 0.75) # Adjust Z for angle
        
        # Point the camera to the origin (0,0,0)
        # Calculate rotation to look at (0,0,0)
        direction = Vector((0,0,0)) - cam_obj.location
        rot_quat = direction.to_track_quat('-Z', 'Y') # -Z for camera direction, Y for up
        cam_obj.rotation_euler = rot_quat.to_euler()

        context.scene.camera = cam_obj # Set as active camera

        # --- Light Setup (Sun Light) ---
        light_data = bpy.data.lights.new("PieChartLight", type='SUN')
        light_obj = bpy.data.objects.new("PieChartLight", light_data)
        context.collection.objects.link(light_obj)

        light_obj.data.energy = light_power
        light_obj.location = (5, -5, 10) # Position the light
        # Point the light towards the origin (pie chart)
        light_obj.rotation_euler = Euler((math.radians(45), 0, math.radians(45)), 'XYZ') # Angle for sunlight

        # --- Background Color ---
        # Set the world background color
        world = context.scene.world
        if not world:
            world = bpy.data.worlds.new("World")
            context.scene.world = world
        
        world.use_nodes = True
        bg_node = world.node_tree.nodes.get('Background')
        if not bg_node:
            bg_node = world.node_tree.nodes.new('ShaderNodeBackground')
            world.node_tree.links.new(bg_node.outputs['Background'], world.node_tree.nodes['World Output'].inputs['Surface'])
        
        bg_node.inputs['Color'].default_value = background_color
        bg_node.inputs['Strength'].default_value = 1.0 # Ensure background is visible


class CSV_PieChartProperties(bpy.types.PropertyGroup):
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
    background_color: bpy.props.FloatVectorProperty(
        name="Background Color",
        subtype='COLOR',
        description="Color of the world background",
        default=(0.1, 0.1, 0.1, 1.0), # Default dark grey
        min=0.0, max=1.0,
        size=4 # RGBA
    )


class CSV_PT_PieChartPanel(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport Sidebar"""
    bl_label = "CSV Pie Chart"
    bl_idname = "CSV_PT_PieChartPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CSV Pie Chart" # This creates a new tab in the N-panel

    def draw(self, context):
        layout = self.layout
        props = context.scene.csv_pie_chart_props

        # File selection
        layout.prop(props, "csv_file_path")
        layout.prop(props, "label_column")
        layout.prop(props, "value_column")

        layout.separator()

        # Pie chart properties
        layout.prop(props, "pie_radius")
        layout.prop(props, "pie_height")
        layout.prop(props, "explode_factor")
        layout.prop(props, "segment_subdivisions")

        layout.separator()

        # Text properties
        layout.prop(props, "text_size")
        layout.prop(props, "text_offset")

        layout.separator()

        # Scene properties
        layout.label(text="Scene Setup:")
        layout.prop(props, "camera_distance")
        layout.prop(props, "light_power")
        layout.prop(props, "background_color")

        layout.separator()

        # Generate button
        layout.operator(CSV_OT_GeneratePieChart.bl_idname)


classes = (
    CSV_OT_GeneratePieChart,
    CSV_PieChartProperties,
    CSV_PT_PieChartPanel
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.csv_pie_chart_props = bpy.props.PointerProperty(type=CSV_PieChartProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.csv_pie_chart_props

if __name__ == "__main__":
    register()
