# prolist 更新机制完整分析

## 关键发现

在 `js_files/index_dhp.js` 文件中找到了完整的 `prolist` 更新逻辑！

## 更新流程

### 1. 初始化调用链

```
页面加载 → playerlist() → cuqie() → 更新 #prolist
```

### 2. 核心函数

#### `playerlist()` (第78-124行)
**功能**: 获取视频专辑信息，确定专辑ID

**API调用**:
```javascript
//api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId?id={itemid1}&serviceId=tvcctv
```

**关键代码**:
```javascript
function playerlist(){
    var videojiid = GetQueryString("id");
    var listurl;
    if (videojiid == "" || videojiid == null || videojiid =="undefined"){
        listurl = "//api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId?id="+itemid1+"&serviceId=tvcctv";
        vbn = false;
    }else{
        listurl = "//api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId?id="+itemid1+"&serviceId=tvcctv&album_id="+videojiid+"";
        vbn = true;
    }
    $.ajax({
        type: "get",
        url: listurl,
        dataType:"jsonp",
        jsonp:"cb",
        cache:true,
        jsonpCallback:"Callback",
        success: function (data) {
            if(data.errcode == "1002"){
                changePlayer(0,"#prolist li");
            }else{
                dataOrder = data.data.order;  // 当前集数
                vida = data.data.id;          // 专辑ID
                codeid = data.data.id;
                cuqie(codeid);  // 调用获取剧集列表
            }
        }
    });
}
```

#### `cuqie(id)` (第146-227行)
**功能**: 获取剧集列表并更新 `#prolist`

**API调用**:
```javascript
//api.cntv.cn/NewVideo/getVideoStreamByAlbumId?id={id}&mode=1&sort=asc&n=100&serviceId=tvcctv&order={dataOrder-36}
```

**关键参数**:
- `id`: 专辑ID
- `mode=1`: 模式1（选集）
- `sort=asc`: 升序排列
- `n=100`: 获取100条
- `order={dataOrder-36}`: 从当前集数往前36集开始

**更新prolist的关键代码** (第189行):
```javascript
$("#prolist").html(liststr);
```

**完整逻辑**:
```javascript
function cuqie(id){
    var data1Array = new Array();
    next_id = id;
    
    $.ajax({
        type: "get",
        url: "//api.cntv.cn/NewVideo/getVideoStreamByAlbumId?id="+id+"&mode=1&sort=asc&n=100&serviceId=tvcctv&order="+(dataOrder-36),
        dataType:"jsonp",
        jsonp:"cb",
        cache:true,
        jsonpCallback:"Callback1",
        success: function (data) {
            var len = data.data.total;
            var data = data.data.list;
            
            // 构建HTML字符串
            var liststr = "";
            for (var i=0; i<data1Array.length; i++) {
                if (itemid1 == data1Array[i].id) {
                    // 当前播放的集，添加cur类
                    liststr += '<li class="swiper-slide cur"><div class="img"><a href="'+data1Array[i].url+'"><img src="'+data1Array[i].image+'"></a></div><div class="text"><a href="'+data1Array[i].url+'" title="'+data1Array[i].title+'">'+data1Array[i].title+'</a></div><div class="bf">'+lens2arr+'</div></li>';
                } else {
                    // 其他集
                    liststr += '<li class="swiper-slide"><div class="img"><a href="'+data1Array[i].url+'"><img src="'+data1Array[i].image+'"></a></div><div class="text"><a href="'+data1Array[i].url+'" title="'+data1Array[i].title+'">'+data1Array[i].title+'</a></div><div class="bf">'+lens2arr+'</div></li>';
                }
            }
            
            // 更新prolist元素
            $("#prolist").html(liststr);
            $("#playlist_sj").append(liststr);
            $("#bofangtanceng .jingxuanList ul").append(bofangtanchuang);
        }
    });
}
```

#### `jingqie(id)` (第238-331行)
**功能**: 获取"节目看点"列表并更新 `#prolist2`

**API调用**:
```javascript
//api.cntv.cn/NewVideo/getVideoStreamByAlbumId?id={id}&mode=0&sort=asc&n=50&serviceId=tvcctv&order={order-25}
```

**关键参数**:
- `mode=0`: 模式0（节目看点）
- `n=50`: 获取50条
- `order={order-25}`: 从当前集数往前25集开始

**更新prolist2的关键代码** (第284行):
```javascript
$("#prolist2").html(liststr1);
```

## API接口总结

### 1. 获取专辑信息
```
URL: //api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId
参数:
  - id: 视频ID (itemid1)
  - serviceId: tvcctv
  - album_id: (可选) 专辑ID
返回:
  - data.id: 专辑ID
  - data.order: 当前集数
  - data.title: 专辑标题
```

### 2. 获取剧集列表（选集）
```
URL: //api.cntv.cn/NewVideo/getVideoStreamByAlbumId
参数:
  - id: 专辑ID
  - mode: 1 (选集模式)
  - sort: asc (升序)
  - n: 100 (数量)
  - serviceId: tvcctv
  - order: 起始集数 (dataOrder-36)
返回:
  - data.list: 剧集列表数组
    - id: 视频ID
    - title: 标题
    - url: 链接
    - image: 缩略图
    - length: 时长
```

### 3. 获取节目看点列表
```
URL: //api.cntv.cn/NewVideo/getVideoStreamByAlbumId
参数:
  - id: 专辑ID
  - mode: 0 (看点模式)
  - sort: asc (升序)
  - n: 50 (数量)
  - serviceId: tvcctv
  - order: 起始集数 (order-25)
```

## 数据流

```
1. 页面加载
   ↓
2. playerlist() 被调用
   ↓
3. 调用 API: getVideoAlbumInfoByVideoId
   ↓
4. 获取专辑ID (vida) 和当前集数 (dataOrder)
   ↓
5. 调用 cuqie(vida)
   ↓
6. 调用 API: getVideoStreamByAlbumId (mode=1)
   ↓
7. 构建HTML字符串 (liststr)
   ↓
8. $("#prolist").html(liststr) 更新DOM
   ↓
9. 同时调用 jingqie(vida) 更新节目看点
   ↓
10. 调用 API: getVideoStreamByAlbumId (mode=0)
   ↓
11. $("#prolist2").html(liststr1) 更新DOM
```

## 关键变量

- `itemid1`: 当前视频ID (从HTML meta标签获取)
- `vida`: 专辑ID (从API获取)
- `dataOrder`: 当前集数 (从API获取)
- `liststr`: 选集HTML字符串
- `liststr1`: 节目看点HTML字符串

## 总结

`prolist` 的更新机制：
1. **触发**: 页面加载时自动调用 `playerlist()`
2. **数据源**: CCTV API (`api.cntv.cn`)
3. **更新方式**: 使用jQuery的 `.html()` 方法直接替换内容
4. **数据范围**: 从当前集数往前36集（选集）或25集（看点）
5. **更新位置**: 
   - `#prolist` - 选集列表
   - `#prolist2` - 节目看点列表
   - `#playlist_sj` - 播放列表（移动端）
   - `#bofangtanceng .jingxuanList ul` - 弹窗列表

