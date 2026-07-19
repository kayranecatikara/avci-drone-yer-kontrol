import os
import json
import math
import sys

WORKSPACE_DIR = r"c:\Users\Zeylo\Desktop\talon_dataset"
if WORKSPACE_DIR not in sys.path:
    sys.path.append(WORKSPACE_DIR)

import keypoint_editor

class DummyEditor(keypoint_editor.KeypointEditor):
    def __init__(self):
        self.current_json_data = {}

def get_pt(kps, name):
    return kps.get(name, {'x': -1, 'y': -1})

def fix_swapped_keypoints():
    editor = DummyEditor()
    dataset_dir = os.path.join(WORKSPACE_DIR, "dataset")
    files = [f for f in os.listdir(dataset_dir) if f.endswith('.json')]
    fixed_count = 0
    
    for f in files:
        filepath = os.path.join(dataset_dir, f)
        with open(filepath, 'r', encoding='utf-8') as jf:
            data = json.load(jf)
            
        if not data.get('manually_edited'):
            continue
            
        editor.current_json_data = data
        default_kps = editor.recompute_default_keypoints()
        manual_kps = data.get('keypoints_2d', {})
        
        ml = get_pt(manual_kps, 'left_wingtip')
        mr = get_pt(manual_kps, 'right_wingtip')
        dl = get_pt(default_kps, 'left_wingtip')
        dr = get_pt(default_kps, 'right_wingtip')
        
        if ml['x'] >= 0 and mr['x'] >= 0 and dl['x'] >= 0 and dr['x'] >= 0:
            dist_l_l = math.hypot(ml['x'] - dl['x'], ml['y'] - dl['y'])
            dist_l_r = math.hypot(ml['x'] - dr['x'], ml['y'] - dr['y'])
            
            # Eğer sol kanat olarak işaretlenen nokta, gerçekteki (default) sağ kanada daha yakınsa ters işaretlenmiştir.
            if dist_l_r < dist_l_l:
                # Kanatları Takas Et
                manual_kps['left_wingtip'], manual_kps['right_wingtip'] = manual_kps['right_wingtip'], manual_kps['left_wingtip']
                
                # Kuyruk kanatçıkları kontrolü
                tl = get_pt(manual_kps, 'left_tail_fin')
                tr = get_pt(manual_kps, 'right_tail_fin')
                dtl = get_pt(default_kps, 'left_tail_fin')
                dtr = get_pt(default_kps, 'right_tail_fin')
                
                if tl['x'] >= 0 and tr['x'] >= 0 and dtl['x'] >= 0 and dtr['x'] >= 0:
                    dist_tl_tl = math.hypot(tl['x'] - dtl['x'], tl['y'] - dtl['y'])
                    dist_tl_tr = math.hypot(tl['x'] - dtr['x'], tl['y'] - dtr['y'])
                    if dist_tl_tr < dist_tl_tl:
                        # Kuyruk kanatçıkları da ters, takas et.
                        manual_kps['left_tail_fin'], manual_kps['right_tail_fin'] = manual_kps['right_tail_fin'], manual_kps['left_tail_fin']
                        
                # JSON verisini kaydet
                with open(filepath, 'w', encoding='utf-8') as jf:
                    json.dump(data, jf, indent=4)
                    
                print(f"[FIXED] {f}")
                fixed_count += 1
                
    print(f"Toplam düzeltilen dosya sayısı: {fixed_count}")

if __name__ == "__main__":
    fix_swapped_keypoints()
