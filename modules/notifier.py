# coding=utf-8

import json
import time
from typing import Dict, List, Tuple, Optional
import requests

from .config import load_config, VERSION
from .utils import get_beijing_time
from .report_generator import (
    render_feishu_content,
    render_dingtalk_content,
    format_title_for_platform,
    prepare_report_data
)
from .push_record import PushRecordManager


# 加载配置
CONFIG = load_config()


def split_content_into_batches(
    report_data: Dict,
    format_type: str,
    update_info: Optional[Dict] = None,
    max_bytes: int = CONFIG["MESSAGE_BATCH_SIZE"],
    mode: str = "daily",
) -> List[str]:
    """分批处理消息内容，确保词组标题+至少第一条新闻的完整性"""
    batches = []

    total_titles = sum(
        len(stat["titles"]) for stat in report_data["stats"] if stat["count"] > 0
    )
    now = get_beijing_time()

    base_header = ""
    if format_type == "wework":
        base_header = f"**总新闻数：** {total_titles}\n\n\n\n"
    elif format_type == "telegram":
        base_header = f"总新闻数： {total_titles}\n\n"

    base_footer = ""
    if format_type == "wework":
        base_footer = f"\n\n\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\n> TrendRadar 发现新版本 **{update_info['remote_version']}**，当前 **{update_info['current_version']}**"
    elif format_type == "telegram":
        base_footer = f"\n\n更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\nTrendRadar 发现新版本 {update_info['remote_version']}，当前 {update_info['current_version']}"

    stats_header = ""
    if report_data["stats"]:
        if format_type == "wework":
            stats_header = f"📊 **热点词汇统计**\n\n"
        elif format_type == "telegram":
            stats_header = f"📊 热点词汇统计\n\n"

    current_batch = base_header
    current_batch_has_content = False

    if (
        not report_data["stats"]
        and not report_data["new_titles"]
        and not report_data["failed_ids"]
    ):
        if mode == "incremental":
            mode_text = "增量模式下暂无新增匹配的热点词汇"
        elif mode == "current":
            mode_text = "当前榜单模式下暂无匹配的热点词汇"
        else:
            mode_text = "暂无匹配的热点词汇"
        simple_content = f"📭 {mode_text}\n\n"
        final_content = base_header + simple_content + base_footer
        batches.append(final_content)
        return batches

    # 处理热点词汇统计
    if report_data["stats"]:
        total_count = len(report_data["stats"])

        # 添加统计标题
        test_content = current_batch + stats_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            < max_bytes
        ):
            current_batch = test_content
            current_batch_has_content = True
        else:
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + stats_header
            current_batch_has_content = True

        # 逐个处理词组（确保词组标题+第一条新闻的原子性）
        for i, stat in enumerate(report_data["stats"]):
            word = stat["word"]
            count = stat["count"]
            sequence_display = f"[{i + 1}/{total_count}]"

            # 构建词组标题
            word_header = ""
            if format_type == "wework":
                if count >= 10:
                    word_header = (
                        f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                elif count >= 5:
                    word_header = (
                        f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                else:
                    word_header = f"📌 {sequence_display} **{word}** : {count} 条\n\n"
            elif format_type == "telegram":
                if count >= 10:
                    word_header = f"🔥 {sequence_display} {word} : {count} 条\n\n"
                elif count >= 5:
                    word_header = f"📈 {sequence_display} {word} : {count} 条\n\n"
                else:
                    word_header = f"📌 {sequence_display} {word} : {count} 条\n\n"

            # 构建第一条新闻
            first_news_line = ""
            if stat["titles"]:
                first_title_data = stat["titles"][0]
                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", first_title_data, show_source=True
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", first_title_data, show_source=True
                    )
                else:
                    formatted_title = f"{first_title_data['title']}"

                first_news_line = f"  1. {formatted_title}\n"
                if len(stat["titles"]) > 1:
                    first_news_line += "\n"

            # 原子性检查：词组标题+第一条新闻必须一起处理
            word_with_first_news = word_header + first_news_line
            test_content = current_batch + word_with_first_news

            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                # 当前批次容纳不下，开启新批次
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + stats_header + word_with_first_news
                current_batch_has_content = True
                start_index = 1
            else:
                current_batch = test_content
                current_batch_has_content = True
                start_index = 1

            # 处理剩余新闻条目
            for j in range(start_index, len(stat["titles"])):
                title_data = stat["titles"][j]
                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", title_data, show_source=True
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data, show_source=True
                    )
                else:
                    formatted_title = f"{title_data['title']}"

                news_line = f"  {j + 1}. {formatted_title}\n"
                if j < len(stat["titles"]) - 1:
                    news_line += "\n"

                test_content = current_batch + news_line
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    >= max_bytes
                ):
                    if current_batch_has_content:
                        batches.append(current_batch + base_footer)
                    current_batch = base_header + stats_header + word_header + news_line
                    current_batch_has_content = True
                else:
                    current_batch = test_content
                    current_batch_has_content = True

            # 词组间分隔符
            if i < len(report_data["stats"]) - 1:
                separator = ""
                if format_type == "wework":
                    separator = f"\n\n\n\n"
                elif format_type == "telegram":
                    separator = f"\n\n"

                test_content = current_batch + separator
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    < max_bytes
                ):
                    current_batch = test_content

    # 处理新增新闻（同样确保来源标题+第一条新闻的原子性）
    if report_data["new_titles"]:
        new_header = ""
        if format_type == "wework":
            new_header = f"\n\n\n\n🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
        elif format_type == "telegram":
            new_header = (
                f"\n\n🆕 本次新增热点新闻 (共 {report_data['total_new_count']} 条)\n\n"
            )

        test_content = current_batch + new_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            >= max_bytes
        ):
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + new_header
            current_batch_has_content = True
        else:
            current_batch = test_content
            current_batch_has_content = True

        # 逐个处理新增新闻来源
        for source_data in report_data["new_titles"]:
            source_header = ""
            if format_type == "wework":
                source_header = f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"
            elif format_type == "telegram":
                source_header = f"{source_data['source_name']} ({len(source_data['titles'])} 条):\n\n"

            # 构建第一条新增新闻
            first_news_line = ""
            if source_data["titles"]:
                first_title_data = source_data["titles"][0]
                title_data_copy = first_title_data.copy()
                title_data_copy["is_new"] = False

                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", title_data_copy, show_source=False
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data_copy, show_source=False
                    )
                else:
                    formatted_title = f"{title_data_copy['title']}"

                first_news_line = f"  1. {formatted_title}\n"

            # 原子性检查：来源标题+第一条新闻
            source_with_first_news = source_header + first_news_line
            test_content = current_batch + source_with_first_news

            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + new_header + source_with_first_news
                current_batch_has_content = True
                start_index = 1
            else:
                current_batch = test_content
                current_batch_has_content = True
                start_index = 1

            # 处理剩余新增新闻
            for j in range(start_index, len(source_data["titles"])):
                title_data = source_data["titles"][j]
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False

                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", title_data_copy, show_source=False
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data_copy, show_source=False
                    )
                else:
                    formatted_title = f"{title_data_copy['title']}"

                news_line = f"  {j + 1}. {formatted_title}\n"

                test_content = current_batch + news_line
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    >= max_bytes
                ):
                    if current_batch_has_content:
                        batches.append(current_batch + base_footer)
                    current_batch = base_header + new_header + source_header + news_line
                    current_batch_has_content = True
                else:
                    current_batch = test_content
                    current_batch_has_content = True

            current_batch += "\n"

    if report_data["failed_ids"]:
        failed_header = ""
        if format_type == "wework":
            failed_header = f"\n\n\n\n⚠️ **数据获取失败的平台：**\n\n"
        elif format_type == "telegram":
            failed_header = f"\n\n⚠️ 数据获取失败的平台：\n\n"

        test_content = current_batch + failed_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            >= max_bytes
        ):
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + failed_header
            current_batch_has_content = True
        else:
            current_batch = test_content
            current_batch_has_content = True

        for i, id_value in enumerate(report_data["failed_ids"], 1):
            failed_line = f"  • {id_value}\n"
            test_content = current_batch + failed_line
            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + failed_header + failed_line
                current_batch_has_content = True
            else:
                current_batch = test_content
                current_batch_has_content = True

    # 完成最后批次
    if current_batch_has_content:
        batches.append(current_batch + base_footer)

    return batches


def send_to_webhooks(
    stats: List[Dict],
    failed_ids: Optional[List] = None,
    report_type: str = "当日汇总",
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> Dict[str, bool]:
    """发送数据到多个webhook平台"""
    results = {}

    if CONFIG["SILENT_PUSH"]["ENABLED"]:
        push_manager = PushRecordManager()
        time_range_start = CONFIG["SILENT_PUSH"]["TIME_RANGE"]["START"]
        time_range_end = CONFIG["SILENT_PUSH"]["TIME_RANGE"]["END"]
        
        if not push_manager.is_in_time_range(time_range_start, time_range_end):
            now = get_beijing_time()
            print(f"静默模式：当前时间 {now.strftime('%H:%M')} 不在推送时间范围 {time_range_start}-{time_range_end} 内，跳过推送")
            return results
        
        if CONFIG["SILENT_PUSH"]["ONCE_PER_DAY"]:
            if push_manager.has_pushed_today():
                print(f"静默模式：今天已推送过，跳过本次推送")
                return results
            else:
                print(f"静默模式：今天首次推送")
    
    report_data = prepare_report_data(stats, failed_ids, new_titles, id_to_name, mode)

    feishu_url = CONFIG["FEISHU_WEBHOOK_URL"]
    dingtalk_url = CONFIG["DINGTALK_WEBHOOK_URL"]
    wework_url = CONFIG["WEWORK_WEBHOOK_URL"]
    telegram_token = CONFIG["TELEGRAM_BOT_TOKEN"]
    telegram_chat_id = CONFIG["TELEGRAM_CHAT_ID"]

    update_info_to_send = update_info if CONFIG["SHOW_VERSION_UPDATE"] else None

    # 发送到飞书
    if feishu_url:
        results["feishu"] = send_to_feishu(
            feishu_url, report_data, report_type, update_info_to_send, proxy_url, mode
        )

    # 发送到钉钉
    if dingtalk_url:
        results["dingtalk"] = send_to_dingtalk(
            dingtalk_url, report_data, report_type, update_info_to_send, proxy_url, mode
        )

    # 发送到企业微信
    if wework_url:
        results["wework"] = send_to_wework(
            wework_url, report_data, report_type, update_info_to_send, proxy_url, mode
        )

    # 发送到 Telegram
    if telegram_token and telegram_chat_id:
        results["telegram"] = send_to_telegram(
            telegram_token,
            telegram_chat_id,
            report_data,
            report_type,
            update_info_to_send,
            proxy_url,
            mode,
        )

    if not results:
        print("未配置任何webhook URL，跳过通知发送")

    # 如果成功发送了任何通知，且启用了每天只推一次，则记录推送
    if CONFIG["SILENT_PUSH"]["ENABLED"] and CONFIG["SILENT_PUSH"]["ONCE_PER_DAY"] and any(results.values()):
        push_manager = PushRecordManager()
        push_manager.record_push(report_type)
        
    return results


def send_to_feishu(
    webhook_url: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """发送到飞书"""
    headers = {"Content-Type": "application/json"}

    text_content = render_feishu_content(report_data, update_info, mode)
    total_titles = sum(
        len(stat["titles"]) for stat in report_data["stats"] if stat["count"] > 0
    )

    now = get_beijing_time()
    payload = {
        "msg_type": "text",
        "content": {
            "total_titles": total_titles,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "report_type": report_type,
            "text": text_content,
        },
    }

    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    try:
        response = requests.post(
            webhook_url, headers=headers, json=payload, proxies=proxies, timeout=30
        )
        if response.status_code == 200:
            print(f"飞书通知发送成功 [{report_type}]")
            return True
        else:
            print(f"飞书通知发送失败 [{report_type}]，状态码：{response.status_code}")
            return False
    except Exception as e:
        print(f"飞书通知发送出错 [{report_type}]：{e}")
        return False


def send_to_dingtalk(
    webhook_url: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """发送到钉钉"""
    headers = {"Content-Type": "application/json"}

    text_content = render_dingtalk_content(report_data, update_info, mode)

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"TrendRadar 热点分析报告 - {report_type}",
            "text": text_content,
        },
    }

    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    try:
        response = requests.post(
            webhook_url, headers=headers, json=payload, proxies=proxies, timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("errcode") == 0:
                print(f"钉钉通知发送成功 [{report_type}]")
                return True
            else:
                print(f"钉钉通知发送失败 [{report_type}]，错误：{result.get('errmsg')}")
                return False
        else:
            print(f"钉钉通知发送失败 [{report_type}]，状态码：{response.status_code}")
            return False
    except Exception as e:
        print(f"钉钉通知发送出错 [{report_type}]：{e}")
        return False


def send_to_wework(
    webhook_url: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """发送到企业微信（支持分批发送）"""
    headers = {"Content-Type": "application/json"}
    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    # 获取分批内容
    batches = split_content_into_batches(report_data, "wework", update_info, mode=mode)

    print(f"企业微信消息分为 {len(batches)} 批次发送 [{report_type}]")

    # 逐批发送
    for i, batch_content in enumerate(batches, 1):
        batch_size = len(batch_content.encode("utf-8"))
        print(
            f"发送企业微信第 {i}/{len(batches)} 批次，大小：{batch_size} 字节 [{report_type}]"
        )

        # 添加批次标识
        if len(batches) > 1:
            batch_header = f"**[第 {i}/{len(batches)} 批次]**\n\n"
            batch_content = batch_header + batch_content

        payload = {"msgtype": "markdown", "markdown": {"content": batch_content}}

        try:
            response = requests.post(
                webhook_url, headers=headers, json=payload, proxies=proxies, timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    print(f"企业微信第 {i}/{len(batches)} 批次发送成功 [{report_type}]")
                    # 批次间间隔
                    if i < len(batches):
                        time.sleep(CONFIG["BATCH_SEND_INTERVAL"])
                else:
                    print(
                        f"企业微信第 {i}/{len(batches)} 批次发送失败 [{report_type}]，错误：{result.get('errmsg')}"
                    )
                    return False
            else:
                print(
                    f"企业微信第 {i}/{len(batches)} 批次发送失败 [{report_type}]，状态码：{response.status_code}"
                )
                return False
        except Exception as e:
            print(f"企业微信第 {i}/{len(batches)} 批次发送出错 [{report_type}]：{e}")
            return False

    print(f"企业微信所有 {len(batches)} 批次发送完成 [{report_type}]")
    return True


def send_to_telegram(
    bot_token: str,
    chat_id: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
) -> bool:
    """发送到Telegram（支持分批发送）"""
    headers = {"Content-Type": "application/json"}
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    # 获取分批内容
    batches = split_content_into_batches(
        report_data, "telegram", update_info, mode=mode
    )

    print(f"Telegram消息分为 {len(batches)} 批次发送 [{report_type}]")

    # 逐批发送
    for i, batch_content in enumerate(batches, 1):
        batch_size = len(batch_content.encode("utf-8"))
        print(
            f"发送Telegram第 {i}/{len(batches)} 批次，大小：{batch_size} 字节 [{report_type}]"
        )

        # 添加批次标识
        if len(batches) > 1:
            batch_header = f"<b>[第 {i}/{len(batches)} 批次]</b>\n\n"
            batch_content = batch_header + batch_content

        payload = {
            "chat_id": chat_id,
            "text": batch_content,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(
                url, headers=headers, json=payload, proxies=proxies, timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f"Telegram第 {i}/{len(batches)} 批次发送成功 [{report_type}]")
                    # 批次间间隔
                    if i < len(batches):
                        time.sleep(CONFIG["BATCH_SEND_INTERVAL"])
                else:
                    print(
                        f"Telegram第 {i}/{len(batches)} 批次发送失败 [{report_type}]，错误：{result.get('description')}"
                    )
                    return False
            else:
                print(
                    f"Telegram第 {i}/{len(batches)} 批次发送失败 [{report_type}]，状态码：{response.status_code}"
                )
                return False
        except Exception as e:
            print(f"Telegram第 {i}/{len(batches)} 批次发送出错 [{report_type}]：{e}")
            return False

    print(f"Telegram所有 {len(batches)} 批次发送完成 [{report_type}]")
    return True