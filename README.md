# Blender-CSV-Visualizer
A Blender add-on for visualizing CSV data as 3D objects.

# 📊 CSV Data Visualizer for Blender

**CSV Data Visualizer** is a Blender add-on that lets you turn CSV data into beautiful 3D visualizations—right inside Blender. Whether you're working with bar charts or 3D scatter plots, this tool makes data exploration visual and intuitive.

---

## 🔧 Features

- 📁 **CSV Import**: Load any CSV file and map columns to axes, scale, and color.
- 📊 **Chart Types**:
  - Bar Chart (X: categorical, Y: numerical)
  - 3D Scatter Plot (X, Y, Z: numerical)
  - Custom configuration
- 🧭 **Axis Mapping**: Choose which columns represent X, Y, Z. Treat them as numerical or categorical.
- 🎨 **Visual Styling**:
  - Choose primitives: Cube, Sphere, Cone, Cylinder
  - Scale objects using data
  - Color mapping or alternating colors
  - Optional labels and axis lines
- 💡 **Scene Setup**:
  - Camera presets: Front, Top, Isometric
  - Lighting presets: Sun Lamp, Point Lamp
- 🖥️ **User Interface**: Integrated into Blender’s 3D Viewport sidebar under the **CSV Viz** tab.

---

## 📦 Installation

1. Download the `csv_data_visualizer.py` file.
2. Open Blender → Edit → Preferences → Add-ons → Install.
3. Select the `.py` file and click **Install Add-on**.
4. Enable the add-on from the list.
5. Go to the 3D Viewport → Press `N` → Find the **CSV Viz** tab.

---

## 🧪 Example Usage

- Load a CSV file with columns like `Category, Value`.
- Choose **Bar Chart** preset.
- Set `X Column = 0`, `Y Column = 1`.
- Click **Visualize CSV Data**.

---

## 📁 File Structure

