import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
import rasterio.plot
from rasterstats import zonal_stats
import numpy as np
import os
import fiona
from pathlib import Path
import argparse
from matplotlib.patches import Patch
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Thư viện tqdm không được cài đặt. Thanh tiến độ sẽ không được hiển thị.")
    print("tqdm library is not installed. Progress bar will not be displayed.")
    print("Bạn có thể cài đặt bằng lệnh: pip install tqdm")
    print("You can install it with: pip install tqdm")
    # Tạo hàm giả để tránh lỗi khi không có tqdm
    def tqdm(iterable, *args, **kwargs):
        return iterable

class WindPotentialAnalyzer:
    """
    Một lớp để phân tích tiềm năng gió dựa trên dữ liệu GIS.
    (A class for analyzing wind potential based on GIS data.)
    """
    
    def __init__(self):
        """
        Khởi tạo lớp WindPotentialAnalyzer
        (Initialize the WindPotentialAnalyzer class)
        """
        # Đảm bảo driver KML được hỗ trợ (Ensure KML driver is supported)
        fiona.supported_drivers['KML'] = 'rw'
        self.catchments = None
        self.demdata = None
        self.voronoi_polygons = None
        self.selected_region = None
        self.province_data = None
        
    def load_data(self, boundary_file, wind_file):
        """
        Đọc dữ liệu ranh giới và dữ liệu gió
        (Read boundary and wind data)
        
        Parameters:
        -----------
        boundary_file : str
            Đường dẫn đến file ranh giới dạng geojson
            (Path to the boundary file in geojson format)
        wind_file : str
            Đường dẫn đến file dữ liệu tốc độ gió dạng GeoTIFF
            (Path to the wind speed data file in GeoTIFF format)
        """
        print(f"Đọc dữ liệu ranh giới từ: {boundary_file}")
        print(f"Reading boundary data from: {boundary_file}")
        self.catchments = gpd.read_file(boundary_file)
        
        print(f"Đọc dữ liệu gió từ: {wind_file}")
        print(f"Reading wind data from: {wind_file}")
        self.demdata = rasterio.open(wind_file)
        
        return self
    
    def load_provinces(self, province_file):
        """
        Đọc dữ liệu ranh giới các tỉnh/thành phố
        (Read province boundaries data)
        
        Parameters:
        -----------
        province_file : str
            Đường dẫn đến file ranh giới các tỉnh dạng geojson
            (Path to the provinces boundary file in geojson format)
        """
        print(f"Đọc dữ liệu ranh giới các tỉnh/thành phố từ: {province_file}")
        print(f"Reading province boundaries data from: {province_file}")
        self.province_data = gpd.read_file(province_file)
        
        # Đảm bảo dữ liệu có cột tên tỉnh/thành phố
        if 'name' not in self.province_data.columns and 'NAME_1' in self.province_data.columns:
            self.province_data['name'] = self.province_data['NAME_1']
        elif 'name' not in self.province_data.columns and 'Name' in self.province_data.columns:
            self.province_data['name'] = self.province_data['Name']
            
        print(f"Đã tải {len(self.province_data)} tỉnh/thành phố: {', '.join(self.province_data['name'].tolist())}")
        print(f"Loaded {len(self.province_data)} provinces: {', '.join(self.province_data['name'].tolist())}")
        
        return self
    
    def select_region(self, region_name=None):
        """
        Chọn một vùng địa lý cụ thể để phân tích
        (Select a specific region for analysis)
        
        Parameters:
        -----------
        region_name : str, optional
            Tên của tỉnh/thành phố để phân tích. Nếu None, sẽ sử dụng toàn bộ ranh giới.
            (Name of the province/city to analyze. If None, will use the whole boundary.)
        """
        if region_name is None:
            print("Sử dụng toàn bộ ranh giới Việt Nam")
            print("Using the entire boundary of Vietnam")
            self.selected_region = self.catchments
            return self
            
        if self.province_data is None:
            raise ValueError("Chưa tải dữ liệu tỉnh/thành phố. Hãy gọi phương thức load_provinces() trước.")
            
        # Tìm tỉnh/thành phố phù hợp
        region = self.province_data[self.province_data['name'].str.lower() == region_name.lower()]
        
        if len(region) == 0:
            # Thử tìm kiếm theo phần tên
            region = self.province_data[self.province_data['name'].str.lower().str.contains(region_name.lower())]
            
        if len(region) == 0:
            available_regions = ', '.join(self.province_data['name'].tolist())
            raise ValueError(f"Không tìm thấy tỉnh/thành phố '{region_name}'. Các tỉnh/thành phố có sẵn: {available_regions}")
        
        if len(region) > 1:
            matched_regions = ', '.join(region['name'].tolist())
            print(f"Tìm thấy nhiều tỉnh/thành phố phù hợp: {matched_regions}. Sử dụng kết quả đầu tiên.")
            print(f"Found multiple matching regions: {matched_regions}. Using the first match.")
            region = region.iloc[[0]]
            
        self.selected_region = region
        print(f"Đã chọn: {region['name'].values[0]}")
        print(f"Selected: {region['name'].values[0]}")
        
        return self
    
    def list_available_regions(self):
        """
        Liệt kê các tỉnh/thành phố có sẵn để phân tích
        (List available provinces/cities for analysis)
        
        Returns:
        --------
        list
            Danh sách tên các tỉnh/thành phố có sẵn
            (List of available province/city names)
        """
        if self.province_data is None:
            raise ValueError("Chưa tải dữ liệu tỉnh/thành phố. Hãy gọi phương thức load_provinces() trước.")
            
        regions = sorted(self.province_data['name'].tolist())
        return regions
    
    def visualize_wind_data(self, figsize=(12, 10), save_path=None):
        """
        Hiển thị dữ liệu gió và ranh giới
        (Display wind data and boundaries)
        
        Parameters:
        -----------
        figsize : tuple, optional
            Kích thước của biểu đồ (Size of the figure)
        save_path : str, optional
            Đường dẫn để lưu biểu đồ (Path to save the figure)
        """
        if self.demdata is None or self.catchments is None:
            raise ValueError("Chưa tải dữ liệu. Hãy gọi phương thức load_data() trước.")
            
        fig, ax = plt.subplots(figsize=figsize)
        
        # Xác định vùng hiển thị (Display region)
        display_region = self.selected_region if self.selected_region is not None else self.catchments
        
        # Lấy phạm vi hiển thị từ vùng đã chọn (Get extent from selected region)
        minx, miny, maxx, maxy = display_region.total_bounds
        
        # Tạo mask cho dữ liệu gió (Create mask for wind data)
        if self.selected_region is not None and self.selected_region is not self.catchments:
            mask = None
            try:
                import rasterio.mask
                # Sử dụng ranh giới của khu vực đã chọn để mask dữ liệu gió
                shapes = [geom.__geo_interface__ for geom in self.selected_region.geometry]
                masked_data, masked_transform = rasterio.mask.mask(self.demdata, shapes, crop=True)
                # Hiển thị dữ liệu gió đã mask
                # Lưu mappable object để sử dụng cho colorbar
                show_result = rasterio.plot.show(masked_data[0], transform=masked_transform, ax=ax, cmap='viridis')
                img = show_result.get_images()[0]  # Lấy đối tượng AxesImage từ kết quả
            except Exception as e:
                print(f"Không thể tạo mặt nạ cho dữ liệu gió: {e}")
                # Hiển thị dữ liệu gió bình thường
                show_result = rasterio.plot.show(self.demdata, ax=ax, cmap='viridis')
                img = show_result.get_images()[0]  # Lấy đối tượng AxesImage từ kết quả
        else:
            # Hiển thị dữ liệu gió bình thường cho toàn bộ Việt Nam
            show_result = rasterio.plot.show(self.demdata, ax=ax, cmap='viridis')
            img = show_result.get_images()[0]  # Lấy đối tượng AxesImage từ kết quả
        
        # Thêm thanh màu chú thích với thông tin tốc độ gió bằng tiếng Việt và tiếng Anh
        cbar = plt.colorbar(img, ax=ax, shrink=0.8, pad=0.01)
        cbar.set_label('Tốc độ gió (m/s) | Wind Speed (m/s)', fontsize=12)
        
        # Hiển thị ranh giới (Display boundaries) - chỉ hiển thị khu vực được chọn
        display_region.boundary.plot(ax=ax, color='red', linewidth=1.5)
        
        # Thêm tên vùng nếu đã chọn (Add region name if selected)
        if self.selected_region is not None and self.selected_region is not self.catchments:
            region_name = self.selected_region['name'].values[0]
            region_centroid = self.selected_region.geometry.centroid.values[0]
            ax.text(region_centroid.x, region_centroid.y, region_name, 
                    color='red', fontsize=14, ha='center', va='center', 
                    fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))
        
        # Thiết lập phạm vi hiển thị (Set display extent)
        buffer = (maxx - minx) * 0.05  # Tạo đệm 5% (Create a 5% buffer)
        ax.set_xlim(minx - buffer, maxx + buffer)
        ax.set_ylim(miny - buffer, maxy + buffer)
        
        # Thêm tiêu đề (Add title)
        if self.selected_region is not None and self.selected_region is not self.catchments:
            region_name = self.selected_region['name'].values[0]
            title = f'Tốc độ gió tại {region_name} (m/s)\nWind Speed in {region_name} (m/s)'
        else:
            title = 'Tốc độ gió tại Việt Nam (m/s)\nWind Speed in Vietnam (m/s)'
        
        ax.set_title(title, fontsize=14)
        
        # Thêm nhãn tọa độ (Add coordinate labels)
        ax.set_xlabel('Kinh độ | Longitude', fontsize=10)
        ax.set_ylabel('Vĩ độ | Latitude', fontsize=10)
        
        # Thêm chú thích về tốc độ gió
        ax.text(minx + (maxx - minx) * 0.02, miny + (maxy - miny) * 0.05, 
                "Màu xanh đậm -> vàng -> đỏ: Tốc độ gió tăng dần\nDark blue -> yellow -> red: Increasing wind speed", 
                fontsize=10, bbox=dict(facecolor='white', alpha=0.7))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Đã lưu biểu đồ tại: {save_path}")
            print(f"Figure saved at: {save_path}")
            
        plt.tight_layout()
        return fig, ax
    
    def create_voronoi_polygons(self, num_points=100, random_state=42):
        """
        Tạo các đa giác Voronoi để phân tích dữ liệu
        (Create Voronoi polygons for data analysis)
        
        Parameters:
        -----------
        num_points : int, optional
            Số điểm để tạo đa giác Voronoi (Number of points to create Voronoi polygons)
            Mặc định là 100 điểm, nên giữ dưới 1000 điểm để tăng tốc độ phân tích
            (Default is 100 points, recommended to keep under 1000 points to improve analysis speed)
        random_state : int, optional
            Giá trị để tạo các điểm ngẫu nhiên có thể lặp lại (Value for reproducible random points)
        """
        from scipy.spatial import Voronoi
        
        if self.catchments is None:
            raise ValueError("Chưa tải dữ liệu. Hãy gọi phương thức load_data() trước.")
        
        print(f"Tạo {num_points} đa giác Voronoi...")
        print(f"Creating {num_points} Voronoi polygons...")
        
        # Sử dụng vùng được chọn hoặc toàn bộ ranh giới
        boundary = self.selected_region if self.selected_region is not None else self.catchments
        
        # Lấy bounding box của ranh giới (Get the bounding box of the boundary)
        minx, miny, maxx, maxy = boundary.total_bounds
        
        # Tạo các điểm ngẫu nhiên trong bounding box (Create random points within the bounding box)
        np.random.seed(random_state)
        points = np.column_stack([
            np.random.uniform(minx, maxx, num_points),
            np.random.uniform(miny, maxy, num_points)
        ])
        
        # Tạo đa giác Voronoi (Create Voronoi polygons)
        vor = Voronoi(points)
        
        # Chuyển đổi đa giác Voronoi thành đa giác không gian địa lý
        # (Convert Voronoi polygons to geographic polygons)
        import shapely.geometry as geometry
        from shapely.ops import cascaded_union
        
        # Tạo từ điển để lưu các đa giác (Create dictionary to store polygons)
        region_polys = {}
        
        # Hiển thị thanh tiến độ khi xử lý từng vùng
        print("Xử lý các đa giác Voronoi...")
        print("Processing Voronoi polygons...")
        
        for i, region_idx in enumerate(tqdm(vor.point_region, desc="Tạo đa giác | Creating polygons")):
            region = vor.regions[region_idx]
            
            if -1 not in region and len(region) > 0:
                # Tạo đa giác từ các điểm của vùng (Create polygon from region points)
                polygon = geometry.Polygon([vor.vertices[i] for i in region])
                
                # Lưu đa giác với chỉ số của điểm (Store polygon with point index)
                region_polys[i] = polygon
        
        # Tạo DataFrame với cột geometry (Create DataFrame with geometry column)
        vonorol = pd.DataFrame()
        vonorol['geometry'] = pd.Series(region_polys)
        
        # Chuyển thành GeoDataFrame (Convert to GeoDataFrame)
        vonorol = gpd.GeoDataFrame(vonorol, geometry='geometry')
        
        # Thêm chỉ số làm tên (Add index as name)
        vonorol['name'] = vonorol.index
        
        # Cắt các đa giác theo ranh giới vùng được chọn
        if self.selected_region is not None and self.selected_region is not self.catchments:
            # Chuyển đổi CRS nếu cần
            if vonorol.crs != self.selected_region.crs and vonorol.crs is not None:
                vonorol = vonorol.to_crs(self.selected_region.crs)
            elif vonorol.crs is None:
                vonorol.crs = self.selected_region.crs
                
            print("Cắt các đa giác Voronoi theo ranh giới vùng được chọn...")
            print("Clipping Voronoi polygons by selected region boundary...")
            vonorol = gpd.clip(vonorol, self.selected_region.geometry.unary_union)
            
        self.voronoi_polygons = vonorol
        print(f"Đã tạo {len(self.voronoi_polygons)} đa giác Voronoi để phân tích.")
        print(f"Created {len(self.voronoi_polygons)} Voronoi polygons for analysis.")
        
        return self
    
    def calculate_wind_statistics(self, wind_file=None):
        """
        Tính toán thống kê gió cho các đa giác Voronoi
        (Calculate wind statistics for Voronoi polygons)
        
        Parameters:
        -----------
        wind_file : str, optional
            Đường dẫn đến file dữ liệu tốc độ gió dạng GeoTIFF, nếu chưa được tải trước đó
            (Path to the wind speed data file in GeoTIFF format, if not loaded previously)
        """
        if self.voronoi_polygons is None:
            raise ValueError("Chưa tạo đa giác Voronoi. Hãy gọi phương thức create_voronoi_polygons() trước.")
        
        if wind_file is not None and self.demdata is None:
            self.demdata = rasterio.open(wind_file)
        
        print("Tính toán thống kê gió cho các đa giác Voronoi...")
        print("Calculating wind statistics for Voronoi polygons...")
        
        # Sử dụng tqdm để hiển thị thanh tiến độ
        # Chia thành các nhóm nhỏ để hiển thị tiến độ
        batch_size = 50  # số polygon xử lý mỗi lần
        results = []
        
        total_polygons = len(self.voronoi_polygons)
        for i in tqdm(range(0, total_polygons, batch_size), desc="Phân tích gió | Wind analysis"):
            batch = self.voronoi_polygons.iloc[i:min(i+batch_size, total_polygons)]
            # Tính toán thống kê gió cho nhóm đa giác
            batch_stats = zonal_stats(batch.geometry, self.demdata.name, stats=['mean', 'std'])
            results.extend(batch_stats)
        
        # Chuyển thành DataFrame (Convert to DataFrame)
        demstats_df = pd.DataFrame(results)
        demstats_df.rename(columns={'mean': 'wind_mean', 'std': 'wind_std'}, inplace=True)
        
        # Kết hợp với GeoDataFrame (Combine with GeoDataFrame)
        self.voronoi_polygons = pd.concat([self.voronoi_polygons, demstats_df], axis=1)
        
        print("Đã tính toán thống kê gió cho các đa giác Voronoi.")
        print("Wind statistics calculated for Voronoi polygons.")
        return self
    
    def filter_high_potential_areas(self, min_wind_speed=6.0):
        """
        Lọc các khu vực có tiềm năng gió cao
        (Filter areas with high wind potential)
        
        Parameters:
        -----------
        min_wind_speed : float, optional
            Tốc độ gió tối thiểu để một khu vực được coi là có tiềm năng cao
            (Minimum wind speed for an area to be considered high potential)
            
        Returns:
        --------
        high_potential : GeoDataFrame
            GeoDataFrame chứa các khu vực có tiềm năng gió cao
            (GeoDataFrame containing areas with high wind potential)
        """
        if self.voronoi_polygons is None or 'wind_mean' not in self.voronoi_polygons.columns:
            raise ValueError("Chưa tính toán thống kê gió. Hãy gọi phương thức calculate_wind_statistics() trước.")
        
        print("Lọc các khu vực có tiềm năng gió cao...")
        print("Filtering areas with high wind potential...")
        
        # Sử dụng tqdm để hiển thị tiến độ khi số lượng đa giác lớn
        if len(self.voronoi_polygons) > 100:
            # Tạo list index của các đa giác có tiềm năng cao
            high_potential_indices = []
            for idx in tqdm(self.voronoi_polygons.index, desc="Kiểm tra tiềm năng | Checking potential"):
                row = self.voronoi_polygons.loc[idx]
                if row.wind_mean > min_wind_speed:
                    high_potential_indices.append(idx)
            
            high_potential = self.voronoi_polygons.loc[high_potential_indices].copy()
        else:
            # Đối với số lượng nhỏ, sử dụng phương pháp lọc nhanh hơn
            high_potential = self.voronoi_polygons[self.voronoi_polygons.wind_mean > min_wind_speed].copy()
        
        region_name = ""
        if self.selected_region is not None and self.selected_region is not self.catchments:
            region_name = f" trong {self.selected_region['name'].values[0]}"
        
        print(f"Có {len(high_potential)} khu vực{region_name} có tốc độ gió trung bình > {min_wind_speed} m/s")
        print(f"There are {len(high_potential)} areas{' in ' + self.selected_region['name'].values[0] if region_name else ''} with average wind speed > {min_wind_speed} m/s")
        return high_potential
    
    def save_results(self, output_dir, file_prefix="vietnam_wind_potential", min_wind_speed=6.0):
        """
        Lưu kết quả phân tích thành file KML và CSV
        (Save analysis results as KML and CSV files)
        
        Parameters:
        -----------
        output_dir : str
            Thư mục đầu ra để lưu kết quả (Output directory to save results)
        file_prefix : str, optional
            Tiền tố cho tên file (Prefix for file names)
        min_wind_speed : float, optional
            Tốc độ gió tối thiểu để một khu vực được coi là có tiềm năng cao
            (Minimum wind speed for an area to be considered high potential)
        """
        if self.voronoi_polygons is None:
            raise ValueError("Chưa tính toán thống kê gió. Hãy gọi phương thức calculate_wind_statistics() trước.")
        
        # Tạo thư mục đầu ra nếu chưa tồn tại (Create output directory if it doesn't exist)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Thêm tên vùng vào tiền tố nếu có chọn vùng cụ thể
        if self.selected_region is not None and self.selected_region is not self.catchments:
            region_name = self.selected_region['name'].values[0].lower().replace(' ', '_')
            file_prefix = f"{file_prefix}_{region_name}"
        
        print("Đang lưu kết quả phân tích...")
        print("Saving analysis results...")
        
        # Lưu tất cả các đa giác (Save all polygons)
        all_polygons_kml = output_dir / f"{file_prefix}_all.kml"
        print(f"Lưu tất cả đa giác vào: {all_polygons_kml}")
        print(f"Saving all polygons to: {all_polygons_kml}")
        self.voronoi_polygons.to_file(str(all_polygons_kml), driver='KML')
        print(f"Đã lưu tất cả các đa giác vào: {all_polygons_kml}")
        print(f"All polygons saved to: {all_polygons_kml}")
        
        # Lưu các đa giác có tiềm năng cao (Save high potential polygons)
        high_potential = self.filter_high_potential_areas(min_wind_speed)
        high_potential_kml = output_dir / f"{file_prefix}_{min_wind_speed}ms.kml"
        print(f"Lưu các đa giác có tiềm năng cao vào: {high_potential_kml}")
        print(f"Saving high potential polygons to: {high_potential_kml}")
        high_potential.to_file(str(high_potential_kml), driver='KML')
        print(f"Đã lưu các đa giác có tiềm năng cao vào: {high_potential_kml}")
        print(f"High potential polygons saved to: {high_potential_kml}")
        
        # Lưu dữ liệu thành CSV (Save data as CSV)
        csv_file = output_dir / f"{file_prefix}_statistics.csv"
        print(f"Lưu thống kê gió vào: {csv_file}")
        print(f"Saving wind statistics to: {csv_file}")
        self.voronoi_polygons[['name', 'wind_mean', 'wind_std']].to_csv(str(csv_file), index=False)
        print(f"Đã lưu thống kê gió vào: {csv_file}")
        print(f"Wind statistics saved to: {csv_file}")
        
        return self
    
    def visualize_high_potential_areas(self, min_wind_speed=5.0, figsize=(12, 10), save_path=None):
        """
        Hiển thị các khu vực có tiềm năng gió cao
        (Display areas with high wind potential)
        
        Parameters:
        -----------
        min_wind_speed : float, optional
            Tốc độ gió tối thiểu để xem xét là khu vực tiềm năng (m/s)
            (Minimum wind speed to consider as potential area (m/s))
        figsize : tuple, optional
            Kích thước của biểu đồ (Size of the figure)
        save_path : str, optional
            Đường dẫn để lưu biểu đồ (Path to save the figure)
        """
        if self.voronoi_polygons is None or 'wind_mean' not in self.voronoi_polygons.columns:
            raise ValueError("Chưa tính toán thống kê gió. Hãy gọi phương thức calculate_wind_statistics() trước.")
        
        # Lọc ra các khu vực có tiềm năng cao (Filter high potential areas)
        high_potential = self.filter_high_potential_areas(min_wind_speed)
        if high_potential.empty:
            print(f"Không tìm thấy khu vực nào có tốc độ gió trung bình >= {min_wind_speed} m/s")
            print(f"No areas found with average wind speed >= {min_wind_speed} m/s")
            return None, None
        
        # Loại bỏ các đa giác có geometry là None
        print("Kiểm tra và làm sạch dữ liệu...")
        print("Checking and cleaning data...")
        high_potential = high_potential[high_potential.geometry.notna()].copy()
        if high_potential.empty:
            print(f"Sau khi làm sạch dữ liệu, không còn khu vực nào có tốc độ gió >= {min_wind_speed} m/s")
            print(f"After cleaning data, no areas left with wind speed >= {min_wind_speed} m/s")
            return None, None
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Xác định vùng hiển thị (Display region)
        display_region = self.selected_region if self.selected_region is not None else self.catchments
        
        # Lấy phạm vi hiển thị từ vùng đã chọn (Get extent from selected region)
        minx, miny, maxx, maxy = display_region.total_bounds
        
        # Tạo mask cho dữ liệu gió (Create mask for wind data)
        if self.selected_region is not None and self.selected_region is not self.catchments:
            mask = None
            try:
                import rasterio.mask
                # Sử dụng ranh giới của khu vực đã chọn để mask dữ liệu gió
                shapes = [geom.__geo_interface__ for geom in self.selected_region.geometry]
                masked_data, masked_transform = rasterio.mask.mask(self.demdata, shapes, crop=True)
                # Hiển thị dữ liệu gió đã mask
                show_result = rasterio.plot.show(masked_data[0], transform=masked_transform, ax=ax, cmap='viridis')
                img = show_result.get_images()[0]  # Lấy đối tượng AxesImage từ kết quả
            except Exception as e:
                print(f"Không thể tạo mặt nạ cho dữ liệu gió: {e}")
                # Hiển thị dữ liệu gió bình thường
                show_result = rasterio.plot.show(self.demdata, ax=ax, cmap='viridis')
                img = show_result.get_images()[0]  # Lấy đối tượng AxesImage từ kết quả
        else:
            # Hiển thị dữ liệu gió bình thường cho toàn bộ Việt Nam
            show_result = rasterio.plot.show(self.demdata, ax=ax, cmap='viridis')
            img = show_result.get_images()[0]  # Lấy đối tượng AxesImage từ kết quả
        
        # Thêm thanh màu chú thích với thông tin tốc độ gió bằng tiếng Việt và tiếng Anh
        cbar = plt.colorbar(img, ax=ax, shrink=0.8, pad=0.01)
        cbar.set_label('Tốc độ gió (m/s) | Wind Speed (m/s)', fontsize=12)
        
        # Hiển thị ranh giới (Display boundaries) - chỉ hiển thị khu vực được chọn
        display_region.boundary.plot(ax=ax, color='red', linewidth=1.5)
        
        # Hiển thị các khu vực tiềm năng cao (Display high potential areas)
        high_potential.plot(ax=ax, color='yellow', edgecolor='orange', alpha=0.6)
        
        # Thêm nhãn cho các khu vực tiềm năng cao (Add labels for high potential areas)
        for idx, row in high_potential.iterrows():
            # Kiểm tra geometry có tồn tại không trước khi truy cập thuộc tính centroid
            if row.geometry is not None:
                try:
                    centroid = row.geometry.centroid
                    avg_speed = row['wind_mean']
                    ax.text(centroid.x, centroid.y, f"{avg_speed:.1f} m/s", 
                            ha='center', va='center', fontsize=9, fontweight='bold',
                            bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.2'))
                except Exception as e:
                    print(f"Lỗi khi xử lý geometry tại index {idx}: {e}")
                    print(f"Error processing geometry at index {idx}: {e}")
        
        # Thiết lập phạm vi hiển thị (Set display extent)
        buffer = (maxx - minx) * 0.05  # Tạo đệm 5% (Create a 5% buffer)
        ax.set_xlim(minx - buffer, maxx + buffer)
        ax.set_ylim(miny - buffer, maxy + buffer)
        
        # Thêm tiêu đề (Add title)
        if self.selected_region is not None and self.selected_region is not self.catchments:
            region_name = self.selected_region['name'].values[0]
            title = f'Khu vực có tiềm năng gió cao tại {region_name} (>= {min_wind_speed} m/s)\nHigh Wind Potential Areas in {region_name} (>= {min_wind_speed} m/s)'
        else:
            title = f'Khu vực có tiềm năng gió cao tại Việt Nam (>= {min_wind_speed} m/s)\nHigh Wind Potential Areas in Vietnam (>= {min_wind_speed} m/s)'
        
        ax.set_title(title, fontsize=14)
        
        # Thêm nhãn tọa độ (Add coordinate labels)
        ax.set_xlabel('Kinh độ | Longitude', fontsize=10)
        ax.set_ylabel('Vĩ độ | Latitude', fontsize=10)
        
        # Thêm chú thích (Add legend)
        legend_elements = [
            Patch(facecolor='yellow', edgecolor='orange', alpha=0.6, 
                  label=f'Khu vực tiềm năng (>= {min_wind_speed} m/s) | Potential areas (>= {min_wind_speed} m/s)')
        ]
        ax.legend(handles=legend_elements, loc='lower right')
        
        # Thêm chú thích về tốc độ gió
        ax.text(minx + (maxx - minx) * 0.02, miny + (maxy - miny) * 0.05, 
                "Màu xanh đậm -> vàng -> đỏ: Tốc độ gió tăng dần\nDark blue -> yellow -> red: Increasing wind speed", 
                fontsize=10, bbox=dict(facecolor='white', alpha=0.7))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Đã lưu biểu đồ tại: {save_path}")
            print(f"Figure saved at: {save_path}")
            
        plt.tight_layout()
        return fig, ax
    
    def export_detailed_statistics(self, output_dir, file_prefix="vietnam_wind_detailed", min_wind_speed=6.0):
        """
        Xuất dữ liệu thống kê chi tiết về tốc độ gió và khu vực tiềm năng cao
        (Export detailed statistics about wind speed and high potential areas)
        
        Parameters:
        -----------
        output_dir : str
            Thư mục đầu ra để lưu kết quả (Output directory to save results)
        file_prefix : str, optional
            Tiền tố cho tên file (Prefix for file names)
        min_wind_speed : float, optional
            Tốc độ gió tối thiểu để một khu vực được coi là có tiềm năng cao
            (Minimum wind speed for an area to be considered high potential)
        """
        if self.voronoi_polygons is None or 'wind_mean' not in self.voronoi_polygons.columns:
            raise ValueError("Chưa tính toán thống kê gió. Hãy gọi phương thức calculate_wind_statistics() trước.")
        
        # Tạo thư mục đầu ra nếu chưa tồn tại (Create output directory if it doesn't exist)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Thêm tên vùng vào tiền tố nếu có chọn vùng cụ thể
        if self.selected_region is not None and self.selected_region is not self.catchments:
            region_name = self.selected_region['name'].values[0].lower().replace(' ', '_')
            file_prefix = f"{file_prefix}_{region_name}"
        
        print("Xuất dữ liệu thống kê chi tiết...")
        print("Exporting detailed statistics...")
        
        # Thống kê cơ bản (Basic statistics)
        total_area = len(self.voronoi_polygons)
        high_potential = self.filter_high_potential_areas(min_wind_speed)
        high_potential_count = len(high_potential)
        percentage = (high_potential_count / total_area) * 100 if total_area > 0 else 0
        
        # Thống kê tốc độ gió (Wind speed statistics)
        wind_stats = {
            'min': self.voronoi_polygons['wind_mean'].min(),
            'max': self.voronoi_polygons['wind_mean'].max(),
            'mean': self.voronoi_polygons['wind_mean'].mean(),
            'median': self.voronoi_polygons['wind_mean'].median(),
            'std': self.voronoi_polygons['wind_mean'].std()
        }
        
        # Phân phối tốc độ gió theo khoảng (Wind speed distribution by range)
        bins = [0, 3, 4, 5, 6, 7, 8, 9, 10, float('inf')]
        labels = ['<3', '3-4', '4-5', '5-6', '6-7', '7-8', '8-9', '9-10', '>10']
        
        print("Phân loại tốc độ gió...")
        print("Categorizing wind speed...")
        if total_area > 1000:
            # Chia nhỏ quá trình phân loại cho các dataset lớn
            self.voronoi_polygons['wind_category'] = None
            batch_size = 500
            for i in tqdm(range(0, total_area, batch_size), desc="Phân loại gió | Wind categorization"):
                end_idx = min(i + batch_size, total_area)
                self.voronoi_polygons.iloc[i:end_idx, self.voronoi_polygons.columns.get_loc('wind_category')] = pd.cut(
                    self.voronoi_polygons['wind_mean'].iloc[i:end_idx], 
                    bins=bins, 
                    labels=labels
                )
        else:
            self.voronoi_polygons['wind_category'] = pd.cut(self.voronoi_polygons['wind_mean'], bins=bins, labels=labels)
            
        distribution = self.voronoi_polygons['wind_category'].value_counts().sort_index()
        
        # Tạo file thống kê tổng hợp (Create summary statistics file)
        summary_file = output_dir / f"{file_prefix}_detailed_summary.txt"
        print(f"Lưu thống kê tổng hợp vào: {summary_file}")
        print(f"Saving summary statistics to: {summary_file}")
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            # Tiêu đề (Title)
            if self.selected_region is not None and self.selected_region is not self.catchments:
                region_name = self.selected_region['name'].values[0]
                f.write(f"THỐNG KÊ CHI TIẾT VỀ TỐC ĐỘ GIÓ TẠI {region_name.upper()}\n")
                f.write(f"DETAILED WIND SPEED STATISTICS FOR {region_name.upper()}\n\n")
            else:
                f.write("THỐNG KÊ CHI TIẾT VỀ TỐC ĐỘ GIÓ TẠI VIỆT NAM\n")
                f.write("DETAILED WIND SPEED STATISTICS FOR VIETNAM\n\n")
            
            # Thông tin cơ bản (Basic information)
            f.write("I. THÔNG TIN CƠ BẢN | BASIC INFORMATION\n")
            f.write("-----------------------------------\n")
            f.write(f"Tổng số khu vực phân tích | Total analyzed areas: {total_area}\n")
            f.write(f"Số khu vực có tiềm năng cao (>{min_wind_speed} m/s) | High potential areas (>{min_wind_speed} m/s): {high_potential_count}\n")
            f.write(f"Tỷ lệ khu vực có tiềm năng cao | Percentage of high potential areas: {percentage:.2f}%\n\n")
            
            # Thống kê tốc độ gió (Wind speed statistics)
            f.write("II. THỐNG KÊ TỐC ĐỘ GIÓ | WIND SPEED STATISTICS\n")
            f.write("-----------------------------------\n")
            f.write(f"Tốc độ gió thấp nhất | Minimum wind speed: {wind_stats['min']:.2f} m/s\n")
            f.write(f"Tốc độ gió cao nhất | Maximum wind speed: {wind_stats['max']:.2f} m/s\n")
            f.write(f"Tốc độ gió trung bình | Average wind speed: {wind_stats['mean']:.2f} m/s\n")
            f.write(f"Tốc độ gió trung vị | Median wind speed: {wind_stats['median']:.2f} m/s\n")
            f.write(f"Độ lệch chuẩn | Standard deviation: {wind_stats['std']:.2f} m/s\n\n")
            
            # Phân phối tốc độ gió (Wind speed distribution)
            f.write("III. PHÂN PHỐI TỐC ĐỘ GIÓ | WIND SPEED DISTRIBUTION\n")
            f.write("-----------------------------------\n")
            f.write("Tốc độ gió (m/s) | Wind Speed (m/s) | Số lượng khu vực | Number of areas | Tỷ lệ | Percentage\n")
            for category, count in distribution.items():
                percentage = (count / total_area) * 100 if total_area > 0 else 0
                f.write(f"{category} m/s | {count} | {percentage:.2f}%\n")
        
        # Tạo file CSV chi tiết (Create detailed CSV file)
        detailed_csv = output_dir / f"{file_prefix}_detailed_statistics.csv"
        print(f"Lưu dữ liệu chi tiết vào: {detailed_csv}")
        print(f"Saving detailed data to: {detailed_csv}")
        
        detailed_df = self.voronoi_polygons[['name', 'wind_mean', 'wind_std', 'wind_category']].copy()
        detailed_df.columns = ['ID', 'Tốc độ gió trung bình (m/s) | Average Wind Speed (m/s)', 
                              'Độ lệch chuẩn (m/s) | Standard Deviation (m/s)', 
                              'Phân loại tốc độ gió | Wind Speed Category']
        
        # Thêm cột phân loại tiềm năng (Add potential classification column)
        print("Thêm phân loại tiềm năng...")
        print("Adding potential classification...")
        detailed_df['Tiềm năng | Potential'] = detailed_df['Tốc độ gió trung bình (m/s) | Average Wind Speed (m/s)'].apply(
            lambda x: 'Cao | High' if x > min_wind_speed else 'Thấp | Low')
        
        detailed_df.to_csv(detailed_csv, index=False, encoding='utf-8')
        
        print(f"Đã xuất thống kê chi tiết tại: {summary_file}")
        print(f"Detailed statistics exported to: {summary_file}")
        print(f"Đã xuất dữ liệu chi tiết tại: {detailed_csv}")
        print(f"Detailed data exported to: {detailed_csv}")
        
        return self
    
    def create_interactive_visualization(self, min_wind_speed=5.0, figsize=(12, 10), save_path=None, html_output=None):
        """
        Tạo biểu đồ tương tác (HTML) cho phép hover chuột để xem thông tin tốc độ gió
        (Create interactive plot (HTML) allowing mouse hover to view wind speed information)
        
        Parameters:
        -----------
        min_wind_speed : float, optional
            Tốc độ gió tối thiểu để xem xét là khu vực tiềm năng (m/s)
            (Minimum wind speed to consider as potential area (m/s))
        figsize : tuple, optional
            Kích thước của biểu đồ (Size of the figure)
        save_path : str, optional
            Đường dẫn để lưu hình ảnh (PNG) (Path to save the image (PNG))
        html_output : str, optional
            Đường dẫn để lưu file HTML tương tác (Path to save interactive HTML file)
            
        Returns:
        --------
        html : str
            Mã HTML của biểu đồ tương tác
        """
        try:
            import mpld3
            from mpld3 import plugins
        except ImportError:
            print("Thư viện mpld3 không được cài đặt. Vui lòng cài đặt bằng lệnh: pip install mpld3")
            print("mpld3 library is not installed. Please install it using: pip install mpld3")
            return None
            
        if self.voronoi_polygons is None or 'wind_mean' not in self.voronoi_polygons.columns:
            raise ValueError("Chưa tính toán thống kê gió. Hãy gọi phương thức calculate_wind_statistics() trước.")
        
        # Lọc ra các khu vực có tiềm năng cao (Filter high potential areas)
        high_potential = self.filter_high_potential_areas(min_wind_speed)
        if high_potential.empty:
            print(f"Không tìm thấy khu vực nào có tốc độ gió trung bình >= {min_wind_speed} m/s")
            print(f"No areas found with average wind speed >= {min_wind_speed} m/s")
            return None
        
        # Loại bỏ các đa giác có geometry là None
        print("Kiểm tra và làm sạch dữ liệu...")
        print("Checking and cleaning data...")
        high_potential = high_potential[high_potential.geometry.notna()].copy()
        if high_potential.empty:
            print(f"Sau khi làm sạch dữ liệu, không còn khu vực nào có tốc độ gió >= {min_wind_speed} m/s")
            print(f"After cleaning data, no areas left with wind speed >= {min_wind_speed} m/s")
            return None
            
        # Làm sạch voronoi_polygons
        self.voronoi_polygons = self.voronoi_polygons[self.voronoi_polygons.geometry.notna()].copy()
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Xác định vùng hiển thị (Display region)
        display_region = self.selected_region if self.selected_region is not None else self.catchments
        
        # Lấy phạm vi hiển thị từ vùng đã chọn (Get extent from selected region)
        minx, miny, maxx, maxy = display_region.total_bounds
        
        # Hiển thị ranh giới (Display boundaries)
        display_region.boundary.plot(ax=ax, color='red', linewidth=1.5)
        
        # Tạo dữ liệu cho các đa giác tương tác
        # Hiển thị tất cả các đa giác voronoi với màu sắc tùy thuộc vào tốc độ gió
        # Tạo viridis colormap
        from matplotlib.colors import Normalize
        from matplotlib.cm import ScalarMappable
        import matplotlib.cm as cm
        
        # Lấy min, max tốc độ gió để tạo colormap
        wind_min = self.voronoi_polygons['wind_mean'].min()
        wind_max = self.voronoi_polygons['wind_mean'].max()
        norm = Normalize(vmin=wind_min, vmax=wind_max)
        cmap = cm.viridis
        
        # Vẽ từng đa giác với màu sắc phụ thuộc vào tốc độ gió
        # và thêm thông tin khi hover
        print("Tạo bản đồ tương tác...")
        print("Creating interactive map...")
        for idx, row in self.voronoi_polygons.iterrows():
            # Kiểm tra geometry có hợp lệ không
            if row.geometry is None or not hasattr(row.geometry, 'exterior') or row.geometry.exterior is None:
                continue
                
            try:
                color = cmap(norm(row['wind_mean']))
                # Vẽ đa giác
                poly = ax.fill(*row.geometry.exterior.xy, alpha=0.7, color=color, 
                              edgecolor='none' if row['wind_mean'] < min_wind_speed else 'orange')
                
                # Chuẩn bị thông tin cho tooltip
                wind_speed = round(row['wind_mean'], 2)
                tooltip_text = f"Tốc độ gió: {wind_speed} m/s\nWind speed: {wind_speed} m/s"
                
                # Thêm tooltip
                plugins.connect(fig, plugins.PointHTMLTooltip(
                    poly[0], [tooltip_text],
                    voffset=10, hoffset=10, css='''
                        .mpld3-tooltip {
                            background-color: white;
                            border: 1px solid black;
                            border-radius: 5px;
                            padding: 5px;
                            font-family: Arial, sans-serif;
                        }
                    '''
                ))
            except Exception as e:
                print(f"Lỗi khi vẽ đa giác tại index {idx}: {e}")
                print(f"Error drawing polygon at index {idx}: {e}")
            
        # Đánh dấu các khu vực tiềm năng cao
        try:
            high_potential.plot(ax=ax, color='yellow', edgecolor='orange', alpha=0.4)
        except Exception as e:
            print(f"Lỗi khi vẽ khu vực tiềm năng cao: {e}")
            print(f"Error plotting high potential areas: {e}")
        
        # Thiết lập phạm vi hiển thị (Set display extent)
        buffer = (maxx - minx) * 0.05  # Tạo đệm 5% (Create a 5% buffer)
        ax.set_xlim(minx - buffer, maxx + buffer)
        ax.set_ylim(miny - buffer, maxy + buffer)
        
        # Thêm thanh màu chú thích (Add colorbar)
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8, pad=0.01)
        cbar.set_label('Tốc độ gió (m/s) | Wind Speed (m/s)', fontsize=12)
        
        # Thêm tiêu đề (Add title)
        if self.selected_region is not None and self.selected_region is not self.catchments:
            region_name = self.selected_region['name'].values[0]
            title = f'Bản đồ tương tác tốc độ gió và khu vực tiềm năng tại {region_name}\nInteractive Wind Speed & Potential Areas Map in {region_name}'
        else:
            title = f'Bản đồ tương tác tốc độ gió và khu vực tiềm năng tại Việt Nam\nInteractive Wind Speed & Potential Areas Map in Vietnam'
        
        ax.set_title(title, fontsize=14)
        
        # Thêm nhãn tọa độ (Add coordinate labels)
        ax.set_xlabel('Kinh độ | Longitude', fontsize=10)
        ax.set_ylabel('Vĩ độ | Latitude', fontsize=10)
        
        # Thêm chú thích (Add legend)
        legend_elements = [
            Patch(facecolor='yellow', edgecolor='orange', alpha=0.4, 
                  label=f'Khu vực tiềm năng (>= {min_wind_speed} m/s) | Potential areas (>= {min_wind_speed} m/s)')
        ]
        ax.legend(handles=legend_elements, loc='lower right')
        
        # Thêm hướng dẫn sử dụng
        ax.text(minx + (maxx - minx) * 0.02, miny + (maxy - miny) * 0.05, 
                "Di chuyển chuột lên các vùng để xem tốc độ gió\nHover over areas to see wind speed", 
                fontsize=10, bbox=dict(facecolor='white', alpha=0.7))
        
        # Lưu hình ảnh PNG nếu cần
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Đã lưu biểu đồ tại: {save_path}")
            print(f"Figure saved at: {save_path}")
        
        print("Tạo HTML tương tác...")
        print("Creating interactive HTML...")
        
        try:
            # Tạo HTML tương tác
            html = mpld3.fig_to_html(fig)
            
            # Lưu file HTML nếu cần
            if html_output:
                with open(html_output, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"Đã lưu file HTML tương tác tại: {html_output}")
                print(f"Interactive HTML file saved at: {html_output}")
        except Exception as e:
            print(f"Lỗi khi tạo HTML tương tác: {e}")
            print(f"Error creating interactive HTML: {e}")
            plt.close(fig)  # Đóng hình để giải phóng bộ nhớ
            return None
            
        plt.close(fig)  # Đóng hình để giải phóng bộ nhớ
        
        return html

def parse_args():
    """
    Phân tích tham số dòng lệnh
    (Parse command line arguments)
    """
    parser = argparse.ArgumentParser(description='Phân tích tiềm năng gió tại Việt Nam / Wind Potential Analysis in Vietnam')
    
    parser.add_argument('--boundary', type=str, required=True,
                        help='Đường dẫn đến file ranh giới dạng geojson / Path to boundary file in geojson format')
    
    parser.add_argument('--wind', type=str, required=True,
                        help='Đường dẫn đến file dữ liệu tốc độ gió dạng GeoTIFF / Path to wind speed data file in GeoTIFF format')
    
    parser.add_argument('--provinces', type=str, 
                        help='Đường dẫn đến file ranh giới các tỉnh/thành phố dạng geojson / Path to provinces boundary file in geojson format')
    
    parser.add_argument('--region', type=str,
                        help='Tên tỉnh/thành phố để phân tích / Name of province/city to analyze')
    
    parser.add_argument('--output', type=str, default='results',
                        help='Thư mục đầu ra để lưu kết quả (mặc định: results) / Output directory to save results (default: results)')
    
    parser.add_argument('--points', type=int, default=100,
                        help='Số điểm để tạo đa giác Voronoi (mặc định: 100) / Number of points to create Voronoi polygons (default: 100)')
    
    parser.add_argument('--min-speed', type=float, default=6.0,
                        help='Tốc độ gió tối thiểu để một khu vực được coi là có tiềm năng cao (mặc định: 6.0 m/s) / Minimum wind speed for high potential areas (default: 6.0 m/s)')
    
    parser.add_argument('--prefix', type=str, default='vietnam_wind_potential',
                        help='Tiền tố cho tên file đầu ra (mặc định: vietnam_wind_potential) / Prefix for output file names (default: vietnam_wind_potential)')
    
    parser.add_argument('--no-plots', action='store_true',
                        help='Không tạo biểu đồ (mặc định: False) / Do not create plots (default: False)')
    
    parser.add_argument('--list-regions', action='store_true',
                        help='Liệt kê các tỉnh/thành phố có sẵn và thoát / List available provinces/cities and exit')
    
    return parser.parse_args()

def main():
    """
    Hàm chính để chạy phân tích tiềm năng gió
    (Main function to run wind potential analysis)
    """
    args = parse_args()
    
    # Tạo thư mục đầu ra nếu chưa tồn tại (Create output directory if it doesn't exist)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Tạo đối tượng phân tích tiềm năng gió (Create wind potential analyzer object)
    analyzer = WindPotentialAnalyzer()
    
    # Đọc dữ liệu (Read data)
    analyzer.load_data(args.boundary, args.wind)
    
    # Đọc dữ liệu tỉnh/thành phố nếu có (Read province data if provided)
    if args.provinces:
        analyzer.load_provinces(args.provinces)
        
        # Liệt kê các tỉnh/thành phố và thoát nếu chỉ định
        if args.list_regions:
            regions = analyzer.list_available_regions()
            print("\nCác tỉnh/thành phố có sẵn để phân tích / Available provinces/cities for analysis:")
            for region in regions:
                print(f"  - {region}")
            return
    
    # Chọn vùng cụ thể nếu có (Select specific region if provided)
    if args.region:
        if not args.provinces:
            print("Lỗi: Cần cung cấp file ranh giới tỉnh/thành phố (--provinces) khi chọn vùng cụ thể.")
            print("Error: Need to provide provinces boundary file (--provinces) when selecting a specific region.")
            return
        analyzer.select_region(args.region)
    
    # Tạo biểu đồ dữ liệu gió và ranh giới (Create wind data and boundary plot)
    if not args.no_plots:
        region_suffix = f"_{args.region.lower().replace(' ', '_')}" if args.region else ""
        wind_data_plot_path = output_dir / f"{args.prefix}{region_suffix}_data.png"
        analyzer.visualize_wind_data(save_path=wind_data_plot_path)
    
    # Tạo các đa giác Voronoi (Create Voronoi polygons)
    analyzer.create_voronoi_polygons(num_points=args.points)
    
    # Tính toán thống kê gió (Calculate wind statistics)
    analyzer.calculate_wind_statistics()
    
    # Lưu kết quả (Save results)
    analyzer.save_results(
        output_dir=args.output,
        file_prefix=args.prefix,
        min_wind_speed=args.min_speed
    )
    
    # Tạo biểu đồ các khu vực có tiềm năng cao (Create high potential areas plot)
    if not args.no_plots:
        region_suffix = f"_{args.region.lower().replace(' ', '_')}" if args.region else ""
        high_potential_plot_path = output_dir / f"{args.prefix}{region_suffix}_high_potential_{args.min_speed}ms.png"
        analyzer.visualize_high_potential_areas(
            min_wind_speed=args.min_speed,
            save_path=high_potential_plot_path
        )
    
    # Xuất dữ liệu thống kê chi tiết (Export detailed statistics)
    analyzer.export_detailed_statistics(
        output_dir=args.output,
        file_prefix=args.prefix,
        min_wind_speed=args.min_speed
    )
    
    # Tạo biểu đồ tương tác (HTML) cho phép hover chuột để xem thông tin tốc độ gió
    if not args.no_plots:
        region_suffix = f"_{args.region.lower().replace(' ', '_')}" if args.region else ""
        interactive_html_path = output_dir / f"{args.prefix}{region_suffix}_interactive.html"
        analyzer.create_interactive_visualization(
            min_wind_speed=args.min_speed,
            save_path=None,
            html_output=interactive_html_path
        )
    
    print("\nPhân tích tiềm năng gió đã hoàn tất! / Wind potential analysis completed!")
    print(f"Kết quả đã được lưu vào thư mục: {args.output} / Results saved to directory: {args.output}")

if __name__ == "__main__":
    main() 