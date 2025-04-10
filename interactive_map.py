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
- NumPy, Pandas, GeoPandas, Matplotlib
- Folium (cho tương tác web / for web interaction)
- Rasterio, Rasterstats (cho xử lý dữ liệu raster / for raster data processing)
- Networkx (cho biểu đồ quy trình / for workflow charts)
"""

import os
import sys
from pathlib import Path
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

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
    from folium.plugins import (MarkerCluster, HeatMap, Geocoder, MeasureControl, 
                               Draw, MiniMap, Fullscreen)
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    print("Thư viện folium không khả dụng. Để sử dụng bản đồ tương tác web, hãy cài đặt bằng lệnh: pip install folium")
    print("Folium library not available. To use web interactive maps, install with command: pip install folium")

# Thêm import cho biểu đồ workflow
# Add imports for workflow chart
try:
    import networkx as nx
    from matplotlib.patches import FancyArrowPatch
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Thư viện networkx không khả dụng. Để tạo biểu đồ workflow, hãy cài đặt bằng lệnh: pip install networkx")
    print("Networkx library not available. To create workflow charts, install with command: pip install networkx")

def create_interactive_map(region_name=None, num_points=100, save_html=True):
    """
    Tạo bản đồ tương tác web cho một khu vực cụ thể hoặc toàn bộ Việt Nam
    Create web interactive map for a specific region or entire Vietnam
    
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
            
            # Tạo bản đồ Folium với nhiều tùy chọn nền / Create Folium map with multiple base layers
            m = folium.Map(
                location=center,
                zoom_start=8,
                tiles=None,  # Không bao gồm tile mặc định / No default tile
                control_scale=True,  # Thêm thanh tỷ lệ / Add scale bar
                attributionControl=False  # Ẩn thuộc tính (sạch hơn) / Hide attribution (cleaner)
            )
            
            # Thêm nhiều lớp bản đồ nền để người dùng lựa chọn
            # Add multiple basemaps for user to choose from
            folium.TileLayer(
                'CartoDB positron', 
                name='Light Map',
                control=True
            ).add_to(m)
            
            folium.TileLayer(
                'CartoDB dark_matter', 
                name='Dark Map',
                control=True
            ).add_to(m)
            
            folium.TileLayer(
                'OpenStreetMap', 
                name='OpenStreetMap',
                control=True
            ).add_to(m)
            
            # Thêm lớp vệ tinh / Add satellite layer
            folium.TileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satellite',
                control=True
            ).add_to(m)
            
            # Thêm lớp choropleth từ dữ liệu Voronoi với màu sắc đẹp và tương phản cao
            # Add choropleth layer from Voronoi data with nice colors and high contrast
            choropleth = folium.Choropleth(
                geo_data=gdf.__geo_interface__,
                name="Tốc độ gió / Wind Speed",
                data=gdf,
                columns=[gdf.index, "wind_mean"],
                key_on="feature.id",
                fill_color="plasma",  # Sử dụng plasma - bảng màu khoa học tốt / Using plasma - good scientific colormap
                fill_opacity=0.7,
                line_opacity=0.2,
                highlight=True,  # Thêm highlight khi hover 
                legend_name="Tốc độ gió trung bình (m/s)"
            ).add_to(m)
            
            # Thêm tooltip tốt hơn khi di chuột qua / Add better tooltip on hover
            choropleth.geojson.add_child(
                folium.features.GeoJsonTooltip(
                    fields=["wind_mean", "wind_std", "name"],
                    aliases=[
                        "Tốc độ gió trung bình / Mean wind speed (m/s)", 
                        "Độ lệch chuẩn / Standard deviation (m/s)", 
                        "Tên / Name"
                    ],
                    localize=True,
                    sticky=False,
                    style="""
                        background-color: rgba(255, 255, 255, 0.8);
                        border: 1px solid rgba(0, 0, 0, 0.2);
                        border-radius: 12px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                        font-family: -apple-system, SF Pro Display, Helvetica Neue, sans-serif;
                        font-size: 14px;
                        padding: 15px;
                        backdrop-filter: blur(5px);
                        -webkit-backdrop-filter: blur(5px);
                    """
                )
            )
            
            # Thêm ranh giới khu vực với style tốt hơn / Add region boundary with better style
            folium.GeoJson(
                boundary.__geo_interface__,
                name="Ranh giới / Boundary",
                tooltip="Ranh giới khu vực / Region boundary",
                style_function=lambda x: {
                    "color": "#000000",
                    "weight": 2,
                    "opacity": 0.8,
                    "fillOpacity": 0,
                    "dashArray": "5, 5"
                }
            ).add_to(m)
            
            # Thêm công cụ tương tác / Add interactive tools
            Geocoder(position='topright').add_to(m)
            MeasureControl(position='bottomleft', primary_length_unit='kilometers').add_to(m)
            Draw(export=True, position='topleft').add_to(m)
            MiniMap(toggle_display=True, position='bottomright').add_to(m)
            Fullscreen(position='topright').add_to(m)
            
            # Thêm tiêu đề bản đồ theo phong cách Apple (tối giản, thanh lịch) 
            # Add map title with Apple-like style (minimalist, elegant)
            title_html = f'''
                <div style="position: fixed; 
                            top: 20px; left: 50%;
                            transform: translateX(-50%);
                            z-index: 9998; font-size: 18px;
                            font-weight: 500; background-color: rgba(255, 255, 255, 0.85);
                            color: #333; padding: 12px 20px;
                            border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                            font-family: -apple-system, SF Pro Display, Helvetica Neue, sans-serif;
                            backdrop-filter: blur(5px);
                            -webkit-backdrop-filter: blur(5px);">
                    <span style="font-weight: 600; display: inline-block; margin-right: 8px;">📍</span>
                    Bản đồ tiềm năng gió {region_name or "Việt Nam"}
                </div>
            '''
            m.get_root().html.add_child(folium.Element(title_html))
            
            # Thêm bảng chú thích riêng bên góc phải dưới / Add custom legend to bottom right
            legend_html = '''
                <div style="position: fixed; 
                            bottom: 30px; right: 30px;
                            z-index: 9999; font-size: 14px;
                            font-weight: 400; background-color: rgba(255, 255, 255, 0.85);
                            color: #333; padding: 15px 20px;
                            border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                            font-family: -apple-system, SF Pro Display, Helvetica Neue, sans-serif;
                            max-width: 280px;
                            backdrop-filter: blur(5px);
                            -webkit-backdrop-filter: blur(5px);">
                    <h4 style="margin-top: 0; margin-bottom: 10px; font-weight: 600; font-size: 16px;">Chú thích / Legend</h4>
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <div style="background: linear-gradient(to right, #0d0887, #5402a3, #8a0da4, #b91b8a, #db2f5e, #ed683f, #fa9b29, #fcce25); 
                                    width: 150px; height: 15px; margin-right: 10px; border-radius: 3px;"></div>
                        <div>Tốc độ gió tăng dần →</div>
                    </div>
                    <div style="margin-top: 12px; font-size: 13px; opacity: 0.8;">
                        Di chuyển chuột để xem thông tin chi tiết.<br>
                        Hover for detailed information.
                    </div>
                </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Thêm công cụ điều khiển lớp với vị trí và kiểu dáng tốt hơn
            # Add layer control with better position and style
            folium.LayerControl(collapsed=False, position='topright').add_to(m)
            
            # Di chuyển thanh tìm kiếm sang bên trái trên cùng để tránh chồng lấp
            # Move search bar to top left to avoid overlap
            m.get_root().html.add_child(folium.Element('''
                <style>
                    .leaflet-control-geocoder {
                        left: 20px !important;
                        top: 20px !important;
                    }
                    .leaflet-control-layers {
                        margin-top: 50px !important;
                    }
                    .leaflet-control-zoom {
                        margin-right: 15px !important;
                    }
                    .leaflet-control-fullscreen {
                        margin-top: 10px !important;
                    }
                    .leaflet-touch .leaflet-bar {
                        border-radius: 8px !important;
                        border: 1px solid rgba(0,0,0,0.1) !important;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
                    }
                    .leaflet-touch .leaflet-control-layers {
                        border-radius: 10px !important;
                        border: 1px solid rgba(0,0,0,0.1) !important;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
                    }
                    .leaflet-control-layers-expanded {
                        background-color: rgba(255,255,255,0.9) !important;
                        backdrop-filter: blur(5px) !important;
                        -webkit-backdrop-filter: blur(5px) !important;
                        padding: 12px !important;
                        border-radius: 12px !important;
                    }
                    .leaflet-control-geocoder-form input {
                        border-radius: 10px !important;
                        padding: 8px 12px !important;
                        font-family: -apple-system, SF Pro Display, Helvetica Neue, sans-serif !important;
                    }
                </style>
            '''))
            
            # Lưu bản đồ với nhiều tùy chọn / Save map with multiple options
            if save_html:
                # Cải thiện tệp HTML với CSS và JavaScript bổ sung
                # Improve HTML file with additional CSS and JavaScript
                html_path = RESULTS_DIR / f'vietnam_wind_folium{region_suffix}.html'
                
                # Lưu bản đồ dưới dạng HTML tương tác / Save map as interactive HTML
                m.save(str(html_path))
                
                # Cải thiện tệp HTML sau khi lưu
                # Enhance HTML file after saving
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Thêm meta tags và responsive settings
                # Add meta tags and responsive settings
                enhanced_html = html_content.replace(
                    '<head>',
                    '''<head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                    <meta name="description" content="Bản đồ tiềm năng gió Việt Nam - Vietnam Wind Potential Map">
                    <meta name="apple-mobile-web-app-capable" content="yes">
                    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
                    <title>Bản đồ tiềm năng gió - ''' + (region_name or "Việt Nam") + ''' / Wind Potential Map - ''' + (region_name or "Vietnam") + '''</title>
                    <style>
                        body {
                            margin: 0;
                            padding: 0;
                            font-family: -apple-system, SF Pro Display, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        }
                        #map {
                            position: absolute;
                            top: 0;
                            bottom: 0;
                            right: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                        }
                        .legend {
                            padding: 12px 15px;
                            font: 14px -apple-system, SF Pro Display, sans-serif;
                            background: rgba(255, 255, 255, 0.9);
                            box-shadow: 0 5px 25px rgba(0, 0, 0, 0.15);
                            border-radius: 12px;
                            line-height: 1.5em;
                            backdrop-filter: blur(5px);
                            -webkit-backdrop-filter: blur(5px);
                        }
                        .legend h4 {
                            margin-top: 0;
                            font-weight: 600;
                        }
                        .leaflet-popup-content {
                            max-width: 300px;
                            max-height: 300px;
                            overflow: auto;
                        }
                        .leaflet-popup-content-wrapper {
                            border-radius: 12px;
                            background-color: rgba(255, 255, 255, 0.85);
                            backdrop-filter: blur(5px);
                            -webkit-backdrop-filter: blur(5px);
                        }
                        .leaflet-popup-tip {
                            background-color: rgba(255, 255, 255, 0.85);
                        }
                        .leaflet-container {
                            font-family: -apple-system, SF Pro Display, sans-serif;
                        }
                        
                        /* Theo phong cách Apple */
                        /* Apple-style design */
                        .leaflet-control-zoom a, .leaflet-control-fullscreen a {
                            border-radius: 8px !important;
                            background-color: rgba(255, 255, 255, 0.85) !important;
                            color: #333 !important;
                            transition: all 0.2s ease;
                        }
                        .leaflet-control-zoom a:hover, .leaflet-control-fullscreen a:hover {
                            background-color: rgba(255, 255, 255, 0.95) !important;
                            transform: translateY(-1px);
                        }
                        .leaflet-bar {
                            box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
                        }
                        @media (max-width: 768px) {
                            .leaflet-control-geocoder {
                                width: calc(100% - 40px) !important;
                                left: 20px !important;
                                top: 20px !important;
                            }
                        }
                    </style>
                    '''
                )
                
                # Thêm JavaScript để cải thiện trải nghiệm người dùng
                # Add JavaScript to improve user experience
                enhanced_html = enhanced_html.replace(
                    '</body>',
                    '''
                    <script>
                    // Thêm tính năng tương tác nâng cao
                    // Add enhanced interactive features
                    document.addEventListener('DOMContentLoaded', function() {
                        // Thêm tính năng làm nổi bật khi hover
                        // Add highlight feature on hover
                        let layers = document.querySelectorAll('.leaflet-overlay-pane path');
                        layers.forEach(function(layer) {
                            layer.addEventListener('mouseover', function(e) {
                                e.target.setAttribute('stroke-width', '3');
                                e.target.setAttribute('stroke', '#fff');
                                e.target.style.transition = 'all 0.2s ease';
                                e.target.style.zIndex = '1000';
                                e.target.style.cursor = 'pointer';
                            });
                            layer.addEventListener('mouseout', function(e) {
                                e.target.setAttribute('stroke-width', '1');
                                e.target.setAttribute('stroke', '#999');
                                e.target.style.zIndex = 'auto';
                            });
                        });
                        
                        // Làm mượt chuyển động zoom
                        // Smooth zoom animation
                        var map = document.querySelector('.leaflet-map-pane').__leaflet_map__;
                        if (map) {
                            map.options.zoomAnimation = true;
                            map.options.fadeAnimation = true;
                            map.options.markerZoomAnimation = true;
                        }
                    });
                    </script>
                    </body>
                    '''
                )
                
                # Lưu tệp HTML đã cải thiện
                # Save the enhanced HTML file
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(enhanced_html)
                
                # Tạo bản sao cho thư mục gốc để dễ truy cập
                # Create a copy in the root directory for easy access
                root_path = Path(f'vietnam_wind_folium{region_suffix}.html')
                with open(root_path, 'w', encoding='utf-8') as f:
                    f.write(enhanced_html)
                
                print(f"Đã lưu bản đồ tương tác web tại / Web interactive map saved at: {html_path}")
                print(f"Đã tạo bản sao tại thư mục gốc: {root_path}")
                print(f"Created a copy in the root directory: {root_path}")
                
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

def create_workflow_chart(save_path=None):
    """
    Tạo biểu đồ minh họa quy trình phân tích tiềm năng gió
    Create workflow chart illustrating wind potential analysis process
    
    Parameters:
    -----------
    save_path : str or Path, optional
        Đường dẫn để lưu biểu đồ. Nếu None, sẽ lưu vào thư mục assets/images
        Path to save the chart. If None, will save to assets/images directory
        
    Returns:
    --------
    str
        Đường dẫn đến file biểu đồ đã lưu
        Path to the saved chart file
    """
    print("\n=== Tạo biểu đồ quy trình phân tích tiềm năng gió ===")
    print("=== Creating wind potential analysis workflow chart ===\n")
    
    if not NETWORKX_AVAILABLE:
        print("Thư viện networkx không khả dụng. Không thể tạo biểu đồ workflow.")
        print("Networkx library not available. Cannot create workflow chart.")
        print("Hãy cài đặt với lệnh: pip install networkx matplotlib")
        print("Please install with command: pip install networkx matplotlib")
        return None
    
    # Tạo thư mục assets nếu chưa tồn tại
    # Create assets directory if it doesn't exist
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Tạo đồ thị / Create graph
    G = nx.DiGraph()
    
    # Các bước trong quy trình / Steps in workflow
    nodes = [
        ("data", "Dữ liệu đầu vào\nInput Data"),
        ("load", "Đọc dữ liệu\nLoad Data"),
        ("region", "Chọn khu vực\nSelect Region"),
        ("voronoi", "Tạo đa giác Voronoi\nCreate Voronoi Polygons"),
        ("wind_stats", "Tính thống kê gió\nCalculate Wind Statistics"),
        ("visualize", "Hiển thị dữ liệu\nVisualize Data"),
        ("interactive_map", "Bản đồ tương tác\nInteractive Map"),
        ("export", "Xuất kết quả\nExport Results")
    ]
    
    # Thêm nút và nhãn / Add nodes and labels
    for node_id, label in nodes:
        G.add_node(node_id, label=label)
    
    # Thêm cạnh / Add edges
    edges = [
        ("data", "load"),
        ("load", "region"),
        ("region", "voronoi"),
        ("voronoi", "wind_stats"),
        ("wind_stats", "visualize"),
        ("visualize", "interactive_map"),
        ("interactive_map", "export")
    ]
    
    # Thêm cạnh vào đồ thị / Add edges to graph
    for src, dst in edges:
        G.add_edge(src, dst)
    
    # Tạo layout cho đồ thị / Create layout for graph
    pos = {
        "data": (0, 0),
        "load": (0, -1),
        "region": (0, -2),
        "voronoi": (0, -3),
        "wind_stats": (0, -4),
        "visualize": (0, -5),
        "interactive_map": (0, -6),
        "export": (0, -7)
    }
    
    # Tạo hình với kích thước lớn hơn / Create figure with larger size
    plt.figure(figsize=(12, 14))
    
    # Vẽ nút với màu sắc chuyên nghiệp / Draw nodes with professional colors
    node_colors = {
        "data": "#4287f5",  # Xanh dương / Blue
        "load": "#42c5f5",  # Xanh dương nhạt / Light blue
        "region": "#42f5e3",  # Xanh lá nhạt / Light green
        "voronoi": "#42f59e",  # Xanh lục / Green
        "wind_stats": "#f5d442",  # Vàng / Yellow
        "visualize": "#f59e42",  # Cam / Orange
        "interactive_map": "#f55442",  # Đỏ / Red
        "export": "#b642f5"  # Tím / Purple
    }
    
    # Vẽ nút / Draw nodes
    for node, (x, y) in pos.items():
        nx.draw_networkx_nodes(
            G, {node: (x, y)}, 
            nodelist=[node], 
            node_color=node_colors[node],
            node_size=3000, 
            alpha=0.8,
            edgecolors='black',
            linewidths=1
        )
    
    # Vẽ cạnh với mũi tên và màu sắc tốt hơn / Draw edges with arrows and better colors
    nx.draw_networkx_edges(
        G, pos, 
        width=2, 
        edge_color='gray',
        arrowsize=20,
        arrowstyle='-|>',
        connectionstyle='arc3,rad=0.1'
    )
    
    # Thêm nhãn / Add labels
    custom_labels = {node: data['label'] for node, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels=custom_labels, font_size=12, font_family='sans-serif', font_weight='bold')
    
    # Thêm tiêu đề / Add title
    plt.title("Quy trình phân tích tiềm năng gió\nWind Potential Analysis Workflow", 
              fontsize=20, fontweight='bold', pad=30)
    
    # Thêm chú thích / Add legend
    legend_elements = []
    for node_name, color in node_colors.items():
        legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, 
                                          markersize=15, label=G.nodes[node_name]['label']))
    
    plt.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.05),
               ncol=3, fontsize=10, frameon=True, fancybox=True, shadow=True)
    
    # Bỏ trục / Turn off axis
    plt.axis('off')
    
    # Thêm watermark / Add watermark
    plt.figtext(0.5, 0.01, "VietnamWind Analysis Tool", 
                ha="center", fontsize=12, alpha=0.5)
    
    # Lưu biểu đồ / Save chart
    if save_path is None:
        save_path = ASSETS_DIR / 'workflow.png'
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Đã lưu biểu đồ quy trình tại / Workflow chart saved at: {save_path}")
    
    # Đóng hình / Close figure
    plt.close()
    
    return str(save_path)

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
    
    # Kiểm tra thư viện Folium / Check Folium library
    if not FOLIUM_AVAILABLE:
        print("\nChú ý: Thư viện folium chưa được cài đặt.")
        print("Note: folium library is not installed.")
        print("Bạn có thể cài đặt bằng lệnh: pip install folium")
        print("You can install it with command: pip install folium")
    
    return True

def create_interactive_map_workflow(save_path=None):
    """
    Tạo biểu đồ quy trình cho việc tạo bản đồ tương tác (option 4 từ menu demo)
    Create workflow chart for interactive map creation (option 4 from demo menu)
    
    Parameters:
    -----------
    save_path : str or Path, optional
        Đường dẫn để lưu biểu đồ. Nếu None, sẽ lưu vào thư mục assets/images
        Path to save the chart. If None, will save to assets/images directory
        
    Returns:
    --------
    str
        Đường dẫn đến file biểu đồ đã lưu
        Path to the saved chart file
    """
    print("\n=== Tạo biểu đồ quy trình cho bản đồ tương tác (Option 4) ===")
    print("=== Creating workflow chart for interactive map (Option 4) ===\n")
    
    if not NETWORKX_AVAILABLE:
        print("Thư viện networkx không khả dụng. Không thể tạo biểu đồ workflow.")
        print("Networkx library not available. Cannot create workflow chart.")
        print("Hãy cài đặt với lệnh: pip install networkx matplotlib")
        print("Please install with command: pip install networkx matplotlib")
        return None
    
    # Tạo thư mục assets nếu chưa tồn tại
    # Create assets directory if it doesn't exist
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Tạo đồ thị / Create graph
    G = nx.DiGraph()
    
    # Các bước trong quy trình tạo bản đồ tương tác / Steps in interactive map workflow
    nodes = [
        ("start", "Bắt đầu\nStart"),
        ("load_data", "Tải dữ liệu ranh giới và gió\nLoad boundary and wind data"),
        ("region_select", "Chọn khu vực (Cả nước hoặc tỉnh)\nSelect region (Country/Province)"),
        ("voronoi", "Tạo đa giác Voronoi\nCreate Voronoi Polygons"),
        ("statistics", "Tính toán thống kê gió\nCalculate Wind Statistics"),
        ("folium_map", "Khởi tạo bản đồ Folium\nInitialize Folium Map"),
        ("basemaps", "Thêm các lớp bản đồ nền\nAdd Basemap Layers"),
        ("choropleth", "Thêm lớp choropleth\nAdd Choropleth Layer"),
        ("tooltips", "Thêm tooltips tương tác\nAdd Interactive Tooltips"),
        ("controls", "Thêm các công cụ điều khiển\nAdd Control Tools"),
        ("style", "Thêm CSS cải thiện giao diện\nAdd CSS Enhancements"),
        ("responsive", "Thêm tính năng responsive\nAdd Responsive Features"),
        ("save_html", "Lưu bản đồ dưới dạng HTML\nSave Map as HTML"),
        ("end", "Hoàn thành\nComplete")
    ]
    
    # Thêm nút và nhãn / Add nodes and labels
    for node_id, label in nodes:
        G.add_node(node_id, label=label)
    
    # Thêm cạnh / Add edges
    edges = [
        ("start", "load_data"),
        ("load_data", "region_select"),
        ("region_select", "voronoi"),
        ("voronoi", "statistics"),
        ("statistics", "folium_map"),
        ("folium_map", "basemaps"),
        ("basemaps", "choropleth"),
        ("choropleth", "tooltips"),
        ("tooltips", "controls"),
        ("controls", "style"),
        ("style", "responsive"),
        ("responsive", "save_html"),
        ("save_html", "end")
    ]
    
    # Thêm cạnh vào đồ thị / Add edges to graph
    for src, dst in edges:
        G.add_edge(src, dst)
    
    # Tạo layout cho đồ thị / Create layout for graph
    pos = {
        "start": (0, 0),
        "load_data": (0, -1),
        "region_select": (0, -2),
        "voronoi": (0, -3),
        "statistics": (0, -4),
        "folium_map": (0, -5),
        "basemaps": (1, -5.5),
        "choropleth": (1, -6.5),
        "tooltips": (1, -7.5),
        "controls": (1, -8.5),
        "style": (0, -9),
        "responsive": (0, -10),
        "save_html": (0, -11),
        "end": (0, -12)
    }
    
    # Tạo hình với kích thước lớn hơn / Create figure with larger size
    plt.figure(figsize=(14, 16))
    
    # Vẽ nút với màu sắc chuyên nghiệp / Draw nodes with professional colors
    node_colors = {
        "start": "#4287f5",     # Xanh dương / Blue
        "load_data": "#42c5f5", # Xanh dương nhạt / Light blue
        "region_select": "#42f5e3", # Xanh lá nhạt / Light green
        "voronoi": "#42f59e",   # Xanh lục / Green
        "statistics": "#f5d442", # Vàng / Yellow
        "folium_map": "#f59e42", # Cam / Orange
        "basemaps": "#f57d42",  # Cam đậm / Dark orange
        "choropleth": "#f55d42", # Đỏ cam / Red-orange
        "tooltips": "#f54242",  # Đỏ / Red
        "controls": "#f542aa",  # Hồng / Pink
        "style": "#d642f5",     # Tím / Purple
        "responsive": "#9e42f5", # Tím nhạt / Light purple
        "save_html": "#7142f5", # Tím xanh / Blue-purple
        "end": "#4287f5"        # Xanh dương / Blue
    }
    
    # Vẽ nút / Draw nodes
    for node, (x, y) in pos.items():
        nx.draw_networkx_nodes(
            G, {node: (x, y)}, 
            nodelist=[node], 
            node_color=node_colors[node],
            node_size=3000, 
            alpha=0.8,
            edgecolors='black',
            linewidths=1
        )
    
    # Vẽ cạnh với mũi tên và màu sắc tốt hơn / Draw edges with arrows and better colors
    edge_arrows = {}
    for u, v in G.edges():
        arrow = FancyArrowPatch(
            posA=pos[u], posB=pos[v],
            arrowstyle='-|>',
            color='gray',
            connectionstyle='arc3,rad=0.1',
            lw=2
        )
        edge_arrows[(u, v)] = arrow
        plt.gca().add_patch(arrow)
    
    # Thêm nhãn / Add labels
    custom_labels = {node: data['label'] for node, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels=custom_labels, font_size=12, font_family='sans-serif', font_weight='bold')
    
    # Thêm tiêu đề / Add title
    plt.title("Quy trình tạo bản đồ tương tác (Option 4)\nInteractive Map Workflow (Option 4)", 
              fontsize=20, fontweight='bold', pad=30)
    
    # Phân loại các nhóm quy trình chính / Categorize main process groups
    process_groups = {
        "Chuẩn bị dữ liệu / Data Preparation": ["start", "load_data", "region_select", "voronoi", "statistics"],
        "Tạo bản đồ / Map Creation": ["folium_map", "basemaps", "choropleth", "tooltips", "controls"],
        "Hoàn thiện / Finalization": ["style", "responsive", "save_html", "end"]
    }
    
    # Tạo chú thích cho các nhóm quy trình / Create legend for process groups
    legend_elements = []
    group_colors = {
        "Chuẩn bị dữ liệu / Data Preparation": "#42c5f5",
        "Tạo bản đồ / Map Creation": "#f59e42",
        "Hoàn thiện / Finalization": "#9e42f5"
    }
    
    for group_name, color in group_colors.items():
        legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, 
                                       markersize=15, label=group_name))
    
    plt.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.05),
               ncol=3, fontsize=12, frameon=True, fancybox=True, shadow=True)
    
    # Thêm mô tả cho từng bước / Add descriptions for each step
    descriptions = {
        "load_data": "Đọc dữ liệu ranh giới và dữ liệu tốc độ gió từ file",
        "region_select": "Lựa chọn phân tích toàn quốc hoặc tỉnh cụ thể",
        "voronoi": "Tạo các ô Voronoi để phân tích dữ liệu",
        "statistics": "Tính toán tốc độ gió trung bình cho từng ô",
        "folium_map": "Khởi tạo bản đồ với tọa độ trung tâm",
        "basemaps": "Thêm nhiều lớp bản đồ nền (sáng, tối, vệ tinh)",
        "choropleth": "Tạo lớp màu sắc hiển thị tốc độ gió",
        "tooltips": "Thêm hiển thị thông tin khi di chuột qua",
        "controls": "Thêm công cụ tìm kiếm, đo khoảng cách, vẽ",
        "style": "Tùy chỉnh giao diện theo phong cách hiện đại",
        "responsive": "Đảm bảo bản đồ hiển thị tốt trên mọi thiết bị",
        "save_html": "Lưu bản đồ thành file HTML tương tác"
    }
    
    # Thêm mô tả vào biểu đồ / Add descriptions to chart
    for node, description in descriptions.items():
        x, y = pos[node]
        plt.text(x + 1.5, y, description, fontsize=10, ha='left', va='center',
                 bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.5'))
    
    # Bỏ trục / Turn off axis
    plt.axis('off')
    
    # Thêm watermark / Add watermark
    plt.figtext(0.5, 0.01, "VietnamWind Analysis Tool - Option 4 Workflow", 
                ha="center", fontsize=12, alpha=0.5)
    
    # Lưu biểu đồ / Save chart
    if save_path is None:
        save_path = ASSETS_DIR / 'interactive_map_workflow.png'
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Đã lưu biểu đồ quy trình tại / Workflow chart saved at: {save_path}")
    
    # Đóng hình / Close figure
    plt.close()
    
    return str(save_path)

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
    parser.add_argument('--workflow', action='store_true',
                        help='Tạo biểu đồ quy trình phân tích tiềm năng gió / Create wind potential analysis workflow chart')
    parser.add_argument('--option4-workflow', action='store_true',
                        help='Tạo biểu đồ quy trình cho tạo bản đồ tương tác (Option 4) / Create workflow chart for interactive map (Option 4)')
    
    args = parser.parse_args()
    
    # Kiểm tra các file cần thiết / Check required files
    if not check_required_files():
        return
    
    # Liệt kê các tỉnh/thành phố nếu được yêu cầu / List provinces/cities if requested
    if args.list_regions:
        list_available_regions()
        return
    
    # Tạo biểu đồ quy trình nếu được yêu cầu / Create workflow chart if requested
    if args.workflow:
        create_workflow_chart()
        return
        
    # Tạo biểu đồ quy trình Option 4 nếu được yêu cầu / Create Option 4 workflow chart if requested
    if args.option4_workflow:
        create_interactive_map_workflow()
        return
    
    # Tạo bản đồ tương tác / Create interactive map
    create_interactive_map(
        region_name=args.region,
        num_points=args.points,
        save_html=True
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
        
        print("Chọn một chức năng / Choose a function:")
        print("1. Tạo bản đồ tương tác / Create interactive map")
        print("2. Tạo biểu đồ quy trình chung / Create general workflow chart")
        print("3. Tạo biểu đồ quy trình option 4 / Create option 4 workflow chart")
        function_choice = input("Lựa chọn / Choice (1/2/3): ")
        
        if function_choice == "2":
            create_workflow_chart()
            sys.exit(0)
        elif function_choice == "3":
            create_interactive_map_workflow()
            sys.exit(0)
            
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
        
        create_interactive_map(region_name=region_name, num_points=points) 