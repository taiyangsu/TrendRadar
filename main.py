    def _has_valid_content(
        self, stats: List[Dict], new_titles: Optional[Dict] = None
    ) -> bool:
        """检查是否有有效的新闻内容"""
        if self.report_mode == "incremental":
            # 增量模式下，只要stats有内容就说明有匹配的新闻
            return any(stat["count"] > 0 for stat in stats)
        elif self.report_mode == "current":
            # current模式下，允许以下情况触发推送：
            # 1. 有匹配的频率词新闻 (stats > 0)
            # 2. 有新增新闻 (new_titles 有内容)
            # 3. 即使是空集，也允许发送"暂无匹配"的提示
            has_matched_news = any(stat["count"] > 0 for stat in stats)
            has_new_news = bool(
                new_titles and any(len(titles) > 0 for titles in new_titles.values())
            )
            # 在current模式下，即使没有匹配内容，也允许发送空集提示
            return True  # 总是允许发送，让后续逻辑决定具体内容
        else:
            # 当日汇总模式下，检查是否有匹配的频率词新闻或新增新闻
            has_matched_news = any(stat["count"] > 0 for stat in stats)
            has_new_news = bool(
                new_titles and any(len(titles) > 0 for titles in new_titles.values())
            )
            return has_matched_news or has_new_news