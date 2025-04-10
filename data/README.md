# Dữ liệu cho vietnamwind

Thư mục này chứa dữ liệu cần thiết để chạy công cụ phân tích tiềm năng gió vietnamwind.

## Các tệp dữ liệu cần thiết

1. **vietnam.geojson** - Ranh giới của Việt Nam
2. **VNM_wind-speed_100m.tif** - Dữ liệu tốc độ gió ở độ cao 100m
3. **vietnam_provinces.geojson** - Ranh giới các tỉnh/thành phố (cho tính năng chọn vùng)

## Cách lấy dữ liệu

### Dữ liệu gió và ranh giới Việt Nam
Bạn có thể tải dữ liệu gió và ranh giới Việt Nam từ trang Global Wind Atlas:
https://globalwindatlas.info/area/Vietnam

### Dữ liệu ranh giới tỉnh/thành phố
Bạn có thể lấy dữ liệu ranh giới các tỉnh/thành phố từ các nguồn sau:

1. **GADM Database**: https://gadm.org/download_country.html
   - Chọn Vietnam và tải định dạng GeoJSON
   - Sử dụng version "level 1" cho ranh giới tỉnh/thành phố

2. **OpenStreetMap**: https://download.geofabrik.de/asia/vietnam.html
   - Tải dữ liệu OSM và sử dụng QGIS để trích xuất ranh giới hành chính

Sau khi tải, đổi tên thành `vietnam_provinces.geojson` và đặt vào thư mục này.

## Cấu trúc file ranh giới tỉnh/thành phố
File ranh giới tỉnh/thành phố nên là một GeoJSON với:
- Mỗi tỉnh/thành phố là một Feature trong FeatureCollection
- Mỗi tỉnh nên có thuộc tính "name" hoặc "NAME_1" hoặc "NAME" chứa tên của tỉnh/thành phố

Ví dụ:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Hà Nội",
        "other_properties": "..."
      },
      "geometry": { ... }
    },
    ...
  ]
}
``` 