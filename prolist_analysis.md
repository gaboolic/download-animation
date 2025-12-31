# prolist 剧集列表更新机制分析

## HTML结构

在HTML源代码中，`prolist` 元素定义在第465行：

```html
<ul id="prolist">
    <!-- 初始为空，通过JavaScript动态填充 -->
</ul>
```

还有一个相关的 `prolist2` 元素（第477行），用于"节目看点"部分。

## 关键变量

### 1. 视频代码变量（第203行）
```javascript
var videotvCodes="VIDA1364349622430611:VIDADgeYZRj236dH9iXNIFHp251217";
```

### 2. 专辑ID提取（第209-211行）
```javascript
var videoalbumId="";
videoalbumId = videotvCodes.split(":")[0];  // 提取第一个视频ID作为专辑ID
// 结果: videoalbumId = "VIDA1364349622430611"
```

### 3. 其他相关变量
- `itemid1`: "VIDE2bG5I0c3AD1EQvX1pxjF251206" (当前视频ID)
- `guid`: "45903e81066841988f0a0d9bba8c525b" (视频GUID)
- `column_id`: "TOPC1460958044779267" (专题ID)
- `sub_column_id`: "PAGEUSm6N7GS6YBptzUMYGK9160421" (页面ID)

## 外部JavaScript文件

负责更新 `prolist` 的脚本很可能在以下外部文件中：

1. **ptjszx_player.js** (第389行)
   - 路径: `//r.img.cctvpic.com/photoAlbum/templet/common/DEPA1666850857533581/ptjszx_player.js`
   - 可能是播放器相关脚本

2. **tv_jlp_tb.videcreat.js** (第391行)
   - 路径: `//r.img.cctvpic.com/photoAlbum/templet/common/DEPA1666850857533581/tv_jlp_tb.videcreat.js`
   - 这个文件名包含"videcreat"，很可能是创建视频列表的脚本

## 可能的更新机制

基于HTML中的其他AJAX调用模式（如热播榜更新），`prolist` 很可能通过以下方式更新：

### 方式1: 通过专辑ID获取剧集列表
```javascript
// 可能的API调用（推测）
$.ajax({
    url: "//api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId",
    data: {
        id: videoalbumId,  // 或 itemid1
        serviceId: "tvcctv"
    },
    dataType: "jsonp",
    success: function(data) {
        // 更新 prolist
        var html = "";
        for(var i = 0; i < data.list.length; i++) {
            html += '<li><a href="' + data.list[i].url + '">' + data.list[i].title + '</a></li>';
        }
        $("#prolist").html(html);
    }
});
```

### 方式2: 通过视频GUID获取相关剧集
```javascript
// 可能的API调用（推测）
$.ajax({
    url: "//api.cntv.cn/video/videoinfoByGuid",
    data: {
        guid: guid,
        serviceId: "tvcctv"
    },
    dataType: "jsonp",
    success: function(data) {
        // 处理数据并更新 prolist
    }
});
```

## 实际观察到的API调用模式

在HTML中可以看到类似的API调用：

1. **获取热播榜** (第498-554行)
   ```javascript
   $.ajax({
       url: "https://api.cntv.cn/List/getHandDataList?id=TDAT1628674905327288&serviceId=tvcctv&n=10",
       dataType: "jsonp",
       success: function(data) {
           var datalist = data.data.itemList;
           var html = "";
           for(var i = 0; i < datalist.length; i++) {
               html += '<li>...</li>';
           }
           $("#bangdan").html(html);
       }
   });
   ```

2. **获取视频专辑信息** (第1501-1529行)
   ```javascript
   $.ajax({
       url: '//api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId?id='+idid+'&serviceId='+serviceId1+'',
       dataType: "jsonp",
       success: function (data) {
           // 处理专辑数据
       }
   });
   ```

## 结论

`prolist` 的更新机制很可能：
1. 在页面加载时，通过外部JavaScript文件（特别是 `tv_jlp_tb.videcreat.js`）执行
2. 使用 `videoalbumId` 或 `itemid1` 作为参数
3. 调用CCTV的API接口获取剧集列表数据
4. 使用jQuery的 `.html()` 方法动态填充 `#prolist` 元素

要确认具体的更新逻辑，需要查看外部JavaScript文件的内容，或者通过浏览器开发者工具的网络请求面板观察实际的API调用。

## 已下载的JavaScript文件分析

### 1. tv_jlp_tb.videcreat.js
- **文件大小**: 2709 字节
- **主要功能**: 播放器切换和全屏控制
- **关键函数**:
  - `changePlayer(index, obj)`: 切换播放器
  - `NextVideo()`: 播放下一集
- **结论**: 此文件主要负责播放器控制，**不包含更新prolist的逻辑**

### 2. ptjszx_player.js
- **文件大小**: 6249 字节
- **主要功能**: 播放器初始化和参数配置
- **关键函数**:
  - `newplayer()`: 创建新播放器
  - 配置播放器参数（宽度、高度、是否自动播放等）
- **结论**: 此文件主要负责播放器初始化，**不包含更新prolist的逻辑**

## 进一步分析建议

由于已下载的两个JavaScript文件都不包含更新prolist的代码，`prolist`的更新可能通过以下方式之一：

1. **其他外部JavaScript文件**: HTML中可能引用了其他未下载的脚本文件
2. **内联脚本**: 可能在HTML的其他部分有内联JavaScript代码（需要完整查看HTML）
3. **动态加载**: 可能通过动态加载的脚本文件来更新
4. **API调用**: 可能直接通过AJAX调用API，然后更新prolist

**建议**: 使用浏览器开发者工具（F12）：
- 查看"网络"（Network）面板，筛选XHR/Fetch请求
- 查找与剧集列表相关的API调用
- 查看"元素"（Elements）面板，观察prolist元素的变化
- 查看"源代码"（Sources）面板，查找所有加载的JavaScript文件

