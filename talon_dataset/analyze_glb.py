import trimesh
import sys

def analyze_model():
    filepath = r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\BreakTalon\SM_Talon_Body.glb"
    
    print("Loading 3D model...")
    scene = trimesh.load(filepath, force='scene')
    
    # Get the bounding box of the entire scene
    bounds = scene.bounds
    extents = scene.extents
    
    print(f"Min Bounds: X={bounds[0][0]:.2f}, Y={bounds[0][1]:.2f}, Z={bounds[0][2]:.2f}")
    print(f"Max Bounds: X={bounds[1][0]:.2f}, Y={bounds[1][1]:.2f}, Z={bounds[1][2]:.2f}")
    print(f"Dimensions (Extents): Length(X)={extents[0]:.2f}, Width(Y)={extents[1]:.2f}, Height(Z)={extents[2]:.2f}")
    
    # Write the results to a file for easy reading
    with open(r"C:\Users\Zeylo\Desktop\Talon_True_Dimensions.txt", "w") as f:
        f.write(f"Min Bounds: X={bounds[0][0]:.2f}, Y={bounds[0][1]:.2f}, Z={bounds[0][2]:.2f}\n")
        f.write(f"Max Bounds: X={bounds[1][0]:.2f}, Y={bounds[1][1]:.2f}, Z={bounds[1][2]:.2f}\n")

if __name__ == "__main__":
    analyze_model()
