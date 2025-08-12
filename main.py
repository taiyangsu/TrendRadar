    def _send_notification_if_needed(
        self,
        stats: List[Dict],
        report_type: str,
        mode: str,
        failed_ids: Optional[List] = None,
        new_titles: Optional[Dict] = None,
        id_to_name: Optional[Dict] = None,
    ) -> bool:
        """统一的通知发送逻辑，包含所有判断条件"""
        has_webhook = self._has_webhook_configured()

        if (
            CONFIG["ENABLE_NOTIFICATION"]
            and has_webhook
            and self._has_valid_content(stats, new_titles)
        ):
            send_to_webhooks(
                stats,
                failed_ids or [],
                report_type,
                new_titles,
                id_to_name,
                self.update_info,
                self.proxy_url,
                mode=mode,
            )
            return True
        elif CONFIG["ENABLE_NOTIFICATION"] and not has_webhook:
            print("⚠️ 警告：通知功能已启用但未配置webhook URL，将跳过通知发送")
        elif not CONFIG["ENABLE_NOTIFICATION"]:
            print(f"跳过{report_type}通知：通知功能已禁用")
        elif (
            CONFIG["ENABLE_NOTIFICATION"]
            and has_webhook
            and not self._has_valid_content(stats, new_titles)
        ):
            mode_strategy = self._get_mode_strategy()
            if "实时" in report_type:
                print(
                    f"跳过实时推送通知：{mode_strategy['mode_name']}下未检测到匹配的新闻"
                )
            else:
                print(
                    f"跳过{mode_strategy['summary_report_type']}通知：未匹配到有效的新闻内容"
                )

        return False