# 抢票系统 1.0

## 项目介绍
这是一个基于 FastAPI、Redis、Lua 和 MySQL 的抢票系统 1.0 示例项目。
项目聚焦于秒杀场景下最关键的两件事：一是通过 Redis Lua 保证库存扣减与重复购买判断的原子性，二是通过 Redis 队列 + MySQL 消费者把订单异步落库，形成一条清晰的下单链路。

当前版本已经具备：
- 秒杀接口
- Redis 异步连接池
- Lua 原子扣减库存
- Redis List 订单消息队列
- MySQL 订单表模型
- 订单消费者
- 基础幂等处理
- 库存预热脚本与并发压测脚本

## 项目目标
- 提供一个最小可运行的抢票接口 `POST /api/seckill`
- 使用 Redis 异步连接池统一管理连接生命周期
- 使用 Lua 脚本把“是否重复购买、是否有库存、扣库存、记录用户”放到 Redis 内部原子执行
- 在秒杀成功后生成订单消息，写入 Redis List 队列
- 使用 SQLAlchemy + PyMySQL 定义 MySQL 订单表模型
- 提供基础订单消费者，将队列消息异步写入 MySQL
- 为消费者加入基础幂等处理，避免重复订单导致消费者崩溃
- 提供订单查询接口，验证消费者落库结果
- 提供库存预热脚本、手工测试脚本和并发压测脚本

## 目录结构
```text
.
├─ app
│  ├─ main.py
│  ├─ core
│  │  ├─ db.py
│  │  ├─ redis.py
│  │  └─ seckill_core.py
│  ├─ model
│  │  └─ order.py
│  ├─ schema
│  │  └─ order_message.py
│  └─ service
│     └─ queue_service.py
├─ scripts
│  ├─ preload_stock.py
│  ├─ test_lua.py
│  ├─ test_concurrency.py
│  └─ order_consumer.py
├─ main.py
├─ requirements.txt
└─ README.md
```

## Redis Key 设计
以 `item_id = 1001` 为例：

- 库存 Key：`item_1001_stock`
- 已抢用户集合 Key：`item_1001_users`
- 订单消息队列 Key：`seckill:order_queue`

说明：
- `item_{item_id}_stock` 使用字符串存储库存数量
- `item_{item_id}_users` 使用 Set 存储已抢购成功的用户 ID
- `seckill:order_queue` 使用 Redis List 作为简单消息队列，保存待落库订单消息

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
- 本项目默认 MySQL 连接串定义在 `app/core/db.py`

默认 MySQL URL：

```text
mysql+pymysql://root:123456@127.0.0.1:3306/seckill_system?charset=utf8mb4
```

建议先在本地 MySQL 中创建数据库：

```sql
CREATE DATABASE seckill_system DEFAULT CHARACTER SET utf8mb4;
```

如需修改连接串，可在启动前设置环境变量：

```bash
set MYSQL_URL=mysql+pymysql://用户名:密码@127.0.0.1:3306/seckill_system?charset=utf8mb4
```

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
- 订单查询接口：`http://127.0.0.1:8000/api/orders/{order_no}`
- Swagger 文档：`http://127.0.0.1:8000/docs`

根路由预期返回：

```json
{"redis_ping": true}
```

如果希望把订单真正落到 MySQL，还需要再启动消费者：

```bash
python scripts/order_consumer.py
```

说明：
- API 服务负责秒杀判断和订单消息入队
- 消费者负责从 Redis 队列读取消息并写入 MySQL
- `scripts/order_consumer.py` 启动时会自动执行 `Base.metadata.create_all(bind=engine)` 建表

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
{"code": 1, "message": "抢购成功，排队中"}
```

```json
{"code": 2, "message": "不可重复购买"}
```

```json
{"code": 0, "message": "库存不足"}
```

成功链路说明：
1. Redis Lua 脚本先完成库存扣减和重复购买判断
2. 如果秒杀成功，接口生成订单消息
3. 订单消息包含 `order_no`、`item_id`、`user_id`、`create_time`
4. 接口调用 `push_order_message()` 将消息写入 Redis List
5. 消费者从队列读取消息并落库到 MySQL `orders` 表

## 订单查询接口示例
请求：

```http
GET /api/orders/{order_no}
```

订单存在时返回：

```json
{
  "code": 1,
  "message": "查询成功",
  "data": {
    "id": 1,
    "order_no": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "user_id": "101",
    "item_id": "1001",
    "status": "CREATED",
    "create_time": "2026-04-02T10:00:00"
  }
}
```

订单不存在时返回：

```json
{"code": 0, "message": "订单不存在"}
```

说明：
- 该接口用于验证消费者是否已经把订单成功写入 MySQL
- 当前接口按 `order_no` 查询订单

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

### 4. 如果要验证订单落库，再启动消费者
```bash
python scripts/order_consumer.py
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

### 1. Redis 秒杀链路验证
```text
python scripts/preload_stock.py
Preload completed.
item_id: 1001
stock_key: item_1001_stock, stock: 10
users_key: item_1001_users, users_count: 0
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

### 4. 新增 MySQL 与队列模块校验结果
```text
python -m py_compile app\main.py app\core\redis.py app\core\seckill_core.py app\core\db.py app\model\order.py app\schema\order_message.py app\service\queue_service.py scripts\preload_stock.py scripts\test_lua.py scripts\test_concurrency.py scripts\order_consumer.py
通过

python -c "import app.main, app.core.db, app.model.order, app.schema.order_message, app.service.queue_service; print('import ok')"
import ok
```

结果说明：
- Redis 秒杀主链路已经验证通过
- 秒杀成功数与预热库存一致，符合预期
- 所有并发请求都使用不同 `user_id`，因此重复购买为 0，符合预期
- 本轮新增的 MySQL、订单消息、队列服务、消费者脚本已完成语法与导入校验
- 订单查询接口已补齐，但使用前需保证本地 MySQL 服务、数据库和消费者均已正常运行

## 后续可优化方向
- 将 `requests` 并发压测升级为更专业的压测工具，如 Locust、wrk、JMeter
- 将订单消息改造为更完整的生产者-消费者模型，例如增加重试、死信队列、消费确认
- 为接口增加统一异常处理和日志记录
- 增加接口鉴权、用户限流、活动时间校验等业务逻辑
- 为 MySQL 写入增加更明确的状态流转和订单查询列表接口
- 将消费者改造成支持优雅退出和更完善的幂等策略
