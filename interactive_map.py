#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bản đồ tương tác phân tích tiềm năng gió Việt Nam
Interactive Map for Vietnam Wind Potential Analysis

Cho phép vẽ bản đồ tương tác với các ô Voronoi, người dùng có thể di chuột 
qua từng ô để xem thông tin về tốc độ gió và tiềm năng năng lượng gió tại khu vực đó.
Allows drawing interactive maps with Voronoi cells, users can hover over
each cell to view information about wind speed and wind energy potential in that area.

Thư viện cần thiết / Required libraries:
- NumPy, Pandas, GeoPandas, Matplotlib, mpld3, Folium (cho tương tác / for interaction)
- Rasterio, Rasterstats (cho xử lý dữ liệu raster / for raster data processing)
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
# Add current directory to path to be able to import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import trực tiếp từ file vietnamwind.py
# Import directly from vietnamwind.py
from vietnamwind import WindPotentialAnalyzer

# Đường dẫn dữ liệu / Data paths
DATA_DIR = Path('data')
RESULTS_DIR = Path('results')
ASSETS_DIR = Path('assets/images')

# Thử import các thư viện tùy chọn / Try to import optional libraries
try:
    import folium
    from folium.plugins import MarkerCluster, HeatMap
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    print("Thư viện folium không khả dụng. Để sử dụng bản đồ tương tác web, hãy cài đặt bằng lệnh: pip install folium")
    print("Folium library not available. To use web interactive maps, install with command: pip install folium")

def create_interactive_map(region_name=None, num_points=100, save_html=True, show_plot=True):
    """
    Tạo bản đồ tương tác cho một khu vực cụ thể hoặc toàn bộ Việt Nam
    Create interactive map for a specific region or entire Vietnam
    
    Parameters:
    -----------
    region_name : str, optional
        Tên tỉnh/thành phố (ví dụ: "Gia Lai"). Nếu None, sẽ phân tích toàn bộ Việt Nam.
        Province/city name (e.g., "Gia Lai"). If None, will analyze entire Vietnam.
    num_points : int, default=100
        Số lượng điểm để tạo các đa giác Voronoi
        Number of points to create Voronoi polygons
    save_html : bool, default=True
        Lưu bản đồ dưới dạng file HTML
        Save map as HTML file
    show_plot : bool, default=True
        Hiển thị biểu đồ (chỉ hoạt động khi chạy script từ notebook hoặc IDE có hỗ trợ)
        Display the chart (only works when running script from notebook or supported IDE)
        
    Returns:
    --------
    str
        Đường dẫn đến file HTML nếu đã lưu
        Path to the HTML file if saved
    """
    print(f"\n=== Tạo bản đồ tương tác cho {region_name or 'toàn bộ Việt Nam'} ===")
    print(f"=== Creating interactive map for {region_name or 'entire Vietnam'} ===\n")
    
    # Tạo thư mục kết quả và assets nếu chưa tồn tại
    # Create results and assets directories if they don't exist
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Tạo đối tượng phân tích tiềm năng gió
    # Create wind potential analyzer object
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu / Read data
    analyzer.load_data(DATA_DIR / 'vietnam.geojson', DATA_DIR / 'VNM_wind-speed_100m.tif')
    
    # Xử lý cho một tỉnh/thành phố cụ thể
    # Process for a specific province/city
    region_suffix = ""
    if region_name:
        province_file = DATA_DIR / 'vietnam_provinces.geojson'
        if not province_file.exists():
            print(f"Lỗi: Không tìm thấy file ranh giới tỉnh/thành phố: {province_file}")
            print(f"Error: Province boundary file not found: {province_file}")
            return None
            
        analyzer.load_provinces(province_file)
        try:
            analyzer.select_region(region_name)
            region_suffix = f"_{region_name.lower().replace(' ', '_')}"
        except ValueError as e:
            print(f"Lỗi/Error: {e}")
            return None
    
    # Tạo các đa giác Voronoi / Create Voronoi polygons
    analyzer.create_voronoi_polygons(num_points=num_points)
    
    # Tính toán thống kê gió / Calculate wind statistics
    analyzer.calculate_wind_statistics()
    
    # Tạo biểu đồ tương tác / Create interactive chart
    try:
        # Tạo hình và trục / Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Lấy dữ liệu Voronoi từ analyzer / Get Voronoi data from analyzer
        if hasattr(analyzer, 'voronoi_polygons') and analyzer.voronoi_polygons is not None:
            gdf = analyzer.voronoi_polygons
            
            # Làm sạch dữ liệu - loại bỏ các đa giác có geometry là None
            # Clean data - remove polygons with None geometry
            gdf = gdf[gdf.geometry.notna()].copy()
            
            if len(gdf) == 0:
                print("Không có dữ liệu Voronoi hợp lệ sau khi làm sạch")
                print("No valid Voronoi data after cleaning")
                return None
                
            # Lấy dữ liệu tốc độ gió trung bình và phân loại
            # Get average wind speed data and classify
            wind_speeds = gdf['wind_mean']
            vmin, vmax = wind_speeds.min(), wind_speeds.max()
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            
            # Tạo colormap cho tốc độ gió / Create colormap for wind speed
            wind_cmap = plt.cm.YlOrRd
            
            # Vẽ các đa giác Voronoi với màu sắc dựa trên tốc độ gió
            # Draw Voronoi polygons with colors based on wind speed
            polygons = []
            for idx, row in gdf.iterrows():
                polygon = row.geometry
                wind_speed = row.wind_mean
                color = wind_cmap(norm(wind_speed))
                
                # Xử lý cả Polygon và MultiPolygon / Handle both Polygon and MultiPolygon
                if polygon is None:
                    continue  # Bỏ qua nếu geometry là None / Skip if geometry is None
                
                if polygon.geom_type == 'Polygon':
                    # Vẽ polygon / Draw polygon
                    patch = ax.fill(*polygon.exterior.xy, alpha=0.7, color=color, edgecolor='k', linewidth=0.5)
                    polygons.append(patch[0])
                elif polygon.geom_type == 'MultiPolygon':
                    # Vẽ từng polygon trong MultiPolygon / Draw each polygon in MultiPolygon
                    for p in polygon.geoms:
                        patch = ax.fill(*p.exterior.xy, alpha=0.7, color=color, edgecolor='k', linewidth=0.5)
                        polygons.append(patch[0])
                        break  # Chỉ lấy polygon đầu tiên cho tooltip để tránh quá nhiều điểm
                              # Only take the first polygon for tooltip to avoid too many points
            
            # Vẽ ranh giới khu vực / Draw region boundary
            display_region = analyzer.selected_region if analyzer.selected_region is not None else analyzer.catchments
            display_region.boundary.plot(ax=ax, color='black', linewidth=1.5)
            
            # Thêm colorbar / Add colorbar
            cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=wind_cmap), ax=ax)
            cbar.set_label('Tốc độ gió trung bình (m/s) / Mean Wind Speed (m/s)')
            
            # Cấu hình trục / Configure axes
            ax.set_title(f'Bản đồ tiềm năng gió - {region_name or "Việt Nam"} / Wind Potential Map')
            ax.set_xlabel('Kinh độ / Longitude')
            ax.set_ylabel('Vĩ độ / Latitude')
            ax.set_aspect('equal')
            
            # Tạo tooltip hiển thị khi hover / Create tooltip to display on hover
            tooltip_html = []
            for idx, row in gdf.iterrows():
                html = f"""
                <div style="background-color: white; padding: 10px; border-radius: 5px; border: 1px solid #ddd;">
                    <h3>Thông tin khu vực / Area info</h3>
                    <p><b>ID:</b> {idx + 1}</p>
                    <p><b>Tốc độ gió trung bình / Mean wind speed:</b> {row.wind_mean:.2f} m/s</p>
                    <p><b>Độ lệch chuẩn / Standard deviation:</b> {row.wind_std:.2f} m/s</p>
                    <p><b>Tên / Name:</b> {row.name if 'name' in row else f'Vùng/Area {idx + 1}'}</p>
                </div>
                """
                tooltip_html.append(html)
            
            # Thêm tương tác / Add interaction
            tooltip = plugins.PointHTMLTooltip(polygons, tooltip_html, voffset=10, hoffset=10)
            plugins.connect(fig, tooltip)
            
            # Tạo ảnh dự phòng để dùng trong README / Create backup image for README
            static_img_path = ASSETS_DIR / f'interactive_map{region_suffix}.png'
            plt.savefig(static_img_path, dpi=300, bbox_inches='tight')
            print(f"Đã lưu ảnh tĩnh tại / Static image saved at: {static_img_path}")
            
            # Lưu dưới dạng HTML / Save as HTML
            if save_html:
                html_path = RESULTS_DIR / f'vietnam_wind_interactive{region_suffix}.html'
                html = mpld3.fig_to_html(fig)
                
                # Thêm một số CSS để cải thiện giao diện / Add some CSS to improve the interface
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
                    <h1>Interactive Wind Potential Map - {region_name or "Vietnam"}</h1>
                    <p style="text-align: center;">Di chuyển chuột trên các khu vực để xem thông tin chi tiết / Hover over areas to see detailed information</p>
                    {html}
                </body>
                </html>
                """
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(styled_html)
                
                print(f"Đã lưu bản đồ tương tác tại / Interactive map saved at: {html_path}")
                
                # Hiển thị hình nếu được yêu cầu / Display figure if requested
                if show_plot:
                    plt.show()
                else:
                    plt.close()
                
                return html_path
        else:
            print("Lỗi: Không tìm thấy dữ liệu Voronoi trong đối tượng analyzer.")
            print("Error: Voronoi data not found in analyzer object.")
            print("Thông tin debug - Các thuộc tính có sẵn / Debug info - Available attributes:", dir(analyzer))
            
            # Kiểm tra xem có thuộc tính tương tự không / Check if there are similar attributes
            potential_attrs = [attr for attr in dir(analyzer) if 'voronoi' in attr.lower() or 'polygon' in attr.lower() or 'gdf' in attr.lower()]
            if potential_attrs:
                print("Các thuộc tính có thể liên quan / Potentially relevant attributes:", potential_attrs)
            
            print("Không tìm thấy dữ liệu Voronoi phù hợp. Hãy đảm bảo bạn đã gọi create_voronoi_polygons()")
            print("No suitable Voronoi data found. Make sure you called create_voronoi_polygons()")
    
    except Exception as e:
        print(f"Lỗi khi tạo bản đồ tương tác / Error creating interactive map: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return None

def create_folium_map(region_name=None, num_points=100, save_html=True):
    """
    Tạo bản đồ tương tác web sử dụng Folium cho một khu vực cụ thể hoặc toàn bộ Việt Nam
    Create web interactive map using Folium for a specific region or entire Vietnam
    
    Parameters:
    -----------
    region_name : str, optional
        Tên tỉnh/thành phố (ví dụ: "Gia Lai"). Nếu None, sẽ phân tích toàn bộ Việt Nam.
        Province/city name (e.g., "Gia Lai"). If None, will analyze entire Vietnam.
    num_points : int, default=100
        Số lượng điểm để tạo các đa giác Voronoi
        Number of points to create Voronoi polygons
    save_html : bool, default=True
        Lưu bản đồ dưới dạng file HTML
        Save map as HTML file
        
    Returns:
    --------
    str
        Đường dẫn đến file HTML nếu đã lưu
        Path to the HTML file if saved
    """
    if not FOLIUM_AVAILABLE:
        print("Thư viện folium không khả dụng. Vui lòng cài đặt với lệnh: pip install folium")
        print("Folium library not available. Please install with command: pip install folium")
        return None
        
    print(f"\n=== Tạo bản đồ tương tác web cho {region_name or 'toàn bộ Việt Nam'} ===")
    print(f"=== Creating web interactive map for {region_name or 'entire Vietnam'} ===\n")
    
    # Tạo thư mục kết quả nếu chưa tồn tại
    # Create results directory if it doesn't exist
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Tạo đối tượng phân tích tiềm năng gió
    # Create wind potential analyzer object
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu / Read data
    analyzer.load_data(DATA_DIR / 'vietnam.geojson', DATA_DIR / 'VNM_wind-speed_100m.tif')
    
    # Xử lý cho một tỉnh/thành phố cụ thể
    # Process for a specific province/city
    region_suffix = ""
    if region_name:
        province_file = DATA_DIR / 'vietnam_provinces.geojson'
        if not province_file.exists():
            print(f"Lỗi: Không tìm thấy file ranh giới tỉnh/thành phố: {province_file}")
            print(f"Error: Province boundary file not found: {province_file}")
            return None
            
        analyzer.load_provinces(province_file)
        try:
            analyzer.select_region(region_name)
            region_suffix = f"_{region_name.lower().replace(' ', '_')}"
        except ValueError as e:
            print(f"Lỗi/Error: {e}")
            return None
    
    # Tạo các đa giác Voronoi / Create Voronoi polygons
    analyzer.create_voronoi_polygons(num_points=num_points)
    
    # Tính toán thống kê gió / Calculate wind statistics
    analyzer.calculate_wind_statistics()
    
    try:
        # Lấy dữ liệu Voronoi từ analyzer / Get Voronoi data from analyzer
        if hasattr(analyzer, 'voronoi_polygons') and analyzer.voronoi_polygons is not None:
            gdf = analyzer.voronoi_polygons
            
            # Làm sạch dữ liệu - loại bỏ các đa giác có geometry là None
            # Clean data - remove polygons with None geometry
            gdf = gdf[gdf.geometry.notna()].copy()
            
            if len(gdf) == 0:
                print("Không có dữ liệu Voronoi hợp lệ sau khi làm sạch")
                print("No valid Voronoi data after cleaning")
                return None
            
            # Chuyển đổi CRS cho Folium (cần EPSG:4326 - WGS84)
            # Convert CRS for Folium (needs EPSG:4326 - WGS84)
            if gdf.crs and gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
                
            # Lấy tâm của vùng để đặt ở giữa bản đồ
            # Get center of region to place in middle of map
            boundary = analyzer.selected_region if analyzer.selected_region is not None else analyzer.catchments
            if boundary.crs and boundary.crs != "EPSG:4326":
                boundary = boundary.to_crs("EPSG:4326")
                
            # Tính toán tâm / Calculate center
            centroid = boundary.geometry.unary_union.centroid
            center = [centroid.y, centroid.x]
            
            # Tạo bản đồ Folium / Create Folium map
            m = folium.Map(
                location=center,
                zoom_start=8,
                tiles="CartoDB positron"
            )
            
            # Thêm lớp choropleth từ dữ liệu Voronoi
            # Add choropleth layer from Voronoi data
            choropleth = folium.Choropleth(
                geo_data=gdf.__geo_interface__,
                name="Tốc độ gió / Wind Speed",
                data=gdf,
                columns=[gdf.index, "wind_mean"],
                key_on="feature.id",
                fill_color="YlOrRd",
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name="Tốc độ gió trung bình (m/s) / Mean Wind Speed (m/s)"
            ).add_to(m)
            
            # Thêm tooltip khi di chuột qua / Add tooltip on hover
            choropleth.geojson.add_child(
                folium.features.GeoJsonTooltip(
                    fields=["wind_mean", "wind_std", "name"],
                    aliases=[
                        "Tốc độ gió trung bình / Mean wind speed (m/s)", 
                        "Độ lệch chuẩn / Standard deviation (m/s)", 
                        "Tên / Name"
                    ],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
                )
            )
            
            # Thêm ranh giới khu vực / Add region boundary
            folium.GeoJson(
                boundary.__geo_interface__,
                name="Ranh giới / Boundary",
                style_function=lambda x: {
                    "color": "black",
                    "weight": 2,
                    "fillOpacity": 0,
                }
            ).add_to(m)
            
            # Thêm công cụ điều khiển lớp / Add layer control
            folium.LayerControl().add_to(m)
            
            # Lưu bản đồ / Save map
            if save_html:
                html_path = RESULTS_DIR / f'vietnam_wind_folium{region_suffix}.html'
                m.save(str(html_path))
                print(f"Đã lưu bản đồ tương tác web tại / Web interactive map saved at: {html_path}")
                return html_path
            
            return m
            
        else:
            print("Lỗi: Không tìm thấy dữ liệu Voronoi trong đối tượng analyzer.")
            print("Error: Voronoi data not found in analyzer object.")
    
    except Exception as e:
        print(f"Lỗi khi tạo bản đồ tương tác web / Error creating web interactive map: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return None

def list_available_regions():
    """
    Liệt kê các tỉnh/thành phố có sẵn để phân tích
    List available provinces/cities for analysis
    """
    # Tạo đối tượng phân tích tiềm năng gió
    # Create wind potential analyzer object
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu tỉnh/thành phố
    # Read province data
    province_file = DATA_DIR / 'vietnam_provinces.geojson'
    if not province_file.exists():
        print(f"Lỗi: Không tìm thấy file ranh giới tỉnh/thành phố: {province_file}")
        print(f"Error: Province boundary file not found: {province_file}")
        return []
        
    analyzer.load_provinces(province_file)
    regions = analyzer.list_available_regions()
    
    print("\nCác tỉnh/thành phố có sẵn để phân tích / Available provinces/cities for analysis:")
    for region in regions:
        print(f"  - {region}")
        
    return regions

def check_required_files():
    """
    Kiểm tra các file dữ liệu cần thiết
    Check required data files
    """
    required_files = [
        DATA_DIR / 'vietnam.geojson',
        DATA_DIR / 'VNM_wind-speed_100m.tif',
        DATA_DIR / 'vietnam_provinces.geojson'
    ]
    
    missing_files = [str(f) for f in required_files if not f.exists()]
    
    if missing_files:
        print("Lỗi: Không tìm thấy các file dữ liệu sau:")
        print("Error: The following data files were not found:")
        for f in missing_files:
            print(f"  - {f}")
        print("\nBạn cần tải dữ liệu từ Global Wind Atlas: https://globalwindatlas.info/area/Vietnam")
        print("You need to download data from Global Wind Atlas: https://globalwindatlas.info/area/Vietnam")
        print("Và đặt vào thư mục data/ với cấu trúc như đã mô tả trong README.md")
        print("And place them in the data/ directory with the structure described in README.md")
        return False
    
    # Kiểm tra thư viện mpld3 / Check mpld3 library
    try:
        import mpld3
    except ImportError:
        print("\nChú ý: Thư viện mpld3 chưa được cài đặt. Tính năng tương tác hover sẽ không hoạt động.")
        print("Note: mpld3 library is not installed. Interactive hover feature will not work.")
        print("Bạn có thể cài đặt bằng lệnh: pip install mpld3")
        print("You can install it with command: pip install mpld3")
        return False
    
    return True

def main():
    """
    Hàm chính để chạy chương trình
    Main function to run the program
    """
    # Tạo parser dòng lệnh / Create command line parser
    parser = argparse.ArgumentParser(description='Tạo bản đồ tương tác phân tích tiềm năng gió Việt Nam / Create interactive map for Vietnam wind potential analysis')
    
    parser.add_argument('--region', type=str, default=None, 
                        help='Tên tỉnh/thành phố, ví dụ: "Gia Lai". Mặc định sẽ phân tích toàn bộ Việt Nam. / Province name, e.g., "Gia Lai". Default analyzes entire Vietnam.')
    parser.add_argument('--points', type=int, default=100, 
                        help='Số lượng điểm để tạo các đa giác Voronoi. Mặc định: 100 / Number of points to create Voronoi polygons. Default: 100')
    parser.add_argument('--list-regions', action='store_true', 
                        help='Liệt kê các tỉnh/thành phố có sẵn để phân tích rồi thoát / List available provinces/cities for analysis then exit')
    parser.add_argument('--no-show', action='store_true', 
                        help='Không hiển thị biểu đồ, chỉ lưu file / Do not display chart, only save file')
    parser.add_argument('--web', action='store_true',
                        help='Tạo bản đồ web tương tác sử dụng Folium / Create web interactive map using Folium')
    
    args = parser.parse_args()
    
    # Kiểm tra các file cần thiết / Check required files
    if not check_required_files():
        return
    
    # Liệt kê các tỉnh/thành phố nếu được yêu cầu / List provinces/cities if requested
    if args.list_regions:
        list_available_regions()
        return
    
    # Chọn loại bản đồ tương tác / Choose type of interactive map
    if args.web and FOLIUM_AVAILABLE:
        create_folium_map(
            region_name=args.region,
            num_points=args.points,
            save_html=True
        )
    else:
        create_interactive_map(
            region_name=args.region,
            num_points=args.points,
            save_html=True,
            show_plot=not args.no_show
        )

if __name__ == "__main__":
    # Khi chạy như một script độc lập / When running as a standalone script
    if len(sys.argv) > 1:
        # Chạy với các tham số dòng lệnh / Run with command line parameters
        main()
    else:
        # Chạy chế độ tương tác nếu không có tham số / Run interactive mode if no parameters
        print("\n===== Tạo bản đồ tương tác phân tích tiềm năng gió Việt Nam =====")
        print("===== Interactive Map for Vietnam Wind Potential Analysis =====\n")
        
        # Kiểm tra xem Folium có sẵn dùng không / Check if Folium is available
        map_type = "1"
        if FOLIUM_AVAILABLE:
            map_type = input("Chọn loại bản đồ tương tác / Choose interactive map type:\n"
                           "1. Bản đồ tương tác trong file HTML (mpld3) / Interactive map in HTML file (mpld3)\n"
                           "2. Bản đồ web tương tác (folium) / Web interactive map (folium)\n"
                           "Lựa chọn / Choice (1/2): ")
        
        choice = input("Bạn muốn phân tích toàn bộ Việt Nam hay một tỉnh/thành phố cụ thể? / Do you want to analyze entire Vietnam or a specific province?\n"
                     "1. Toàn bộ Việt Nam / Entire Vietnam\n"
                     "2. Tỉnh/thành phố cụ thể / Specific province\n"
                     "Lựa chọn / Choice (1/2): ")
        
        region_name = None
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
            print("Giá trị không hợp lệ, sử dụng mặc định: 100 điểm / Invalid value, using default: 100 points")
        
        if map_type == "2" and FOLIUM_AVAILABLE:
            create_folium_map(region_name=region_name, num_points=points)
        else:
            create_interactive_map(region_name=region_name, num_points=points) 