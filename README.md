# Camera Above Target - Synthetic Data Generation

这个项目提供了在Isaac Sim中实现合成数据生成的完整解决方案，其中相机随机位置于目标资产上方，永远不会出现在目标资产下方。

## 项目文件

1. **`simple_camera_above_target.py`** - 简单的示例脚本
2. **`config_driven_camera_above_target.py`** - 配置驱动的脚本
3. **`camera_above_target_config.json`** - 配置文件
4. **`camera_above_target_sdg.py`** - 完整的实现脚本

## 核心功能

✅ **相机始终位于目标上方** - 通过球坐标系统确保相机永远不会出现在目标下方  
✅ **可配置的高度和距离范围** - 灵活设置相机位置参数  
✅ **域随机化** - 光照、材质、相机位置的随机化  
✅ **多种标注格式** - RGB、边界框、语义分割等  
✅ **易于配置** - JSON配置文件支持  

## 快速开始

### 1. 运行简单示例

```bash
cd /home/ubuntu/lxd/lxd_code/isaacsim
python simple_camera_above_target.py
```

这个脚本会：
- 创建一个目标资产（默认为block）
- 创建一个相机随机位置于目标上方
- 生成50帧合成数据
- 输出到 `./camera_above_target_output` 目录

### 2. 使用配置文件运行

```bash
python config_driven_camera_above_target.py --config camera_above_target_config.json
```

### 3. 无头模式运行（批量生成）

```bash
python config_driven_camera_above_target.py --config camera_above_target_config.json --headless
```

## 配置说明

编辑 `camera_above_target_config.json` 来自定义您的设置：

### 目标资产配置

```json
"target_asset": {
    "usd_path": "/Isaac/Props/Blocks/block_instanceable.usd",  // 您的资产路径
    "position": [0, 0, 0.5],  // 资产位置 [x, y, z]
    "semantic_label": "target_object"  // 语义标签
}
```

### 相机位置配置

```json
"camera_positioning": {
    "height_range": [1.5, 4.0],      // 目标上方的高度范围
    "radius_range": [0.8, 2.5],      // 与目标的水平距离范围
    "polar_angle_range": [0, 75]     // 极角范围（0=正上方，90=水平）
}
```

**重要参数说明：**
- `height_range`: 控制相机在目标上方的高度
- `radius_range`: 控制相机与目标中心的水平距离
- `polar_angle_range`: 控制相机的俯视角度
  - `0度` = 正上方俯视
  - `45度` = 45度角俯视
  - `75度` = 接近水平视角
  - `90度` = 完全水平（但仍在上方）

### 数据生成配置

```json
"data_generation": {
    "num_frames": 100,
    "output_directory": "./synthetic_data_output",
    "annotations": {
        "rgb": true,                    // RGB图像
        "bounding_box_2d_tight": true,  // 2D边界框
        "semantic_segmentation": true,  // 语义分割
        "instance_segmentation": true,  // 实例分割
        "depth": false,                 // 深度图
        "bounding_box_3d": false        // 3D边界框
    }
}
```

## 核心算法：相机位置计算

脚本使用球坐标系统确保相机始终位于目标上方：

```python
def get_random_camera_pose_above_target(target_position, height_range, radius_range, polar_angle_range):
    # 生成随机球坐标
    theta = random.uniform(0, 2 * π)              # 方位角（围绕Z轴）
    phi = random.uniform(polar_angle_range)       # 极角（从Z轴正方向）
    radius = random.uniform(radius_range)         # 半径
    height = random.uniform(height_range)         # 额外高度
    
    # 转换为笛卡尔坐标（确保在目标上方）
    x = target_x + radius * cos(theta) * sin(phi)
    y = target_y + radius * sin(theta) * sin(phi)
    z = target_z + height + radius * cos(phi)     # 始终为正值
    
    return (x, y, z)
```

## 使用您自己的资产

### 1. 替换资产路径

在配置文件中修改：

```json
"target_asset": {
    "usd_path": "/path/to/your/asset.usd",
    "position": [0, 0, 0],  // 调整为适合您资产的位置
    "semantic_label": "your_object_class"
}
```

### 2. 调整相机参数

根据您资产的大小调整相机位置参数：

```json
"camera_positioning": {
    "height_range": [2.0, 5.0],    // 大型资产需要更高的相机
    "radius_range": [1.0, 3.0],    // 大型资产需要更远的距离
    "polar_angle_range": [0, 60]   // 调整俯视角度
}
```

### 3. 示例：不同资产类型的配置

**小型物体（如产品、工具）：**
```json
"camera_positioning": {
    "height_range": [0.5, 1.5],
    "radius_range": [0.3, 1.0],
    "polar_angle_range": [0, 75]
}
```

**中型物体（如机器人、家具）：**
```json
"camera_positioning": {
    "height_range": [1.5, 4.0],
    "radius_range": [0.8, 2.5],
    "polar_angle_range": [0, 60]
}
```

**大型物体（如车辆、建筑）：**
```json
"camera_positioning": {
    "height_range": [3.0, 10.0],
    "radius_range": [2.0, 8.0],
    "polar_angle_range": [15, 75]
}
```

## 域随机化选项

### 光照随机化

```json
"lighting": {
    "enabled": true,
    "dome_intensity_range": [800, 1500],
    "dome_color_range": [[0.8, 0.8, 0.8], [1.0, 1.0, 1.0]],
    "randomize_interval": 5  // 每5帧随机化一次
}
```

### 材质随机化

```json
"materials": {
    "enabled": true,
    "metallic_range": [0.0, 1.0],
    "roughness_range": [0.0, 1.0],
    "diffuse_color_range": [[0.1, 0.1, 0.1], [0.9, 0.9, 0.9]],
    "randomize_interval": 10  // 每10帧随机化一次
}
```

## 输出数据格式

生成的数据将保存在指定的输出目录中，包含：

```
output_directory/
├── rgb/                    # RGB图像
├── bounding_box_2d_tight/ # 2D边界框标注
├── semantic_segmentation/ # 语义分割图像
├── instance_segmentation/ # 实例分割图像
└── metadata.json         # 元数据信息
```

## 性能优化建议

1. **使用无头模式**进行批量生成：
   ```bash
   python config_driven_camera_above_target.py --headless
   ```

2. **调整rt_subframes**平衡质量和速度：
   - `rt_subframes: 1` - 快速生成
   - `rt_subframes: 4` - 平衡质量
   - `rt_subframes: 8` - 高质量

3. **禁用不需要的标注**以提高速度

4. **使用适当的分辨率**：
   - 训练：512x512 或 640x640
   - 验证：1024x1024

## 故障排除

### 常见问题

1. **相机看不到目标**
   - 检查`polar_angle_range`是否太大
   - 确保`height_range`适合您的资产大小

2. **数据生成缓慢**
   - 减少`rt_subframes`
   - 禁用不必要的标注
   - 使用较低的分辨率

3. **资产未正确加载**
   - 验证USD文件路径是否正确
   - 检查资产是否在Isaac Sim资产库中

### 调试模式

运行时不使用`--headless`标志，可以实时查看相机位置和生成过程：

```bash
python config_driven_camera_above_target.py --config camera_above_target_config.json
```

## 扩展功能

### 添加多个相机

在配置中增加相机数量：

```json
"camera_properties": {
    "num_cameras": 3,  // 同时使用3个相机
    ...
}
```

### 添加背景环境

```json
"environment": {
    "background_environment": "/Isaac/Environments/Simple_Room/simple_room.usd"
}
```

### 自定义随机化

您可以在脚本中添加更多随机化选项，如：
- 目标资产的旋转
- 额外的干扰物体
- 动态光照变化
- 相机内参随机化

## 联系与支持

如果您在使用过程中遇到问题，请：

1. 检查Isaac Sim版本兼容性
2. 确认所有依赖已正确安装
3. 查看生成的日志文件
4. 尝试使用默认配置进行测试

这个解决方案为您提供了一个完整的、可配置的相机定位系统，确保在合成数据生成过程中相机始终位于目标资产上方。