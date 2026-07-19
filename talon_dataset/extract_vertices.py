import trimesh
import json

def get_vertices():
    body = trimesh.load(r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\BreakTalon\SM_Talon_Body.glb", force='scene')
    wing_l = trimesh.load(r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\BreakTalon\SM_Talon_Wing_L.glb", force='scene')
    wingsmall_l = trimesh.load(r"C:\Users\Zeylo\Desktop\FModel\Output\Exports\DronesOfWar\Content\Art\Meshes\Talon\BreakTalon\SM_Talon_WingSmall_L.glb", force='scene')
    
    # Get all vertices from body
    bv = []
    for geom in body.geometry.values():
        bv.extend(geom.vertices)
        
    # Get all vertices from wing_l
    wlv = []
    for geom in wing_l.geometry.values():
        wlv.extend(geom.vertices)
        
    wslv = []
    for geom in wingsmall_l.geometry.values():
        wslv.extend(geom.vertices)
        
    # Find specific points
    # Nose = max X in body
    nose = max(bv, key=lambda v: v[0])
    # Tail = min X in body
    tail = min(bv, key=lambda v: v[0])
    
    # Left wingtip = min Z in wing_l
    lw = min(wlv, key=lambda v: v[2])
    
    # Left tail fin tip = min Z in wingsmall_l
    l_tail_fin = min(wslv, key=lambda v: v[2])
    
    print(f"Nose Vertex: {nose}")
    print(f"Tail Vertex: {tail}")
    print(f"Left Wingtip Vertex: {lw}")
    print(f"Left Tail Fin Vertex: {l_tail_fin}")

if __name__ == "__main__":
    get_vertices()
