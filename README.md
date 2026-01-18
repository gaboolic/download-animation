# Bilibili合集下载工具

## 功能

1. **提取视频URL列表** - 从bilibili合集页面提取所有视频的URL
2. **下载视频** - 使用yt-dlp下载bilibili视频

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 只提取视频URL列表（不下载）

```bash
python extract_bilibili_urls.py <bilibili合集URL> [输出文件]
```

示例：
```bash
python extract_bilibili_urls.py https://space.bilibili.com/4520265/lists/3308869?type=season
```

这会：
- 从API获取合集中的所有视频
- 显示视频列表（标题和URL）
- 将URL列表保存到文本文件

### 2. 下载合集中的所有视频

```bash
python download_bilibili_collection.py <bilibili合集URL> [输出目录]
```

示例：
```bash
python download_bilibili_collection.py https://space.bilibili.com/4520265/lists/3308869?type=season
```

这会：
- 提取所有视频URL
- 使用yt-dlp下载每个视频到指定目录

**注意**：下载功能需要安装 `yt-dlp`：
```bash
pip install yt-dlp
```

## 其他工具

### CCTV视频下载

```bash
python download_episodes_m3u8.py <CCTV视频页面URL> [输出目录]
```