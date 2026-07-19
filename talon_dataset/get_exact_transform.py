import numpy as np

# Coordinates in talon_0001.json
json_pts = np.array([
    [804, 530],   # nose
    [890, 659],   # left_wingtip
    [960, 351],   # right_wingtip
    [1024, 544]   # tail
])

# Coordinates in user_img
user_pts = np.array([
    [111, 376],   # nose
    [275, 668],   # left_wingtip
    [421, 60],    # right_wingtip
    [532, 403]    # tail
])

# Fit: user_x = s * json_x + tx
# Fit: user_y = s * json_y + ty
# We can solve for s, tx, ty.
# Let's stack x and y coordinates
A_x = np.column_stack((json_pts[:, 0], np.ones(4)))
s_x, tx = np.linalg.lstsq(A_x, user_pts[:, 0], rcond=None)[0]

A_y = np.column_stack((json_pts[:, 1], np.ones(4)))
s_y, ty = np.linalg.lstsq(A_y, user_pts[:, 1], rcond=None)[0]

print(f"X-fit: scale={s_x:.6f}, translation={tx:.2f}")
print(f"Y-fit: scale={s_y:.6f}, translation={ty:.2f}")

# Let's check average scale and transform the fin tips
s = (s_x + s_y) / 2.0
print(f"Average scale: {s:.6f}")

# The tail fin tips in user image (measured from grid):
# fin1 (up-pointing): (508, 252)
# fin2 (down-pointing): (498, 436)
for name, (ux, uy) in [("fin_up", (508, 252)), ("fin_down", (498, 436))]:
    jx = (ux - tx) / s_x
    jy = (uy - ty) / s_y
    print(f"Original 1920x1080 target for {name}: ({jx:.2f}, {jy:.2f})")
