import trimesh
import os

base_dir = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\V2"

parts = {
    "Body": "SM_Talon_Body.glb",
    "Wing_L": "SM_Talon_Wing_L.glb",
    "Wing_R": "SM_Talon_Wing_R.glb"
}

print("=== TALON OTOMATIK KOORDINAT OLCUM SISTEMI ===")

for part_name, filename in parts.items():
    path = os.path.join(base_dir, filename)
    if os.path.exists(path):
        mesh = trimesh.load(path)
        if isinstance(mesh, trimesh.Scene):
            if len(mesh.geometry) > 0:
                geom_name = list(mesh.geometry.keys())[0]
                mesh = mesh.geometry[geom_name]
            else:
                continue
                
        # Get bounding box extremes
        vertices = mesh.vertices
        
        print(f"\n[{part_name}] ({filename})")
        
        if part_name == "Body":
            # Y usually represents forward/backward in these exports (or X).
            # Let's find extremes in all axes
            min_x_v = vertices[vertices[:, 0].argmin()]
            max_x_v = vertices[vertices[:, 0].argmax()]
            min_y_v = vertices[vertices[:, 1].argmin()]
            max_y_v = vertices[vertices[:, 1].argmax()]
            min_z_v = vertices[vertices[:, 2].argmin()]
            max_z_v = vertices[vertices[:, 2].argmax()]
            
            # Print in Unreal format (multiplied by 100)
            print("  -> Max X Extreme (Unreal X/Y/Z):", [round(v*100, 2) for v in max_x_v])
            print("  -> Min X Extreme (Unreal X/Y/Z):", [round(v*100, 2) for v in min_x_v])
            print("  -> Max Y Extreme (Unreal X/Y/Z):", [round(v*100, 2) for v in max_y_v])
            print("  -> Min Y Extreme (Unreal X/Y/Z):", [round(v*100, 2) for v in min_y_v])
            print("  -> Max Z Extreme (Unreal X/Y/Z):", [round(v*100, 2) for v in max_z_v])
            
        elif part_name == "Wing_L":
            min_x_v = vertices[vertices[:, 0].argmin()]
            max_x_v = vertices[vertices[:, 0].argmax()]
            min_y_v = vertices[vertices[:, 1].argmin()]
            max_y_v = vertices[vertices[:, 1].argmax()]
            print("  -> Max X Extreme (Left Wing Tip):", [round(v*100, 2) for v in max_x_v])
            print("  -> Min X Extreme (Left Wing Tip):", [round(v*100, 2) for v in min_x_v])
            print("  -> Max Y Extreme (Left Wing Tip):", [round(v*100, 2) for v in max_y_v])
            print("  -> Min Y Extreme (Left Wing Tip):", [round(v*100, 2) for v in min_y_v])
            
        elif part_name == "Wing_R":
            min_x_v = vertices[vertices[:, 0].argmin()]
            max_x_v = vertices[vertices[:, 0].argmax()]
            min_y_v = vertices[vertices[:, 1].argmin()]
            max_y_v = vertices[vertices[:, 1].argmax()]
            print("  -> Max X Extreme (Right Wing Tip):", [round(v*100, 2) for v in max_x_v])
            print("  -> Min X Extreme (Right Wing Tip):", [round(v*100, 2) for v in min_x_v])
            print("  -> Max Y Extreme (Right Wing Tip):", [round(v*100, 2) for v in max_y_v])
            print("  -> Min Y Extreme (Right Wing Tip):", [round(v*100, 2) for v in min_y_v])
