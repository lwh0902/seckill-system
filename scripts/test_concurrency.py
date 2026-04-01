import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

URL = "http://127.0.0.1:8000/api/seckill"
TOTAL_USERS = 100


def send_request(user_id: str) -> str:
    payload = {
        "item_id": "1001",
        "user_id": user_id,
    }

    try:
        response = requests.post(URL, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return "请求异常"

    return data.get("message", "请求异常")


def main() -> None:
    counter = Counter()

    with ThreadPoolExecutor(max_workers=TOTAL_USERS) as executor:
        futures = [
            executor.submit(send_request, f"user_{index:03d}")
            for index in range(1, TOTAL_USERS + 1)
        ]

        for future in as_completed(futures):
            counter[future.result()] += 1

    print(f"抢购成功: {counter['抢购成功']}")
    print(f"库存不足: {counter['库存不足']}")
    print(f"不可重复购买: {counter['不可重复购买']}")
    print(f"请求异常: {counter['请求异常']}")


if __name__ == "__main__":
    main()
