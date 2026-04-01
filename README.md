# 抢票系统 1.0

## 项目介绍
本项目是一个基于 FastAPI + Redis + Lua 的抢票系统 1.0 示例实现。
核心目标是用 Redis Lua 脚本保证扣减库存和记录用户行为的原子性，避免高并发场景下出现超卖和重复抢购。

## 项目目标
- 提供一个最小可运行的抢票接口 `POST /api/seckill`
- 使用 Redis 异步连接池统一管理连接生命周期
- 使用 Lua 脚本把“是否重复购买、是否有库存、扣库存、记录用户”放到 Redis 内部原子执行
- 提供库存预热脚本，便于手工测试和重复测试
- 提供并发压测脚本，快速验证秒杀逻辑是否符合预期

## 目录结构
```text
.
├─ app
│  ├─ main.py
│  └─ core
│     ├─ redis.py
│     └─ seckill_core.py
├─ scripts
│  ├─ preload_stock.py
│  ├─ test_lua.py
│  └─ test_concurrency.py
├─ main.py
└─ requirements.txt
```

## Redis Key 设计
以 `item_id = 1001` 为例：

- 库存 Key：`item_1001_stock`
- 已抢用户集合 Key：`item_1001_users`

说明：
- `item_{item_id}_stock` 用字符串存储库存数量
- `item_{item_id}_users` 用 Set 存储已经抢购成功的用户 ID

## Lua 返回值约定
秒杀 Lua 脚本位于 `app/core/seckill_core.py`，返回值约定如下：

- `1`：抢购成功
- `2`：不可重复购买
- `0`：库存不足

脚本逻辑：
1. 先判断 `user_id` 是否已在用户 Set 中
2. 再判断库存是否大于 0
3. 库存充足时执行 `DECR` 扣减库存，并执行 `SADD` 记录用户

## 环境准备
安装依赖：

```bash
pip install -r requirements.txt
pip install requests
```

说明：
- `requests` 用于运行并发压测脚本 `scripts/test_concurrency.py`
- 本项目默认连接本地 Redis：`127.0.0.1:6379`

## 怎么预热库存
先执行库存预热脚本：

```bash
python scripts/preload_stock.py
```

默认会做两件事：
- 将 `item_1001_stock` 设置为 `10`
- 清空 `item_1001_users`

预期输出示例：

```text
Preload completed.
item_id: 1001
stock_key: item_1001_stock, stock: 10
users_key: item_1001_users, users_count: 0
```

## 怎么启动接口
推荐启动方式：

```bash
python -m uvicorn app.main:app
```

启动后可访问：

- 根路由：`http://127.0.0.1:8000/`
- 秒杀接口：`http://127.0.0.1:8000/api/seckill`
- Swagger 文档：`http://127.0.0.1:8000/docs`

根路由预期返回：

```json
{"redis_ping": true}
```

## 秒杀接口请求示例
请求：

```http
POST /api/seckill
Content-Type: application/json
```

请求体：

```json
{
  "item_id": "1001",
  "user_id": "101"
}
```

可能返回：

```json
{"code": 1, "message": "抢购成功"}
```

```json
{"code": 2, "message": "不可重复购买"}
```

```json
{"code": 0, "message": "库存不足"}
```

## 怎么跑并发测试
### 1. 先预热库存
```bash
python scripts/preload_stock.py
```

### 2. 启动 FastAPI 服务
```bash
python -m uvicorn app.main:app
```

### 3. 新开一个终端运行并发测试脚本
```bash
python scripts/test_concurrency.py
```

测试脚本行为：
- 使用 `ThreadPoolExecutor` 开启 100 个线程
- 每个线程使用一个不同的 `user_id`
- 同时向 `http://127.0.0.1:8000/api/seckill` 发起 POST 请求
- 统计以下结果数量：
  - 抢购成功
  - 库存不足
  - 不可重复购买
  - 请求异常

## 手工 Lua 测试
可使用下面脚本做快速验证：

```bash
python scripts/test_lua.py
```

预期逻辑：
- 同一个用户第一次购买成功
- 同一个用户第二次返回不可重复购买
- 新用户在库存充足时仍可成功购买

## 本轮测试结果
测试日期：2026-04-02

### 1. 根路由检查
```json
{"redis_ping": true}
```

### 2. 手工 Lua 测试结果
```text
execute_seckill("1001", "101") -> 1
execute_seckill("1001", "101") -> 2
execute_seckill("1001", "102") -> 1
```

### 3. 100 线程并发测试结果
```text
抢购成功: 10
库存不足: 86
不可重复购买: 0
请求异常: 4
```

结果说明：
- 预热库存为 10，因此成功数为 10，符合预期
- 所有请求都使用不同 `user_id`，因此重复购买为 0，符合预期
- 剩余请求大部分返回库存不足，符合预期
- 本轮有 4 个请求异常，说明压测脚本或本地服务在高并发下仍有少量请求超时/失败现象，后续可继续优化超时参数、服务启动方式或压测方式

## 后续可优化方向
- 将 `requests` 并发压测升级为更专业的压测工具，如 Locust、wrk、JMeter
- 为接口增加统一异常处理和日志记录
- 增加接口鉴权、用户限流、活动时间校验等业务逻辑
- 将商品信息、订单记录等扩展为更完整的业务模型
