import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
import matplotlib.colors as mcolors

# Thiết lập trang với phong cách Apple
plt.figure(figsize=(12, 6))
plt.style.use('default')
ax = plt.subplot(111)
ax.set_facecolor('#ffffff')

# Định nghĩa màu theo phong cách Apple
apple_colors = [
    '#007AFF',  # Xanh dương (blue)
    '#34C759',  # Xanh lá (green)
    '#5856D6',  # Tím (purple)
    '#FF9500',  # Cam (orange)
    '#FF2D55',  # Hồng (pink)
    '#AF52DE',  # Tím nhạt (purple light)
    '#FFCC00',  # Vàng (yellow)
    '#FF3B30'   # Đỏ (red)
]

# Các bước trong quy trình
steps = [
    'Dữ liệu đầu vào\nInput Data',
    'Đọc dữ liệu\nLoad Data',
    'Chọn khu vực\nSelect Region',
    'Tạo đa giác Voronoi\nCreate Voronoi Polygons',
    'Tính thống kê gió\nCalculate Wind Statistics',
    'Hiển thị dữ liệu\nVisualize Data',
    'Bản đồ tương tác\nInteractive Map',
    'Xuất kết quả\nExport Results'
]

# Vẽ quy trình theo chiều dọc
num_steps = len(steps)
y_positions = np.linspace(0.2, 0.8, num_steps)
x_position = 0.5

# Thêm tiêu đề
plt.text(0.5, 0.95, 'Quy trình phân tích tiềm năng gió', fontsize=18, weight='bold', ha='center', va='center')
plt.text(0.5, 0.9, 'Wind Potential Analysis Workflow', fontsize=16, alpha=0.8, ha='center', va='center')

# Vẽ các node và liên kết
for i, (step, color, y) in enumerate(zip(steps, apple_colors, y_positions)):
    # Vẽ node
    circle = Circle((x_position, y), 0.05, color=color, alpha=0.85)
    ax.add_patch(circle)
    
    # Bóng mờ nhẹ (subtle shadow) cho hiệu ứng 3D
    shadow = Circle((x_position+0.0015, y-0.0015), 0.05, color='#00000020', alpha=0.2, zorder=1)
    ax.add_patch(shadow)
    
    # Đường viền sáng (highlight) ở phía trên
    highlight = Circle((x_position, y), 0.05, color=color, alpha=0.3, fill=False, linewidth=2)
    ax.add_patch(highlight)
    
    # Thêm số thứ tự
    plt.text(x_position, y, str(i+1), color='white', ha='center', va='center', fontsize=14, weight='bold')
    
    # Thêm tên bước
    plt.text(x_position + 0.07, y, step.split('\n')[0], ha='left', va='center', fontsize=11, weight='bold')
    plt.text(x_position + 0.07, y - 0.02, step.split('\n')[1], ha='left', va='center', fontsize=10, color='#666666')
    
    # Vẽ đường nối giữa các node
    if i < num_steps - 1:
        plt.plot([x_position, x_position], [y-0.05, y_positions[i+1]+0.05], 
                color='#D1D1D6', linewidth=2, linestyle='-', alpha=0.8)

# Thêm giải thích
ax.text(0.05, 0.05, '© VietnamWind', fontsize=10, color='#8E8E93')

# Thiết lập kích thước và tỷ lệ
ax.set_xlim(0.15, 0.9)
ax.set_ylim(0, 1)
ax.set_aspect('equal')
ax.axis('off')

# Lưu hình ảnh
plt.tight_layout()
plt.savefig('assets/images/workflow_refined.png', dpi=300, bbox_inches='tight')
plt.close()
print('Đã tạo workflow mới theo phong cách Apple UI/UX.')
