#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bilibili合集URL提取脚本
功能：只提取视频URL列表，不下载视频
"""

import re
import requests
import os
import json
from urllib.parse import urlparse

class BilibiliURLExtractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def extract_collection_id(self, url):
        """从URL中提取合集ID"""
        match = re.search(r'/lists/(\d+)', url)
        if match:
            return match.group(1)
        return None
    
    def extract_video_urls_from_api(self, collection_id, mid=None):
        """从API获取视频列表"""
        video_urls = []
        video_info_list = []
        
        api_url = "https://api.bilibili.com/x/polymer/web-space/seasons_archives_list"
        page = 1
        page_size = 50
        
        while True:
            params = {
                'mid': mid or '',
                'season_id': collection_id,
                'sort_reverse': 'false',
                'page_num': page,
                'page_size': page_size
            }
            
            try:
                response = self.session.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get('code') == 0 and 'data' in data:
                    data_obj = data['data']
                    
                    archives = []
                    if 'archives' in data_obj:
                        archives = data_obj['archives']
                    elif 'list' in data_obj:
                        archives = data_obj['list']
                    elif 'vlist' in data_obj:
                        archives = data_obj['vlist']
                    
                    if not archives:
                        if isinstance(data_obj, list):
                            archives = data_obj
                        else:
                            break
                    
                    print(f"  第{page}页: 获取到 {len(archives)} 个视频")
                    
                    for archive in archives:
                        bvid = archive.get('bvid', '')
                        aid = archive.get('aid', '')
                        title = archive.get('title', '未知标题')
                        
                        if bvid:
                            url = f"https://www.bilibili.com/video/{bvid}"
                            video_urls.append(url)
                            video_info_list.append({
                                'url': url,
                                'title': title,
                                'bvid': bvid,
                                'aid': aid
                            })
                        elif aid:
                            url = f"https://www.bilibili.com/video/av{aid}"
                            video_urls.append(url)
                            video_info_list.append({
                                'url': url,
                                'title': title,
                                'bvid': '',
                                'aid': aid
                            })
                    
                    # 获取总数，可能在data_obj或data中
                    total = data_obj.get('total', data.get('data', {}).get('total', 0))
                    if total == 0:
                        total = data.get('total', 0)
                    
                    print(f"  当前总数: {len(video_urls)}, API返回总数: {total}")
                    
                    # 如果当前页返回的视频数少于page_size，说明已经是最后一页
                    # 或者已经获取的数量达到或超过总数
                    if len(archives) < page_size:
                        print(f"  已获取所有页面（当前页视频数 {len(archives)} < 每页大小 {page_size}）")
                        break
                    
                    if total > 0 and len(video_urls) >= total:
                        print(f"  已获取所有视频（{len(video_urls)} >= {total}）")
                        break
                    
                    page += 1
                else:
                    error_msg = data.get('message', '未知错误')
                    print(f"  API返回错误: code={data.get('code')}, message={error_msg}")
                    break
            except Exception as e:
                print(f"获取第{page}页失败: {e}")
                break
        
        return video_urls, video_info_list
    
    def extract_urls(self, collection_url, output_file=None):
        """提取视频URL列表"""
        print(f"开始处理合集URL: {collection_url}")
        print("=" * 60)
        
        # 提取合集ID和用户ID
        collection_id = self.extract_collection_id(collection_url)
        if not collection_id:
            print("无法提取合集ID")
            return None, None
        
        mid_match = re.search(r'/space\.bilibili\.com/(\d+)', collection_url)
        mid = mid_match.group(1) if mid_match else None
        
        print(f"合集ID: {collection_id}")
        if mid:
            print(f"用户ID: {mid}")
        
        # 从API获取视频列表
        print("\n正在获取视频列表...")
        video_urls, video_info_list = self.extract_video_urls_from_api(collection_id, mid)
        
        if not video_urls:
            print("无法获取视频列表")
            return None, None
        
        print(f"找到 {len(video_urls)} 个视频\n")
        
        # 显示视频列表
        for i, info in enumerate(video_info_list, 1):
            title = info.get('title', '')
            url = info.get('url', '')
            print(f"{i:3d}. {title}")
            print(f"     {url}")
        
        # 保存到文件
        if output_file is None:
            output_file = f"bilibili_urls_{collection_id}.txt"
        
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Bilibili合集视频URL列表\n")
            f.write(f"合集URL: {collection_url}\n")
            f.write(f"合集ID: {collection_id}\n")
            f.write(f"视频数量: {len(video_urls)}\n")
            f.write(f"{'='*60}\n\n")
            
            for i, info in enumerate(video_info_list, 1):
                title = info.get('title', '')
                url = info.get('url', '')
                f.write(f"{i}. {title}\n")
                f.write(f"   {url}\n\n")
        
        print(f"\n{'='*60}")
        print(f"URL列表已保存到: {output_path}")
        print(f"{'='*60}")
        
        return video_urls, video_info_list


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python extract_bilibili_urls.py <bilibili合集URL> [输出文件]")
        print("\n示例:")
        print("  python extract_bilibili_urls.py https://space.bilibili.com/4520265/lists/3308869?type=season")
        sys.exit(1)
    
    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    extractor = BilibiliURLExtractor()
    extractor.extract_urls(url, output_file)


if __name__ == "__main__":
    main()
