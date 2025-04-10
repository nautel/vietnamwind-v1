#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo cho công cụ phân tích tiềm năng gió tại Việt Nam
(Demo for the Vietnam Wind Potential Analysis Tool)

Các thư viện cần thiết:
- NumPy, Pandas, GeoPandas, Matplotlib, Rasterio, Rasterstats, Fiona, Scipy
- mpld3 (cho tính năng tương tác): pip install mpld3

Required libraries:
- NumPy, Pandas, GeoPandas, Matplotlib, Rasterio, Rasterstats, Fiona, Scipy
- mpld3 (for interactive features): pip install mpld3
"""

import os
import sys
from pathlib import Path

# Thêm thư mục hiện tại vào đường dẫn để có thể import
# (Add current directory to path to be able to import)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sửa lỗi import - Import trực tiếp từ file vietnamwind.py
from vietnamwind import WindPotentialAnalyzer

# Đường dẫn dữ liệu
# (Data paths)
DATA_DIR = Path('data')
RESULTS_DIR = Path('results')

def check_input_files():
    """
    Kiểm tra xem các file dữ liệu đầu vào có tồn tại không
    (Check if input data files exist)
    """
    boundary_file = DATA_DIR / 'vietnam.geojson'
    wind_file = DATA_DIR / 'VNM_wind-speed_100m.tif'
    province_file = DATA_DIR / 'vietnam_provinces.geojson'
    
    if not boundary_file.exists() or not wind_file.exists():
        print("Lỗi: Không tìm thấy file dữ liệu đầu vào. / Error: Input data files not found.")
        print("Kiểm tra lại đường dẫn: / Check paths:", boundary_file, "và/and", wind_file)
        print("\nBạn cần tải dữ liệu từ Global Wind Atlas: / You need to download data from Global Wind Atlas:")
        print("https://globalwindatlas.info/area/Vietnam")
        print("Và đặt vào thư mục data/ với cấu trúc như sau: / And place in the data/ directory with structure:")
        print("data/")
        print("  ├── vietnam.geojson        # Ranh giới Việt Nam / Vietnam boundary")
        print("  └── VNM_wind-speed_100m.tif # Dữ liệu tốc độ gió ở độ cao 100m / Wind speed data at 100m height")
        
        # Thêm thông tin về file ranh giới tỉnh/thành phố
        print("  └── vietnam_provinces.geojson # Dữ liệu ranh giới các tỉnh/thành phố / Province boundaries (optional)")
        
        return False
    
    # Kiểm tra thư viện mpld3 cho tính năng tương tác
    try:
        import mpld3
    except ImportError:
        print("\nChú ý: Thư viện mpld3 chưa được cài đặt. Tính năng tương tác hover sẽ không hoạt động.")
        print("Note: mpld3 library is not installed. Interactive hover feature will not work.")
        print("Bạn có thể cài đặt bằng lệnh: / You can install it with: pip install mpld3")
        
    return True

def analyze_entire_vietnam():
    """
    Phân tích tiềm năng gió cho toàn bộ Việt Nam
    (Analyze wind potential for the entire Vietnam)
    """
    print("\n=== Phân tích tiềm năng gió cho toàn bộ Việt Nam / Analyzing wind potential for entire Vietnam ===\n")
    
    # Tạo thư mục kết quả nếu chưa tồn tại (Create results directory if it doesn't exist)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Tạo đối tượng phân tích tiềm năng gió (Create wind potential analyzer object)
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu (Read data)
    analyzer.load_data(DATA_DIR / 'vietnam.geojson', DATA_DIR / 'VNM_wind-speed_100m.tif')
    
    # Tạo biểu đồ dữ liệu gió và ranh giới (Create wind data and boundary plot)
    analyzer.visualize_wind_data(save_path=RESULTS_DIR / 'vietnam_wind_data.png')
    
    # Tạo các đa giác Voronoi (Create Voronoi polygons)
    analyzer.create_voronoi_polygons(num_points=100)  # Giảm còn 100 điểm để tăng tốc độ phân tích
    
    # Tính toán thống kê gió (Calculate wind statistics)
    analyzer.calculate_wind_statistics()
    
    # Lưu kết quả (Save results)
    analyzer.save_results(output_dir=RESULTS_DIR)
    
    # Tạo biểu đồ các khu vực có tiềm năng cao (Create high potential areas plot)
    analyzer.visualize_high_potential_areas(save_path=RESULTS_DIR / 'vietnam_wind_high_potential.png')
    
    # Xuất dữ liệu thống kê chi tiết (Export detailed statistics)
    analyzer.export_detailed_statistics(output_dir=RESULTS_DIR)
    
    # Tạo biểu đồ tương tác (Create interactive plot)
    try:
        analyzer.create_interactive_visualization(
            html_output=RESULTS_DIR / 'vietnam_wind_interactive.html'
        )
        print("\nĐã tạo bản đồ tương tác tại: " + str(RESULTS_DIR / 'vietnam_wind_interactive.html'))
        print("Created interactive map at: " + str(RESULTS_DIR / 'vietnam_wind_interactive.html'))
    except Exception as e:
        print(f"Không thể tạo biểu đồ tương tác: {e}")
        print(f"Cannot create interactive plot: {e}")
    
    print("\nPhân tích cho toàn bộ Việt Nam đã hoàn tất! / Analysis for entire Vietnam completed!")
    print(f"Kết quả đã được lưu vào thư mục: {RESULTS_DIR} / Results saved to directory: {RESULTS_DIR}")

def analyze_specific_region(region_name):
    """
    Phân tích tiềm năng gió cho một vùng cụ thể
    (Analyze wind potential for a specific region)
    
    Parameters:
    -----------
    region_name : str
        Tên tỉnh/thành phố để phân tích
        (Name of province/city to analyze)
    """
    print(f"\n=== Phân tích tiềm năng gió cho {region_name} / Analyzing wind potential for {region_name} ===\n")
    
    # Tạo thư mục kết quả nếu chưa tồn tại (Create results directory if it doesn't exist)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Tạo đối tượng phân tích tiềm năng gió (Create wind potential analyzer object)
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu (Read data)
    analyzer.load_data(DATA_DIR / 'vietnam.geojson', DATA_DIR / 'VNM_wind-speed_100m.tif')
    
    # Đọc dữ liệu tỉnh/thành phố (Read province data)
    province_file = DATA_DIR / 'vietnam_provinces.geojson'
    if not province_file.exists():
        print(f"Lỗi: Không tìm thấy file ranh giới tỉnh/thành phố: {province_file}")
        print(f"Error: Province boundary file not found: {province_file}")
        return
        
    analyzer.load_provinces(province_file)
    
    try:
        # Chọn vùng cụ thể (Select specific region)
        analyzer.select_region(region_name)
        
        # Tạo biểu đồ dữ liệu gió và ranh giới (Create wind data and boundary plot)
        region_suffix = region_name.lower().replace(' ', '_')
        analyzer.visualize_wind_data(save_path=RESULTS_DIR / f'vietnam_wind_data_{region_suffix}.png')
        
        # Tạo các đa giác Voronoi (Create Voronoi polygons)
        analyzer.create_voronoi_polygons(num_points=100)  # Giảm còn 100 điểm để tăng tốc độ phân tích
        
        # Tính toán thống kê gió (Calculate wind statistics)
        analyzer.calculate_wind_statistics()
        
        # Lưu kết quả (Save results)
        analyzer.save_results(output_dir=RESULTS_DIR)
        
        # Tạo biểu đồ các khu vực có tiềm năng cao (Create high potential areas plot)
        analyzer.visualize_high_potential_areas(save_path=RESULTS_DIR / f'vietnam_wind_high_potential_{region_suffix}.png')
        
        # Xuất dữ liệu thống kê chi tiết (Export detailed statistics)
        analyzer.export_detailed_statistics(output_dir=RESULTS_DIR)
        
        # Tạo biểu đồ tương tác (Create interactive plot)
        try:
            analyzer.create_interactive_visualization(
                html_output=RESULTS_DIR / f'vietnam_wind_interactive_{region_suffix}.html'
            )
            print(f"\nĐã tạo bản đồ tương tác tại: {RESULTS_DIR / f'vietnam_wind_interactive_{region_suffix}.html'}")
            print(f"Created interactive map at: {RESULTS_DIR / f'vietnam_wind_interactive_{region_suffix}.html'}")
        except Exception as e:
            print(f"Không thể tạo biểu đồ tương tác: {e}")
            print(f"Cannot create interactive plot: {e}")
        
        print(f"\nPhân tích cho {region_name} đã hoàn tất! / Analysis for {region_name} completed!")
        print(f"Kết quả đã được lưu vào thư mục: {RESULTS_DIR} / Results saved to directory: {RESULTS_DIR}")
    
    except ValueError as e:
        print(f"Lỗi: {e}")
        print(f"Error: {e}")

def list_available_regions():
    """
    Liệt kê các tỉnh/thành phố có sẵn để phân tích
    (List available provinces/cities for analysis)
    """
    # Tạo đối tượng phân tích tiềm năng gió (Create wind potential analyzer object)
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu tỉnh/thành phố (Read province data)
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

def main():
    """
    Hàm chính để chạy demo
    (Main function to run demo)
    """
    # Kiểm tra dữ liệu đầu vào (Check input data)
    if not check_input_files():
        return
    
    print("\n===== Demo phân tích tiềm năng gió tại Việt Nam =====")
    print("===== Vietnam Wind Potential Analysis Demo =====\n")
    
    print("Lưu ý: Chương trình đã được cấu hình để chỉ tạo 100 đa giác Voronoi để tăng tốc độ phân tích")
    print("Note: Program is configured to create only 100 Voronoi polygons to improve analysis speed")
    print("Để phân tích chi tiết hơn, bạn có thể tăng số lượng điểm trong mã nguồn")
    print("For more detailed analysis, you can increase the number of points in the source code\n")
    
    # Tùy chọn demo (Demo options)
    print("Tùy chọn demo / Demo options:")
    print("1. Phân tích toàn bộ Việt Nam / Analyze entire Vietnam")
    print("2. Phân tích một tỉnh/thành phố cụ thể / Analyze a specific province/city")
    print("3. Liệt kê các tỉnh/thành phố có sẵn / List available provinces/cities")
    print("4. Tạo bản đồ tương tác có thể hover chuột / Create interactive map with hover")
    print("0. Thoát / Exit")
    
    choice = input("\nNhập lựa chọn của bạn / Enter your choice (0-4): ")
    
    if choice == '1':
        analyze_entire_vietnam()
    elif choice == '2':
        regions = list_available_regions()
        if not regions:
            return
            
        region_name = input("\nNhập tên tỉnh/thành phố (ví dụ: Hà Nội) / Enter province/city name (e.g., Ha Noi): ")
        analyze_specific_region(region_name)
    elif choice == '3':
        list_available_regions()
    elif choice == '4':
        regions = list_available_regions()
        if not regions:
            return
            
        print("\n1. Tạo bản đồ tương tác cho toàn Việt Nam / Create interactive map for entire Vietnam")
        print("2. Tạo bản đồ tương tác cho một tỉnh/thành phố / Create interactive map for a specific province/city")
        sub_choice = input("\nNhập lựa chọn của bạn / Enter your choice (1-2): ")
        
        analyzer = WindPotentialAnalyzer()
        analyzer.load_data(DATA_DIR / 'vietnam.geojson', DATA_DIR / 'VNM_wind-speed_100m.tif')
        
        if sub_choice == '2':
            # Đọc dữ liệu tỉnh/thành phố (Read province data)
            province_file = DATA_DIR / 'vietnam_provinces.geojson'
            if not province_file.exists():
                print(f"Lỗi: Không tìm thấy file ranh giới tỉnh/thành phố: {province_file}")
                print(f"Error: Province boundary file not found: {province_file}")
                return
                
            analyzer.load_provinces(province_file)
            region_name = input("\nNhập tên tỉnh/thành phố (ví dụ: Hà Nội) / Enter province/city name (e.g., Ha Noi): ")
            analyzer.select_region(region_name)
            region_suffix = region_name.lower().replace(' ', '_')
            
            # Tạo các đa giác Voronoi (Create Voronoi polygons)
            analyzer.create_voronoi_polygons(num_points=100)
        else:
            # Tạo các đa giác Voronoi cho toàn bộ Việt Nam (Create Voronoi polygons for entire Vietnam)
            analyzer.create_voronoi_polygons(num_points=100)
            region_suffix = ""
            
        # Tính toán thống kê gió (Calculate wind statistics)
        analyzer.calculate_wind_statistics()
        
        # Tạo biểu đồ tương tác (Create interactive plot)
        try:
            output_path = RESULTS_DIR / f'vietnam_wind_interactive{region_suffix}.html'
            analyzer.create_interactive_visualization(
                html_output=output_path
            )
            print(f"\nĐã tạo bản đồ tương tác tại: {output_path}")
            print(f"Created interactive map at: {output_path}")
            
            # Hướng dẫn sử dụng (Usage instructions)
            print("\nHướng dẫn / Instructions:")
            print("- Mở file HTML trong trình duyệt để xem bản đồ tương tác")
            print("- Di chuyển chuột trên các vùng để xem thông tin tốc độ gió")
            print("- Open the HTML file in a browser to view the interactive map")
            print("- Hover over areas to see wind speed information")
        except Exception as e:
            print(f"Không thể tạo biểu đồ tương tác: {e}")
            print(f"Cannot create interactive plot: {e}")
    elif choice == '0':
        print("Thoát chương trình / Exiting program")
    else:
        print("Lựa chọn không hợp lệ / Invalid choice")

if __name__ == "__main__":
    main() 