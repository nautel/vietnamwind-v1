#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bản đồ tương tác phân tích tiềm năng gió Việt Nam
Interactive Map for Vietnam Wind Potential Analysis

Cho phép vẽ bản đồ tương tác với các ô Voronoi, người dùng có thể di chuột 
qua từng ô để xem thông tin về tốc độ gió và tiềm năng năng lượng gió tại khu vực đó.

Thư viện cần thiết:
- NumPy, Pandas, GeoPandas, Matplotlib, mpld3, Folium (cho tương tác)
- Rasterio, Rasterstats (cho xử lý dữ liệu raster)
"""

import os
import sys
from pathlib import Path
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import mpld3
from mpld3 import plugins

# Thêm thư mục hiện tại vào đường dẫn để có thể import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import trực tiếp từ file vietnamwind.py
from vietnamwind import WindPotentialAnalyzer

# Đường dẫn dữ liệu
DATA_DIR = Path('data')
RESULTS_DIR = Path('results')
ASSETS_DIR = Path('assets/images')

def create_interactive_map(region_name=None, num_points=100, save_html=True, show_plot=True):
    """
    Tạo bản đồ tương tác cho một khu vực cụ thể hoặc toàn bộ Việt Nam
    
    Parameters:
    -----------
    region_name : str, optional
        Tên tỉnh/thành phố (ví dụ: "Gia Lai"). Nếu None, sẽ phân tích toàn bộ Việt Nam.
    num_points : int, default=100
        Số lượng điểm để tạo các đa giác Voronoi
    save_html : bool, default=True
        Lưu bản đồ dưới dạng file HTML
    show_plot : bool, default=True
        Hiển thị biểu đồ (chỉ hoạt động khi chạy script từ notebook hoặc IDE có hỗ trợ)
        
    Returns:
    --------
    str
        Đường dẫn đến file HTML nếu đã lưu
    """
    print(f"\n=== Tạo bản đồ tương tác cho {region_name or 'toàn bộ Việt Nam'} ===\n")
    
    # Tạo thư mục kết quả và assets nếu chưa tồn tại
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Tạo đối tượng phân tích tiềm năng gió
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu
    analyzer.load_data(DATA_DIR / 'vietnam.geojson', DATA_DIR / 'VNM_wind-speed_100m.tif')
    
    # Xử lý cho một tỉnh/thành phố cụ thể
    region_suffix = ""
    if region_name:
        province_file = DATA_DIR / 'vietnam_provinces.geojson'
        if not province_file.exists():
            print(f"Lỗi: Không tìm thấy file ranh giới tỉnh/thành phố: {province_file}")
            return None
            
        analyzer.load_provinces(province_file)
        try:
            analyzer.select_region(region_name)
            region_suffix = f"_{region_name.lower().replace(' ', '_')}"
        except ValueError as e:
            print(f"Lỗi: {e}")
            return None
    
    # Tạo các đa giác Voronoi
    analyzer.create_voronoi_polygons(num_points=num_points)
    
    # Tính toán thống kê gió
    analyzer.calculate_wind_statistics()
    
    # Tạo biểu đồ tương tác
    try:
        # Tạo hình và trục
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Lấy dữ liệu Voronoi từ analyzer
        if hasattr(analyzer, 'voronoi_polygons') and analyzer.voronoi_polygons is not None:
            gdf = analyzer.voronoi_polygons
            
            # Làm sạch dữ liệu - loại bỏ các đa giác có geometry là None
            gdf = gdf[gdf.geometry.notna()].copy()
            
            if len(gdf) == 0:
                print("Không có dữ liệu Voronoi hợp lệ sau khi làm sạch")
                return None
                
            # Lấy dữ liệu tốc độ gió trung bình và phân loại
            wind_speeds = gdf['wind_mean']
            vmin, vmax = wind_speeds.min(), wind_speeds.max()
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            
            # Tạo colormap cho tốc độ gió
            wind_cmap = plt.cm.YlOrRd
            
            # Vẽ các đa giác Voronoi với màu sắc dựa trên tốc độ gió
            polygons = []
            for idx, row in gdf.iterrows():
                polygon = row.geometry
                wind_speed = row.wind_mean
                color = wind_cmap(norm(wind_speed))
                
                # Xử lý cả Polygon và MultiPolygon
                if polygon is None:
                    continue  # Bỏ qua nếu geometry là None
                
                if polygon.geom_type == 'Polygon':
                    # Vẽ polygon
                    patch = ax.fill(*polygon.exterior.xy, alpha=0.7, color=color, edgecolor='k', linewidth=0.5)
                    polygons.append(patch[0])
                elif polygon.geom_type == 'MultiPolygon':
                    # Vẽ từng polygon trong MultiPolygon
                    for p in polygon.geoms:
                        patch = ax.fill(*p.exterior.xy, alpha=0.7, color=color, edgecolor='k', linewidth=0.5)
                        polygons.append(patch[0])
                        break  # Chỉ lấy polygon đầu tiên cho tooltip để tránh quá nhiều điểm
            
            # Vẽ ranh giới khu vực
            display_region = analyzer.selected_region if analyzer.selected_region is not None else analyzer.catchments
            display_region.boundary.plot(ax=ax, color='black', linewidth=1.5)
            
            # Thêm colorbar
            cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=wind_cmap), ax=ax)
            cbar.set_label('Tốc độ gió trung bình (m/s) / Mean Wind Speed (m/s)')
            
            # Cấu hình trục
            ax.set_title(f'Bản đồ tiềm năng gió - {region_name or "Việt Nam"} / Wind Potential Map')
            ax.set_xlabel('Kinh độ / Longitude')
            ax.set_ylabel('Vĩ độ / Latitude')
            ax.set_aspect('equal')
            
            # Tạo tooltip hiển thị khi hover
            tooltip_html = []
            for idx, row in gdf.iterrows():
                html = f"""
                <div style="background-color: white; padding: 10px; border-radius: 5px; border: 1px solid #ddd;">
                    <h3>Thông tin khu vực / Area info</h3>
                    <p><b>ID:</b> {idx + 1}</p>
                    <p><b>Tốc độ gió trung bình / Mean wind speed:</b> {row.wind_mean:.2f} m/s</p>
                    <p><b>Độ lệch chuẩn / Standard deviation:</b> {row.wind_std:.2f} m/s</p>
                    <p><b>Tên:</b> {row.name if 'name' in row else f'Vùng {idx + 1}'}</p>
                </div>
                """
                tooltip_html.append(html)
            
            # Thêm tương tác
            tooltip = plugins.PointHTMLTooltip(polygons, tooltip_html, voffset=10, hoffset=10)
            plugins.connect(fig, tooltip)
            
            # Tạo ảnh dự phòng để dùng trong README
            static_img_path = ASSETS_DIR / f'interactive_map{region_suffix}.png'
            plt.savefig(static_img_path, dpi=300, bbox_inches='tight')
            print(f"Đã lưu ảnh tĩnh tại: {static_img_path}")
            
            # Lưu dưới dạng HTML
            if save_html:
                html_path = RESULTS_DIR / f'vietnam_wind_interactive{region_suffix}.html'
                html = mpld3.fig_to_html(fig)
                
                # Thêm một số CSS để cải thiện giao diện
                styled_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Bản đồ tương tác tiềm năng gió - {region_name or "Việt Nam"}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                        h1 {{ text-align: center; color: #2c3e50; }}
                        .mpld3-figure {{ margin: 0 auto; max-width: 900px; }}
                        .tooltip {{ font-size: 14px; }}
                    </style>
                </head>
                <body>
                    <h1>Bản đồ tương tác tiềm năng gió - {region_name or "Việt Nam"}</h1>
                    <p style="text-align: center;">Di chuyển chuột trên các khu vực để xem thông tin chi tiết / Hover over areas to see detailed information</p>
                    {html}
                </body>
                </html>
                """
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(styled_html)
                
                print(f"Đã lưu bản đồ tương tác tại: {html_path}")
                
                # Hiển thị hình nếu được yêu cầu
                if show_plot:
                    plt.show()
                else:
                    plt.close()
                
                return html_path
        else:
            print("Lỗi: Không tìm thấy dữ liệu Voronoi trong đối tượng analyzer.")
            print("Thông tin debug - Các thuộc tính có sẵn:", dir(analyzer))
            
            # Kiểm tra xem có thuộc tính tương tự không
            potential_attrs = [attr for attr in dir(analyzer) if 'voronoi' in attr.lower() or 'polygon' in attr.lower() or 'gdf' in attr.lower()]
            if potential_attrs:
                print("Các thuộc tính có thể liên quan:", potential_attrs)
            
            print("Không tìm thấy dữ liệu Voronoi phù hợp. Hãy đảm bảo bạn đã gọi create_voronoi_polygons()")
    
    except Exception as e:
        print(f"Lỗi khi tạo bản đồ tương tác: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return None

def list_available_regions():
    """Liệt kê các tỉnh/thành phố có sẵn để phân tích"""
    # Tạo đối tượng phân tích tiềm năng gió
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu tỉnh/thành phố
    province_file = DATA_DIR / 'vietnam_provinces.geojson'
    if not province_file.exists():
        print(f"Lỗi: Không tìm thấy file ranh giới tỉnh/thành phố: {province_file}")
        return []
        
    analyzer.load_provinces(province_file)
    regions = analyzer.list_available_regions()
    
    print("\nCác tỉnh/thành phố có sẵn để phân tích / Available provinces/cities for analysis:")
    for region in regions:
        print(f"  - {region}")
        
    return regions

def check_required_files():
    """Kiểm tra các file dữ liệu cần thiết"""
    required_files = [
        DATA_DIR / 'vietnam.geojson',
        DATA_DIR / 'VNM_wind-speed_100m.tif',
        DATA_DIR / 'vietnam_provinces.geojson'
    ]
    
    missing_files = [str(f) for f in required_files if not f.exists()]
    
    if missing_files:
        print("Lỗi: Không tìm thấy các file dữ liệu sau:")
        for f in missing_files:
            print(f"  - {f}")
        print("\nBạn cần tải dữ liệu từ Global Wind Atlas: https://globalwindatlas.info/area/Vietnam")
        print("Và đặt vào thư mục data/ với cấu trúc như đã mô tả trong README.md")
        return False
    
    # Kiểm tra thư viện mpld3
    try:
        import mpld3
    except ImportError:
        print("\nChú ý: Thư viện mpld3 chưa được cài đặt. Tính năng tương tác hover sẽ không hoạt động.")
        print("Bạn có thể cài đặt bằng lệnh: pip install mpld3")
        return False
    
    return True

def main():
    """Hàm chính để chạy chương trình"""
    # Tạo parser dòng lệnh
    parser = argparse.ArgumentParser(description='Tạo bản đồ tương tác phân tích tiềm năng gió Việt Nam')
    
    parser.add_argument('--region', type=str, default=None, 
                        help='Tên tỉnh/thành phố, ví dụ: "Gia Lai". Mặc định sẽ phân tích toàn bộ Việt Nam.')
    parser.add_argument('--points', type=int, default=100, 
                        help='Số lượng điểm để tạo các đa giác Voronoi. Mặc định: 100')
    parser.add_argument('--list-regions', action='store_true', 
                        help='Liệt kê các tỉnh/thành phố có sẵn để phân tích rồi thoát')
    parser.add_argument('--no-show', action='store_true', 
                        help='Không hiển thị biểu đồ, chỉ lưu file')
    
    args = parser.parse_args()
    
    # Kiểm tra các file cần thiết
    if not check_required_files():
        return
    
    # Liệt kê các tỉnh/thành phố nếu được yêu cầu
    if args.list_regions:
        list_available_regions()
        return
    
    # Tạo bản đồ tương tác
    create_interactive_map(
        region_name=args.region,
        num_points=args.points,
        save_html=True,
        show_plot=not args.no_show
    )

if __name__ == "__main__":
    # Khi chạy như một script độc lập
    if len(sys.argv) > 1:
        # Chạy với các tham số dòng lệnh
        main()
    else:
        # Chạy chế độ tương tác nếu không có tham số
        print("\n===== Tạo bản đồ tương tác phân tích tiềm năng gió Việt Nam =====")
        print("===== Interactive Map for Vietnam Wind Potential Analysis =====\n")
        
        choice = input("Bạn muốn phân tích toàn bộ Việt Nam hay một tỉnh/thành phố cụ thể? / Do you want to analyze entire Vietnam or a specific province?\n1. Toàn bộ Việt Nam / Entire Vietnam\n2. Tỉnh/thành phố cụ thể / Specific province\nLựa chọn / Choice (1/2): ")
        
        if choice == '2':
            regions = list_available_regions()
            if not regions:
                sys.exit(1)
            
            region_name = input("\nNhập tên tỉnh/thành phố (ví dụ: Gia Lai) / Enter province name (e.g., Gia Lai): ")
            points = input("Số lượng điểm Voronoi (mặc định: 100) / Number of Voronoi points (default: 100): ")
            
            try:
                points = int(points) if points.strip() else 100
            except ValueError:
                points = 100
                print("Giá trị không hợp lệ, sử dụng mặc định: 100 điểm")
            
            create_interactive_map(region_name=region_name, num_points=points)
            
        else:
            points = input("Số lượng điểm Voronoi (mặc định: 100) / Number of Voronoi points (default: 100): ")
            
            try:
                points = int(points) if points.strip() else 100
            except ValueError:
                points = 100
                print("Giá trị không hợp lệ, sử dụng mặc định: 100 điểm")
            
            create_interactive_map(num_points=points) 