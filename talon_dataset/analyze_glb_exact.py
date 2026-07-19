import trimesh
import json

def get_exact():
    body = trimesh.load(r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\BreakTalon\SM_Talon_Body.glb", force='scene')
    wing_l = trimesh.load(r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\BreakTalon\SM_Talon_Wing_L.glb", force='scene')
    
    b_min = body.bounds[0]
    b_max = body.bounds[1]
    
    wl_min = wing_l.bounds[0]
    wl_max = wing_l.bounds[1]
    
    print(f"Body Min: {b_min}")
    print(f"Body Max: {b_max}")
    print(f"WingL Min: {wl_min}")
    print(f"WingL Max: {wl_max}")

if __name__ == "__main__":
    get_exact()
